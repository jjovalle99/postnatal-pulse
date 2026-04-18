# Postnatal Pulse — Voice AI Hack London 2026

A voice-first adjunct triage tool for the NHS midwife's 6-week postnatal phone call. It listens to the call, compares what the mother says against how she sounds, and flags the gap when reassuring words don't match a distressed voice. The midwife sees a triage flag and three structured probes before the call ends.

Status: track 1 (Voice & Medical), built solo, target = global winner.

---

## What we're actually building

The 6-week postnatal phone check is mandatory NHS workflow. The midwife reads EPDS (Edinburgh Postnatal Depression Scale, ten questions) and listens for distress. Mothers tick "coping" because that's the answer that ends the call faster, especially first-time mothers and women from communities where mental health stigma is heavier. The questionnaire never sees that.

Postnatal Pulse runs alongside the call. Speechmatics transcribes. Thymia Sentinel scores acoustic biomarkers (depression cluster, anxiety cluster, wellness cluster, real-time affect). When the words sound calm but the voice carries exhaustion, anhedonia, and sleep deprivation, Sentinel's concordance feature fires `MINIMIZATION DETECTED`. The midwife sees the flag, the system serves three contextual probes (sleep, enjoyment, support), the answers re-run through the policy, the triage flag updates green→amber→red, and a one-page handoff lands with the GP after the call.

We do not diagnose. We surface the false-negative cases EPDS misses and route them to a clinician who already had the patient on the line.

---

## Why this is the right thesis

Three things converged.

**The regulatory gap is real and acknowledged.** The UK National Screening Committee closed a consultation on perinatal mental health screening in February 2026 and concluded population screening is not currently recommended. The reason they cite: EPDS positive predictive value is too low, sensitivity is acceptable but real-world detection rates are not. They will reassess in three years. That is the regulator publicly saying *the current tool is insufficient and we don't have a better one.* Postnatal Pulse is not a population screen. It is an adjunct inside an existing call, exactly the workflow shape that sidesteps the NSC concern.

**Voice is non-substitutable.** The judging criterion that carries 25% weight is "Voice AI Integration — core not bolted on." Concordance literally cannot exist from text alone. The transcript reads "I'm coping fine." The acoustic vector reads exhausted, flat, anhedonic. That mismatch is the entire product. There is no version of this thesis that you could build with a better LLM and a microphone button.

**The kit ships the killer feature.** Thymia Sentinel exposes concordance analysis natively, with `wellbeing-awareness` policy pre-built (four severity levels plus suicidal content flags) and inline custom policies that need no server config. Example 04 already includes a `symptom_minimization` field in its prompt template — we are forking working sample code, not inventing a research project.

The other thesis candidates that came up over four rounds of design — NHS 111 crisis triage, Parkinson's medication state tracking, post-discharge IVR check-in, T2D pharmacy screen — each died on a single point. Crowding (everyone will pick crisis triage), thymia capability (no Parkinson's biomarkers), API gating (T2D requires Apollo medical-API access not in the hackathon key), or demo aesthetic (post-discharge looks like SaaS dashboards). Postnatal Pulse passes all five filters: voice-non-substitutable, sponsor-strategic without being a sponsor wrapper, regulator-recognized gap, buildable in one day with proven-winner velocity and AI-agent leverage, and demoable with anyone's voice on stage.

---

## The numbers (use these in the README and the pitch)

