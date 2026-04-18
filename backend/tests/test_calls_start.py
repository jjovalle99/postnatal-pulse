from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from postnatal_pulse.main import app


async def test_start_fixture_call_requires_scenario_id() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/calls",
                headers={"X-API-Key": "dev-api-key"},
                json={"source": "fixture"},
            )

    assert response.status_code == 400
    assert response.json() == {"detail": "scenario_id required"}


async def test_start_fixture_call_returns_call_urls() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.post(
                "/api/calls",
                headers={"X-API-Key": "dev-api-key"},
                json={"source": "fixture", "scenario_id": "A"},
            )

    assert response.status_code == 201
    response_json = response.json()
    call_id = response_json["call_id"]
    assert response_json == {
        "call_id": call_id,
        "sse_url": f"/api/calls/{call_id}/events",
        "ws_url": None,
    }
