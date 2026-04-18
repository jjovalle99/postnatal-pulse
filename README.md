# Postnatal Pulse

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org) [![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688)](https://fastapi.tiangolo.com) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![ty](https://img.shields.io/badge/type%20checked-ty-blue)](https://github.com/astral-sh/ty) [![React 19](https://img.shields.io/badge/React-19-149eca)](https://react.dev) [![Vite 8](https://img.shields.io/badge/Vite-8-646cff)](https://vite.dev) [![Biome](https://img.shields.io/badge/linted%20with-biome-60a5fa)](https://biomejs.dev) [![Bun](https://img.shields.io/badge/bun-1.3-f472b6)](https://bun.sh)

[![Hackathon Prototype](https://img.shields.io/badge/hackathon-prototype-f59e0b?style=flat-square&logo=rocket&logoColor=white)]()

Voice-first clinical support for the six week postnatal call. Postnatal Pulse gives the clinician one live screen with a diarized transcript, voice biomarker signals, a concordance alert when reassuring language does not match vocal strain, three structured follow-up probes, and a handoff summary ready for the next step in care.

## Overview

Postnatal mental health follow-up often depends on what the caller is willing to say in the moment. This project is built around the harder case: the patient says she is coping, while her voice suggests fatigue, distress, or disengagement. Postnatal Pulse combines transcript, biomarker snapshots, and a deterministic alert policy, then turns that signal into a workflow a midwife can act on immediately.

The repository is organized around three operating paths:

- fixture replay for the core product story
- browser microphone for local live input
- Twilio phone ingress for the real call experience

## Product Flow

1. Start a call in fixture, browser, or Twilio mode.
2. Stream transcript, biomarker, and concordance events into a single live screen.
3. Surface a minimization alert when language and vocal strain diverge.
4. Capture three structured probes and update triage.
5. Generate a clinician handoff summary and send it through the existing workflow.

## Project Structure

```text
├── backend/                   # FastAPI app, fixture replay, live providers, PDF generation
│   ├── src/postnatal_pulse/   # Application modules
│   ├── templates/             # Handoff PDF template
│   └── tests/                 # Backend verification surface
├── frontend/                  # React + Vite single-screen UI
│   ├── src/                   # Screen, store, API client, styles
│   └── public/                # Static assets
├── assets/tts/                # Scenario WAV fixtures
├── docs/                      # PRD, system spec, UI spec, execution plan
└── .env.example               # Required and optional local configuration
```

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/PRD.md](./docs/PRD.md) | Product framing and demo thesis |
| [docs/SPEC.md](./docs/SPEC.md) | System behavior and interface contracts |
| [docs/UI-SPEC.md](./docs/UI-SPEC.md) | One-screen experience and microcopy |
| [backend/README.md](./backend/README.md) | Backend entry points, modules, API surface |
| [frontend/README.md](./frontend/README.md) | Frontend screen map, state flow, local commands |

## Getting Started

### 1. Configure environment

```bash
cp .env.example .env
```

### 2. Run the backend

```bash
cd backend
uv sync
uv run fastapi run --app postnatal_pulse.main:app --host 0.0.0.0 --port 8000
```

### 3. Run the frontend

```bash
cd frontend
bun install
VITE_API_BASE_URL=http://127.0.0.1:8000 bun run dev --host 0.0.0.0 --port 5173
```

## Verification

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

## Where to Look First

- [`backend/src/postnatal_pulse/main.py`](./backend/src/postnatal_pulse/main.py) for the API, SSE, WebSocket, and Twilio entry points
- [`backend/src/postnatal_pulse/fixtures.py`](./backend/src/postnatal_pulse/fixtures.py) for Scenario A, B, and C
- [`frontend/src/App.tsx`](./frontend/src/App.tsx) for the current single-screen implementation
- [`frontend/src/lib/call-state.ts`](./frontend/src/lib/call-state.ts) for the typed SSE reducer