| Stat | Source |
| --- | --- |
| Mental health is the leading cause of late maternal death in the UK (6 weeks–1 year postpartum). 88 women died by suicide between 2021 and 2023. 46% of all 643 maternal deaths involved known mental health problems. | MBRRACE-UK 2025 / Maternal Mental Health Alliance |
| 10–15% of UK mothers develop postnatal depression — 56,000 to 85,000 women in England in 2024. | RCPsych, July 2025 |
| Untreated perinatal mental illness costs the UK an estimated £8.1 billion per birth cohort, £74,000 per mother lifetime, 72% of which is attributable to child outcomes. | LSE / Centre for Mental Health, 2014, republished Nov 2023 |
| Over 50% of postnatal depression cases go undetected at first contact. 30% of mothers who receive the mandatory 6-week check are not asked about their mental health. | Healthwatch, March 2023 |
| EPDS at cutoff ≥11: sensitivity 81%, specificity 88%, positive predictive value 0.25–0.40 depending on setting. | Levis et al., BMJ 2020 (IPDMA, 36 studies, n=9,066) |
| UK NSC, February 2026: population screening for postnatal mental health is not currently recommended; reassess in three years. | UK National Screening Committee |
| NHS midwife shortage in England: ~2,500 posts. 78% of GPs given ≤15 minutes per six-week check. | RCM, February 2024 |
| Voice as a clinical biomarker: AI voice tool achieved 74% sensitivity for depression in primary care women. | Mazur et al., Annals of Family Medicine 2025 |
| Thymia depression model: AUC 0.84 from voice, primary care setting. | Thymia clinical validation, Annals of Family Medicine, January 2025 |

Two corrections from earlier drafts: Black women in the UK face roughly 3x maternal mortality risk vs white women (not 2x — MBRRACE-UK 2022–24 data brief). The "2x South Asian PND risk" claim should be replaced by ROSHNI-2 (Lancet, October 2024, the largest UK study on South Asian perinatal depression) which confirms higher prevalence and lower treatment access without committing to a single multiplier.

---

## Stack

Two sponsor APIs do the heavy lifting. The hackathon key, distributed at registration, gives both.

**Speechmatics** — speech to text. The medical domain model gives 93% accuracy and 96% medical keyword recall, with speaker diarization that distinguishes clinician from patient. Configured by setting `domain="medical"` and `operating_point=OperatingPoint.ENHANCED`. Three SDKs available: `speechmatics-rt` (real-time), `speechmatics-batch` (file), `speechmatics-voice` (voice agent). We use real-time.

**Thymia Sentinel** — acoustic voice biomarker analysis. The Python SDK is `thymia-sentinel>=1.1.0`. Three biomarker layers:

- **Helios** (wellness, 0–1): `distress`, `stress`, `burnout`, `fatigue`, `low_self_esteem`
- **Apollo** (clinical, PHQ-9 and GAD-7 aligned): depression cluster (`anhedonia`, `low_mood`, `sleep_issues`, `low_energy`, `appetite`, `worthlessness`, `concentration`, `psychomotor`) and anxiety cluster (`nervousness`, `uncontrollable_worry`, `excessive_worry`, `trouble_relaxing`, `restlessness`, `irritability`, `dread`)
- **Psyche** (real-time affect, ~5s update cadence): `neutral`, `happy`, `sad`, `angry`, `fearful`, `disgusted`, `surprised`

Two policies pre-loaded on the hackathon key: `wellbeing-awareness` (four severity levels plus suicidal content flags) and `passthrough` (raw biomarkers). Custom policies are inline dicts — no server-side setup.

The killer feature is concordance analysis. Sentinel returns it under `result["concordance_analysis"]` with `scenario` and `agreement_level` fields. The example 04 prompt template already includes a `symptom_minimization` boolean ("true if patient's words suggest they're OK but biomarkers indicate distress"). That field, with our postnatal-tuned policy, is the entire product.

**Twilio** — inbound voice number plus SMS. ~$1/month for a UK number plus per-call costs, set up tonight. Used for the wow demo (judges dial in, get screened, receive a summary text).

**Frontend** — TypeScript/Next.js (whatever ships fastest from the Cursor scaffold). One screen with four panes: live transcript, biomarker timeline, concordance highlight, triage flag. A modal for the three probes. A button to generate the handoff PDF.

**Deploy** — Render (sponsor). Public URL, Docker, dropped in last.

---

## Architecture

