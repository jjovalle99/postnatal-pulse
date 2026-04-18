import asyncio
import audioop
import base64
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
import json
from typing import Annotated
from uuid import NAMESPACE_URL, UUID, uuid5

import jwt
import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, Path, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import Response
from fastapi import WebSocket, WebSocketDisconnect
from sse_starlette import EventSourceResponse
from starlette.requests import HTTPConnection
from twilio.request_validator import RequestValidator
import ulid

from postnatal_pulse.calls import (
    CallRegistry,
    CallSessionNotFoundError,
    create_call_session,
    dismiss_flag,
    end_call,
    get_call,
    get_latest_call,
    increment_audio_frames,
    store_call,
    update_call_probes,
)
from postnatal_pulse.config import AppSettings, get_settings
from postnatal_pulse.fixtures import SCENARIO_FIXTURES, ScenarioFixture, get_scenario_fixture
from postnatal_pulse.live_runtime import LiveCallRuntime
from postnatal_pulse.live_session import LiveProviderSession, create_live_provider_session
from postnatal_pulse.pdfs import (
    PdfRegistry,
    create_signed_download_url,
    get_pdf_artifact,
    render_handoff_pdf,
    store_pdf_artifact,
    update_pdf_sms_delivery,
    update_pdf_sms_dispatch,
    verify_pdf_download_signature,
)


class HealthzResponse(BaseModel):
    version: str
    db_pool_state: str
    sentinel_status: str
    speechmatics_status: str


class ScenarioSummaryResponse(BaseModel):
    id: str
    label: str
    duration_seconds: int
    has_flag: bool
    flag_at_t: int | None
    audio_url: str


class StartCallRequest(BaseModel):
    source: str
    scenario_id: str | None = None


class StartCallResponse(BaseModel):
    call_id: UUID
    sse_url: str
    ws_url: str | None


class LatestCallResponse(BaseModel):
    call_id: UUID
    source: str
    phase: str
    sse_url: str


class SaveProbesRequest(BaseModel):
    flag_id: UUID
    answers: list[str]


class EndEventResponse(BaseModel):
    call_id: UUID
    duration_seconds: int
    summary: dict[str, str]


class TriageEventResponse(BaseModel):
    t: int
    state: str
    source: str
    flag_id: UUID | None


class TranscriptEventResponse(BaseModel):
    t: int
    speaker: str
    text: str
    is_final: bool
    confidence: float | None


type DeterministicPayloadValue = str | int | bool | None | list[str]


class FlagEventResponse(BaseModel):
    flag_id: UUID
    kind: str
    t: int
    contributing_signals: list[str]
    deterministic_payload: dict[str, DeterministicPayloadValue]


class RationaleDoneEventResponse(BaseModel):
    flag_id: UUID
    drivers: list[str]
    confidence: str


class SaveProbesResponse(BaseModel):
    triage: TriageEventResponse
    flag: FlagEventResponse


class GenerateHandoffResponse(BaseModel):
    pdf_id: UUID
    preview_url: str
    download_url: str


class DismissFlagRequest(BaseModel):
    reason: str


class DismissFlagResponse(BaseModel):
    triage: TriageEventResponse
    flag: FlagEventResponse


class EndCallResponse(BaseModel):
    call_id: UUID
    ended_at: datetime
    duration_seconds: int
    summary: dict[str, str]


class SendHandoffRequest(BaseModel):
    recipient_phone: str


class SendHandoffResponse(BaseModel):
    sms_id: str
    dispatched_at: datetime
    signed_download_url: str
    expires_at: datetime


PROBE_SCORES = (
    {
        "Most days": 0,
        "Most days I rest": 0,
        "Some days": 1,
        "Hardly ever": 2,
    },
    {
        "Yes, mostly": 0,
        "Sometimes": 1,
        "Not really": 2,
        "Often": 2,
    },
    {
        "Yes": 0,
        "Plenty of support": 0,
        "Somewhat": 1,
        "Some help": 1,
        "No": 2,
        "Mostly on my own": 2,
    },
)


