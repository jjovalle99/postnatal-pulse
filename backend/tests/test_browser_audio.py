from urllib.parse import urlparse

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from postnatal_pulse.main import app


async def test_start_browser_call_returns_websocket_url() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/calls",
                headers={"X-API-Key": "dev-api-key"},
                json={"source": "browser"},
            )

    assert response.status_code == 201
    ws_url = response.json()["ws_url"]
    assert ws_url is not None
    parsed_url = urlparse(ws_url)
    assert parsed_url.path == "/ws/audio/browser"
    assert "token=" in parsed_url.query


async def test_browser_audio_websocket_accepts_binary_frames() -> None:
    async with LifespanManager(app):
        async with ASGIWebSocketTransport(app=app) as transport:
            async with AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    "/api/calls",
                    headers={"X-API-Key": "dev-api-key"},
                    json={"source": "browser"},
                )
                ws_url = response.json()["ws_url"]
                assert ws_url is not None

                async with aconnect_ws(ws_url, client) as websocket:
                    await websocket.send_bytes(b"\x00\x01\x02\x03")
