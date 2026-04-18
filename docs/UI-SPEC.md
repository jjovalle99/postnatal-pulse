# Postnatal Pulse — UI Specification

A voice-first adjunct triage tool for the NHS midwife's 6-week postnatal phone call. The midwife sees one screen during the call. The screen shows what the patient is saying, how she's actually sounding, and surfaces the gap when reassuring words don't match a distressed voice.

This spec is declarative. It defines what's on screen, hierarchy, behavior, and aesthetic intent. Pixel coordinates, exact RGB values, and Tailwind classes are render decisions and stay out.

---

## Aesthetic intent

Editorial / clinical. The product feels designed by someone who has actually met a midwife. It is humane without being a wellness app, operational without being Epic. Production-grade NHS-adjacent tooling, not a hackathon mockup.

- **Background:** warm paper tone (off-white with a hint of warmth — not pure white, not grey)
- **Structural accent:** deep clinic blue (NHS-adjacent without cloning)
- **Dividers:** cool slate
- **Body text:** strong ink (near-black, not pure black)
- **Status colours:** green / amber / red reserved almost exclusively for triage and concordance alert states. Never decorative.
- **Typography:** Frutiger-adjacent humanist sans throughout. Open apertures. High legibility. Tabular numerals for the timer, score chips, and any digit run. No geometric SaaS font. No serif display moments.
- **Spacing:** generous, procedural. Density is not a virtue here. The midwife is on a call — she glances at this screen, she does not read it.
- **Motion:** brief and functional only. One soft pulse on flag entry. No blinking. No flashing. No spinners that spin forever.

---

## The one screen

```
┌────────────────────────────────────────────────────────────────────────┐
│  TOP CLINICAL STRIP                                                    │
│  [Triage lozenge] [Patient context]              [Call status] [Demo line]
├────────────────────────────────────────────────────────────────────────┤
│  CONCORDANCE RIBBON  (thin live timeline → amber banner when fired)    │
├──────────────────────────────────────────┬─────────────────────────────┤
│                                          │  CLINICAL SIGNALS           │
│                                          │  (6 fixed-order biomarkers) │
│                                          │                             │
│           LIVE TRANSCRIPT                ├─────────────────────────────┤
│           (diarized, scrolling,          │  ASSESSMENT & HANDOFF       │
│            timestamped)                  │  · Why flagged?             │
│                                          │  · Open 3 probes            │
│                                          │  · Generate handoff PDF     │
│                                          │                             │
└──────────────────────────────────────────┴─────────────────────────────┘
```

No tabs. No nav rail. No settings page. No patient queue. No avatar. No mascot. No mood emoji. No decorative analytics. If a surface does not show timestamped evidence, current system state, or a clinician action, it does not belong on this screen.

---

## Top Clinical Strip

Single horizontal band across the top.

**Left half** (visually dominant):
- `Triage lozenge` — primary at-a-glance status. States: `Awaiting call` / `Green: routine` / `Amber: review` / `Red: urgent review`. Lozenge shape, status colour fill, tabular timestamp underneath ("flagged 02:14"). Never colour-only — always paired with the text label.
- `Patient context` — small but present. Multiple short strings, comma-separated or chip-stacked: `Maya Patel, 29` · `6 weeks postpartum` · `First baby` · `Baby: Leo Patel, 6 weeks` · `Routine postnatal follow-up`.

**Right half:**
- `Call status` — `Call live` with running timer in tabular numerals; replaces with `Inbound call ringing` / `Connecting...` / `Call ended` as appropriate. `Check mute` chip appears only when relevant.
- `Demo line` — dedicated inset block, far right. Contains the Twilio number formatted as spaced UK international (`+44 20 7946 0123` style — never raw digits). Larger numerals pre-call and during ringing. Drops one size step once the call is live so it reads as metadata, not the focus.

**No QR code.** Judges dial faster than they scan, and a QR code reads as demo apparatus rather than clinical UI.

---

## Concordance Ribbon (the memorable element)

Full-width strip immediately below the Top Clinical Strip. Always present.

