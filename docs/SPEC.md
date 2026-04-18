# Postnatal Pulse — Specification

> **Version:** 0.2 (closed open questions Q1–Q10 from v0.1; aligned to Sentinel's native `concordance_analysis`; Mistral structured output via `chat.parse` + `instructor`; Render persistent disk for PDFs; CORS allowlist + JWT for browser-mic WS; 20-second sliding window grounded in clinical literature)
> **Status:** Build-ready
> **Last updated:** 2026-04-18 (Saturday — hackathon day)
> **Companion docs:** [`./PRD.md`](./PRD.md) (the why) · [`./PLAN.md`](./PLAN.md) (the Saturday execution plan) · [`./UI-SPEC.md`](./UI-SPEC.md) (the one-screen UI brief) · [`./PRD-GUIDE.md`](./PRD-GUIDE.md) (the PRD writing rules)

---

## 1. System Overview

Postnatal Pulse is a voice-first adjunct triage tool that runs alongside the NHS midwife's mandatory 6-week postnatal phone call. It ingests the live call audio, produces a clinical-grade transcript, scores the mother's voice for clinical biomarkers, and surfaces the specific failure mode the existing EPDS questionnaire misses: a mother who says "I'm coping fine" while her voice carries fatigue, anhedonia, and distress. When that mismatch crosses a tuned threshold, the midwife sees a `MINIMIZATION DETECTED` banner and is prompted to ask three structured probes about sleep, enjoyment, and support. The probe answers re-score the triage flag and a one-page handoff PDF lands with the GP and an SMS lands with the caller.

The user is the midwife, not the patient. The product never diagnoses, never escalates autonomously, and never hides what it is doing — every triage state and every flag is paired with a plain-English rationale and the specific transcript moment that triggered it. The system is positioned as adjunct decision-support inside an existing workflow, deliberately avoiding the regulatory shape of a population screening tool that the UK National Screening Committee declined to recommend in February 2026.

## 2. Success Criteria

1. A demo viewer who has never seen the product can, after 45 seconds of watching the hero scenario, state in one sentence what the product does, who the user is, why voice matters here, and that it does not diagnose. (PLAN cold-viewer test, both rounds.)
2. The hero scenario (Scenario A — Minimizing Exhaustion) reaches the `MINIMIZATION DETECTED` flag within 5 seconds of the trigger transcript line on three consecutive runs, with no manual nudge.
3. From the moment the deterministic policy fires the flag, the UI banner is rendered within p99 250ms, and the LLM rationale begins streaming to the "Why flagged?" panel within p99 1.5 seconds.
4. From the moment the midwife clicks `Save responses` on the 3-probes modal, the triage lozenge re-classifies and the handoff PDF preview becomes available within 2 seconds.
5. The handoff PDF generated from any of the three canned scenarios fits on one page (spilling to a second only for an oversized transcript excerpt) and contains every section listed in UI-SPEC modal C in the specified order, with the verbatim disclaimer footer.
6. The deterministic replay path runs end-to-end with no live API calls (Twilio off, Speechmatics off, Sentinel off, Mistral off) and produces the identical triage state, flag timestamp, transcript excerpt, and PDF as the live path on the same fixture.
7. Zero clinician-facing string in the deployed UI contains the substrings `diagnose`, `detect postpartum`, `detects PPD`, or `replaces clinician` (case-insensitive). A static check enforces this on every release.
8. When Sentinel returns an empty or partial payload, the affected biomarker rows show a "Signal delayed" chip and freeze on their last good value rather than dropping to zero or disappearing. The triage state and flag history are preserved.
9. A judge dialing the published Twilio number from a UK mobile reaches the live UI within 3 seconds of pickup, sees their own transcript and biomarker stream populate inside 6 seconds of speaking, and receives an SMS containing the triage state and a link to the handoff PDF within 90 seconds of call end. (P2 wow demo.)
10. The React frontend renders the same payload shape (`PATIENT`, `CLINICIAN`, `SCENARIOS`-equivalent runtime data) the existing reference app in `Voice Hackathon.zip` consumes, so the visual design, motion, and microcopy carry over unchanged.

## 3. Feature-Verification Matrix

System layers reflect the actual architecture: a real-time **Audio Ingest** layer that handles Twilio Media Streams and browser microphone, an **Analysis** layer that runs Speechmatics + Sentinel + the deterministic policy + the LLM rationale stream, a **Persistence & Storage** layer (Neon Postgres + filesystem PDFs), a **Backend API** layer (FastAPI) that exposes REST + WebSocket + SSE, and a **Frontend** layer (Vite + React + TypeScript). Cross-layer rows capture end-to-end behaviors that span them all.

### 3.1 Audio Ingest

| ID | Feature | Verification (observable outcome) | Traces to |
|---|---|---|---|
| AI-01 | Twilio inbound voice webhook | A POST to `/twilio/voice` returns valid TwiML containing a `<Stream>` directive that points at the deployed `/ws/twilio/media` URL with the correct codec hint, and a phone call dialed to the published number connects without dropping inside 3 seconds. | §5.1, §7.1 |
| AI-02 | Twilio Media Stream consumer | While a Twilio call is connected, the `/ws/twilio/media` WebSocket receives μ-law 8 kHz frames continuously and emits PCM 16-bit 16 kHz mono frames downstream within 50 ms of arrival, with no gaps longer than 200 ms across a 2-minute call. | §5.3, BR-013 |
| AI-03 | Browser microphone fallback | When the demo selects browser-mic mode, the `/ws/audio/browser` endpoint accepts PCM 16 kHz frames from the browser's `AudioWorklet` and produces a stream identical in shape to AI-02's output (same downstream contract). | §5.3, C2 |
| AI-04 | Deterministic fixture replay | When the demo selects fixture mode, the system streams the canned audio file for the chosen scenario at real-time pace and produces the identical downstream shape as AI-02/AI-03 — no live API calls are made. | §5.4, BR-018, C3 |

### 3.2 Analysis

| ID | Feature | Verification (observable outcome) | Traces to |
|---|---|---|---|
| AN-01 | Speechmatics medical transcription | While audio flows, transcript segments arrive on the call event stream tagged with speaker (`Clinician` or `Patient`), elapsed-call timestamp, and a `final` vs `partial` marker. Final segments stop changing once emitted. Speaker IDs from the Speechmatics diarizer (max 2) map deterministically to `Clinician` (the first speaker to talk) and `Patient` (the other). | §5.5, BR-009 |
| AN-02 | Thymia Sentinel biomarker stream | While audio flows, biomarker snapshots arrive at ~5-second cadence containing values for each of the six tracked rows (`Fatigue`, `Sleep issues`, `Low energy`, `Anhedonia`, `Distress`, `Stress`) plus the raw Helios + Apollo + Psyche payloads. Each snapshot carries the call_id and elapsed-call timestamp. | §5.5, BR-008 |
| AN-03 | Concordance ribbon traces (visualization) | While audio flows, a two-channel time series is emitted at the same cadence as the biomarker stream. `transcript_min` is snapped to Sentinel's `concordance_analysis.agreement_level` mapped `none→0`, `mild→0.33`, `moderate→0.66`, `severe→1.0` whenever a policy result arrives; values interpolate linearly between updates. `acoustic_strain` is computed each Sentinel progress tick as `0.5·distress + 0.3·stress + 0.2·negative_psyche` where `negative_psyche = clamp(sad + fearful + disgusted, 0, 1)`. Both align to the same elapsed-call clock as AN-01 and AN-02. These traces drive the ribbon SVG only — they are not the gate. | §5.5, W18, BR-019 |
| AN-04 | Deterministic gate (Sentinel concordance + postnatal cluster) | A `MINIMIZATION DETECTED` flag fires when BOTH conditions hold within the same 20-second sliding window (re-evaluated each Sentinel policy result, ~5s cadence): (a) Sentinel's `wellbeing-awareness` policy returns `concordance_analysis.scenario == "minimization"` AND `concordance_analysis.agreement_level ∈ {"moderate", "severe"}`; AND (b) the postnatal cluster threshold is satisfied: `sleep_issues ≥ 0.60` AND (`low_energy ≥ 0.60` OR `anhedonia ≥ 0.55`). The flag fires within p99 100 ms of the second condition becoming true (Sentinel's policy result is the trigger; cluster check is a local table lookup). | BR-001, BR-003, W5 |
| AN-05 | LLM rationale stream | When the deterministic gate fires, an LLM-generated rationale begins streaming over the call's SSE event stream within 1.5 seconds, producing exactly three plain-English driver sentences (no model jargon, no raw biomarker names) and a confidence label of `High`, `Medium`, or `Low`. The stream is consumable token-by-token by the frontend. If the LLM call fails or exceeds a 10-second total budget, the system emits a fallback rationale built from a static template using the deterministic payload, marked with `confidence: low`. | §5.6, BR-002, BR-014 |
| AN-06 | Wellbeing-awareness suicidal-content escalation | When Sentinel's `wellbeing-awareness` policy returns a suicidal-content flag at any point during the call, the triage state immediately advances to `red` regardless of the deterministic concordance gate, and the flag carries a `kind: suicidal_content` discriminator. | BR-003 |

### 3.3 Persistence & Storage

