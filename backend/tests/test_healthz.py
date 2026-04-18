from importlib.metadata import version

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from postnatal_pulse.main import app


async def test_healthz_returns_service_statuses() -> None:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "version": version("postnatal-pulse"),
        "db_pool_state": "not_configured",
        "sentinel_status": "not_configured",
        "speechmatics_status": "not_configured",
    }