**Thin state** (default during a live call):
- A literal live microtimeline plotting two lines on shared time: a `transcript minimization signal` line and an `acoustic distress / affect strain` line.
- Restrained, low-contrast, blue-slate. About one row tall.
- Label on the left: `Concordance stable`.
- The two lines track each other quietly when nothing is firing.

**Divergence state:**
- When the acoustic line stays elevated while the transcript line stays flat, the gap fills with restrained amber. The midwife can see the divergence happening before the formal flag fires.

**Expanded state** (`MINIMIZATION DETECTED`):
- Smooth ~200ms expansion into a full-width amber banner.
- Banner content: `MINIMIZATION DETECTED` (primary), with the single instruction line `Review rationale and ask 3 probes.`
- The recent trace remains faintly visible behind the label, anchoring the alert to the live evidence.
- Single soft pulse / elevation on entry, then static. **No audio. No blinking. No auto-opening modals.** The midwife is on a call with the patient — the patient must not hear an alert sound.
- Persistence: stays expanded until call end. If triage subsequently escalates to red, the lozenge carries that severity but the ribbon remains the anchor for the flagged event.

---

## Live Transcript (left main panel)

Dominant by visual area. The clinical record of the call as it happens.

- Diarized rows, each labeled `Clinician` and `Patient` (text labels, not colour-only). Subtle side rule beside each row reinforces speaker identity.
- Each row stamped with elapsed call time (`00:42`).
- Auto-scrolls to newest. If the midwife has scrolled up to review an earlier moment, auto-scroll yields and a `Resume live` chip appears at the bottom.
- When `MINIMIZATION DETECTED` fires, the transcript cluster around the trigger moment stays in view with an amber side rule and matching timestamp. The midwife can see the exact words that triggered without scrolling.
- No chat bubbles. No avatar circles next to messages. This is a clinical record, not an iMessage thread.

---

## Right rail

Two stacked cards. Stable layout — slots never reorder.

### Card 1 — Live biomarker signals

Six fixed-order rows, top to bottom: `Fatigue`, `Sleep issues`, `Low energy`, `Anhedonia`, `Distress`, `Stress`.

Each row contains:
- Label (left)
- Restrained live meter or sparkline (centre — small, low-contrast in idle, gains amber emphasis when contributing to a fire)
- Score chip with the current value in tabular numerals (right)

Refresh roughly every 5 seconds with subdued motion. Order never re-sorts. When a flag fires, contributing rows gain amber emphasis; non-contributing rows recede.

### Card 2 — Assessment & handoff

Three vertically stacked actions, stable position. The action area never jumps:

- `Why flagged?` — disabled in idle (greyed but visible); becomes primary when a flag fires
- `Open 3 probes` — disabled in idle; becomes primary when a flag fires
- `Generate handoff PDF` — always available; secondary until probes are reviewed

---

## Three modals

### Modal A — `Why this was flagged`

Right-side sheet (slides in from the right). The live screen continues to update behind it — the call doesn't pause.

Content:
- Title: `Why this was flagged`
- `Confidence` indicator (high / medium / low, with the current value)
- Exactly **three plain-English drivers**, one sentence each. No model jargon, no technical biomarker names — translate `anhedonia: 0.65` into "Voice signals reduced enjoyment / engagement."
- Close action returns focus to the trigger element.

### Modal B — `3 probes`

Centred modal with backdrop scrim. The live screen continues to update behind the scrim.

Content:
- Three stacked questions, one-tap multiple-choice answers. No free text inputs.
- Probe 1: `How have you been sleeping when the baby sleeps?` — choices: `Most days I rest` / `Some days` / `Hardly ever`
- Probe 2: `Are you still enjoying anything day to day?` — choices: `Yes, mostly` / `Sometimes` / `Not really`
- Probe 3: `Who is helping you at the moment?` — choices: `Plenty of support` / `Some help` / `Mostly on my own`
- Primary action: `Save responses` — writes the responses back to the live screen and the handoff draft, closes the modal.

### Modal C — `Handoff preview`

Wide modal. Read-only PDF preview of the document the GP would receive.

