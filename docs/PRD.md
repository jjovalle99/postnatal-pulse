# Postnatal Pulse — PRD

Voice-first adjunct triage for the NHS midwife's 6-week postnatal phone call.

Status: draft for hackathon scope; pilot-readiness scope flagged where it differs.

---

## 1. Problem and why now

The mandatory NHS 6-week postnatal phone check uses the Edinburgh Postnatal Depression Scale (EPDS), a ten-question self-report instrument. New mothers under-report on EPDS — particularly first-time mothers and women from communities where mental health stigma is heavier — because the questionnaire makes "coping fine" the easier answer to give a midwife on the phone. The result: more than half of postnatal depression cases are missed at first contact (Healthwatch 2023), and 30% of mothers who complete the check are not asked about mental health at all. EPDS itself has acceptable sensitivity (81%) and specificity (88%) at cutoff ≥11 (Levis et al., BMJ 2020), but its real-world positive predictive value sits at 0.25–0.40 in routine primary care use, depending on prevalence assumptions.

The cost of missing these cases is not abstract. Mental health is the leading cause of late maternal death in the UK between 6 weeks and 1 year postpartum (MBRRACE-UK 2025): 88 women died by suicide between 2021 and 2023, and 46% of all 643 maternal deaths in that period involved known mental health problems. The financial cost of untreated perinatal mental illness is an estimated £8.1 billion per UK birth cohort, with 72% of that figure attributable to longer-term child outcomes (Centre for Mental Health, 2014; republished 2023).

Why now: the UK National Screening Committee closed a public consultation on antenatal and postnatal mental health screening in February 2026 and concluded — explicitly — that current evidence does not support a population screening programme. They will reassess in three years. That is a regulator publicly stating that the current tool is insufficient and that they do not yet have a better one. The gap is regulator-acknowledged, and any future intervention has to operate inside the existing 6-week call without adding patient burden — population screening is off the table as a path.

## 2. Goals

- Reduce the false-negative rate at the 6-week postnatal call by surfacing mismatches between spoken transcript and acoustic affect to the midwife in real time, accepting modest increase in midwife per-call review effort.
- Stay strictly within the adjunct decision-support regulatory framing throughout — no diagnostic claim, no autonomous action, all recommendations route to a clinician.
- Ship a midwife-facing workflow that integrates into the existing call structure with zero added patient burden (no new app, no new touchpoint, no extra appointment).

## 3. Non-goals

- We are not replacing EPDS. The questionnaire continues; we layer alongside it. Replacing it would invite the regulator review that EPDS itself failed.
- We are not building a patient-facing application. The mother is the speaker; the user of the product is the midwife.
- We are not addressing perinatal mental health screening before delivery. Antenatal is a different workflow with different stakeholders.
- We are not solving for community mental health team capacity. We surface signal; the downstream pathway is unchanged.

## 4. Scope, constraints, appetite

Time appetite: 11 hours of build (single-day hackathon). One full-stack engineer, AI-agent-assisted, no team handoffs.

Hard constraints:
- Must use the Thymia Sentinel + Speechmatics joint platform (the hackathon track sponsor stack).
- Must not require any patient-side software install.
- All clinical-facing copy must avoid the words *diagnose, detect postpartum depression, replace clinician*; framing is *flag, surface, support, follow-up*.

Decision boundaries: the team owns custom policy thresholds, midwife UI design, demo flow, eval methodology. Any clinical claim language requires sponsor validation (Stefano Goria, Thymia CTO, on site).

## 5. Solution sketch

The midwife runs the 6-week call as she does today. While the call is in progress, the audio passes through two parallel analyses in the background: a clinical-grade transcript and a layer of acoustic biomarkers reading the mother's voice for affect and clinical signals. A "minimization" rule combines the two — when the transcript contains reassuring language while the acoustic signal carries elevated distress and a postnatal symptom cluster, the midwife sees a banner: *Minimization detected.*

When the banner fires, the midwife is prompted with three short follow-up questions to ask aloud — about sleep, enjoyment, and support. The mother's verbal responses are captured, the rule re-evaluates with the new information, and a triage flag updates green/amber/red before the call ends. The midwife then sees a one-page summary on screen — biomarkers, transcript excerpt, the moment of mismatch, the probe responses, and a recommended follow-up window — which can be sent to the patient's GP with one click.

Critically: the midwife is the decision-maker throughout. The system surfaces signal and prompts structured questions; it does not autonomously triage, refer, or escalate. If the midwife disagrees with the flag, she dismisses it and continues the call.

Visual (call-time flow):

```
Midwife-mother phone call
        │
        ├─→ Live transcript pane (what was said)
        │
        ├─→ Acoustic biomarker timeline (how it was said)
        │
        └─→ Minimization banner ──→ 3 probes ──→ Triage flag ──→ GP handoff
```

Detailed thresholds, biomarker field names, audio-window logic, and the policy DSL live in the engineering tech spec — see appendix.

## 6. Alternatives considered

**Status quo: EPDS-only at the 6-week check.** Familiar, cheap, regulatory-compliant. Rejected because the false-negative rate is the core problem being addressed; preserving EPDS without augmentation is preserving the failure mode.

