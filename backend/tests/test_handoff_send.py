import re
from importlib import import_module

from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from pytest import MonkeyPatch

from postnatal_pulse.main import app


FLAG_ID_PATTERN = re.compile(r'"flag_id":"([^"]+)"')


async def test_send_handoff_sms_returns_dispatch_metadata(
    monkeypatch: MonkeyPatch,
) -> None:
    async def fake_send_sms(
        recipient_phone: str,
        body: str,
        status_callback_url: str | None,
    ) -> str:
        assert recipient_phone == "+12065550199"
        assert "Postnatal Pulse" in body
        assert status_callback_url == "http://testserver/twilio/sms-status"
        return "SM123"

    main_module = import_module("postnatal_pulse.main")
    monkeypatch.setattr(main_module, "send_sms_message", fake_send_sms)

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
            pdf_id = pdf_response.json()["pdf_id"]

            response = await client.post(
                f"/api/calls/{call_id}/handoff/{pdf_id}/send",
                headers={"X-API-Key": "dev-api-key"},
                json={"recipient_phone": "+12065550199"},
            )

    assert response.status_code == 202
    payload = response.json()
    assert payload["sms_id"] == "SM123"
    assert payload["signed_download_url"].startswith("/api/pdfs/")
