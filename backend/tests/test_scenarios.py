from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from postnatal_pulse.main import app


async def test_get_scenarios_returns_fixture_metadata() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get(
                "/api/scenarios",
                headers={"X-API-Key": "dev-api-key"},
            )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "A",
            "label": "Scenario A — Minimizing exhaustion",
            "duration_seconds": 240,
            "has_flag": True,
            "flag_at_t": 134,
            "audio_url": "/assets/tts/scenario-a.wav",
        },
        {
            "id": "B",
            "label": "Scenario B — Open distress",
            "duration_seconds": 210,
            "has_flag": True,
            "flag_at_t": 92,
            "audio_url": "/assets/tts/scenario-b.wav",
        },
        {
            "id": "C",
            "label": "Scenario C — Stable recovery",
            "duration_seconds": 200,
            "has_flag": False,
            "flag_at_t": None,
            "audio_url": "/assets/tts/scenario-c.wav",
        },
    ]
