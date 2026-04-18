import base64
import json
import asyncio

from asgi_lifespan import LifespanManager
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from postnatal_pulse.main import app


async def test_twilio_media_websocket_accepts_start_media_and_stop_events() -> None:
    async with LifespanManager(app):
        async with ASGIWebSocketTransport(app=app) as transport:
            async with AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                async with aconnect_ws("http://testserver/ws/twilio/media", client) as websocket:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "start",
                                "start": {
                                    "callSid": "CA123",
                                    "streamSid": "MZ123",
                                },
                            }
                        )
                    )
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "media",
                                "media": {
                                    "track": "inbound",
                                    "payload": base64.b64encode(b"\xff" * 160).decode("ascii"),
                                },
                            }
                        )
                    )
                    await asyncio.sleep(0.2)
                    await websocket.send_text(
                        json.dumps(
                            {
                                "event": "stop",
                                "stop": {
                                    "callSid": "CA123",
                                    "streamSid": "MZ123",
                                },
                            }
                        )
                    )

        dependencies = app.state.dependencies
        calls = list(dependencies.call_registry.calls.values())
        assert len(calls) == 1
        assert calls[0].source == "twilio"
        assert calls[0].audio_frames_received == 1
        assert calls[0].phase == "ended"