```
Inbound voice (Twilio number OR browser mic)
        │
        ├── Speechmatics RT (medical domain, speaker diarization)
        │           │
        │           └── transcript chunks → midwife UI
        │
        └── Thymia Sentinel (sidecar)
                    │
                    ├── biomarkers (Helios + Apollo + Psyche) → midwife UI timeline
                    │
                    └── postnatal-minimization custom policy
                                │
                                ├── concordance flag → UI banner
                                │
                                └── triage state → 3-probe modal → re-score → handoff PDF + SMS
```

Pattern 1 from the kit (transcription + biomarker sidecar). The two SDKs run in parallel on the same audio stream. Sentinel does not block the STT path — if it fails, the transcript still lands. The midwife UI consumes both.

---

## Features

### P1 — Core (kills the project if missing)

- Green data path: audio → Speechmatics → Sentinel → JSON. Forked from `examples/02_combined_pipeline/run.py`.
- Custom inline `postnatal-minimization` policy. Forked from `examples/04_custom_policy/`. The prompt is tuned for postnatal context. Composition: concordance + `sleep_issues` + `low_energy` + `anhedonia`. Returns `flag`, three plain-English `drivers`, `confidence`, and `triage_pre_probe`.
- Hero clip: one self-recorded audio file where the words sound calm and reassuring but the voice carries fatigue. Validated tonight by running it through the pipeline three consecutive times and confirming concordance fires every time.
- Midwife UI core: one screen, four panes (transcript, biomarker timeline, concordance highlight, triage flag). Renders from cached fixture if the live path is unavailable.
- Probe-and-reclassify loop: when concordance fires, the UI shows three boxed probes (sleep, anhedonia, support — see the probe set below). Each answer is scored deterministically. The triage flag updates green→amber→red. No free-text generation. No live token-by-token classification — answers submit as a batch and the policy re-runs.
- Deterministic demo mode: a one-click switcher between three canned scenarios. Each loads a stored fixture (audio + cached pipeline outputs). Same fixtures power the live demo, the fallback video, and the cold-viewer test. This is the reliability layer.

### P2 — Wow

- **Twilio inbound dial-in.** Judges dial a published UK number during the showcase. They speak for 45–60 seconds. Speechmatics transcribes, Sentinel scores, the midwife UI updates live in front of the audience, and the judge gets an SMS within 90 seconds with the triage flag, a one-line summary, and a link to the PDF the GP would receive. This is the headline. The counterfactual replay video drops from "primary demo" to "fallback if Twilio breaks at the venue."
- **"Why flagged?" rationale view.** One tap on the concordance flag opens a panel showing three plain-English drivers and a confidence level. Built from policy outputs, no new logic. Closes the "but how does it know?" objection without being asked.

### P3 — Evidence

- **Eval harness.** 60 utterances total across four buckets. 30 ElevenLabs v3 controlled synthetic pairs (using inline emotion tags — `[sad] I'm doing fine [exhausted]` vs `[cheerful] I'm doing fine`). 30 MELD naturalistic clips (Friends TV corpus, direct download from `web.eecs.umich.edu/~mihalcea/downloads/MELD.Raw.tar.gz`, no registration). Filtered programmatically by sentiment (positive) × emotion (sadness/disgust/anger) for minimization, vs (positive × joy/neutral) for controls. Pipeline batch-runs, scorecard reports per-bucket sensitivity and specificity. Framed as "internal calibration" in the README, not "clinical validation."
- **Trend tracking screen.** A clinician review screen for one patient across three check-ins (week 6, week 8, week 12). Trajectory chart, concordance event markers, click-through to each call's transcript and policy result. Static fixtures are fine — the point is showing this is a longitudinal product, not a one-shot detector.

### P4 — Conditional (only if Discord confirms tonight)

- **Multilingual passthrough.** ONE verified non-English language, with a prerecorded clip and a translated transcript. Punjabi or Polish, depending on what Stefano confirms. The story is the UK NHS perinatal MH gap concentrated in non-English-speaking communities (ROSHNI-2 anchors this for South Asian women). +3–6 percentage points of win probability if it lands cleanly. Dies if Discord is silent or sponsor cannot confirm.

