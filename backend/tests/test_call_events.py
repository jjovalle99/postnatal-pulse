from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from postnatal_pulse.main import app


async def test_fixture_call_events_stream_ends_with_end_event() -> None:
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

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: end" in stream_body


async def test_scenario_a_events_include_triage_transcript_flag_and_rationale() -> None:
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

    assert response.status_code == 200
    assert "event: triage" in stream_body
    assert '"state":"green"' in stream_body
    assert "event: transcript" in stream_body
    assert "I’m fine. Honestly. I’m fine." in stream_body
    assert "event: flag" in stream_body
    assert '"kind":"minimization"' in stream_body
    assert "event: rationale_done" in stream_body
    assert '"confidence":"High"' in stream_body
    assert "event: end" in stream_body


async def test_fixture_call_events_accept_api_key_query_param() -> None:
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
                f"/api/calls/{call_id}/events?api_key=dev-api-key",
                headers={"Accept": "text/event-stream"},
            ) as response:
                stream_body = ""
                async for line in response.aiter_lines():
                    stream_body += f"{line}\n"

    assert response.status_code == 200
    assert "event: end" in stream_body