@dataclass(frozen=True, slots=True)
class AppDependencies:
    call_registry: CallRegistry
    live_provider_sessions: dict[UUID, LiveProviderSession]
    live_runtimes: dict[UUID, LiveCallRuntime]
    pdf_registry: PdfRegistry
    twilio_stream_call_ids: dict[str, UUID]
    settings: AppSettings
    version: str
    db_pool_state: str
    sentinel_status: str
    speechmatics_status: str


def create_dependencies() -> AppDependencies:
    return AppDependencies(
        call_registry=CallRegistry(),
        live_provider_sessions={},
        live_runtimes={},
        pdf_registry=PdfRegistry(),
        twilio_stream_call_ids={},
        settings=get_settings(),
        version=version("postnatal-pulse"),
        db_pool_state="not_connected",
        sentinel_status="not_configured",
        speechmatics_status="not_configured",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.dependencies = create_dependencies()
    yield


def get_dependencies(connection: HTTPConnection) -> AppDependencies:
    return connection.app.state.dependencies


ApiKeyHeader = Annotated[str | None, Header(alias="X-API-Key")]
ApiKeyQuery = Annotated[str | None, Query(alias="api_key")]


def require_api_key(
    request: Request,
    x_api_key: ApiKeyHeader = None,
    api_key: ApiKeyQuery = None,
) -> AppDependencies:
    dependencies = get_dependencies(request)
    provided_api_key = x_api_key if x_api_key is not None else api_key
    if provided_api_key != dependencies.settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return dependencies


AuthenticatedDependencies = Annotated[AppDependencies, Depends(require_api_key)]


def to_scenario_summary_response(
    scenario: ScenarioFixture,
) -> ScenarioSummaryResponse:
    return ScenarioSummaryResponse(
        id=scenario.id,
        label=scenario.label,
        duration_seconds=scenario.duration_seconds,
        has_flag=scenario.has_flag,
        flag_at_t=scenario.flag_at_t,
        audio_url=scenario.audio_url,
    )


def create_sse_event(
    event: str,
    payload: BaseModel,
) -> dict[str, str]:
    return {
        "event": event,
        "id": str(ulid.new()),
        "data": payload.model_dump_json(),
    }


def get_flag_id_for_scenario(scenario: ScenarioFixture) -> UUID | None:
    if scenario.flag_kind is None or scenario.flag_at_t is None:
        return None

    return uuid5(NAMESPACE_URL, f"postnatal-pulse:{scenario.id}:flag")


def score_probe_answers(answers: list[str]) -> int:
    total_score = 0
    for index, answer in enumerate(answers):
        try:
            total_score += PROBE_SCORES[index][answer]
        except KeyError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"invalid answer for probe {index}",
            ) from error

    return total_score


def create_browser_audio_token(call_id: UUID, settings: AppSettings) -> str:
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    return jwt.encode(
        {
            "call_id": str(call_id),
            "source": "browser",
            "exp": int(expires_at.timestamp()),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )


def decode_browser_audio_token(token: str, settings: AppSettings) -> UUID:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as error:
        raise ValueError("invalid browser audio token") from error

    return UUID(str(payload["call_id"]))


def get_triage_label(triage_state: str | None) -> str:
    if triage_state == "red":
        return "Red: urgent review"
    if triage_state == "amber":
        return "Amber: review"
    if triage_state == "green":
        return "Green: routine"

    return "Awaiting call"


def build_call_summary(scenario: ScenarioFixture) -> dict[str, str]:
    return {
        "source": "fixture",
        "scenario_id": scenario.id,
    }


def decode_twilio_mulaw_payload(payload: str) -> bytes:
    mulaw_audio = base64.b64decode(payload)
    pcm_8khz = audioop.ulaw2lin(mulaw_audio, 2)
    pcm_16khz, _ = audioop.ratecv(pcm_8khz, 2, 1, 8000, 16000, None)
    return pcm_16khz


def validate_twilio_request(request: Request, settings: AppSettings, form_data: dict[str, str]) -> None:
    signature = request.headers.get("X-Twilio-Signature")
    if signature is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid twilio signature",
        )

    validator = RequestValidator(settings.twilio_auth_token)
    if not validator.validate(str(request.url), form_data, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid twilio signature",
        )