### P5 — Polish (only after feature freeze)

- Render deploy with public URL.
- README with one-screen thesis, architecture diagram, eval scorecard, 8–12 perinatal MH citations, hackathon-safe disclaimers (decision-support, not diagnostic).
- Counterfactual replay video: 90 seconds, "same words, different truth" structure. Was the headline before Twilio became the wow. Now serves as the bulletproof fallback if every live dependency breaks.

### Explicitly NOT building

- Patient-facing companion app (scope poison)
- Fine-tuning any model (invisible to judges, data-poor, weak ROI)
- Multimodal facial fusion
- A standalone GP dashboard separate from the midwife UI (absorbed into trend tracking)
- Open-ended LLM probes (use boxed function-call constrained probes only)
- "Real-time AI coach" framing (use rationale-view framing instead — "AI coaches the doctor" reads badly with safety-conscious judges)
- Additional scenarios beyond the three archetypes
- More than one verified non-English language

---

## The custom policy

`postnatal-minimization` is an inline custom policy. Forked from `examples/04_custom_policy/policy_prompt.txt`, retuned for postnatal context.

Composition (the policy fires when ALL three are true within the same 15-second window):

| Signal | Threshold |
| --- | --- |
| Minimizing language in transcript | Phrases: "I'm coping fine", "I'm okay", "just tired", "fine overall", "nothing to worry about", "managing" |
| Acoustic distress | `distress >= 0.60` OR `stress >= 0.65` OR negative Psyche affect dominates the recent 5-second segment |
| Postnatal symptom cluster | `sleep_issues >= 0.60` AND (`low_energy >= 0.60` OR `anhedonia >= 0.55`) |

Triage state machine:

| Stage | Logic |
| --- | --- |
| Pre-probe triage | Red: suicidal flag from `wellbeing-awareness` OR severe biomarker cluster. Amber: concordance flag fires. Green: otherwise. |
| Post-probe triage | Re-run after probe responses. Red: probe score 4–6 OR persistent suicidal flag. Amber: probe score 2–3 OR concordance still firing. Green: probe score 0–1 AND biomarkers below threshold. |
| Confidence | High: transcript mismatch + biomarkers + probes all align. Medium: 2 of 3. Low: 1 of 3. |

Policy returns `flag`, `drivers` (top three plain-English causes), `confidence`, `triage`. UI displays the four fields plus a one-tap rationale view.

---

## Scenarios

Three canned archetypes drive the entire demo, the eval harness, and the cold-viewer test.

| Scenario | Role | Expected pipeline behavior |
| --- | --- | --- |
| **A. Minimizing Exhaustion** | Hero demo | Words sound reassuring ("I'm doing okay, baby's lovely, just a bit tired"). Voice carries fatigue, low energy, anhedonia. Concordance fires. Probes push triage from amber to red. |
| **B. Open Distress** | Control case | Distress is obvious in both words and voice. Triage goes straight to red without concordance firing. Demonstrates the system handles overt cases too. |
| **C. Stable Recovery** | Negative control | Supportive language, calm affect, biomarkers low. Triage stays green. Demonstrates the system does not over-flag. |

Each scenario has a stored audio file plus cached pipeline outputs. The deterministic demo mode loads them with one click — no live API call needed for the fallback path.

---

## The probes

When concordance fires, the UI presents three boxed questions to the midwife. She reads each aloud, the mother responds, the response is transcribed, the policy re-runs.

| Probe | Choices | Score |
| --- | --- | --- |
| In the last week, how often have you had at least a 3-hour block of uninterrupted sleep? | Most days / Some days / Hardly ever | 0 / 1 / 2 |
| Have things felt flatter or harder to enjoy than usual? | Not really / Sometimes / Often | 0 / 1 / 2 |
| Today, do you feel you have enough support to rest and manage feeding or baby care? | Yes / Somewhat / No | 0 / 1 / 2 |