Content sections in order:
1. **Header** — `Postnatal Call Handoff Summary`, generated date/time, patient name + age, weeks postpartum, baby name + age, call date/time, total call duration, sending clinician name.
2. **Current triage** — lozenge text (`Amber: review` or `Red: urgent review`), flag timestamp, handoff status.
3. **Why this was flagged** — 2–3 sentence rationale summary tied to the flagged moment, plus the exact flag time.
4. **Probe responses** — the 3 probe questions with the captured response under each, saved timestamp.
5. **Transcript excerpt** — 6–10 diarized lines centred on the flagged window. Speaker label + timestamp per line.
6. **Footer disclaimer** (verbatim):
   > *Decision-support summary generated from live call signals and transcript excerpts for clinician review only. This document is not a diagnosis and does not replace clinical judgment, safeguarding procedure, or local perinatal mental health pathways. Confirm details against the full conversation before acting.*

Length target: one page hard. Spill to page two only if the transcript excerpt overruns.

Visual: editorial lane translated to clinical document. Warm paper tone, deep-blue section rules, humanist sans, tabular numerals. No product chrome, no startup badges, no decorative elements. It should look like something a midwife would actually email a GP.

Primary action: `Send PDF` — only exists inside this preview. No inline editing in v1.

---

## Eight demo flow states

| State | What's on screen | What changes from prior state |
| --- | --- | --- |
| `Pre-call empty` | Full shell visible. Patient context preloaded (Maya Patel). Triage = `Awaiting call`. Demo line enlarged in Top Clinical Strip. Transcript panel reads `Waiting for live audio`. Biomarker rows in muted standby. | (initial state) |
| `Inbound call ringing` | Top Clinical Strip flips to `Inbound call ringing`. Demo-line block inverts to clinic blue with single soft pulse. Rest of layout intact. | Only call-status emphasis changes — not a new screen. |
| `Connecting / first 5s` | Shared time starts at `00:00`. Concordance Ribbon becomes thin live two-line timeline. Transcript shows `Listening...` placeholders. Each biomarker row reads `Warming up`. | Audio is live even though content not yet populated. |
| `Idle (active call, no flag)` | Eye path: triage lozenge → newest transcript line → biomarker rail. Concordance Ribbon thin and stable. Transcript autoscrolls. Biomarkers refresh ~5s with subdued motion. | Content populates; nothing alarming. |
| `Flag fired (MINIMIZATION DETECTED)` | Concordance Ribbon expands to amber banner. Triage lozenge crossfades to `Amber: review`. Trigger-adjacent transcript cluster gains amber side rule. Contributing biomarker rows emphasised; others recede. `Why flagged?` and `Open 3 probes` become primary. | Single soft pulse on entry. No audio. Eye drawn to banner. |
| `Probes in progress` | `3 probes` modal sits above ongoing call. Transcript, timer, biomarker rows continue updating behind the scrim. | Task focus, not layout change. |
| `Post-probe re-classify` | Modal closes. Triage lozenge crossfades to `Amber: review` or `Red: urgent review` with fresh timestamp. Right-rail rationale and handoff block rewrites against saved probe answers. | Classification severity and copy change; structure stable. |
| `Handoff PDF generated` | Handoff preview closes. Right-rail action becomes `PDF generated · 19:42` (or `Sent`). Active call surfaces remain live. | Confirmation of output; no new workflow surface. |
| `Call ended` | Top strip changes to `Call ended` with total duration. Transcript and biomarker rows freeze in place. Rationale and handoff stay readable but non-editable. | Feeds stop; record remains reviewable. |
| `Error / degraded` | Affected module swaps to timestamped `Delayed` or `Disconnected` copy. Top Clinical Strip adds a subdued system-status chip. Rest of screen persists. | Explicit loss-of-confidence without collapsing the clinical view. |

---

## Patient persona (for the demo)

| Field | Value |
| --- | --- |
| Name | `Maya Patel` |
| Age | `29` |
| Weeks postpartum | `6 weeks postpartum` |
| Parity | `First baby` |
| Baby name + age | `Leo Patel, 6 weeks` |
| Visit reason | `Routine postnatal follow-up` |

