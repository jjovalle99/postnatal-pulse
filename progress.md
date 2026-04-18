# Progress

## Done

- Built the fixture-first backend skeleton in `backend/` with FastAPI lifespan, settings, CORS, scenario listing, fixture call creation, SSE replay, and probe reclassification.
- Added deterministic Scenario A/B/C fixture data ported from the reference frontend and generated local Voxtral audio clips in `assets/tts/`.
- Added server-side handoff PDF generation, signed PDF downloads, and a frontend preview modal wired to the generated PDF URL.
- Added browser-mic session issuance with JWT-protected `/ws/audio/browser` handling and tests covering binary frame acceptance.
- Added the Twilio inbound voice webhook with real Twilio signature validation and `<Stream>` TwiML generation for `/ws/twilio/media`.
- Added end-call, flag-dismiss, handoff-send, and Twilio SMS status endpoint coverage to the backend lifecycle surface.
- Added provider-facing live analysis logic and configuration builders for Speechmatics and Thymia Sentinel, based on the official SDK/docs surfaces now installed in the backend environment.
- Added a typed live runtime/event buffer and provider session orchestration layer for Speechmatics + Sentinel, plus a tested Twilio media WebSocket consumer with μ-law decoding and 8k→16k PCM conversion.
- Added `GET /api/calls/latest` and extended the frontend so it can attach to the latest live call and consume live `biomarker`, `concordance_trace`, and `system` SSE events.
- Built the frontend shell in `frontend/` with Bun/Vite/React, a tested SSE reducer, Zustand call state, scenario drawer, transcript panel, rationale sheet, probe modal, live-call attach path, and handoff preview wired to the backend.
- Ported the main frontend visuals much closer to the reference code: top strip, concordance ribbon, transcript panel, biomarker rail, right-rail actions, and the handoff modal now follow the reference layout and styling much more directly.
- Fixed frontend live-state polish issues found in browser smoke tests: the triage lozenge now shows the real flag timestamp, and fixture/live SSE streams no longer fall into an `error` state after a clean `end` event.

## Tradeoffs

- The fixture replay still advances too quickly for a faithful long-lived hero-state browser comparison; it reaches `ended` almost immediately, so final visual parity checks against the reference hero frame are noisier than they should be.
- The handoff flow now uses an in-app HTML preview for visual fidelity while still generating the backend PDF; opening the generated PDF remains a separate action from the preview modal.
- The PDF preview and SMS dispatch endpoints are implemented, but the full Twilio delivery-confirmation roundtrip has not been smoke-tested against the real Twilio service yet.
- The browser-mic and Twilio media paths can feed the live provider session code, but that code path still needs a real external-provider smoke test with `LIVE_PROVIDER_ENABLED=true`.
- The Twilio webhook and media consumer are implemented and a real Twilio number is configured locally, but the number still needs a public webhook target before the phone path can be exercised end-to-end.
- A public Cloudflare tunnel is currently up and the Twilio number has been repointed to it, but that is an operational runtime state, not a durable deployment.
- `LIVE_PROVIDER_ENABLED` is still effectively off by default for safe local testing; the code path exists, but it still needs a real live smoke test against the external provider services.

## Uncertain Edge Cases

- Probe answer wording differs between `docs/SPEC.md` and `docs/UI-SPEC.md`. The backend currently accepts the UI copy plus the spec shorthand where they differ.
- Scenario audio timing does not yet align to the canonical `02:14` hero trigger timestamp from the reference fixture timeline.
- The browser SSE path now supports `api_key` as a query param because native `EventSource` cannot set `X-API-Key` headers; this matches browser constraints but should be reviewed before production hardening.
- The fixture replay currently compresses the timeline enough that browser screenshots often land on `Call ended` instead of the reference `Call live` hero frame, even though the layout is now aligned.
- The Twilio webhook currently derives the stream URL from the incoming request URL. That is correct behind a public HTTPS host, but it still needs a deployed base URL smoke test once the public backend is up.
- The Twilio media consumer currently uses `audioop` for μ-law decode/resample, which works on Python 3.12 but is deprecated in Python 3.13 and should be replaced before a future Python upgrade.