Probe choices are clickable buttons in the UI (no free text). Sum drives the post-probe triage state. The questions map directly to PHQ-9 dimensions Apollo already scores (sleep_issues, anhedonia, support is a known compounding factor) — picking these means probe responses and acoustic signals are measuring related constructs and reinforcing each other.

---

## Schedule

Tonight you cannot test end-to-end (no API keys until on-site). The kit is verified, the SDK signatures are confirmed, the example 04 fork path is clear. Saturday is the build day. Treat the morning as the critical window.

| Time | Block | Done when |
| --- | --- | --- |
| Sat 09:30–10:00 | Venue arrival, power, Wi-Fi or hotspot, registration, get keys | Laptop on venue power, both API keys in `.env`, Discord open |
| Sat 10:00–10:30 | Sponsor recon with Stefano (4 minutes max — see protocol below) | UI labels updated to whatever Stefano prefers; multilingual confirmed or dead |
| Sat 10:30–11:30 | Run example 02 untouched on your hero clip. Confirm Sentinel + Speechmatics return data. | Sentinel returns biomarker scores + concordance field on the hero clip |
| Sat 11:30–12:30 | Fork example 04, drop in `postnatal-minimization` policy prompt, validate concordance fires on the hero clip three runs in a row | Hero fixture frozen on disk |
| Sat 12:30–13:30 | Build the midwife UI core from cached fixture. Single screen, four panes. Cursor does the heavy lifting. | UI renders the hero scenario from cached fixture without any live API |
| Sat 13:30–14:30 | Probe-and-reclassify loop wired to the policy. Deterministic scenario switcher with all three archetypes. | One click loads each archetype, probes update triage |
| Sat 14:30–15:00 | Twilio inbound number provisioned and connected to the live UI. Test from your own phone. | A call from your phone updates the UI in real time |
| Sat 15:00–15:30 | "Why flagged?" rationale view. SMS summary template. | Rationale panel opens on tap; SMS sends after Twilio call ends |
| Sat 15:30–16:00 | **Cold-viewer test #1** — see protocol | 2 of 2 viewers can state the product in one sentence |
| Sat 16:00–17:00 | Eval harness if cold test passed (otherwise rewrite story). MELD download started in parallel from morning if possible. | Scorecard exists, ~60 utterances, sensitivity/specificity per bucket |
| Sat 17:00–17:30 | Trend tracking screen if ahead. Otherwise polish demo reliability. | Static three-checkin trajectory renders |
| Sat 17:30–18:00 | **Hard feature freeze.** Bug bash. Three clean runs of the chosen demo path. | No new feature work. Reliability only. |
| Sat 18:00–19:00 | Counterfactual replay video as fallback (screen-record the deterministic mode with voiceover). README + architecture diagram + citations. Render deploy if time allows. | README first screen explains thesis, safety, architecture, evidence |
| Sat 19:00–19:30 | **Cold-viewer test #2** with a new viewer. Pitch rehearsal. | New viewer repeats thesis unprompted. 2:30 pitch lands under time. |
| Sat 19:30–20:00 | Final logistics — Twilio number tested from two devices, fallback ladder verified end-to-end, laptop opens directly into chosen demo mode | Everything in the pre-judging checklist below ticks |
| Sat 20:00–21:00 | Submission + judging | Repo, README, video uploaded; demo runs |

---

## Sponsor recon (Stefano, 4 minutes maximum)

Stefano Goria is Thymia's CTO and is judging Track 1 in person. The morning conversation is for blocker answers only — not for him to redesign your project.

```
1. Which exposed signals are safest to cite on screen — Helios fatigue/distress,
   Apollo sleep_issues/low_energy/anhedonia, or Psyche affect drift?
   (Updates UI labels immediately.)

2. If Sentinel responses come back empty or partial, what behavior do you want —
   retry, hold last good state, or show uncertainty and continue?
   (Implements the safe failure path. Mention it in Q&A.)

3. Is "concordance check" the right term, or do you prefer "voice-text mismatch",
   given we frame this as decision-support and not diagnosis?
   (Renames UI copy if needed.)

4. (Only if slack) If we add one non-English language tonight, which would you
   trust most — Punjabi or Polish?
   (Decides multilingual: live or dead.)
```

