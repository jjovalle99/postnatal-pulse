from collections.abc import Callable
from dataclasses import dataclass, field
import asyncio
from typing import Optional
from uuid import uuid4

from speechmatics.rt import ServerMessageType

from postnatal_pulse.live_analysis import SpeechmaticsMessage
from postnatal_pulse.live_session import (
    LiveProviderSession,
    SentinelAdapter,
    SpeechmaticsAdapter,
)
from postnatal_pulse.live_runtime import LiveCallRuntime


@dataclass
class FakeSpeechmaticsClient:
    handlers: dict[ServerMessageType, Callable[[SpeechmaticsMessage], None]] = field(default_factory=dict)
    started: bool = False
    audio_frames: list[bytes] = field(default_factory=list)
    closed: bool = False

    def on(
        self,
        event: ServerMessageType,
        callback: Optional[Callable[[SpeechmaticsMessage], None]] = None,
    ) -> Callable[[SpeechmaticsMessage], None]:
        assert callback is not None
        self.handlers[event] = callback
        return callback

    async def start_session(self, **_: object) -> None:
        self.started = True

    async def send_audio(self, payload: bytes) -> None:
        self.audio_frames.append(payload)

    async def close(self) -> None:
        self.closed = True


@dataclass
class FakeSentinelClient:
    connected: bool = False
    user_audio: list[bytes] = field(default_factory=list)
    agent_audio: list[bytes] = field(default_factory=list)
    user_transcripts: list[tuple[str, bool]] = field(default_factory=list)
    agent_transcripts: list[tuple[str, bool]] = field(default_factory=list)
    closed: bool = False

    async def connect(self) -> None:
        self.connected = True

    async def send_user_audio(self, audio_data: bytes) -> None:
        self.user_audio.append(audio_data)

    async def send_agent_audio(self, audio_data: bytes) -> None:
        self.agent_audio.append(audio_data)

    async def send_user_transcript(self, text: str, is_final: bool = True) -> None:
        self.user_transcripts.append((text, is_final))

    async def send_agent_transcript(self, text: str, is_final: bool = True) -> None:
        self.agent_transcripts.append((text, is_final))

    async def close(self) -> None:
        self.closed = True


async def test_live_provider_session_starts_forwards_audio_and_emits_transcript() -> None:
    speechmatics_client = FakeSpeechmaticsClient()
    sentinel_client = FakeSentinelClient()
    runtime = LiveCallRuntime(call_id=uuid4())
    session = LiveProviderSession(
        runtime=runtime,
        speechmatics=SpeechmaticsAdapter(
            register_handler=speechmatics_client.on,
            start_session=speechmatics_client.start_session,
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

    await session.start()
    await session.push_audio(b"\x00\x01", track="user")
    speechmatics_client.handlers[ServerMessageType.ADD_TRANSCRIPT](
        {
            "message": "AddTranscript",
            "metadata": {"transcript": "Hello there", "start_time": 2.0},
            "results": [
                {
                    "alternatives": [
                        {
                            "content": "Hello",
                            "confidence": 0.98,
                            "speaker": "speaker-a",
                        }
                    ]
                }
            ],
        }
    )
    await asyncio.sleep(0)
    await session.close()

    drained = await runtime.drain_pending()

    assert speechmatics_client.started is True
    assert sentinel_client.connected is True
    assert speechmatics_client.audio_frames == [b"\x00\x01"]
    assert sentinel_client.user_audio == [b"\x00\x01"]
    assert sentinel_client.agent_transcripts == [("Hello there", True)]
    assert drained[0] == ("triage", {"t": 0, "state": "green", "source": "pre-flag", "flag_id": None})
    assert ("transcript", {"t": 2.0, "speaker": "Clinician", "text": "Hello there", "is_final": True, "confidence": 0.98}) in drained