**LLM-evaluated custom policy (Sentinel's `custom_prompt` executor).** Use an LLM to interpret biomarkers + transcript through a natural-language policy prompt. Considered because it allows richer reasoning. Rejected because it adds 500–2000ms latency per evaluation, costs per-call API spend, and introduces hallucination/refusal failure modes during a live demo. Deterministic threshold logic on raw biomarkers achieves the same triage output with none of these costs.

**NHS 111 mental health crisis triage with the same concordance approach.** Considered as an alternative use case. Rejected because in a crisis call the transcript itself usually carries the distress signal, making concordance decorative rather than central. The distinguishing power of the approach is in cases where the words sound fine — postnatal under-reporting is the cleaner fit.

**Patient companion app with daily voice journaling.** Considered as an alternative product shape. Rejected on scope grounds: doubles the build surface, introduces a patient-facing UX with its own usability bar, and competes for the same midwife handoff window without improving the signal at the existing 6-week call.

## 7. Success metrics and guardrails

| Type | Metric | Baseline | Target | Window |
|---|---|---|---|---|
| Usage | Probe-loop completion rate per fired flag (midwife reads all 3 probes to mother) | 0% (does not exist today) | ≥80% within first 4 weeks of pilot | First 4 weeks post-deploy |
| Usage | Concordance flag firing rate per 100 mothers screened | 0 per 100 (no current detection mechanism) | 8–14 per 100 (calibrated against ~10–15% UK PND prevalence at the relevant cluster threshold) | First 8 weeks post-deploy |
| Business | Confirmed PND cases identified at the 6-week call rate (per 100 calls) — the leading indicator of false-negative reduction | NHS baseline ~5 per 100 (i.e. ~50% of true cases missed at first contact, against 10% prevalence) | +30% relative improvement (i.e. ≥6.5 per 100) within 6 months of pilot | 6-month NHS pilot, paired-comparison vs control midwifery teams |
| Business | Time-to-clinician-follow-up for amber/red-flagged mothers (median days from flag to community MH first contact) | NHS baseline median 28 days (NHS Talking Therapies first-contact wait) | Median ≤14 days for system-flagged cohort | 6-month pilot |
| Guardrail | False-positive rate on internal calibration eval (text-positive + acoustic-positive controls) | (eval-only baseline) | ≤15% | Pre-pilot internal eval |
| Guardrail | UI renders triage state within p99 250ms of policy result | (engineering target) | p99 ≤250ms | Live operation |
| Guardrail | Zero patient-facing copy uses "diagnose," "detect PPD," or "replace clinician" — static review on every release | 0 violations | 0 violations | Every release |

## 8. Risks, dependencies, open questions

| Question | Owner | Resolution date | Blocking |
|---|---|---|---|
| Does Sentinel's hackathon-key endpoint expose concordance reliably on simulated minimization? | J. Ovalle (lead builder) | Sat 18 Apr, 11:00 (sponsor recon + first end-to-end run) | Blocking |
| What exact Sentinel biomarker fields are sponsor-approved for on-screen citation? | Stefano Goria (Thymia CTO) | Sat 18 Apr, 10:30 (sponsor conversation) | Non-blocking — defaults to Helios layer if unanswered |
| Does Twilio inbound from the venue network meet latency requirements? | J. Ovalle | Sat 18 Apr, 09:30 (field test on arrival) | Non-blocking — browser mic fallback exists |
| Can MELD-only eval produce credible sensitivity/specificity numbers without synthetic pairs? | J. Ovalle | Sat 18 Apr, 14:30 | Non-blocking — eval can be cut without killing the demo |
| What is the appropriate framing for finalist deliberation if a competing team also pitches concordance-on-mental-health? | J. Ovalle | Sat 18 Apr, 10:00 (room recon) | Non-blocking — pitch language can adjust |

Risks: live demo dependency on Twilio (mitigated by browser-mic and deterministic-replay fallbacks), single-source-of-truth on Sentinel's concordance behavior (mitigated by validating with sponsor on-site before committing build hours), small-N eval (acknowledged in framing — "internal calibration, not clinical validation").

Dependencies: Thymia Sentinel hackathon key (delivered at venue), Speechmatics medical-domain access (in same key bundle), Twilio account ($15 trial credit covers the hackathon usage), Render free tier (deploy is post-freeze polish).

## 9. Appendix

- MBRRACE-UK 2025 / Maternal Mental Health Alliance — leading cause of late maternal death: https://maternalmentalhealthalliance.org/news/mbrrace-2025-suicide-leading-cause-maternal-death/
- RCPsych July 2025 — UK PND prevalence: https://www.rcpsych.ac.uk/news-and-features/latest-news/detail/2025/07/24/postnatal-depression-harming-up-to-85-000-new-mums-in-england--warns-rcpsych
- Centre for Mental Health / LSE — £8.1bn cost: https://www.centreformentalhealth.org.uk/news/item/shocking-failure-fully-address-mental-health-problems-pregnancy-and-following-childbirth-costs-over-ps8-billion-report-finds/
- Healthwatch March 2023 — six-week check failure rates: https://www.healthwatch.co.uk/news/2023-03-14/six-week-postnatal-checks-are-failing-many-new-mothers
- Levis et al., BMJ 2020 — EPDS IPDMA (n=9,066): https://pubmed.ncbi.nlm.nih.gov/33177069/
- UK NSC November 2025 / February 2026 — perinatal screening consultation: https://nationalscreening.blog.gov.uk/2025/11/12/uk-nsc-consults-on-evidence-related-to-screening-for-antenatal-and-postnatal-mental-health-conditions/
- Mazur et al. 2025, Annals of Family Medicine — voice-tool depression sensitivity: https://pubmed.ncbi.nlm.nih.gov/39805690/
- Thymia clinical validation, Annals of Family Medicine Jan 2025 — depression AUC 0.84
- Hackathon execution plan: [`./PLAN.md`](./PLAN.md)
- PRD writing conventions: [`./PRD-GUIDE.md`](./PRD-GUIDE.md)
- Engineering tech spec for Sentinel + Speechmatics integration: TBD (separate document, owned by builder)
</content>
</invoke>