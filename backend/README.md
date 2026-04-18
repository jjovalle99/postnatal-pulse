# Backend

FastAPI backend for Postnatal Pulse. It runs the call lifecycle, serves scenario replay, accepts browser and Twilio audio, streams live events to the UI, stores handoff artifacts, and dispatches SMS notifications through Twilio.

For the full product context, see the root [README.md](../README.md), [docs/PRD.md](../docs/PRD.md), and [docs/SPEC.md](../docs/SPEC.md).

## Local Development

```bash
uv sync
uv run fastapi run --app postnatal_pulse.main:app --host 0.0.0.0 --port 8000
```

Runs at [localhost:8000](http://localhost:8000). Configuration is loaded from the repo root `.env`. A starter file is available at [`../.env.example`](../.env.example).

## Configuration

The backend reads all settings from the repo root `.env`.

### Required backend settings

- `API_KEY`
- `JWT_SECRET`
- `PDF_SIGNING_SECRET`

### Optional backend settings

- `CORS_ALLOWED_ORIGINS`
- `LIVE_PROVIDER_ENABLED`
- `SPEECHMATICS_API_KEY`
- `SPEECHMATICS_RT_URL`
- `THYMIA_API_KEY`
- `THYMIA_SERVER_URL`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER`

The root [README.md](../README.md) explains what each value is and where to get provider credentials.

## Modules

| Module | Purpose |
|--------|---------|
| `main.py` | FastAPI entry point, REST API, SSE stream, browser audio WebSocket, Twilio webhooks |
| `fixtures.py` | Scenario catalog and deterministic transcript data |
| `calls.py` | In-memory call session registry and state transitions |
| `live_analysis.py` | Transcript normalization and alert-side transformation logic |
| `live_providers.py` | Provider configuration builders for Speechmatics and Thymia |
| `live_runtime.py` | Buffered live event state and streaming runtime helpers |
| `live_session.py` | Live provider orchestration for audio, transcript, biomarker, and policy events |
| `pdfs.py` | Handoff PDF rendering, storage, and signed download helpers |
| `config.py` | Environment-backed application settings |

## API Surface

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/healthz` | GET | Health and provider status |
| `/api/scenarios` | GET | Fixture scenario catalog |
| `/api/calls` | POST | Start fixture, browser, or Twilio call session |
| `/api/calls/latest` | GET | Attach the UI to the latest active call |
| `/api/calls/{id}/events` | GET | EventSource stream for transcript, triage, biomarker, flag, and end events |
| `/api/calls/{id}/probes` | POST | Save the three structured probe answers |
| `/api/calls/{id}/handoff` | POST | Generate a handoff PDF artifact |
| `/api/calls/{id}/handoff/{pdf_id}/send` | POST | Send the handoff summary through Twilio SMS |
| `/twilio/voice` | POST | Twilio inbound voice webhook |
| `/twilio/sms-status` | POST | Twilio SMS delivery callback |
| `/ws/audio/browser` | WebSocket | Browser microphone ingest |
| `/ws/twilio/media` | WebSocket | Twilio Media Streams ingest |

## Tests

```bash
uv run pytest -q
```

The backend test suite covers the API surface, fixture replay, Twilio integration boundaries, live session adapters, and PDF generation.

## Linting and Types

```bash
uv run ruff check
uv run ty check
```

## Notes

- The backend is designed so the same UI can run against deterministic fixtures or a real live stream.
- The repo root `.env.example` separates baseline local configuration from optional live-provider and Twilio settings.
