from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from postnatal_pulse.main import app


async def test_end_call_returns_summary() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            start_response = await client.post(
                "/api/calls",
                headers={"X-API-Key": "dev-api-key"},
                json={"source": "fixture", "scenario_id": "A"},
            )

            response = await client.post(
                f"/api/calls/{start_response.json()['call_id']}/end",
                headers={"X-API-Key": "dev-api-key"},
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["call_id"] == start_response.json()["call_id"]
    assert payload["duration_seconds"] >= 0
    assert payload["summary"] == {
        "source": "fixture",
        "scenario_id": "A",
    }
