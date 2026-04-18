import re

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from postnatal_pulse.main import app


FLAG_ID_PATTERN = re.compile(r'"flag_id":"([^"]+)"')


async def test_generate_handoff_pdf_returns_signed_download() -> None:
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

            flag_id_match = FLAG_ID_PATTERN.search(stream_body)
            assert flag_id_match is not None

            await client.post(
                f"/api/calls/{call_id}/probes",
                headers={"X-API-Key": "dev-api-key"},
                json={
                    "flag_id": flag_id_match.group(1),
                    "answers": ["Hardly ever", "Not really", "Mostly on my own"],
                },
            )

            pdf_response = await client.post(
                f"/api/calls/{call_id}/handoff",
                headers={"X-API-Key": "dev-api-key"},
            )

            assert pdf_response.status_code == 200
            pdf_payload = pdf_response.json()
            assert pdf_payload["preview_url"] == pdf_payload["download_url"]

            download_response = await client.get(pdf_payload["download_url"])

    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/pdf"
    assert download_response.content.startswith(b"%PDF")
