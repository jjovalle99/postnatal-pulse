import re

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from postnatal_pulse.main import app


FLAG_ID_PATTERN = re.compile(r'"flag_id":"([^"]+)"')


async def test_save_probe_responses_reclassifies_scenario_a_to_red() -> None:
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
            call_id = start_response.json()["call_id"]

            async with client.stream(
                "GET",
                f"/api/calls/{call_id}/events",
                headers={
                    "Accept": "text/event-stream",
                    "X-API-Key": "dev-api-key",
                },
            ) as response:
                stream_body = ""
                async for line in response.aiter_lines():
                    stream_body += f"{line}\n"

            flag_id_match = FLAG_ID_PATTERN.search(stream_body)
            assert flag_id_match is not None
            flag_id = flag_id_match.group(1)

            response = await client.post(
                f"/api/calls/{call_id}/probes",
                headers={"X-API-Key": "dev-api-key"},
                json={
                    "flag_id": flag_id,
                    "answers": ["Hardly ever", "Not really", "Mostly on my own"],
                },
            )

    assert response.status_code == 200
    assert response.json()["triage"]["state"] == "red"
    assert response.json()["flag"]["flag_id"] == flag_id
