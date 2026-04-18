import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from speechmatics.rt import AsyncClient as SpeechmaticsAsyncClient
from speechmatics.rt import ServerMessageType
from thymia_sentinel import SentinelClient
from thymia_sentinel.models import PolicyResult, ProgressResult

from postnatal_pulse.config import AppSettings
from postnatal_pulse.live_analysis import (
    LiveSpeakerState,
    SpeechmaticsMessage,
    normalize_speechmatics_message,
)
from postnatal_pulse.live_providers import (
    build_speechmatics_audio_format,
    build_speechmatics_transcription_config,
)
from postnatal_pulse.live_runtime import LiveCallRuntime


@dataclass(frozen=True, slots=True)
class SpeechmaticsAdapter:
    register_handler: Callable[[ServerMessageType, Callable[[SpeechmaticsMessage], None]], object]
    start_session: Callable[[], Awaitable[None]]
    send_audio: Callable[[bytes], Awaitable[None]]
    close: Callable[[], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class SentinelAdapter:
    connect: Callable[[], Awaitable[None]]
    send_user_audio: Callable[[bytes], Awaitable[None]]
    send_agent_audio: Callable[[bytes], Awaitable[None]]
    send_user_transcript: Callable[[str, bool], Awaitable[None]]
    send_agent_transcript: Callable[[str, bool], Awaitable[None]]
    close: Callable[[], Awaitable[None]]


@dataclass(slots=True)
class LiveProviderSession:
    runtime: LiveCallRuntime
    speechmatics: SpeechmaticsAdapter
    sentinel: SentinelAdapter
    speaker_state: LiveSpeakerState = field(default_factory=LiveSpeakerState)
    started: bool = False

    async def start(self) -> None:
        if self.started:
            return

        def on_final(message: SpeechmaticsMessage) -> None:
            asyncio.create_task(self._handle_transcript(message))

        def on_partial(message: SpeechmaticsMessage) -> None:
            asyncio.create_task(self._handle_transcript(message))

        self.speechmatics.register_handler(ServerMessageType.ADD_TRANSCRIPT, on_final)
        self.speechmatics.register_handler(ServerMessageType.ADD_PARTIAL_TRANSCRIPT, on_partial)
        await self.speechmatics.start_session()
        await self.sentinel.connect()
        await self.runtime.publish_initial_triage()
        self.started = True

    async def push_audio(self, payload: bytes, track: str) -> None:
        await self.speechmatics.send_audio(payload)
        if track == "agent":
            await self.sentinel.send_agent_audio(payload)
        else:
            await self.sentinel.send_user_audio(payload)

    async def close(self) -> None:
        await self.speechmatics.close()
        await self.sentinel.close()
        await self.runtime.event_buffer.close()

    async def _handle_transcript(self, message: SpeechmaticsMessage) -> None:
        transcript_event = normalize_speechmatics_message(
            message,
            self.speaker_state,
        )
        await self.runtime.event_buffer.publish("transcript", transcript_event)
        transcript_text = transcript_event["text"]
        is_final = transcript_event["is_final"]
        speaker = transcript_event["speaker"]
        if not isinstance(transcript_text, str) or not isinstance(is_final, bool) or not isinstance(speaker, str):
            return

        if speaker == "Clinician":
            await self.sentinel.send_agent_transcript(
                transcript_text,
                is_final,
            )
        else:
            await self.sentinel.send_user_transcript(
                transcript_text,
                is_final,
            )

    async def handle_policy_result(self, policy_result: PolicyResult) -> None:
        await self.runtime.handle_reasoner_result(policy_result)


    async def handle_progress_result(self, progress_result: ProgressResult) -> None:
        timestamp = progress_result["timestamp"] if "timestamp" in progress_result else 0.0
        await self.runtime.event_buffer.publish(
            "system",
            {
                "kind": "signal_progress",
                "timestamp": timestamp,
            },
        )


def create_live_provider_session(
    settings: AppSettings,
    runtime: LiveCallRuntime,
) -> LiveProviderSession:
    session_holder: dict[str, LiveProviderSession] = {}

    async def on_policy_result(policy_result: PolicyResult) -> None:
        await session_holder["session"].handle_policy_result(policy_result)

    async def on_progress_result(progress_result: ProgressResult) -> None:
        await session_holder["session"].handle_progress_result(progress_result)

    speechmatics_client = SpeechmaticsAsyncClient(
        api_key=settings.speechmatics_api_key,
        url=settings.speechmatics_rt_url,
    )
    sentinel_client = SentinelClient(
        language="en-GB",
        policies=["wellbeing-awareness", "passthrough"],
        biomarkers=["helios", "apollo", "psyche"],
        on_policy_result=on_policy_result,
        on_progress_result=on_progress_result,
        progress_updates_frequency=1.0,
        sample_rate=16000,
        server_url=settings.thymia_server_url,
        api_key=settings.thymia_api_key,
    )
    session = LiveProviderSession(
        runtime=runtime,
        speechmatics=SpeechmaticsAdapter(
            register_handler=speechmatics_client.on,
            start_session=lambda: speechmatics_client.start_session(
                transcription_config=build_speechmatics_transcription_config(),
                audio_format=build_speechmatics_audio_format(),
            ),
            send_audio=speechmatics_client.send_audio,
            close=speechmatics_client.close,
        ),
        sentinel=SentinelAdapter(
            connect=sentinel_client.connect,
            send_user_audio=sentinel_client.send_user_audio,
            send_agent_audio=sentinel_client.send_agent_audio,
            send_user_transcript=sentinel_client.send_user_transcript,
            send_agent_transcript=sentinel_client.send_agent_transcript,
            close=sentinel_client.close,
        ),
    )
    session_holder["session"] = session
    return session
