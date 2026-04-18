# Frontend

React 19 + Vite single-screen UI for Postnatal Pulse. The frontend is built around one operational surface: transcript on the left, clinical signals on the right, and a concordance alert that expands into action when language and voice stop telling the same story.

For the broader product framing, see the root [README.md](../README.md) and [docs/UI-SPEC.md](../docs/UI-SPEC.md).

## Local Development

```bash
bun install
VITE_API_BASE_URL=http://127.0.0.1:8000 bun run dev --host 0.0.0.0 --port 5173
```

Runs at [localhost:5173](http://localhost:5173). The frontend expects the backend to be available at `:8000` unless `VITE_API_BASE_URL` is changed.

## Key Files

| File | Purpose |
|------|---------|
| `src/App.tsx` | Main screen implementation, modals, transcript, ribbon, biomarker rail, handoff preview |
| `src/lib/api.ts` | Typed HTTP client for scenarios, latest-call attach, probes, and handoff generation |
| `src/lib/call-state.ts` | SSE event model and reducer |
| `src/lib/call-store.ts` | Zustand store for the active call session |
| `src/lib/runtime.ts` | Runtime-injected patient and clinician context |
| `src/index.css` | Global design tokens, typography, and motion primitives |

## Screen Map

| Region | Role |
|--------|------|
| Top Clinical Strip | Triage state, patient context, call status, demo line |
| Concordance Ribbon | Live mismatch signal and alert banner |
| Transcript Panel | Diarized transcript with elapsed-call timestamps |
| Biomarker Rail | Six fixed-order voice biomarker rows |
| Assessment Card | Why flagged, 3 probes, handoff actions |
| Handoff Preview | Read-only summary view for the generated PDF |

## Data Flow

- One `EventSource` stream powers the live UI state.
- The reducer in `call-state.ts` normalizes backend events into a typed client state.
- The store in `call-store.ts` keeps the active call session available across the screen.
- `runtime.ts` lets the UI swap patient and clinician identity at runtime without a rebuild.

## Tests

```bash
bun test
```

## Linting and Build

```bash
bun run lint
bun run build
```

## Notes

- The UI is intentionally single-screen and direct. There is no extra routing layer or admin shell around it.
- Scenario A is the fastest way to see the full intended interaction: monitoring, alert, probes, and handoff.
