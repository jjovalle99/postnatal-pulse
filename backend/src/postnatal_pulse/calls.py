from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from uuid import UUID, uuid4


class CallSessionNotFoundError(LookupError):
    pass


@dataclass(frozen=True, slots=True)
class CallSession:
    id: UUID
    source: str
    scenario_id: str | None
    started_at: datetime
    phase: str
    ended_at: datetime | None = None
    audio_frames_received: int = 0
    probe_answers: tuple[str, str, str] | None = None
    triage_state: str | None = None
    dismissed_flag_ids: tuple[UUID, ...] = ()
    dismissed_reason: str | None = None


@dataclass(slots=True)
class CallRegistry:
    calls: dict[UUID, CallSession] = field(default_factory=dict)


def create_call_session(source: str, scenario_id: str | None) -> CallSession:
    return CallSession(
        id=uuid4(),
        source=source,
        scenario_id=scenario_id,
        started_at=datetime.now(UTC),
        phase="connecting",
    )


def store_call(registry: CallRegistry, call: CallSession) -> CallSession:
    registry.calls[call.id] = call
    return call


def get_call(registry: CallRegistry, call_id: UUID) -> CallSession:
    try:
        return registry.calls[call_id]
    except KeyError as error:
        raise CallSessionNotFoundError(str(call_id)) from error


def update_call_probes(
    registry: CallRegistry,
    call_id: UUID,
    answers: tuple[str, str, str],
    triage_state: str,
) -> CallSession:
    updated_call = replace(
        get_call(registry, call_id),
        probe_answers=answers,
        triage_state=triage_state,
    )
    registry.calls[call_id] = updated_call
    return updated_call


def increment_audio_frames(registry: CallRegistry, call_id: UUID) -> CallSession:
    call = get_call(registry, call_id)
    updated_call = replace(
        call,
        audio_frames_received=call.audio_frames_received + 1,
    )
    registry.calls[call_id] = updated_call
    return updated_call


def end_call(registry: CallRegistry, call_id: UUID) -> CallSession:
    updated_call = replace(
        get_call(registry, call_id),
        phase="ended",
        ended_at=datetime.now(UTC),
    )
    registry.calls[call_id] = updated_call
    return updated_call


def dismiss_flag(
    registry: CallRegistry,
    call_id: UUID,
    flag_id: UUID,
    triage_state: str,
    reason: str,
) -> CallSession:
    updated_call = replace(
        get_call(registry, call_id),
        triage_state=triage_state,
        dismissed_flag_ids=(*get_call(registry, call_id).dismissed_flag_ids, flag_id),
        dismissed_reason=reason,
    )
    registry.calls[call_id] = updated_call
    return updated_call


def get_latest_call(registry: CallRegistry) -> CallSession:
    if len(registry.calls) == 0:
        raise CallSessionNotFoundError("latest")

    return max(
        registry.calls.values(),
        key=lambda call: call.started_at,
    )
