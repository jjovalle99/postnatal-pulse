# Backend Guide

This backend is a FastAPI application that owns the demo call lifecycle: scenario start, SSE event streaming, browser and Twilio audio ingress, live-provider orchestration, probe capture, and handoff PDF generation.

## Start here

If you are reviewing the backend for the first time, these files matter most:

1. [`src/postnatal_pulse/main.py`](./src/postnatal_pulse/main.py)
   Main application entry point. Defines the REST API, SSE stream, Twilio webhook, browser audio WebSocket, and handoff endpoints.
2. [`src/postnatal_pulse/fixtures.py`](./src/postnatal_pulse/fixtures.py)
   Scenario A, B, and C source of truth.
3. [`src/postnatal_pulse/live_session.py`](./src/postnatal_pulse/live_session.py)
   Speechmatics and Thymia live-session orchestration.
4. [`src/postnatal_pulse/live_runtime.py`](./src/postnatal_pulse/live_runtime.py)
   In-memory event buffering and runtime state used by the live path.
5. [`src/postnatal_pulse/pdfs.py`](./src/postnatal_pulse/pdfs.py)
   Handoff PDF rendering and signed-download handling.
6. [`tests/`](./tests/)
   Backend verification surface.

## Current architecture

- Fixture replay is fully available and is the fastest way to review the product story.
- Browser and Twilio audio entry points are implemented.
- Live provider adapters for Speechmatics and Thymia are present behind configuration.
- Call state and PDF state are still stored in memory. Neon persistence is the next major backend milestone.

## Useful commands

### Install and run

```bash
uv sync
uv run fastapi run --app postnatal_pulse.main:app --host 0.0.0.0 --port 8000
```

### Test and gates

```bash
uv run pytest -q
uv run ruff check
uv run ty check
```

## Reviewing the flow

### Fixture path

- `POST /api/calls` with `source=fixture`
- open the returned SSE stream
- inspect transcript, flag, triage, and end events
- generate a handoff with `POST /api/calls/{id}/handoff`

### Live path

- create a browser or Twilio call session
- stream audio into the corresponding WebSocket
- watch SSE events populate from the live runtime

## Important caveats

- Persistence is not wired to Neon yet.
- The fixture event stream does not yet mirror every live-event nuance.
- `audioop` is still used for Twilio μ-law decode and resample, which is acceptable on Python 3.12 but should be replaced before Python 3.13.
