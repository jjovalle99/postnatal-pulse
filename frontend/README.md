# Frontend Guide

This frontend is a single-screen React application built for reviewers and demo operators. It is responsible for presenting the live call state, transcript, biomarker rail, concordance alert, probes workflow, and handoff preview.

## Start here

If you want to understand the UI quickly, read these files in order:

1. [`src/App.tsx`](./src/App.tsx)
   The full single-screen clinical experience lives here.
2. [`src/lib/call-state.ts`](./src/lib/call-state.ts)
   Typed reducer for SSE events from the backend.
3. [`src/lib/call-store.ts`](./src/lib/call-store.ts)
   Zustand store that holds the active call state.
4. [`src/lib/api.ts`](./src/lib/api.ts)
   HTTP client surface for scenarios, live attach, probes, and handoff generation.
5. [`src/index.css`](./src/index.css)
   Global tokens, typography, and motion primitives for the current visual port.

## What the frontend currently does

- Renders the top strip, concordance ribbon, transcript panel, biomarker card, and assessment card.
- Supports fixture scenario start and latest-live-call attach.
- Consumes one SSE stream for transcript, triage, biomarker, concordance, flag, rationale, system, and end updates.
- Opens the rationale sheet, probe modal, and handoff preview.

## What to pay attention to

- The current implementation is intentionally single-screen and direct. There is no routing layer yet.
- The visual port is close to the reference, but the remaining differences are mostly in timing and polish rather than missing major UI regions.
- The demo drawer is still present for local operation and fixture switching.

## Local run

```bash
bun install
VITE_API_BASE_URL=http://127.0.0.1:8000 bun run dev --host 0.0.0.0 --port 5173
```

## Frontend gates

```bash
bun test
bun run lint
bun run build
```

## Review tips

- Use Scenario A first. It shows the full intended transition from routine monitoring to alert and follow-up.
- The key reviewer question is not whether every last pixel is finished, but whether the screen makes the clinical logic legible in one pass.
- The handoff preview is rendered in-app for review speed, while the backend still generates the underlying PDF artifact.