| ID | Feature | Verification (observable outcome) | Traces to |
|---|---|---|---|
| DB-01 | Call record persists | After every call completes, the `calls` table contains exactly one row with the call_id, source (`twilio` / `browser` / `fixture`), started_at and ended_at timestamps, scenario_id (if fixture), and total duration in seconds. | §4.1, §5.7 |
| DB-02 | Transcript persisted in order | After every call, the `transcript_segments` table contains one row per final segment, ordered by elapsed-call timestamp, each carrying speaker, text, and the t_seconds offset. The full ordered concatenation matches what the UI displayed during the call. | §4.1 |
| DB-03 | Biomarker snapshots persisted | After every call, the `biomarker_snapshots` table contains one row per snapshot per layer, recoverable as a continuous time series for any of the six tracked names. | §4.1 |
| DB-04 | Flag events persisted | After every flag fires, the `flag_events` table contains a row with kind (`minimization` / `suicidal_content`), fired_at_t (elapsed-call seconds), the deterministic payload, the LLM rationale (if generated), confidence, and contributing biomarker names. | §4.1 |
| DB-05 | Probe responses persisted | After the midwife clicks `Save responses`, the `probe_responses` table contains exactly three rows for that flag_event, in order, each with the probe text, the chosen option text, the deterministic score (0/1/2), and the saved_at timestamp. | §4.1, BR-004 |
| DB-06 | Triage history persisted | The `triage_states` table contains one row per state change for the call, in order, each carrying state (`awaiting`/`green`/`amber`/`red`), reason source (`pre-flag`/`post-flag`/`post-probe`/`escalation`/`dismiss`), and timestamp. The latest row reflects the current triage shown in the UI. | §4.1, BR-005 |
| DB-07 | Handoff PDF artifact persisted | After PDF generation, the `handoff_pdfs` table contains one row per generated PDF with call_id, generated_at, the storage path of the PDF on disk (or object store), and (after Send) the recipient phone number and sms_sent_at timestamp. The file at the storage path is a valid PDF that opens. | §4.1, §5.8 |
| DB-08 | Connection pool resilience | Under simulated database disconnects (Neon serverless suspend after 5 min idle), the next request succeeds within 1 second of reconnect with no client-visible error. Pool is configured with `pool_recycle=300` and `pool_pre_ping=True`. | §7.1, R3 |

### 3.4 Backend API

| ID | Feature | Verification (observable outcome) | Traces to |
|---|---|---|---|
| BE-01 | Start a call (REST) | `POST /api/calls` with body `{source: "twilio"|"browser"|"fixture", scenario_id?: "A"|"B"|"C"}` returns 201 with `{call_id, sse_url, ws_url}` and creates a `calls` row with status `connecting`. | §5.1 |
| BE-02 | Subscribe to call events (SSE) | A GET to `/api/calls/{id}/events` with `Accept: text/event-stream` keeps the connection open and emits typed events: `transcript`, `partial_transcript`, `biomarker`, `concordance_trace`, `flag`, `rationale_token`, `rationale_done`, `triage`, `probe_saved`, `pdf_generated`, `sms_status`, `error`. Each event has `event:` + `data:` + `id:` per W3C SSE spec. The connection cleanly closes when the call ends and emits an `event: end` first. | §5.2, W18 |
| BE-03 | Save probe responses | `POST /api/calls/{id}/probes` with body `{flag_id, answers: [string, string, string]}` returns 200 with the recomputed triage state and a `triage` event is emitted on the SSE stream within 300 ms. | §5.1, BR-004 |
| BE-04 | Generate handoff PDF | `POST /api/calls/{id}/handoff` returns 200 with `{pdf_id, preview_url, download_url}`. The PDF is rendered server-side from the persisted call record using WeasyPrint and is byte-stable for the same input. | §5.1, R5 |
| BE-05 | Send handoff SMS | `POST /api/calls/{id}/handoff/{pdf_id}/send` with body `{recipient_phone}` returns 202. A Twilio SMS is dispatched containing the triage label, a one-line summary, and a signed download URL valid for 7 days. The `sms_status` event fires on the SSE stream when Twilio's webhook reports delivery. | §5.1, BR-006 |
| BE-06 | Dismiss a flag | `POST /api/calls/{id}/flags/{flag_id}/dismiss` with body `{reason}` returns 200 and the triage state regresses one step (`amber → green`, `red → amber`) with `source: dismiss`. The dismiss is recorded on the flag_event row. | §5.1, BR-005 |
| BE-07 | End a call | `POST /api/calls/{id}/end` returns 200 with the final summary record. Audio ingest stops, SSE emits `end`, and the `calls` row's `ended_at` is set. | §5.1 |
| BE-08 | Twilio voice webhook | `POST /twilio/voice` returns valid TwiML on every request with HMAC signature validation enforced; requests with an invalid signature return 403. | §5.1, §7.2 |
| BE-09 | Twilio SMS status webhook | `POST /twilio/sms-status` accepts Twilio's status callback and updates the matching `handoff_pdfs` row. Idempotent for duplicate deliveries. | §5.1, §7.2 |
| BE-10 | Health endpoint | `GET /healthz` returns 200 with a JSON body containing the version, the database pool state, the Sentinel SDK status, and the Speechmatics SDK status. Used by Render for liveness probing. | §7.5 |
| BE-11 | Static check on banned strings | A unit test scans every clinician-facing string source (frontend bundle output + backend response templates + PDF templates) for the banned substrings; the test fails the build if any match is found. | BR-007, W8 |

### 3.5 Frontend

