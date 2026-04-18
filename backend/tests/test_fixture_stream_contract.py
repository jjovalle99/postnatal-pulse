"""Fixture SSE contract: biomarker, concordance_trace, rationale_token.

Spec references: SPEC §3.2 (AN-03 concordance_ribbon_traces, AN-05 LLM rationale
stream), §5.2 SSE Event Contract, §5.4 Fixture Contract.
"""

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from postnatal_pulse.main import app


async def _fetch_scenario_stream(scenario_id: str) -> str:
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            start_response = await client.post(
                "/api/calls",
                headers={"X-API-Key": "dev-api-key"},
                json={"source": "fixture", "scenario_id": scenario_id},
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

    return stream_body


async def test_scenario_a_stream_emits_biomarker_and_concordance_trace() -> None:
    stream_body = await _fetch_scenario_stream("A")

    assert "event: biomarker" in stream_body
    assert '"layer":"helios"' in stream_body
    assert '"layer":"apollo"' in stream_body
    assert '"layer":"psyche"' in stream_body
    assert "event: concordance_trace" in stream_body
    assert '"transcript_min"' in stream_body
    assert '"acoustic_strain"' in stream_body


async def test_scenario_a_stream_emits_rationale_token_stream_then_done() -> None:
    stream_body = await _fetch_scenario_stream("A")

    token_index = stream_body.find("event: rationale_token")
    done_index = stream_body.find("event: rationale_done")

    assert token_index != -1, "rationale_token events must fire for a flagged scenario"
    assert done_index != -1, "rationale_done must follow rationale_token"
    assert token_index < done_index, "tokens must arrive before the done event"
    assert '"driver_index":0' in stream_body
    assert '"driver_index":2' in stream_body


async def test_scenario_c_stream_does_not_emit_flag_or_rationale_events() -> None:
    stream_body = await _fetch_scenario_stream("C")

    assert "event: flag" not in stream_body
    assert "event: rationale_token" not in stream_body
    assert "event: rationale_done" not in stream_body
    assert "event: biomarker" in stream_body
    assert "event: concordance_trace" in stream_body