Plausibly NHS, demographically generic enough to not distract, supports the postnatal-minimization narrative cleanly. No avatar image. The patient context strip uses text strings only.

---

## Microcopy (use these exact strings)

**Header / shell:**
- Product label: `Postnatal Pulse`
- Section labels: `Live triage`, `Live transcript`, `Live biomarker signals`, `Demo line`, `Assessment & handoff`

**Status:**
- `Awaiting call`, `Inbound call ringing`, `Connecting...`, `Call live`, `Call ended`
- `Check mute`
- `Concordance stable`, `MINIMIZATION DETECTED`
- Triage states: `Green: routine`, `Amber: review`, `Red: urgent review`

**Calls to action:**
- `Why flagged?`
- `Open 3 probes`
- `Generate handoff PDF`
- `Save responses`
- `Send PDF`
- `Resume live` (transcript scroll)

**Modal titles:**
- `Why this was flagged`
- `Handoff preview`
- `Confidence`

**Probe questions:**
- `How have you been sleeping when the baby sleeps?`
- `Are you still enjoying anything day to day?`
- `Who is helping you at the moment?`

**Disclaimer footer (verbatim, in handoff PDF):**
> Decision-support summary generated from live call signals and transcript excerpts for clinician review only. This document is not a diagnosis and does not replace clinical judgment, safeguarding procedure, or local perinatal mental health pathways. Confirm details against the full conversation before acting.

---

## Accessibility

- WCAG AA contrast minimum in every state.
- Triage state, concordance state, and speaker identity are never colour-only. Each has a text label and a stable positional cue.
- Status colours support dark text overlay; never rely on pale fills alone.
- Motion is brief and functional. One soft pulse on flag entry. Nothing flashes.
- All modals are keyboard reachable, focus-trapped, clearly dismissible (`Esc`), and return focus to the trigger element on close.
- Live updates never steal input focus. If the user is reviewing older transcript lines, auto-scroll yields.
- Probe answers and primary action targets are large and sparse — sized for low-attention use during a phone call.
- Tab order is predictable: Top Clinical Strip → Concordance Ribbon → Transcript → Right rail.

---

## Demo mode toggle

`Shift + D` opens a small bottom-left dev drawer with three buttons: `Scenario A — Minimizing exhaustion`, `Scenario B — Open distress`, `Scenario C — Stable recovery`. Click loads the canned fixture and auto-closes the drawer.

In production / clinical mode, the shortcut is disabled and the drawer never appears. Always-visible scenario chips would immediately signal "staged demo" to the judges and break the production-grade illusion. The drawer is for the demonstrator only.

---

## Hard rules — what the UI must NOT do

These are the markers of clinical-SaaS hackathon mockups. Avoid all of them.

- **No patient avatar image.** Real EHRs don't have selfies. Text only.
- **No emoji mood meters.** No 😊 / 😔 / 😟 anywhere.
- **No decorative analytics.** No mini-charts that don't serve a clinical action.
- **No icon clutter.** Icons must earn their space — disable an action, indicate live state, mark severity. Decorative icons go.
- **No vendor / startup badges** ("Powered by..."). The product is the product.
- **No animated loading spinners on idle states.** A spinner that spins forever is a sign of broken software.
- **No notification toasts for routine events.** The Concordance Ribbon and triage lozenge ARE the notification system.
- **No multiple "live" panels competing for attention.** One alert system. One thing draws the eye when something happens.

---

## The single non-mockup signal

**Shared time.** The call timer, transcript timestamps, biomarker refresh tick, the Concordance Ribbon trace, and the flagged-event marker all align to the same live clock. When the flag fires at `02:14`, the ribbon notch sits at `02:14`, the highlighted transcript moment shows `02:14`, and the post-probe handoff PDF cites `02:14`. That temporal causality is what makes the UI feel operational rather than staged.

Most hackathon mockups pretend to have live data. This one actually has it, and the timestamps prove it.