| ID | Feature | Verification (observable outcome) | Traces to |
|---|---|---|---|
| FE-01 | One-screen layout matches reference | The deployed frontend renders the same five regions as the reference app in `Voice Hackathon.zip`: Top Clinical Strip, Concordance Ribbon, Live Transcript, Live Biomarker Signals card, Assessment & Handoff card. Region positions, sizes, and stacking order match the reference within ±4px. | UI-SPEC §"The one screen", §8 |
| FE-02 | Live transcript with diarized rows | While the call is live, transcript rows appear in real time, each labeled `Clinician` or `Patient` (text labels, not colour-only), each timestamped to elapsed-call seconds in tabular numerals, and the panel auto-scrolls to the newest row. | UI-SPEC §"Live Transcript", BR-009 |
| FE-03 | Resume-live yield-on-scroll | When the user scrolls up while the call is live, auto-scroll suspends. A `Resume live` chip appears at the bottom; clicking it scrolls back to the newest row and re-enables auto-scroll. | UI-SPEC §"Live Transcript", W10 |
| FE-04 | Concordance ribbon — three states | The ribbon is always present and renders one of three states: `idle` (pre-call, no traces), `thin` (live, two low-contrast lines tracking each other), or `expanded` (after flag fires, full-width amber banner with `MINIMIZATION DETECTED` headline and the recent trace remaining faintly visible behind). The expansion animates over ~200ms. | UI-SPEC §"Concordance Ribbon", W9 |
| FE-05 | Triage lozenge — four states | The lozenge in the Top Clinical Strip is always present and renders exactly one of: `Awaiting call`, `Green: routine`, `Amber: review`, `Red: urgent review`. Each carries the text label and a status colour fill. State transitions cross-fade smoothly. The lozenge never appears as colour-only. | UI-SPEC §"Top Clinical Strip", W11 |
| FE-06 | Biomarker rail — fixed order, never re-sorts | The right-rail biomarker card always shows the same six rows in the same order, top to bottom: `Fatigue`, `Sleep issues`, `Low energy`, `Anhedonia`, `Distress`, `Stress`. Rows refresh ~every 5 seconds with subdued motion. After a flag fires, contributing rows gain amber emphasis; non-contributing rows recede. | UI-SPEC §"Card 1 — Live biomarker signals" |
| FE-07 | Assessment card — stable action layout | The right-rail assessment card always shows the same three actions in the same vertical order: `Why flagged?`, `Open 3 probes`, `Generate handoff PDF`. The first two are visible-but-disabled in idle and become primary when a flag fires. The third is always available, secondary until probes are reviewed. | UI-SPEC §"Card 2 — Assessment & handoff" |
| FE-08 | Why-flagged sheet streams the rationale | Clicking `Why flagged?` opens a right-side sheet. The three plain-English drivers stream in token-by-token via the SSE `rationale_token` events, finalising when `rationale_done` arrives. The Confidence chip renders alongside. The live screen continues to update behind the sheet. | UI-SPEC §"Modal A", FE-15 |
| FE-09 | 3 probes modal — boxed answers only | Clicking `Open 3 probes` opens a centred modal with the three exact probe questions from UI-SPEC, each with its three exact one-tap option buttons. No free-text input exists anywhere. `Save responses` is disabled until all three are answered. The live screen continues to update behind the scrim. | UI-SPEC §"Modal B", W6 |
| FE-10 | Handoff preview modal — read-only PDF preview | Clicking `Generate handoff PDF` opens a wide modal with a read-only render of the PDF. The render contains every section listed in UI-SPEC modal C in the specified order, including the verbatim disclaimer footer. The `Send PDF` button is the only call-to-action that actually dispatches the PDF + SMS. | UI-SPEC §"Modal C" |
| FE-11 | Demo-mode toggle — Shift+D | In development mode, pressing `Shift+D` opens a small bottom-left drawer with three buttons (`Scenario A`, `Scenario B`, `Scenario C`). Clicking one resets the call state and loads the chosen fixture. In production mode (`VITE_DEMO_MODE=false`), the shortcut is disabled and the drawer never appears. | UI-SPEC §"Demo mode toggle", C10 |
| FE-12 | Aesthetic intent — paper, ink, clinic blue, humanist sans | The deployed UI uses a warm-paper background, deep-ink body text, deep-clinic-blue structural accent, slate dividers, status colours used only for triage and concordance alerts (never decorative), and humanist sans (Source Sans 3 / Inter Tight) throughout. Tabular numerals are used for the timer, score chips, and any digit run. | UI-SPEC §"Aesthetic intent" |
| FE-13 | Hard rules — no patient avatar, no emoji, no decorative analytics | The deployed UI contains zero patient avatar images, zero emoji mood meters, zero decorative analytics charts, zero vendor/startup badges, and zero animated loading spinners on idle states. A static check on the bundle source enforces this. | UI-SPEC §"Hard rules", BR-007 |
| FE-14 | Accessibility — keyboard, focus, contrast, motion | All modals are keyboard-reachable, focus-trapped, dismissible with Esc, and return focus to the trigger element on close. Triage state, concordance state, and speaker identity are never colour-only. WCAG AA contrast holds in every state. Motion is brief and functional — one soft pulse on flag entry, nothing flashes. | UI-SPEC §"Accessibility", §7.3 |
| FE-15 | Single SSE channel powers the whole UI | The frontend opens exactly one `EventSource` connection to `/api/calls/{id}/events` per active call and routes typed events to a single in-memory store. No polling, no second long-lived connection, no XHR retry loop. | §5.2, R6 |
| FE-16 | Patient and clinician are runtime-injected | The deployed frontend reads `PATIENT` and `CLINICIAN` from a runtime-injected context (matching the reference app's `window.POSTNATAL` shape) so the demo can swap fixture identities without a rebuild. | A4, W14 |

### 3.6 Cross-Layer

| ID | Feature | Verification (observable outcome) | Layers | Traces to |
|---|---|---|---|---|
| X-01 | Hero scenario end-to-end (fixture replay) | Loading Scenario A in fixture mode produces the canonical timeline: triage starts `green`, the concordance ribbon enters `thin` state once audio flows, the flag fires at elapsed `02:14`, the ribbon expands to amber, the lozenge crossfades to `Amber: review`, the transcript cluster around `02:14` gains amber side rule, the contributing biomarker rows gain amber emphasis, the LLM rationale streams the three drivers, opening probes and answering with worst-case answers re-classifies to `red`, generating the PDF and clicking Send dispatches an SMS. Every event timestamp aligns to the same call clock. | All | UI-SPEC §"Eight demo flow states", §8.1 |
| X-02 | Live Twilio call end-to-end | A judge dials the published number, speaks for ~60 seconds, hangs up. The call appears in the UI within 3 seconds of pickup, transcript and biomarkers populate within 6 seconds of speech, the call appears in the persisted `calls` table after end, the SMS dispatches within 90 seconds of end, and the deterministic replay of the same call (replayed from the persisted audio) produces identical downstream events. | All | §8.1, AI-01, AI-02 |
| X-03 | Browser-mic call end-to-end | Selecting browser-mic mode and speaking into the laptop produces identical downstream behavior to X-02 (transcript, biomarkers, flag, rationale, triage, PDF, SMS). The two paths are interchangeable from the Analysis layer onward. | All | C2 |
| X-04 | Sentinel partial-payload degradation | When a Sentinel response arrives missing the `apollo` block, the affected biomarker rows freeze on their last good value, a `Signal delayed · apollo` chip appears in the Top Clinical Strip, and the deterministic gate skips the postnatal symptom cluster condition until a complete payload returns. The call continues normally. No flag fires falsely. | Analysis, Frontend | C1, BR-008 |
| X-05 | Trend-tracking screen | Navigating to `/patients/maya-patel/trends` renders three stacked check-in cards (week 6, 8, 12) with trajectory lines for the six biomarkers, concordance event markers on the timeline, click-through to each call's full transcript and policy result. Static fixtures populate the older check-ins; the most recent is the live demo call. | Persistence, Frontend | PLAN P3 |
| X-06 | Eval harness page | Navigating to `/eval` renders a scorecard table with one row per scenario bucket (controlled-synthetic positive / controlled-synthetic negative / MELD positive / MELD negative) showing N, sensitivity, specificity, false-positive rate, and the per-utterance breakdown is downloadable as CSV. | Backend, Frontend | PLAN P3 |
| X-07 | Multilingual passthrough | When the chosen scenario's audio is in a confirmed non-English language (Punjabi or Polish, sponsor-verified), the transcript renders in the original language, an English translation appears below each row in muted ink, the deterministic gate runs against the translation, and the LLM rationale generates in English. (Conditional — see §11 Q-3.) | All | PLAN P4 |
| X-08 | Tuner observability ingestion | After every call ends, the call summary (transcript, biomarker time series, flag events, triage history, deterministic-vs-LLM agreement marker, latency budgets, error counts) is posted to Tuner's ingestion API. The post happens out-of-band, never blocks the user-visible flow, and is gated by a feature flag (`TUNER_ENABLED=true`). Failures log a warning but do not surface to the UI. | Backend | §7.6 |

## 4. Domain Model

### 4.1 Core Entities

**Entity: Call**
- Description: a single midwife-patient phone consultation, real or replayed.
- Key attributes:
  - `id`: UUID — primary key
  - `source`: enum (`twilio`, `browser`, `fixture`) — provenance of the audio
  - `scenario_id`: enum (`A`, `B`, `C`, null) — set only when `source=fixture`
  - `twilio_call_sid`: string, nullable — set only when `source=twilio`
  - `started_at`: timestamptz — when audio ingest began
  - `ended_at`: timestamptz, nullable — when audio ingest stopped
  - `duration_seconds`: int, computed from started_at/ended_at
  - `clinician_id`: foreign key to `clinicians`
  - `patient_id`: foreign key to `patients`
- Invariants:
  - `ended_at >= started_at` once set
  - exactly one of `scenario_id` or `twilio_call_sid` is non-null when source is non-browser
  - call cannot be deleted, only soft-marked

**Entity: Patient** (fixture-only in v1)
- Key attributes: `id`, `name`, `age`, `weeks_postpartum`, `parity`, `baby_name`, `baby_age`, `visit_reason`
- Invariants: v1 contains exactly one row, Maya Patel, per UI-SPEC patient persona.

**Entity: Clinician** (fixture-only in v1)
- Key attributes: `id`, `name`, `role`, `phone`
- Invariants: v1 contains exactly one row, Sister J. Okafor.

**Entity: TranscriptSegment**
- Key attributes:
  - `call_id`: FK
  - `t_seconds`: float — elapsed call time of segment start
  - `speaker`: enum (`Clinician`, `Patient`)
  - `text`: text
  - `is_final`: bool
  - `confidence`: float, nullable
- Invariants:
  - segments with the same `(call_id, t_seconds)` and `is_final=true` are unique
  - `t_seconds >= 0`
  - speaker mapping is fixed once established for the call (the first speaker to talk is `Clinician`)

**Entity: BiomarkerSnapshot**
- Key attributes:
  - `call_id`: FK
  - `t_seconds`: float
  - `layer`: enum (`helios`, `apollo`, `psyche`)
  - `name`: string — e.g. `distress`, `sleep_issues`, `anhedonia`, `neutral`
  - `value`: float, range [0.0, 1.0]
  - `raw_payload`: JSONB — the original Sentinel response block
- Invariants: `value` always in `[0.0, 1.0]`; `raw_payload` is preserved verbatim for audit.

**Entity: ConcordanceTrace**
- Key attributes: `call_id`, `t_seconds`, `transcript_min` (float 0-1), `acoustic_strain` (float 0-1)
- Invariants: emitted at the same cadence as biomarker snapshots; both fields always populated.

**Entity: FlagEvent**
- Key attributes:
  - `id`: UUID
  - `call_id`: FK
  - `kind`: enum (`minimization`, `suicidal_content`)
  - `fired_at_t`: float — elapsed-call seconds at firing
  - `deterministic_payload`: JSONB — which conditions were satisfied and the values
  - `contributing_signals`: text[] — biomarker names that contributed (e.g. `['Fatigue', 'Anhedonia', 'Sleep issues']`)
  - `llm_rationale_drivers`: text[3], nullable — three plain-English driver sentences
  - `confidence`: enum (`High`, `Medium`, `Low`), nullable
  - `dismissed_at`: timestamptz, nullable
  - `dismissed_reason`: text, nullable
- Invariants:
  - `kind = suicidal_content` always carries `confidence = High`
  - `llm_rationale_drivers` has exactly 3 elements when set

**Entity: ProbeResponse**
- Key attributes: `flag_id` (FK), `probe_index` (0|1|2), `question_text`, `chosen_option`, `score` (0|1|2), `saved_at`
- Invariants: exactly three rows per saved flag (probe_index 0, 1, 2); chosen_option must be one of the three options for that probe_index.

**Entity: TriageState**
- Key attributes: `call_id`, `t_seconds`, `state` (enum `awaiting`/`green`/`amber`/`red`), `source` (enum `pre-flag`/`post-flag`/`post-probe`/`escalation`/`dismiss`/`call-end`), `flag_id` (FK, nullable)
- Invariants: state transitions follow §4.3; the latest row by `t_seconds` is the current triage shown in the UI.

**Entity: HandoffPDF**
- Key attributes: `id`, `call_id`, `generated_at`, `storage_path`, `recipient_phone` (nullable), `sms_dispatched_at` (nullable), `sms_delivered_at` (nullable), `signed_download_url` (nullable)
- Invariants: `recipient_phone` and `sms_dispatched_at` are set together or neither; `signed_download_url` expires 7 days after issue.

### 4.2 Relationships

- `Call` 1:N `TranscriptSegment`
- `Call` 1:N `BiomarkerSnapshot`
- `Call` 1:N `ConcordanceTrace`
- `Call` 1:N `FlagEvent`
- `FlagEvent` 1:0-3 `ProbeResponse` (zero or three, never one or two)
- `Call` 1:N `TriageState`
- `Call` 1:0-N `HandoffPDF`
- `Patient` 1:N `Call`
- `Clinician` 1:N `Call`

### 4.3 State Machines

**Call phase** (in-memory state, not persisted as a column — derived from started_at/ended_at + audio activity):
- States: `pre`, `ringing`, `connecting`, `live`, `ended`, `error`
- Transitions:
  - `pre → ringing` when Twilio webhook arrives or browser-mic stream opens
  - `ringing → connecting` when audio ingest WebSocket established
  - `connecting → live` when first audio frame downstream of upsampler is ready (≤900ms target)
  - `live → ended` when caller hangs up, or `POST /api/calls/{id}/end`, or audio silence > 30s
  - `(any) → error` on unrecoverable ingest failure; UI surfaces "Disconnected" chip
- Invariant: state is monotonic forward; `ended` is terminal except for explicit reset

**Triage state** (persisted in `triage_states`):
- States: `awaiting`, `green`, `amber`, `red`
- Transitions:
  - `awaiting → green` at `connecting → live` (default pre-flag)
  - `green → amber` when concordance gate fires
  - `amber → red` when (post-probe score ≥ 2 worst-case answers) OR (suicidal_content event) OR (scenario.id = B + post-probe)
  - `green/amber/red → awaiting` only at call end, never mid-call
  - `red → amber → green` only via explicit clinician dismiss (BE-06), one step at a time
- Invariant: severity ratchets up automatically; severity decreases only via explicit dismiss (BR-005).

**Flag lifecycle** (persisted in `flag_events`):
- States: `not-fired`, `fired`, `enriched`, `probes-pending`, `probes-saved`, `dismissed`
- Transitions:
  - `not-fired → fired` when deterministic gate satisfied
  - `fired → enriched` when LLM rationale stream completes
  - `enriched → probes-pending` when `Open 3 probes` clicked
  - `probes-pending → probes-saved` when all three answered and Save clicked
  - `(any non-terminal) → dismissed` when `BE-06` invoked

## 5. Interface Contracts

### 5.1 REST API (FastAPI)

**`POST /api/calls`** — Start a call session
- Auth: shared-secret `X-API-Key` header (env `API_KEY`)
- Input: `{source: "twilio"|"browser"|"fixture", scenario_id?: "A"|"B"|"C"}`
- Output (201): `{call_id: UUID, sse_url: str, ws_url: str|null}`
- Errors:
  - `source=fixture` without `scenario_id` → 400 with `{detail: "scenario_id required"}`
  - any other validation failure → 422 (FastAPI default)
- Constraints: idempotent on `(source, scenario_id, started_at_minute)` to survive double-clicks; rate-limited to 30/min per API key.

**`POST /api/calls/{id}/end`** — End a call
- Auth: shared-secret
- Output (200): `{call_id, ended_at, duration_seconds, summary}`
- Side effects: closes audio ingest, finalises persistence, emits SSE `event: end`

**`POST /api/calls/{id}/probes`** — Save probe responses
- Auth: shared-secret
- Input: `{flag_id: UUID, answers: [str, str, str]}`
- Output (200): `{triage: TriageState, flag: FlagEvent}`
- Errors: `answers.length != 3` → 422; flag belongs to different call → 404; option not in allowed list for that probe → 422
- Constraints: re-classification computed in <300ms; SSE `triage` event fires before HTTP response returns.

**`POST /api/calls/{id}/handoff`** — Generate PDF
- Auth: shared-secret
- Output (200): `{pdf_id, preview_url, download_url}`
- Constraints: byte-stable for the same input call record (deterministic WeasyPrint render); generation time <1.5s p99.

**`POST /api/calls/{id}/handoff/{pdf_id}/send`** — Send PDF via SMS
- Auth: shared-secret
- Input: `{recipient_phone: E.164 string}`
- Output (202): `{sms_id, dispatched_at, signed_download_url, expires_at}`
- Constraints: signed URL valid 7 days; SMS body ≤160 chars when triage label + summary fit, else split.

**`POST /api/calls/{id}/flags/{flag_id}/dismiss`** — Dismiss a flag
- Auth: shared-secret
- Input: `{reason: str}`
- Output (200): `{triage: TriageState, flag: FlagEvent}`
- Constraints: triage regresses exactly one step.

**`POST /twilio/voice`** — Twilio inbound webhook
- Auth: HMAC signature validation via Twilio's request validator
- Input: Twilio's standard webhook form-encoded body
- Output (200): `text/xml` TwiML containing `<Stream url="{ws_url}/ws/twilio/media" />`
- Errors: invalid signature → 403

**`POST /twilio/sms-status`** — Twilio SMS delivery callback
- Auth: HMAC signature validation
- Input: Twilio's standard callback body
- Output (200): empty
- Idempotent on `(MessageSid, MessageStatus)`.

**`GET /api/pdfs/{pdf_id}`** — Signed PDF download
- Auth: HMAC signature in query (`?sig=...&exp=...`) — no API key required
- Output (200): `Content-Type: application/pdf`, body = PDF bytes
- Errors: invalid signature → 403; expired (`exp < now`) → 410 Gone; unknown pdf_id → 404
- Used by: SMS link target, handoff preview iframe in the frontend.

**`GET /healthz`** — Liveness probe
- Auth: none
- Output (200): `{version, db_pool_state, sentinel_status, speechmatics_status}`

**`GET /api/scenarios`** — List demo scenarios
- Auth: shared-secret
- Output (200): `[{id, label, duration_seconds, has_flag, flag_at_t, audio_url}]`

**`GET /api/patients/{id}/trends`** — Trend-tracking data (P3)
- Auth: shared-secret
- Output (200): three check-in summaries (week 6, 8, 12) for biomarker trajectories + concordance events.

**`GET /api/eval`** — Eval scorecard (P3)
- Auth: shared-secret
- Output (200): `{buckets: [{name, n, sensitivity, specificity, false_positive_rate, per_utterance: [...]}], generated_at}`

### 5.2 SSE Event Contract

Endpoint: `GET /api/calls/{id}/events` (`Accept: text/event-stream`, sse-starlette `EventSourceResponse`)

Each event is `event: <type>\nid: <ulid>\ndata: <json>\n\n`. Types:

| event | data shape | Trigger |
|---|---|---|
| `transcript` | `{t, speaker, text, is_final: true, confidence?}` | Speechmatics emits a final segment |
| `partial_transcript` | `{t, speaker, text, is_final: false}` | Speechmatics emits a partial segment |
| `biomarker` | `{t, layer, snapshots: {name: value, ...}}` | Sentinel emits a progress event |
| `concordance_trace` | `{t, transcript_min, acoustic_strain}` | every cadence tick |
| `flag` | `{flag_id, kind, t, contributing_signals, deterministic_payload}` | Deterministic gate or suicidal_content escalation |
| `rationale_token` | `{flag_id, token, driver_index?}` | LLM streams a token |
| `rationale_done` | `{flag_id, drivers: [str, str, str], confidence}` | LLM stream completes |
| `triage` | `{t, state, source, flag_id?}` | TriageState row inserted |
| `probe_saved` | `{flag_id, answers, score}` | Probes saved |
| `pdf_generated` | `{pdf_id, preview_url, download_url}` | PDF generation done |
| `sms_status` | `{pdf_id, sms_id, status: queued/sent/delivered/failed}` | Twilio status callback |
| `system` | `{kind: "signal_delayed", layer}` | Sentinel partial-payload degradation |
| `error` | `{kind, message}` | unrecoverable downstream failure |
| `end` | `{call_id, duration_seconds, summary}` | call ends; connection closes after |

Constraints:
- Connection survives Neon serverless reconnect (≤1s) without dropping the SSE stream.
- Heartbeat comment `: keepalive\n\n` every 15s to defeat proxy idle timeouts.
- Client disconnect detection cleans up per-call subscriber set.

### 5.3 WebSocket Contract — Audio Ingest

**`/ws/twilio/media`** — Twilio Media Streams consumer
- Protocol: Twilio's `text/json` WebSocket framing (`event: start | media | stop`)
- Frames: μ-law 8 kHz mono base64-encoded
- Server upsamples to PCM 16-bit 16 kHz mono using `audioop.ulaw2lin` + a SciPy resample (or `pydub` AudioSegment) — chosen for accuracy; fallback to `audioop.ratecv` if SciPy unavailable.
- Backpressure: bounded `asyncio.Queue` per connection; if downstream consumers fall behind by >2s, log a warning and drop the oldest frames (newer frames matter more for biomarker freshness).

**`/ws/audio/browser`** — Browser microphone consumer
- Protocol: binary frames, PCM 16-bit 16 kHz mono produced by an `AudioWorkletNode`
- Auth: query param `?token=<JWT>` where the JWT is issued by `POST /api/calls` in its response body. JWT signed with `JWT_SECRET` (HS256), single-use, scoped to the specific `call_id`, expires 1 hour after issue. Server rejects with WS close code 4401 on missing/invalid/expired token.
- Frame size: 4096 samples (matches `examples/02_combined_pipeline` chunk size)
- CORS: the WebSocket itself is cross-origin-permissive (browsers don't enforce CORS on WS), but the issuing `POST /api/calls` is locked by the CORS allowlist (see §7.2).

### 5.4 Fixture Contract

For `source=fixture`, the system reads `fixtures/{A|B|C}/audio.wav` (16 kHz mono PCM) and feeds it through the same downstream path as live audio at 1× real-time pace. Cached pipeline outputs (`fixtures/{A|B|C}/scenario.json` matching the existing `scenarios.jsx` shape) are used to produce identical SSE events when the live path is disabled (`FIXTURE_OFFLINE=true`), satisfying C3.

### 5.5 Speechmatics + Sentinel SDK Wrapping

**Speechmatics**: use `speechmatics.rt.AsyncClient` (the kit ships `speechmatics-rt>=1.0.0`). Configuration: `language="en"` (or sponsor-confirmed alt), `domain="medical"`, `operating_point=OperatingPoint.ENHANCED`, `diarization="speaker"`, `speaker_diarization_config=SpeakerDiarizationConfig(max_speakers=2)`. The first speaker to produce a final segment is mapped to `Clinician`. (See `examples/03_clinical_voice_monitor/run.py`.)

**Sentinel**: use `thymia_sentinel.SentinelClient(user_label, policies=["wellbeing-awareness"], biomarkers=["helios","apollo","psyche"], sample_rate=16000, language="en-GB")`. **Sentinel's `wellbeing-awareness` policy already returns `concordance_analysis` natively** — every `policy_result` event carries `result["concordance_analysis"]` with `scenario` ∈ {`concordance`, `minimization`, `amplification`, `mood_not_discussed`} and `agreement_level` ∈ {`none`, `mild`, `moderate`, `severe`} (confirmed in `examples/03_clinical_voice_monitor/run.py:147` and `examples/common/printing.py:21`). The deterministic gate AN-04 reads this output directly; we do not reimplement linguistic-acoustic mismatch detection. The same policy result also surfaces `wellbeing-awareness` severity levels (0–3) and suicidal-content flags for AN-06.

### 5.6 LLM Provider Contract

```python
from typing import AsyncIterator, Literal, Protocol
from pydantic import BaseModel, Field

class RationaleResult(BaseModel):
    drivers: tuple[str, str, str] = Field(
        description="Exactly three plain-English driver sentences. "
                    "Speak about voice signals, not patient state. "
                    "Translate biomarker names ('anhedonia' → 'voice signals reduced enjoyment')."
    )
    confidence: Literal["High", "Medium", "Low"]

class LLMProvider(Protocol):
    async def stream_rationale(
        self,
        transcript_last_30s: list[TranscriptSegment],
        biomarker_snapshot_at_flag: dict[str, float],
        sentinel_concordance: dict,  # {scenario, agreement_level}
        contributing_signals: list[str],
    ) -> AsyncIterator[PartialRationaleResult]: ...
```

Implementations:
- **`MistralRationaleProvider` (default)** — calls `mistralai.Mistral().chat.parse(model="mistral-medium-2026", response_format=RationaleResult, messages=[...], max_tokens=400, temperature=0.3)` for non-streaming. For streaming uses `instructor.from_provider("mistral/mistral-medium-2026")` with `Partial[RationaleResult]` per BR-020. System prompt enforces BR-014 (no `diagnose`/`detect`/`replace`, voice-signals language). Total prompt ≤800 tokens per BR-021.
- **`SentinelCustomPromptProvider`** — uses Sentinel's `executor: "custom_prompt"` (example 04 pattern). Stays within sponsor stack. Slower latency but tighter sponsor narrative. Use only if Mistral hits rate limits Saturday morning.
- **`MuseSparkRationaleProvider`** — placeholder Protocol implementation, raises `NotImplementedError` until Meta opens the API beyond private preview.
- **`StaticTemplateProvider`** — always-on fallback when AN-05's 10-second budget is exceeded or schema validation fails twice. Returns three pre-written sentences with deterministic-payload values substituted (`f"Voice strain at {distress:.2f} while words remained reassuring."`). Tagged `confidence: low`.

Provider selection is driven by `LLM_PROVIDER` env var (`mistral` | `sentinel` | `static`), defaulting to `mistral`.

### 5.7 Component Interfaces (Frontend)

The new Vite + React + TypeScript frontend mirrors the reference React-on-CDN app's component decomposition. Each component below maps 1:1 to a file in the reference (`src/app.jsx`, `src/ribbon.jsx`, `src/transcript.jsx`, `src/rightrail.jsx`, `src/modals.jsx`, `src/scenarios.jsx`, `src/primitives.jsx`).

**Component: `<App>`** — top-level shell, owns the `useCallStream(call_id)` hook that manages the single SSE connection and the in-memory call store.

**Component: `<TopStrip>`** — Top Clinical Strip per UI-SPEC.
- Props: `{callPhase, elapsed, scenario?, triage, flagFired, checkMute?, error?, tweaks}`
- States: `pre`, `ringing`, `connecting`, `live`, `ended`, `error`
- A11y: triage state always carries text label + status fill; demo-line chip uses spaced UK international format `+44 20 7946 0123`.

**Component: `<ConcordanceRibbon>`** — three-state ribbon per UI-SPEC and the reference `src/ribbon.jsx`.
- Props: `{state: "idle"|"thin"|"expanded", elapsed, scenario, flagFired, flagAt}`
- Renders an SVG with the two trace lines + divergence polygon fill + flag vertical guide.
- Animations: `idle → thin` (no animation), `thin → expanded` (~200ms ease-out, single soft pulse, no audio, no blinking).

**Component: `<TranscriptPanel>`** — diarized scrolling transcript.
- Props: `{state, elapsed, scenario, flagFired, flagAt}`
- Behavior: auto-scroll to newest; if user scrolls up, suspend and show `Resume live` chip; cluster around flag moment gets amber side rule + matching timestamp.

**Component: `<BiomarkerRail>`** — six fixed-order rows per UI-SPEC card 1.
- Props: `{state, scenario, elapsed, flagFired}`
- Refresh ~5s; contributing rows gain amber emphasis post-flag.

**Component: `<AssessmentCard>`** — three stable actions per UI-SPEC card 2.
- Props: `{state, flagFired, scenario, probesSaved, pdfState, pdfTimestamp, onWhyFlagged, onOpenProbes, onGenerate}`

**Component: `<WhyFlaggedSheet>`** — right-side sheet, streams the LLM rationale tokens via the parent's SSE store.

**Component: `<ProbesModal>`** — centred modal with three boxed questions; non-blocking scrim (live screen continues to update behind).

**Component: `<HandoffPreviewModal>`** — wide modal with read-only PDF render (server-side rendered HTML, displayed in an iframe or as styled HTML directly).

**Component: `<TrendTrackingScreen>`** (P3) — `/patients/:id/trends` route.

**Component: `<EvalScreen>`** (P3) — `/eval` route.

### 5.8 PDF Render + Storage Contract

PDF rendering uses **WeasyPrint** (mature, deterministic HTML→PDF, well-tested in clinical contexts). The HTML template is `backend/templates/handoff.html` rendered with Jinja2 from the persisted call record.

**Storage**: PDFs land on Render's persistent disk at `/data/pdfs/{pdf_id}.pdf`. The `handoff_pdfs.storage_path` column stores the absolute path. Render's free-tier persistent disk (1 GB) holds ~10,000 typical PDFs — far beyond hackathon needs.

**Signed download URLs**: served by FastAPI at `GET /api/pdfs/{pdf_id}?sig={hmac}&exp={unix_ts}`. The `sig` is HMAC-SHA256 of `f"{pdf_id}|{exp}"` keyed with `PDF_SIGNING_SECRET`. URLs expire 7 days after issue. The endpoint streams the PDF with `Content-Type: application/pdf` and `Content-Disposition: inline` (so the GP can preview in-browser before downloading). No auth required on this endpoint — security is in the signature.

Sections and order match UI-SPEC modal C exactly:
1. Header (Postnatal Pulse mark, `Postnatal Call Handoff Summary`, generated date/time, patient name + age, weeks postpartum, baby name + age, call date/time, total duration, sending clinician name)
2. Current triage (lozenge text, flag timestamp, handoff status)
3. Why this was flagged (2–3 sentence rationale + flag time)
4. Probe responses (3 questions with chosen answers, saved timestamp)
5. Transcript excerpt (6–10 diarized lines centered on flagged window, speaker label + timestamp per line)
6. Footer disclaimer (verbatim per UI-SPEC microcopy block)

Length target: one page. Spill to page two only for oversized transcript excerpts. Visual matches the editorial-clinical aesthetic (warm paper, deep-blue section rules, humanist sans, tabular numerals).

## 6. Business Rules

- **BR-001: Deterministic gate uses Sentinel concordance + postnatal cluster** — A `MINIMIZATION DETECTED` flag fires if and only if BOTH of the following are true within the same 20-second sliding window (re-evaluated each Sentinel policy result tick): (a) Sentinel's `wellbeing-awareness` policy result contains `concordance_analysis.scenario == "minimization"` AND `concordance_analysis.agreement_level ∈ {"moderate", "severe"}`; (b) the postnatal cluster check holds: `sleep_issues ≥ 0.60` AND (`low_energy ≥ 0.60` OR `anhedonia ≥ 0.55`). The 20-second window matches the lower bound of clinical voice-biomarker literature (Kintsugi 20s; Mazur et al. 2025 25s on n=14,898). Sentinel's own `concordance_analysis.scenario` is the linguistic-acoustic mismatch detector — we do not reimplement it. The cluster check is the postnatal domain filter that prevents this firing on, e.g., a tired junior doctor who happens to also minimize.
- **BR-002: LLM rationale latency budget** — From flag firing, the rationale stream begins within 1.5s and completes within 10s. If the budget is exceeded, the system emits a `StaticTemplateProvider` fallback marked `confidence: low` and the LLM call is logged as a degradation.
- **BR-003: Suicidal-content escalation bypasses concordance gate** — Sentinel's `wellbeing-awareness` suicidal-content flag at any point during the call immediately advances triage to `red` regardless of BR-001's state. This event is non-dismissable.
- **BR-004: Probe re-scoring is deterministic** — For each probe response, score = 0 (`Most days I rest` / `Yes, mostly` / `Plenty of support`), 1 (`Some days` / `Sometimes` / `Some help`), 2 (`Hardly ever` / `Not really` / `Mostly on my own`). Sum across three probes. Post-probe triage: `red` if sum ≥ 4 OR scenario is B (PLAN §"Scenarios"); else `amber` if BR-001 was true; else `green`.
- **BR-005: Triage severity ratchets up automatically; down only via dismiss** — Triage state transitions UP automatically per the state machine in §4.3. Triage can decrease only via explicit clinician dismiss (`POST /api/calls/{id}/flags/{flag_id}/dismiss`), one severity step at a time, with a recorded reason.
- **BR-006: Handoff PDF Send dispatches both PDF (via signed URL) and SMS** — `Send PDF` is the only action that dispatches the PDF outside the system. The SMS contains the triage label, a one-line summary, and the signed URL valid for 7 days.
- **BR-007: Banned strings in clinician-facing copy** — No clinician-facing string (frontend text, backend response messages, PDF templates) may contain the substrings `diagnose`, `detect postpartum`, `detects PPD`, `replaces clinician`, or `replace clinician` (case-insensitive). A static check enforces this on every release.
- **BR-008: Sentinel partial-payload degradation** — If a Sentinel response is missing a layer (e.g. `apollo` block absent), freeze the affected biomarker rows on their last good value, surface a `Signal delayed · {layer}` chip in the Top Clinical Strip, and skip BR-001's contribution from that layer until a complete payload returns. Do not zero out values; do not falsely fire flags.
- **BR-009: Speaker labels are stable for the call** — The first speaker to produce a final transcript segment is mapped to `Clinician`; the other speaker is `Patient`. This mapping does not change for the duration of the call even if Speechmatics' diarizer reassigns IDs.
- **BR-010: Demo-mode toggle is dev-only** — The `Shift+D` shortcut and the bottom-left scenario drawer are present only when the frontend bundle is built with `VITE_DEMO_MODE=true`. Production builds never expose them.
- **BR-011: Twilio webhook signature validation** — All Twilio webhook handlers reject requests where the `X-Twilio-Signature` header does not validate against the request URL + body using the configured Auth Token.
- **BR-012: SMS body fits in one segment when triage label + summary allow** — The SMS body template is constructed to fit ≤160 GSM-7 characters when the summary is ≤80 chars; otherwise it splits into multi-part messages, never truncates.
- **BR-013: Audio resample preserves fidelity** — The μ-law 8 kHz → PCM 16 kHz upsampler uses anti-aliasing-correct resampling (SciPy `resample_poly` or equivalent), not naive sample duplication. Sentinel and Speechmatics receive PCM 16 kHz indistinguishable in quality from a native 16 kHz capture.
- **BR-014: LLM never claims diagnosis** — The Mistral system prompt enforces three rules: (1) speak about voice signals, not patient state ("voice signals reduced engagement", not "patient has anhedonia"); (2) never use the words `diagnose`, `detect`, `replace`; (3) confidence is `High` only when the deterministic payload + transcript context + biomarker cluster all align. Output is JSON-validated against the `RationaleResult` schema; non-conforming responses trigger a single retry then fall through to `StaticTemplateProvider`.
- **BR-015: One concurrent call per deployment** (v1 scope, A5) — The system rejects `POST /api/calls` with 409 Conflict if another call is currently in `live` state. The trend-tracking screen reads from completed calls only.
- **BR-016: Tuner ingestion is non-blocking** — The Tuner post-call ingestion runs in a fire-and-forget background task. It must never delay `POST /api/calls/{id}/end` returning, never block SSE, and never surface errors to the UI.
- **BR-017: PDF artifacts are immutable** — Once a `HandoffPDF` row is created, its `storage_path` content does not change. Re-generating produces a new row with a new `id`.
- **BR-018: Fixture replay is bit-for-bit deterministic** — Two consecutive runs of the same fixture produce identical transcript segments, identical biomarker snapshots, identical flag fire timestamps, and identical PDF bytes. This satisfies G4 and X-01.
- **BR-019: Visual ribbon traces are not the gate** — The `transcript_min` and `acoustic_strain` channels rendered in the Concordance Ribbon (AN-03) are visualization-only. They never independently fire a flag. The flag firing decision is owned by BR-001 (Sentinel concordance + postnatal cluster). The ribbon traces exist solely to make the divergence visible to the midwife in real time.
- **BR-020: LLM uses Mistral structured output, not free text** — The rationale generation calls `mistralai.Mistral.chat.parse(model="mistral-medium-2026", response_format=RationaleResult, ...)` with a Pydantic `RationaleResult` schema (BaseModel containing `drivers: tuple[str, str, str]` and `confidence: Literal["High", "Medium", "Low"]`). For streaming, use the `instructor` library's `Partial[RationaleResult]` pattern (`instructor.from_provider("mistral/mistral-medium-2026")`). Schema-violating responses trigger one retry then fall through to `StaticTemplateProvider` per BR-002.
- **BR-021: LLM prompt context window is bounded** — The Mistral prompt receives the last 30 seconds of transcript (clinician + patient turns) and the biomarker snapshot at flag-fire moment, plus a system prompt enforcing BR-014. Total prompt budget ≤800 tokens to keep first-token latency under 1.5s on `mistral-medium-2026`.

## 7. Non-Functional Requirements

### 7.1 Performance
- UI banner render after deterministic flag fire: p99 ≤ 250 ms (measured from gate fire to first paint on the frontend).
- LLM rationale stream first token: p99 ≤ 1.5 s.
- LLM rationale stream completion: p99 ≤ 10 s; falls through to static template at 10 s exactly.
- Twilio call → first audio frame downstream of upsampler: p99 ≤ 3 s.
- Audio frame upsampler latency: p99 ≤ 50 ms per frame.
- PDF generation: p99 ≤ 1.5 s.
- SSE message delivery (server emit → client receive on local network): p95 ≤ 100 ms.
- SMS dispatched after `Send PDF` click: ≤ 90 s end-to-end.

### 7.2 Security
- Authentication: shared-secret `X-API-Key` for all `/api/*` endpoints except `GET /api/pdfs/{pdf_id}` which uses HMAC-signed URLs (single key for the demo; rotate after the hackathon if deployed beyond).
- Twilio webhooks: HMAC signature validation enforced (`X-Twilio-Signature`).
- Browser audio WebSocket: short-lived JWT (HS256, signed with `JWT_SECRET`) issued by `POST /api/calls`, single-use, scoped to one `call_id`, expires 1 hour after issue.
- **CORS allowlist**: `CORS_ALLOWED_ORIGINS` env var holds a comma-separated list. Default for Saturday: `http://localhost:5173,https://*.vercel.app,https://postnatal-pulse.vercel.app`. The `*.vercel.app` glob covers preview deployments. FastAPI middleware (`CORSMiddleware`) enforces; any origin outside the list is rejected with no `Access-Control-Allow-Origin` header.
- No PHI handling required for v1 (Maya Patel is fixture data). If extended past v1, NHS IG Toolkit compliance + DTAC assessment.
- Signed download URLs for PDFs: 7-day expiry, HMAC-SHA256 signed with `PDF_SIGNING_SECRET`, single-resource scope, no path traversal possible (pdf_id is a UUID validated against the table).
- LLM provider: outbound calls go to Mistral's API only by default; no transcript leaves the system to any other vendor unless `LLM_PROVIDER` is explicitly switched.

### 7.3 Accessibility
- WCAG AA contrast in every state.
- Triage state, concordance state, and speaker identity never colour-only — each carries text label and stable positional cue.
- All modals keyboard-reachable, focus-trapped, dismissible with `Esc`, return focus to trigger element on close.
- Live updates never steal input focus; auto-scroll yields when user scrolls up.
- Tab order: Top Clinical Strip → Concordance Ribbon → Transcript → Right rail.
- Motion is brief and functional. One soft pulse on flag entry. Nothing flashes.

### 7.4 Scalability
- v1 designed for 1 concurrent call (A5, BR-015). Single Render service instance.
- Trend-tracking and eval screens are read-only against persisted data; safe under any read load.
- Neon Postgres pooled connection: PgBouncer fronting Postgres; pool sized 5 in app, infinite at PgBouncer.

### 7.5 Reliability
- Render auto-restart on crash; `/healthz` liveness probe.
- Fixture replay path runs fully offline (`FIXTURE_OFFLINE=true`) — no external API calls for the hero scenario, satisfying C3.
- Sentinel partial-payload degradation per BR-008.
- LLM 10-second budget fall-through per BR-002.
- Neon serverless reconnect handled by `pool_recycle=300` + `pool_pre_ping=True` (R3).

### 7.6 Observability
- **Tuner** (https://app.usetuner.ai) — voice-AI call observability; receives a post-call summary per call. **Gated by `TUNER_ENABLED` env var, default `false` for Saturday's deploy.** Flip to `true` only after cold-viewer test #1 passes if you want it running during the live demo. Captures intent, outcomes, behavior quality, latency budgets, deterministic-vs-LLM agreement, error counts. See X-08.
- **Local logging** — structured JSON logs (loguru) for every call event, every flag fire, every LLM call (provider, latency, token count, fall-through decisions). One log line per SSE event, one line per Sentinel response (truncated if large).
- **Metrics endpoint** — `GET /metrics` exposes Prometheus-format counters for: calls started/ended, flags fired by kind, LLM provider invocations and latencies, Sentinel partial-payload events, Twilio webhook validations failed, SMS dispatch successes/failures.

## 8. UI/UX Specifications

UI-SPEC.md is the authoritative source for visual design, microcopy, motion, and the eight demo flow states. The frontend implementation must satisfy every rule in that document plus the verifications in §3.5.

### 8.1 User Flows

**Flow: Live call with minimization detected (hero scenario)**
1. Midwife sees `Pre-call empty` state with patient context preloaded and demo line enlarged.
2. Twilio call arrives → Top strip flips to `Inbound call ringing`, demo-line block inverts to clinic blue with a single soft pulse.
3. Midwife (or auto-pickup) → `Connecting / first 5s`. Concordance Ribbon becomes thin two-line timeline. Transcript shows `Listening...` placeholders. Biomarker rows read `Warming up`.
4. Audio flows → `Idle (active call, no flag)`. Triage `green`. Transcript autoscrolls. Biomarkers refresh ~5s. Concordance lines track each other quietly.
5. Trigger window arrives → ribbon divergence visibly grows (acoustic strain climbs while transcript minimization stays flat).
6. Deterministic gate fires → ribbon expands to `MINIMIZATION DETECTED` banner with single soft pulse, triage lozenge crossfades to `Amber: review`, transcript cluster around trigger gains amber side rule, contributing biomarker rows gain amber emphasis, `Why flagged?` and `Open 3 probes` become primary buttons.
7. LLM rationale streams into the right rail (and into Why-flagged sheet if opened).
8. Midwife clicks `Open 3 probes` → modal appears over a continuing live screen (transcript + biomarkers keep updating behind scrim). Midwife reads each question aloud, taps the patient's response.
9. Midwife clicks `Save responses` → modal closes, triage re-classifies (likely `Amber: review` or `Red: urgent review` depending on answers), right-rail rationale and handoff block rewrites against saved probe answers.
10. Midwife clicks `Generate handoff PDF` → preview modal opens. Midwife clicks `Send PDF` → modal closes, right-rail action becomes `PDF generated · 19:42` then `Sent · 19:42` after Twilio confirms.
11. Call ends → top strip changes to `Call ended` with total duration. Transcript and biomarker rows freeze. Rationale and handoff stay readable.

**Flow: Browser-mic fallback** — identical to above starting from step 3, except the audio source is the laptop microphone via `AudioWorkletNode` instead of Twilio.

**Flow: Deterministic replay** — identical to above, except no live API calls; SSE events are emitted from the cached fixture timeline at 1× pace. The replay can be triggered with `Shift+D` → pick scenario, satisfying X-01 and PLAN's pre-judging fallback.

**Flow: Sentinel signal delayed** — identical until Sentinel returns a partial payload; at that moment the affected biomarker rows freeze, a `Signal delayed · apollo` chip appears in the Top Clinical Strip, the deterministic gate skips the affected condition. When a complete payload returns, rows unfreeze and the chip disappears.

### 8.2 Responsive Behavior
- v1 viewport: minimum 1280px wide (matches reference frontend's `min-width: 1280px`). Mobile/tablet out of scope.
- Desktop window resizing within ≥1280px: layout fluidly grows the transcript panel; right rail stays fixed at 400px.

## 9. Implementation Notes

> These are recommendations. The declarative sections above are authoritative. An agent may deviate if it has good reason and the underlying constraint is preserved.

**Stack choices and rationale:**

- **Backend: Python 3.13 + FastAPI** (latest stable 2026, with native `EventSourceResponse`). `uv` for dependency + venv management (`uv sync`, `uv run`). See R1.
- **Async runtime: `uvicorn` with `uvloop`** behind Render's HTTPS proxy. Single worker for v1 (BR-015's one-concurrent-call constraint means no need for multi-worker SSE pub/sub yet).
- **STT SDK**: `speechmatics-rt>=1.0.0` (the kit's verified version). Pattern from `examples/03_clinical_voice_monitor/run.py`.
- **Voice biomarkers SDK**: `thymia-sentinel>=1.1.0` (kit verified). Pattern from `examples/02_combined_pipeline/run.py` for live mic + `examples/04_custom_policy/run.py` for the custom policy scaffolding (we replace the LLM `executor: "custom_prompt"` with our deterministic gate).
- **LLM client**: `mistralai>=1.5` Python SDK + `instructor>=1.5` for streaming `Partial[RationaleResult]`. Wrapped behind `LLMProvider` Protocol (§5.6). Confirmed pattern: `mistralai.Mistral().chat.parse(response_format=PydanticModel)` for non-streaming; `instructor.from_provider("mistral/mistral-medium-2026")` for streaming partials.
- **DB**: Neon serverless Postgres + `psycopg[binary,pool]>=3.2` + SQLModel (or SQLAlchemy 2.x async). Pool config: `pool_recycle=300`, `pool_pre_ping=True` to survive Neon's 5-min idle suspend (R3).
- **Migrations**: Alembic, two migrations to start (initial schema; trend-tracking fixtures).
- **SSE**: `sse-starlette>=2.1` (production-grade, automatic disconnect detection, multi-loop safe). FastAPI's native `EventSourceResponse` is also acceptable; choose whichever lands faster.
- **Audio resampling**: `scipy.signal.resample_poly` for the μ-law 8 kHz → PCM 16 kHz step (BR-013).
- **PDF**: `weasyprint>=63` (mature, deterministic, well-tested). `Jinja2>=3.1` for the HTML template.
- **Twilio**: `twilio>=9.4` Python SDK (latest as of April 2026) — request validator + Voice + SMS.
- **Frontend**: Vite 6 + React 19 + TypeScript 5.6. Routing via `react-router@7` (data routers). State via Zustand (light, predictable, easy to wire to SSE). EventSource via the browser native API (no library). HTTP via `ky` (light fetch wrapper). PDF preview rendered as styled HTML in an iframe (server returns the same HTML used for WeasyPrint, so preview = production PDF).
- **Type-safe contract between backend and frontend**: generate TypeScript types from FastAPI's OpenAPI schema using `openapi-typescript@7` at build time (`bun run gen:api`). Pydantic models on the backend are the single source of truth.
- **Observability**: `loguru>=0.7` for structured logging; `prometheus-client>=0.21` for metrics; `httpx>=0.27` for the Tuner ingestion call.
- **Test runner**: `pytest>=8.3` + `pytest-asyncio>=0.24` for unit/integration; `playwright>=1.49` for the cold-viewer-equivalent UI smoke tests; `httpx.AsyncClient` for FastAPI test client.
- **Code style**: `ruff>=0.7` (lint + format), `mypy --strict` for backend.

**Repository layout:**

```
voice-hackathon/
├── backend/
│   ├── pyproject.toml         # uv-managed
│   ├── src/postnatal_pulse/
│   │   ├── main.py            # FastAPI app
│   │   ├── api/               # REST + SSE + WS routes
│   │   ├── audio/             # Twilio + browser ingest, upsampler
│   │   ├── analysis/          # Speechmatics + Sentinel wrappers, deterministic policy
│   │   ├── llm/               # LLMProvider + Mistral impl + StaticTemplate fallback
│   │   ├── storage/           # SQLModel + Alembic
│   │   ├── pdf/               # WeasyPrint + Jinja2 templates
│   │   ├── observability/     # Tuner adapter, loguru, prometheus
│   │   └── fixtures/          # A/B/C audio + cached pipeline outputs
│   ├── templates/handoff.html # the WeasyPrint template
│   ├── tests/
│   └── alembic/
├── frontend/
│   ├── package.json           # bun-managed
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/        # TopStrip, ConcordanceRibbon, TranscriptPanel, BiomarkerRail, AssessmentCard, modals
│   │   ├── hooks/             # useCallStream (SSE + Zustand)
│   │   ├── api/               # generated types + ky client
│   │   ├── routes/            # /, /patients/:id/trends, /eval
│   │   └── styles/            # tokens matching reference frontend
│   └── public/
└── reference-frontend/        # the unzipped Voice Hackathon.zip — kept for diffing
```

**Deploy:**
- Backend: Render (Docker, single service). WebSocket + Twilio webhook support is verified on Render.
- Frontend: Vercel static (or Render static) with `VITE_API_BASE_URL` env var pointed at the Render backend URL.
- DB: Neon Postgres (serverless free tier; pooled connection string).
- Secrets/env vars (Render dashboard):
  - `SPEECHMATICS_API_KEY`, `THYMIA_API_KEY`, `THYMIA_SERVER_URL` (defaults `wss://ws.thymia.ai`)
  - `MISTRAL_API_KEY`, `LLM_PROVIDER` (default `mistral`)
  - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
  - `NEON_DATABASE_URL` (pooled connection string, ends in `-pooler.aws.neon.tech`)
  - `API_KEY` (X-API-Key shared secret)
  - `JWT_SECRET` (HS256 key for browser-mic WS tokens)
  - `PDF_SIGNING_SECRET` (HMAC key for signed PDF URLs)
  - `CORS_ALLOWED_ORIGINS` (comma-separated)
  - `TUNER_API_KEY`, `TUNER_ENABLED` (default `false`)
  - `FIXTURE_OFFLINE` (default `true` for first deploy → no live API calls; flip to `false` for live demo)
  - `VITE_API_BASE_URL`, `VITE_DEMO_MODE` (frontend, set in Vercel)

**Build order matching PLAN's Saturday schedule:**
1. Skeleton FastAPI + uv setup, `/healthz` returns 200, Neon connected, migrations apply (≤30 min).
2. Fork `examples/02_combined_pipeline` into `analysis/`; verify Speechmatics + Sentinel return data on the hero clip (PLAN 10:30–11:30).
3. Replace `examples/04_custom_policy` LLM executor with the deterministic gate; verify it fires on the hero clip three times in a row (PLAN 11:30–12:30).
4. Wire SSE; render the existing reference frontend pointed at the SSE stream first (the React-on-CDN bundle works as a smoke test for the contract); then start the Vite/TS rewrite from the same data shape (PLAN 12:30–14:30).
5. Probe-and-reclassify (PLAN 13:30–14:30).
6. Twilio inbound + browser-mic fallback (PLAN 14:30–15:00).
7. LLM rationale streaming + Why-flagged sheet (PLAN 15:00–15:30).
8. Cold-viewer test #1 (PLAN 15:30).
9. Eval harness page if cold test passed (PLAN 16:00–17:00).
10. Trend-tracking screen if ahead (PLAN 17:00–17:30).
11. **Hard feature freeze 17:30**. PDF + SMS + reliability bug bash (PLAN 17:30–19:00).
12. Cold-viewer test #2 + pitch rehearsal (PLAN 19:00–19:30).
13. Submission (PLAN 20:00–21:00).

## 10. Design Rationale Appendix

**R1: Why FastAPI + native SSE**
- Supports: §5.2, FE-15
- Original choice: User specified FastAPI 2026 with modern features.
- Underlying concern: We need a single-direction server→client streaming channel for transcript + biomarker + flag + LLM-token events. WebSocket is overkill (the UI never sends back through this channel — REST handles dismiss/probe/end), adds reconnect complexity, and is harder behind proxies.
- Acceptable alternatives: WebSocket on the same path with a typed message envelope (would also work but doubles failure surface).
- Unacceptable alternatives: Long-polling (loses token-streaming UX); pure REST with polling (kills the "live" feel that earns the demo).

**R2: Why deterministic gate first, LLM enriches**
- Supports: BR-001, BR-002, AN-04, AN-05
- Original choice: PRD §6 explicitly rejected LLM-evaluated policies on three grounds: 500–2000ms latency, hallucination/refusal risk during a live demo, per-call API spend.
- Underlying concern: The flag firing on the same wall-clock as the trigger transcript line is THE memorable demo beat. Anything that introduces multi-second variability between "I'm fine" being said and `MINIMIZATION DETECTED` appearing kills the impact.
- Acceptable alternative: LLM-only with sub-second guaranteed latency (no current model meets this for our payload size).
- Unacceptable alternative: LLM gates the flag (the user's "both" answer was specifically about division of labour — deterministic decides, LLM explains).

**R3: Why Neon Postgres + connection pool tuning**
- Supports: §7.5, DB-08
- Original choice: User has Neon access; modern serverless Postgres pattern.
- Underlying concern: Neon's compute auto-suspend after 5 minutes idle could drop connections mid-call. A naive SQLAlchemy pool will hand out a stale connection and fail the next query.
- Acceptable alternative: Render's managed Postgres (no idle suspend, but no branching).
- Unacceptable alternative: SQLite (kills the trend-tracking screen and complicates Render deploys with persistent disk).
- Mitigation: `pool_recycle=300` aligns with Neon's 5-minute auto-suspend; `pool_pre_ping=True` adds a single-round-trip health check before each checkout. The cost (one round-trip per query) is acceptable at v1's load.

**R4: Why Vite + React + TS instead of keeping React-on-CDN**
- Supports: §3.5, §5.7, FE-16
- Original choice: User specified rewrite for "modern features and good UX."
- Underlying concern: The reference React-on-CDN file is excellent design but couples runtime data, types, and component code into one bundle. Type-safe SSE event handling is a clear win for hackathon iteration speed. Vite + React 19 + TS gives hot reload, generated types from FastAPI's OpenAPI schema, and matches modern frontend tooling 2026.
- What we preserve: The reference's component decomposition (TopStrip, ConcordanceRibbon, TranscriptPanel, BiomarkerRail, AssessmentCard, three modals), all microcopy, all aesthetic tokens (colours, fonts, spacing, animations). The Vite rewrite is a skin migration, not a redesign.
- Unacceptable alternative: Next.js (over-kill; adds SSR complexity we don't need; bigger bundle).

**R5: Why WeasyPrint for the PDF**
- Supports: §5.8, BE-04
- Original choice: WeasyPrint is the well-tested HTML→PDF library in Python that handles the editorial-clinical aesthetic (tabular numerals, custom fonts, structured page layout) without a headless browser dependency.
- Acceptable alternatives: `playwright` headless print-to-PDF (heavier dep but pixel-perfect); `reportlab` (more code, less idiomatic).
- Unacceptable alternative: Generate PDF in the browser (the GP-handoff flow needs server-side generation so the SMS link points at a stable URL the GP can open without our frontend running).

**R6: Why one SSE channel instead of separate streams per signal type**
- Supports: FE-15
- Original choice: User answered "SSE and check latest docs of FastAPI" — implying they want the clean built-in pattern, not multi-stream architecture.
- Underlying concern: Multiple long-lived connections per call multiply browser/proxy/server failure surface and complicate timestamp alignment for the "shared time" signal that UI-SPEC calls out as the single non-mockup signal (W18).
- Acceptable alternative: Two streams — one for high-frequency audio events, one for low-frequency UI-state events. Adds complexity without improvement.

**R7: Why Tuner over a generic OTel/Langfuse stack**
- Supports: §7.6, X-08
- Original choice: User has Tuner beta access; Tuner is voice-AI-specific observability.
- Underlying concern: Generic LLM observability tools (Langfuse, Arize) capture the LLM call but miss the call-level intent/outcome story Tuner is built around. For a voice-AI hackathon project, Tuner's call-summary view aligns naturally with how judges and reviewers would assess the system.
- Acceptable fallback: Langfuse self-hosted if Tuner ingestion is unstable.
- The integration is gated by `TUNER_ENABLED` so removing it is a one-env-var change.

**R8: Why a separate `/metrics` Prometheus endpoint when Tuner exists**
- Supports: §7.6
- Original choice: Tuner is call-level analytics. `/metrics` is system-level operations (request counts, latencies, error rates, pool state). Both have a job and they don't overlap.
- The two-source observability split lets us keep the "is the system healthy right now" surface (Render dashboard + Prometheus scrape) cleanly separate from the "how good were the voice analyses" surface (Tuner).

**R9: Why uv for backend, bun for frontend**
- Supports: §9 stack choices
- Original choice: User's global rules require `uv run` / `uv add` for Python and `bun run` / `bun add` for Node.
- The toolchain is fast, well-tested at 2026 maturity, and gives reproducible installs across the two-laptop demo setup.

## 11. Open Questions

The decisions below are everything still genuinely open. The spec carries documented defaults for each so build is non-blocking.

### Sponsor-confirmation needed (target: 10:30 Saturday with Stefano)

- **Q-1**: Which Sentinel biomarker labels are sponsor-approved for on-screen citation? (PLAN sponsor recon Q1.) Default: the six labels in UI-SPEC card 1 (Fatigue, Sleep issues, Low energy, Anhedonia, Distress, Stress). Stefano may prefer alternatives.
- **Q-2**: For multilingual passthrough X-07 — Punjabi or Polish, and is the model performance sponsor-confirmed for clinical use? (PLAN sponsor recon Q4.) Default: X-07 stays in spec but is removed from the §3 matrix and not implemented if Stefano (or Discord `#thymia` channel) cannot confirm by 11:00 Saturday.
- **Q-3**: Is "concordance check" the right framing in the UI, or does Stefano prefer "voice-text mismatch" given the decision-support framing? Default: "MINIMIZATION DETECTED" headline + "concordance" in supporting copy. Rename pass takes <30 min if Stefano asks for it.

### Verify on the ground Saturday

- **Q-4**: Mistral rate limits on `mistral-medium-2026` — does our key support sustained streaming at the demo cadence? Default: budget one rationale call per flag fire (≤3 flags per 4-min demo run = well within typical limits). Verify with a synthetic test before 12:00. If rate-limited, switch `LLM_PROVIDER=sentinel` to use Sentinel's `custom_prompt` executor instead.
- **Q-5**: Does the Twilio number printed on the demo line (UI-SPEC top strip) display the real provisioned number or the placeholder `+44 20 7946 0123`? Default: production build reads `TWILIO_PHONE_NUMBER` env var; demo build uses the placeholder. Pre-judging checklist confirms which is rendered.
- **Q-6**: Render persistent disk provisioning — does it activate immediately on the free plan, or require a paid upgrade? Default: provision Saturday morning during deploy block; if free tier blocks it, fall back to Cloudflare R2 (15 min config) or in-memory storage for the single demo call (PDFs are regenerated on demand).

### Deferred to post-cold-viewer-test

- **Q-7**: Trend-tracking screen X-05 — ship if cold-viewer test #1 (15:30 Saturday) passes; cut if it fails. Same gate for the eval harness page X-06 and Tuner observability X-08. PLAN's decision tree governs.
- **Q-8**: Should we render the LLM rationale tokens as they arrive (smoother UX) or buffer until each driver sentence is complete (cleaner reading)? Default: stream by token within `Partial[RationaleResult]`; visible character-by-character per driver. Switch to sentence-buffered if cold viewers find streaming distracting.

## 12. Glossary

- **Adjunct decision-support**: a tool that surfaces signal to a clinician for review. Never autonomous, never diagnostic. The regulatory framing this product operates under.
- **Concordance**: agreement between what is said (transcript content) and how it is said (acoustic affect). High concordance = words match voice. Low concordance ("minimization") = words sound calm while voice carries distress.
- **EPDS (Edinburgh Postnatal Depression Scale)**: the ten-question self-report used in the existing 6-week postnatal call. EPDS sensitivity 81%, specificity 88% at cutoff ≥11; PPV 0.25–0.40 in routine primary care. We layer alongside, do not replace.
- **Fixture mode**: a deterministic replay of a stored audio + cached pipeline outputs for one of three canned scenarios (A/B/C). Used for the demo fallback and offline development.
- **Helios / Apollo / Psyche**: Thymia Sentinel's three biomarker layers. Helios (wellness, 0-1 scores including distress, stress, fatigue, burnout, low_self_esteem). Apollo (PHQ-9 + GAD-7 aligned clinical). Psyche (real-time affect, ~5s update cadence).
- **MINIMIZATION DETECTED**: the headline UI banner that appears when the deterministic concordance gate fires. The product's signature moment.
- **Probe**: one of three structured follow-up questions the system surfaces when a flag fires. Probes are boxed multiple-choice only; no free text. Map to PHQ-9 dimensions Apollo already scores.
- **Triage state**: one of `awaiting`, `green: routine`, `amber: review`, `red: urgent review`. The midwife's at-a-glance status.
- **Wellbeing-awareness policy**: a Sentinel pre-built policy with four severity levels plus suicidal-content flags. Runs in parallel with our deterministic gate; suicidal-content escalates triage to red regardless of concordance.

---

## Transformation Report

### Coverage

- Knowledge Ledger items: 19 wisdom + 11 constraints + 7 environmental assumptions + 7 end goals + 10 open questions = 54 total
- Represented in spec: 54 (every ledger item maps to a section, BR, FE/BE/AN/DB row, or rationale)
- Intentionally omitted: 0
- New items surfaced during transformation: 8
  - State machine for flag lifecycle (was implicit across UI-SPEC + frontend code; now §4.3)
  - PDF byte-stability constraint (BR-017 — implicit in PLAN's deterministic-replay requirement)
  - SSE keepalive heartbeat (§5.2 — required to defeat proxy idle timeouts on Render)
  - Tuner non-blocking constraint (BR-016 — implicit user requirement; spec calls it out)
  - LLM JSON-schema validation + retry (BR-014 — implicit safety requirement; spec makes it explicit)
  - Audio backpressure policy (§5.3 — implicit ops concern; spec specifies bounded queue + drop-oldest)
  - Twilio webhook signature validation (BR-011 — implicit; spec promotes to a business rule)
  - Speaker-mapping stability (BR-009 — implicit clinical UX; spec promotes to BR)

### Feature-Verification Matrix

- System layers identified: Audio Ingest, Analysis, Persistence & Storage, Backend API, Frontend, Cross-Layer
- Total features: 50 (AI: 4, AN: 6, DB: 8, BE: 11, FE: 16, Cross: 8)
- Spec sections with verification coverage: every Interface Contract (§5.1–§5.8) and every Business Rule (§6) traces to at least one matrix row.
- Spec sections without verification coverage: none.

### Key changes

- 9 imperative procedures (PLAN's Saturday schedule, PRD's solution sketch, UI-SPEC's flow states) → declarative state machines, business rules, and verification outcomes.
- 11 implicit business rules → explicit BR-001 through BR-018.
- Stack choices preserved with rationale (R1–R9) — every framework choice has an "underlying concern" articulated, so the build agent can substitute equivalents that satisfy the same concern.
- 8 edge cases surfaced that were implicit in the imperative source: signal-delayed degradation with affected-condition skipping (BR-008 + X-04), speaker-mapping stability (BR-009), audio backpressure (§5.3), LLM budget fall-through (BR-002), PDF byte-stability (BR-017), SSE keepalive (§5.2), Twilio signature validation (BR-011), Tuner non-blocking ingestion (BR-016).
- The reference React-on-CDN frontend is preserved as `reference-frontend/` and treated as the visual + microcopy + motion source of truth (FE-01 verifies layout parity within ±4px).

### What agents will do differently with this spec

- The deterministic policy is implemented in pure Python with sub-100ms latency and no LLM dependency on the hot path; LLM enriches asynchronously over SSE. Agents won't reach for `executor: "custom_prompt"` even though example 04 makes it the obvious shortcut.
- Frontend rebuild starts from the reference `src/*.jsx` files for component decomposition + microcopy + motion (FE-01), but generates types from FastAPI's OpenAPI schema for type safety. Agents won't redesign the visual language while rewriting.
- Sentinel partial-payload handling is a first-class business rule (BR-008) with explicit UI behavior (X-04). Agents won't silently zero-out missing values or false-fire flags.
- PDF generation is server-side and byte-stable (BR-017, R5). Agents won't put PDF generation in the browser even though it's faster to ship.
- Triage severity ratchets up automatically and decreases only via explicit dismiss (BR-005, §4.3). Agents won't silently downgrade a red flag when the next biomarker reading drops.

### Items that need your attention

See §11 Open Questions. The most schedule-critical:
- Q-3 (multilingual) — confirm by 11:00 Saturday or X-07 drops out.
- Q-4 (Mistral vs Sentinel custom_prompt) — confirm at venue with Stefano.
- Q-9 (Mistral rate limits) — verify quotas Saturday morning before relying on streaming rationale in the live demo.