If you cannot get him in person before 11am, post the same questions in the Discord `#thymia` or `#voice-medical` channel and proceed on local assumptions while you wait.

---

## Cold-viewer test

Run this twice. Once around 15:30 (gates feature additions). Once around 19:00 (gates the pitch).

Show 45 seconds of the demo to a stranger. No setup, no explanation while it plays. Then ask, in this order:

1. In one sentence, what does this product do?
2. Who is the user?
3. Why does voice matter here instead of just transcript?
4. Is it diagnosing the patient?

Pass criteria, all four must hit:

- The answer to (1) is something close to "it helps a midwife catch hidden postnatal distress when someone says she's fine but sounds unwell"
- The answer to (2) is the midwife or the clinician, not the patient or the mother
- The answer to (3) names the mismatch — voice carries something words don't
- The answer to (4) is no, with the right reasoning (it screens, it surfaces, it supports the clinician)

If the noon test fails on any of these:

| Failure pattern | Fix |
| --- | --- |
| "It diagnoses postpartum depression" | Rewrite subtitle, opening line, and triage labels. Strip the word "detect," use "flag" or "surface." |
| "It's a patient app" | Put the midwife UI first. Drop any visual that looks patient-facing. |
| "It's sentiment analysis for calls" | Lead the demo with the same-words-different-truth contrast pair before anything else. |
| "It summarizes the call" | Make the concordance moment and the probe modal visually larger than the transcript. |
| "I'm not sure why voice matters" | The hero story is buried. Open the demo with a transcript-only view that looks fine, then reveal the acoustic signal. |

A failed noon test kills the trend tracking and multilingual additions immediately.

---

## Pitch (2:30, extends demo time if slot is longer — never extend exposition)

```
0:00–0:20  COLD OPEN
"At the 6-week postnatal phone call, the hardest sentence to catch is:
 'I'm coping fine.' A transcript hears reassurance. A midwife often hears
 exhaustion. Postnatal Pulse helps the midwife see that mismatch before
 the call ends."

0:20–0:35  STACK
"We combine Speechmatics medical transcription with Thymia Sentinel
 biomarkers and a custom postnatal minimization policy. This is adjunct
 decision-support, not diagnosis."

0:35–1:15  LIVE DEMO
[Judge dials the Twilio number. Speaks for 45–60s. UI updates in front
 of the audience. Concordance flag fires. Three probes appear.]

1:15–1:45  WORKFLOW
"We don't auto-label the patient. The system asks three structured
 follow-up questions about sleep, enjoyment, and support. The triage
 flag updates before handoff."

1:45–2:05  RATIONALE VIEW
[Tap "Why flagged?" — show three plain-English drivers and confidence]
"The clinician can see why the system became concerned. No black box."

2:05–2:20  EVIDENCE
"Internal calibration on 60 controlled and naturalistic utterances:
 sensitivity X, specificity Y on concordance detection. Deterministic
 scenarios and a fallback video make this reproducible."

2:20–2:30  CLOSE
"Postnatal Pulse does not diagnose. It prevents a missed human
 follow-up by turning a voice-text mismatch into structured next
 questions."
```

If live telephony is shaky on stage: *"I'm switching to the validated replay to keep this deterministic — same production pipeline and policy outputs we generated from the live stack."* Then play the deterministic mode.

Things never to say: *diagnoses*, *replaces a midwife*, *makes autonomous clinical decisions*, *clinically validated* (unless we have evidence to back it), *works in multiple languages* (unless multilingual is verified and demoed).

---

## Q&A preparation

