from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from postnatal_pulse.main import app


async def test_get_latest_call_returns_most_recent_active_call() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            await client.post(
                "/api/calls",
                headers={"X-API-Key": "dev-api-key"},
                json={"source": "fixture", "scenario_id": "A"},
            )
            second = await client.post(
                "/api/calls",
                headers={"X-API-Key": "dev-api-key"},
                json={"source": "browser"},
            )

            response = await client.get(
                "/api/calls/latest",
                headers={"X-API-Key": "dev-api-key"},
            )

    assert response.status_code == 200
    assert response.json() == {
        "call_id": second.json()["call_id"],
        "source": "browser",
        "phase": "connecting",
        "sse_url": f"/api/calls/{second.json()['call_id']}/events",
    }