def regress_triage_state(triage_state: str) -> str:
    if triage_state == "red":
        return "amber"
    if triage_state == "amber":
        return "green"
    return "green"


async def send_sms_message(
    recipient_phone: str,
    body: str,
    status_callback_url: str | None,
) -> str:
    from twilio.rest import Client

    settings = get_settings()
    client = Client(
        settings.twilio_account_sid,
        settings.twilio_auth_token,
    )

    def create_message() -> str:
        message = client.messages.create(
            body=body,
            from_=settings.twilio_phone_number,
            to=recipient_phone,
            status_callback=status_callback_url,
        )
        return str(message.sid)

    return await asyncio.to_thread(create_message)


def build_fixture_stream_events(
    call_id: UUID,
    scenario: ScenarioFixture,
) -> tuple[dict[str, str], ...]:
    events: list[dict[str, str]] = [
        create_sse_event(
            "triage",
            TriageEventResponse(
                t=0,
                state=scenario.triage_pre_flag,
                source="pre-flag",
                flag_id=None,
            ),
        ),
    ]
    flag_id = get_flag_id_for_scenario(scenario)
    flag_emitted = False

    for transcript_entry in scenario.transcript:
        events.append(
            create_sse_event(
                "transcript",
                TranscriptEventResponse(
                    t=transcript_entry.t,
                    speaker=transcript_entry.speaker,
                    text=transcript_entry.text,
                    is_final=True,
                    confidence=None,
                ),
            ),
        )
        if (
            scenario.flag_at_t is not None
            and transcript_entry.t >= scenario.flag_at_t
            and scenario.flag_kind is not None
            and flag_id is not None
            and not flag_emitted
        ):
            events.append(
                create_sse_event(
                    "flag",
                    FlagEventResponse(
                        flag_id=flag_id,
                        kind=scenario.flag_kind,
                        t=scenario.flag_at_t,
                        contributing_signals=list(scenario.contributing_signals),
                        deterministic_payload={
                            "scenario_id": scenario.id,
                            "flag_at_t": scenario.flag_at_t,
                            "has_flag": scenario.has_flag,
                            "contributing_signals": list(scenario.contributing_signals),
                        },
                    ),
                ),
            )
            events.append(
                create_sse_event(
                    "rationale_done",
                    RationaleDoneEventResponse(
                        flag_id=flag_id,
                        drivers=list(scenario.drivers),
                        confidence=scenario.confidence,
                    ),
                ),
            )
            events.append(
                create_sse_event(
                    "triage",
                    TriageEventResponse(
                        t=scenario.flag_at_t,
                        state=scenario.triage_post_flag,
                        source="post-flag",
                        flag_id=flag_id,
                    ),
                ),
            )
            flag_emitted = True

    events.append(
        create_sse_event(
            "end",
            EndEventResponse(
                call_id=call_id,
                duration_seconds=scenario.duration_seconds,
                summary=build_call_summary(scenario),
            ),
        ),
    )
    return tuple(events)


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", response_model=HealthzResponse)
    async def healthz(request: Request) -> HealthzResponse:
        dependencies = get_dependencies(request)
        return HealthzResponse(
            version=dependencies.version,
            db_pool_state=dependencies.db_pool_state,
            sentinel_status=dependencies.sentinel_status,
            speechmatics_status=dependencies.speechmatics_status,
        )

    @app.get("/api/scenarios", response_model=list[ScenarioSummaryResponse])
    async def get_scenarios(_: AuthenticatedDependencies) -> list[ScenarioSummaryResponse]:
        return [
            to_scenario_summary_response(scenario)
            for scenario in SCENARIO_FIXTURES.values()
        ]

    @app.get("/api/calls/latest", response_model=LatestCallResponse)
    async def get_latest_call_endpoint(
        _: AuthenticatedDependencies,
        request: Request,
    ) -> LatestCallResponse:
        try:
            call = get_latest_call(get_dependencies(request).call_registry)
        except CallSessionNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="call not found",
            ) from error

        return LatestCallResponse(
            call_id=call.id,
            source=call.source,
            phase=call.phase,
            sse_url=f"/api/calls/{call.id}/events",
        )

    @app.post("/api/calls", response_model=StartCallResponse, status_code=status.HTTP_201_CREATED)
    async def start_call(
        request: Request,
        request_body: StartCallRequest,
        dependencies: AuthenticatedDependencies,
    ) -> StartCallResponse:
        if request_body.source == "fixture" and request_body.scenario_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scenario_id required",
            )

        call = store_call(
            dependencies.call_registry,
            create_call_session(
                source=request_body.source,
                scenario_id=request_body.scenario_id,
            ),
        )
        if request_body.source != "fixture":
            dependencies.live_runtimes[call.id] = LiveCallRuntime(call_id=call.id)
        ws_url = None
        if request_body.source == "browser":
            token = create_browser_audio_token(call.id, dependencies.settings)
            ws_url = str(request.base_url.replace(path=f"ws/audio/browser?token={token}"))

        return StartCallResponse(
            call_id=call.id,
            sse_url=f"/api/calls/{call.id}/events",
            ws_url=ws_url,
        )

    @app.post("/api/calls/{call_id}/probes", response_model=SaveProbesResponse)
    async def save_probes(
        call_id: Annotated[UUID, Path()],
        request_body: SaveProbesRequest,
        dependencies: AuthenticatedDependencies,
    ) -> SaveProbesResponse:
        if len(request_body.answers) != 3:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="answers must contain exactly 3 items",
            )

        try:
            call = get_call(dependencies.call_registry, call_id)
        except CallSessionNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="call not found",
            ) from error

        scenario = get_scenario_fixture(call.scenario_id or "C")
        flag_id = get_flag_id_for_scenario(scenario)
        if (
            flag_id is None
            or scenario.flag_kind is None
            or scenario.flag_at_t is None
            or request_body.flag_id != flag_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="flag not found",
            )

        probe_score = score_probe_answers(request_body.answers)
        triage_state = "red" if probe_score >= 4 else scenario.triage_post_flag
        update_call_probes(
            dependencies.call_registry,
            call_id,
            (request_body.answers[0], request_body.answers[1], request_body.answers[2]),
            triage_state,
        )
        flag_response = FlagEventResponse(
            flag_id=flag_id,
            kind=scenario.flag_kind,
            t=scenario.flag_at_t,
            contributing_signals=list(scenario.contributing_signals),
            deterministic_payload={
                "scenario_id": scenario.id,
                "flag_at_t": scenario.flag_at_t,
                "has_flag": scenario.has_flag,
                "contributing_signals": list(scenario.contributing_signals),
                "probe_score": probe_score,
            },
        )
        triage_response = TriageEventResponse(
            t=scenario.flag_at_t,
            state=triage_state,
            source="post-probe",
            flag_id=flag_id,
        )
        return SaveProbesResponse(triage=triage_response, flag=flag_response)

    @app.post("/api/calls/{call_id}/handoff", response_model=GenerateHandoffResponse)
    async def generate_handoff(
        call_id: Annotated[UUID, Path()],
        dependencies: AuthenticatedDependencies,
    ) -> GenerateHandoffResponse:
        try:
            call = get_call(dependencies.call_registry, call_id)
        except CallSessionNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="call not found",
            ) from error

        scenario = get_scenario_fixture(call.scenario_id or "C")
        triage_label = get_triage_label(call.triage_state or scenario.triage_post_flag)
        pdf_bytes = render_handoff_pdf(
            call_id=call.id,
            scenario=scenario,
            triage_label=triage_label,
            probe_answers=call.probe_answers,
        )
        artifact = store_pdf_artifact(
            dependencies.pdf_registry,
            call_id,
            pdf_bytes,
        )
        signed_download_url = create_signed_download_url(
            artifact.id,
            dependencies.settings.pdf_signing_secret,
        )
        return GenerateHandoffResponse(
            pdf_id=artifact.id,
            preview_url=signed_download_url,
            download_url=signed_download_url,
        )

    @app.post("/api/calls/{call_id}/handoff/{pdf_id}/send", response_model=SendHandoffResponse, status_code=status.HTTP_202_ACCEPTED)
    async def send_handoff(
        request: Request,
        call_id: Annotated[UUID, Path()],
        pdf_id: Annotated[UUID, Path()],
        request_body: SendHandoffRequest,
        dependencies: AuthenticatedDependencies,
    ) -> SendHandoffResponse:
        try:
            call = get_call(dependencies.call_registry, call_id)
            artifact = get_pdf_artifact(dependencies.pdf_registry, pdf_id)
        except (CallSessionNotFoundError, KeyError) as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="handoff not found",
            ) from error

        if artifact.call_id != call.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="handoff not found",
            )

        signed_download_url = create_signed_download_url(
            pdf_id,
            dependencies.settings.pdf_signing_secret,
        )
        status_callback_url = str(request.url_for("twilio_sms_status"))
        body = (
            f"Postnatal Pulse {get_triage_label(call.triage_state)} summary: "
            f"{signed_download_url}"
        )
        sms_id = await send_sms_message(
            request_body.recipient_phone,
            body,
            status_callback_url,
        )
        updated_artifact = update_pdf_sms_dispatch(
            dependencies.pdf_registry,
            pdf_id,
            request_body.recipient_phone,
            sms_id,
            signed_download_url,
        )
        expires_at = datetime.fromtimestamp(
            int(updated_artifact.generated_at.timestamp()) + 7 * 24 * 60 * 60,
            UTC,
        )
        dispatched_at = updated_artifact.sms_dispatched_at
        if dispatched_at is None or updated_artifact.signed_download_url is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="handoff dispatch failed",
            )

        return SendHandoffResponse(
            sms_id=sms_id,
            dispatched_at=dispatched_at,
            signed_download_url=updated_artifact.signed_download_url,
            expires_at=expires_at,
        )

    @app.post("/api/calls/{call_id}/flags/{flag_id}/dismiss", response_model=DismissFlagResponse)
    async def dismiss_flag_endpoint(
        call_id: Annotated[UUID, Path()],
        flag_id: Annotated[UUID, Path()],
        request_body: DismissFlagRequest,
        dependencies: AuthenticatedDependencies,
    ) -> DismissFlagResponse:
        try:
            call = get_call(dependencies.call_registry, call_id)
        except CallSessionNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="call not found",
            ) from error

        scenario = get_scenario_fixture(call.scenario_id or "C")
        scenario_flag_id = get_flag_id_for_scenario(scenario)
        if (
            scenario_flag_id is None
            or scenario.flag_kind is None
            or scenario.flag_at_t is None
            or flag_id != scenario_flag_id
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="flag not found",
            )

        current_triage = call.triage_state or scenario.triage_post_flag
        next_triage = regress_triage_state(current_triage)
        dismiss_flag(
            dependencies.call_registry,
            call_id,
            flag_id,
            next_triage,
            request_body.reason,
        )
        return DismissFlagResponse(
            triage=TriageEventResponse(
                t=scenario.flag_at_t,
                state=next_triage,
                source="dismiss",
                flag_id=flag_id,
            ),
            flag=FlagEventResponse(
                flag_id=flag_id,
                kind=scenario.flag_kind,
                t=scenario.flag_at_t,
                contributing_signals=list(scenario.contributing_signals),
                deterministic_payload={
                    "scenario_id": scenario.id,
                    "dismissed_reason": request_body.reason,
                },
            ),
        )

    @app.post("/api/calls/{call_id}/end", response_model=EndCallResponse)
    async def end_call_endpoint(
        call_id: Annotated[UUID, Path()],
        dependencies: AuthenticatedDependencies,
    ) -> EndCallResponse:
        try:
            call = end_call(dependencies.call_registry, call_id)
        except CallSessionNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="call not found",
            ) from error

        scenario = get_scenario_fixture(call.scenario_id or "C")
        if call.ended_at is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="call did not end correctly",
            )

        return EndCallResponse(
            call_id=call.id,
            ended_at=call.ended_at,
            duration_seconds=max(
                0,
                int((call.ended_at - call.started_at).total_seconds()),
            ),
            summary=build_call_summary(scenario),
        )

    @app.get("/api/pdfs/{pdf_id}")
    async def get_pdf(
        pdf_id: Annotated[UUID, Path()],
        sig: Annotated[str, Query()],
        exp: Annotated[int, Query()],
        dependencies: Request,
    ) -> Response:
        settings = get_dependencies(dependencies).settings
        now = int(datetime.now(UTC).timestamp())
        if exp < now:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="signed url expired",
            )

        if not verify_pdf_download_signature(pdf_id, exp, sig, settings.pdf_signing_secret):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="invalid signature",
            )

        try:
            artifact = get_pdf_artifact(
                get_dependencies(dependencies).pdf_registry,
                pdf_id,
            )
        except KeyError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="pdf not found",
            ) from error

        return Response(
            artifact.storage_path.read_bytes(),
            media_type="application/pdf",
        )

    @app.post("/twilio/sms-status", name="twilio_sms_status")
    async def twilio_sms_status(request: Request) -> Response:
        form = await request.form()
        form_data: dict[str, str] = {}
        for key, value in form.items():
            if not isinstance(value, str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="unsupported twilio payload",
                )
            form_data[key] = value
        validate_twilio_request(request, get_settings(), form_data)
        update_pdf_sms_delivery(
            get_dependencies(request).pdf_registry,
            form_data.get("MessageSid", ""),
            form_data.get("MessageStatus") == "delivered",
        )
        return Response(status_code=status.HTTP_200_OK)

    @app.post("/twilio/voice")
    async def twilio_voice(request: Request) -> Response:
        form = await request.form()
        form_data: dict[str, str] = {}
        for key, value in form.items():
            if not isinstance(value, str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="unsupported twilio payload",
                )
            form_data[key] = value
        validate_twilio_request(request, get_settings(), form_data)
        stream_url = str(request.url.replace(path="/ws/twilio/media", query="")).replace(
            "http://",
            "ws://",
        ).replace("https://", "wss://")
        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response><Connect><Stream url="{stream_url}" /></Connect></Response>'
        )
        return Response(twiml, media_type="text/xml")

    @app.websocket("/ws/twilio/media")
    async def twilio_media_stream(websocket: WebSocket) -> None:
        dependencies = get_dependencies(websocket)
        current_call_id: UUID | None = None
        current_stream_sid: str | None = None

        await websocket.accept()
        try:
            while True:
                message = json.loads(await websocket.receive_text())
                if not isinstance(message, dict):
                    continue
                event_type = message.get("event")
                if event_type == "start":
                    start = message.get("start")
                    if not isinstance(start, dict):
                        continue
                    stream_sid = start.get("streamSid")
                    if not isinstance(stream_sid, str):
                        continue
                    current_stream_sid = stream_sid
                    call = store_call(
                        dependencies.call_registry,
                        create_call_session(source="twilio", scenario_id=None),
                    )
                    current_call_id = call.id
                    dependencies.twilio_stream_call_ids[stream_sid] = call.id
                    runtime = LiveCallRuntime(call_id=call.id)
                    dependencies.live_runtimes[call.id] = runtime
                    if dependencies.settings.live_provider_enabled:
                        session = create_live_provider_session(
                            dependencies.settings,
                            runtime,
                        )
                        await session.start()
                        dependencies.live_provider_sessions[call.id] = session
                elif event_type == "media" and current_call_id is not None:
                    media = message.get("media")
                    if not isinstance(media, dict):
                        continue
                    payload = media.get("payload")
                    if not isinstance(payload, str):
                        continue
                    track = media.get("track")
                    track_name = "agent" if track == "outbound" else "user"
                    pcm_audio = decode_twilio_mulaw_payload(payload)
                    increment_audio_frames(
                        dependencies.call_registry,
                        current_call_id,
                    )
                    session = dependencies.live_provider_sessions.get(current_call_id)
                    if session is not None:
                        await session.push_audio(pcm_audio, track=track_name)
                elif event_type == "stop":
                    if current_call_id is not None:
                        end_call(dependencies.call_registry, current_call_id)
                        session = dependencies.live_provider_sessions.get(current_call_id)
                        if session is not None:
                            await session.close()
                    if current_stream_sid is not None:
                        dependencies.twilio_stream_call_ids.pop(current_stream_sid, None)
                    return
        except WebSocketDisconnect:
            return

    @app.get("/api/calls/{call_id}/events")
    async def get_call_events(
        call_id: Annotated[UUID, Path()],
        dependencies: AuthenticatedDependencies,
    ) -> EventSourceResponse:
        try:
            call = get_call(dependencies.call_registry, call_id)
        except CallSessionNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="call not found",
            ) from error

        async def event_stream() -> AsyncIterator[dict[str, str]]:
            if call.source == "fixture":
                scenario = get_scenario_fixture(call.scenario_id or "C")
                for event in build_fixture_stream_events(call.id, scenario):
                    yield event
                return

            runtime = dependencies.live_runtimes.get(call.id)
            if runtime is None:
                return

            async for event_name, payload in runtime.event_buffer.stream():
                yield {
                    "event": event_name,
                    "id": str(ulid.new()),
                    "data": json.dumps(payload),
                }

        return EventSourceResponse(event_stream())

    @app.websocket("/ws/audio/browser")
    async def browser_audio_stream(
        websocket: WebSocket,
        token: str,
    ) -> None:
        try:
            call_id = decode_browser_audio_token(token, get_settings())
        except ValueError:
            await websocket.close(code=4401)
            return

        dependencies = get_dependencies(websocket)
        runtime = dependencies.live_runtimes.get(call_id)
        if runtime is None:
            await websocket.close(code=4404)
            return
        try:
            get_call(dependencies.call_registry, call_id)
        except CallSessionNotFoundError:
            await websocket.close(code=4404)
            return

        if (
            dependencies.settings.live_provider_enabled
            and call_id not in dependencies.live_provider_sessions
        ):
            session = create_live_provider_session(
                dependencies.settings,
                runtime,
            )
            await session.start()
            dependencies.live_provider_sessions[call_id] = session

        await websocket.accept()
        try:
            while True:
                payload = await websocket.receive_bytes()
                increment_audio_frames(dependencies.call_registry, call_id)
                session = dependencies.live_provider_sessions.get(call_id)
                if session is not None:
                    await session.push_audio(payload, track="user")
        except WebSocketDisconnect:
            return

    return app


app = create_app()


def main() -> None:
    uvicorn.run("postnatal_pulse.main:app", factory=False, reload=False)