| Question | Answer |
| --- | --- |
| Why voice instead of transcript? | "Because minimization is often invisible in text. Same words can read as reassuring while the voice carries fatigue, distress, or flattening. Our product exists for that mismatch." |
| Is this diagnosing postpartum depression? | "No. It is adjunct triage support for a midwife's existing postnatal phone call. It surfaces mismatch, asks structured follow-up, and supports human handoff." |
| How do you avoid false positives? | "We don't escalate on a single signal. We require a task-specific mismatch pattern, show the drivers, and use structured probes before final triage." |
| Why technically novel if Sentinel already exists? | "The sponsor models are the foundation. The novelty is the postnatal minimization policy and the probe-and-reclassify loop tuned for this exact workflow." |
| What if the patient is openly distressed? | "That's one of our control scenarios. The system still triages correctly — it routes to red without needing concordance. The hero value is the case where the patient says she's fine and a transcript would miss it." |
| What about Kintsugi-style regulatory risk? | "We don't diagnose, direct treatment, or replace a clinician. The UI is rationale and follow-up support only. The framing matches the only voice-biomarker positioning that has a working commercial path." |
| Accents, noise, real call quality? | "Speechmatics medical-domain transcription handles accent variation. When the acoustic signal is weak, the system surfaces uncertainty rather than overclaiming." |
| NHS workflow fit? | "It slots into the existing 6-week phone call. No new patient app, no extra burden. It gives the midwife a clearer handoff signal and a one-page summary the GP can act on." |
| Why not multilingual? | "Only if a single language is sponsor-verified and tested end-to-end. Otherwise we keep the claim narrow — English now, multilingual readiness as future work." |
| Eval source? | "MELD for naturalistic conversational speech with independent text-sentiment and acoustic-emotion labels. ElevenLabs v3 for controlled synthetic pairs. No public postnatal corpus exists. We frame the methodology as transferable once one becomes available." |

---

## Pre-failure-mode map

Every critical-path component has one prevention strategy and one recovery path. The recovery path matters more than the prevention.

| Component | What fails | Prevention | Recovery |
| --- | --- | --- | --- |
| Sentinel API | Returns empty or partial biomarker payloads | Log raw responses, schema-check Helios/Apollo/Psyche on every result, fail loud if a block is missing, cache last good fixture | Freeze last-good biomarker state, show "signal unavailable" banner, switch to deterministic replay |
| Speechmatics | Latency spike, transcript stalls during demo beat | Keep utterances 45–60s, use medical domain preset, test both Twilio and browser mic paths in advance | Stop live capture early, switch to the validated replay using the same pipeline outputs |
| Twilio inbound | Regional routing failure, call setup unreliable | Buy and test UK number tonight, test from two carriers, keep the flow minimal, browser mic ready | Browser mic becomes primary live path. Twilio stays as a documented integration but not the centerpiece. On-screen summary if SMS also fails. |
| Venue Wi-Fi | DHCP issues, captive portal, dropouts | Arrive early, connect before the crowd, hotspot already paired, all assets local | Switch to hotspot or fully offline deterministic mode. No live dependency blocks the core demo. |
| Hero clip | Self-recorded clip fires inconsistently | Five takes in a quiet room, test each three times, vary delivery and tempo | Use the most stable take. If concordance is still flaky, record via the phone-call path and use that capture. |
| Probe loop | Misclassifies after follow-up | All responses boxed, deterministic score mapping, no open-ended generation | Submit-then-recompute on a button click rather than live. |
| Scenario switcher | Demo state leaks between scenarios | Centralize reset state, test ten consecutive resets before the venue | Separate buttons or routes per scenario, hard reload into preloaded scenario |
| SMS summary | Lags or fails to deliver | Trigger off final state only, keep content short, test from venue | Show the exact summary on screen, keep a screenshot ready |
| README and video | Incomplete by judging | Start artifacts as soon as the core is stable, README first screen brutally clear | README beats deploy. Video beats deploy. Public URL is optional if local demo is strong. |
| Render deploy | Build or hosting fails | Keep local demo as primary all day | Cut deploy first. Don't burn late-stage time on hosting. |

---

## Decision tree

If you fall behind, drop in this order. Keep what's marked "no matter what."

