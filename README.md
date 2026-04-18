# Postnatal Pulse

Postnatal Pulse is a hackathon prototype for a voice-first adjunct triage tool used during the six week postnatal phone call. It listens to the call, tracks transcript and voice biomarkers in parallel, flags the mismatch between reassuring words and distressed vocal signals, prompts three structured follow-up probes, and generates a handoff summary for the next clinician.

This repository is best read as a working product checkpoint. The core screen, fixture-driven backend, live audio entry points, and handoff generation are implemented. Neon persistence and the final real-world Twilio and provider smoke path are still open.

## Fast review path

If you want the shortest path to understanding the project, read these in order:

1. [`docs/PRD.md`](./docs/PRD.md) for the product case and constraints.
2. [`docs/UI-SPEC.md`](./docs/UI-SPEC.md) for the single-screen clinical workflow.
3. [`backend/src/postnatal_pulse/main.py`](./backend/src/postnatal_pulse/main.py) for the HTTP, SSE, WebSocket, Twilio, and handoff endpoints.
4. [`frontend/src/App.tsx`](./frontend/src/App.tsx) for the current screen implementation.
5. [`backend/tests/`](./backend/tests/) and [`frontend/src/lib/call-state.test.ts`](./frontend/src/lib/call-state.test.ts) for the verification surface.

## Repo map

- [`backend/`](./backend/) contains the FastAPI app, fixture replay, live provider adapters, and PDF generation.
- [`frontend/`](./frontend/) contains the React single-screen UI and client-side call state.
- [`assets/tts/`](./assets/tts/) contains the scenario WAV fixtures used by the backend scenario catalog.
- [`docs/`](./docs/) contains the product, system, and UI specs that define the intended behavior.

## What is implemented

- Fixture scenarios A, B, and C with deterministic transcript and flag flow.
- FastAPI endpoints for scenario listing, call start, event streaming, probe save, handoff generation, Twilio voice ingress, and Twilio SMS send.
- Browser and Twilio audio ingest entry points.
- A reviewer-facing UI that mirrors the reference single-screen layout closely enough to exercise the core demo story.
- Server-side handoff PDF generation and an in-app handoff preview.

## What is not finished yet

- Neon-backed persistence is not wired yet. Current call and PDF registries are in memory.
- The real Twilio phone call and real provider smoke path still need final end-to-end verification.
- The fixture replay reaches the end state too quickly for a perfect long-lived hero screenshot comparison.

## Local run

### Backend

```bash
cd backend
uv sync
uv run fastapi run --app postnatal_pulse.main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
bun install
VITE_API_BASE_URL=http://127.0.0.1:8000 bun run dev --host 0.0.0.0 --port 5173
```

## Verification commands

### Backend

```bash
cd backend
uv run pytest -q
uv run ruff check
uv run ty check
```

### Frontend

```bash
cd frontend
bun test
bun run lint
bun run build
```

## Notes for evaluators

- The repository is intentionally split into a backend review surface and a frontend review surface so the clinical demo path is easy to inspect.
- The live provider path exists, but the safest path to understand behavior quickly is the fixture flow.
- The most important end-to-end state change is Scenario A, where the UI transitions from routine monitoring to the concordance alert and probe workflow.