| Checkpoint | If not true by then | Drop immediately | Keep no matter what |
| --- | --- | --- | --- |
| Sat 11:30 | Untouched example 02 runs on your clip | Everything except environment/debugging | Green path |
| Sat 13:30 | One full end-to-end hero case exists | Eval harness | Green path, policy, hero clip |
| Sat 15:00 | UI renders cached fixture | Styling, nonessential chrome | Single review screen |
| Sat 15:30 | Cold viewers understand the product | Trend tracking, multilingual | Story rewrite |
| Sat 16:30 | Eval scorecard is clean | Eval harness | README and video |
| Sat 17:00 | Twilio connects from venue | Twilio as headline | Browser mic as primary, deterministic replay as backup |
| Sat 17:30 | Any feature still half-built | That feature | Reliability only |
| Sat 18:30 | Deploy is stable | Public URL | Local demo, README, video |
| Sat 19:30 | Pitch is smooth | All coding | Rehearsal only |

Final rule at T-10 before judging: if network confidence is green, run the live path. If not, run the deterministic replay. Do not gamble the final on venue telephony.

---

## Pre-judging checklist

**Demo**
- [ ] Hero scenario loads in one click
- [ ] Green, amber, and red triage states all demoable
- [ ] Twilio number tested from at least two devices
- [ ] Browser mic fallback tested
- [ ] Deterministic replay works fully offline
- [ ] 90-second fallback video plays locally
- [ ] SMS summary content visible on screen even if delivery fails
- [ ] Rationale view shows three drivers and confidence

**Artifacts**
- [ ] README first screen states the one-sentence thesis
- [ ] README explicitly says "adjunct decision-support, not diagnostic"
- [ ] Architecture diagram included
- [ ] Evidence section included if real, omitted if weak
- [ ] 8–12 citations
- [ ] Run instructions tested from a fresh terminal
- [ ] Submission links saved to a notes file for fast paste

**Safety**
- [ ] No screen says "diagnose", "detect postpartum depression", or "replace clinician"
- [ ] Red triage means urgent human review, never automated instruction
- [ ] Probes are boxed and deterministic
- [ ] UI copy uses: "why flagged", "follow-up", "triage", "rationale"

**Logistics**
- [ ] Charger, hotspot, USB-C cable, backup phone packed
- [ ] Demo tabs and windows pre-opened
- [ ] Twilio number visible on screen and printed on a card
- [ ] Do-not-disturb configured so demo calls and texts still go through
- [ ] Laptop opens directly into the chosen demo mode

**Pitch**
- [ ] 2:30 version under time
- [ ] 1:30 compressed version memorized
- [ ] First 15 seconds land without slides
- [ ] Closing line memorized verbatim
- [ ] Fallback line ready if live telephony is shaky

---

## Kill rules

Tape these to the laptop lid. Enforce them.

1. If a feature is not in the wow demo or does not materially help Q&A, kill it.
2. If you don't have one full green end-to-end case by 13:30 Saturday, cut the eval harness first.
3. If cold viewers cannot explain the product in one sentence by 15:30 Saturday, cut all polish and fix the story.
4. Every live dependency gets a prerecorded fallback.
5. Hard feature freeze 17:30 Saturday. No exceptions.
6. Multilingual is dead unless sponsor-confirmed in person and verified on one language only.

---

## Probability and what's left on the table

Four iterations of design with Codex converged at 82–85% global-win probability for the locked plan as written. That includes Twilio dial-in, the rationale view, the eval harness, trend tracking, deterministic demo mode, and the polished pitch. Above 85% is structural: judge taste, the strength of the finalist field, demo-order variance, the random other team that ships something orthogonally brilliant. None of that is addressable through more strategy. It's addressable only through better execution, and execution starts at 9:30 Saturday morning.

The only live lever above 85% is the multilingual addition, conditional on a sponsor-confirmed yes tonight on Discord. If that comes through and lands cleanly, the ceiling moves to 84–86%. Past that, ship.
