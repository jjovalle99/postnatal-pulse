# How to Write a PRD

A prescriptive template, one worked example, and a review rubric. Built from the convergent canon (Cagan, Bryar/Carr, Singer, Bezos, Doshi, Larson, Ubl, Orosz, Linear) and adjudicated through structured back-and-forth — what's here is what survived disagreement.

The PRD is not documentation. It's a forcing function for thinking. Its value is the thinking it forces, not the artifact it produces. Every rule below exists to prevent a specific failure mode that has been observed at companies that ship.

---

## The doctrine

**Length is sized by blast radius, not by duration.**
- Incremental, low-blast-radius work: 1–2 pages
- Cross-functional bets, hard-to-reverse decisions: 3–6 pages
- Hard cap: 6 pages of narrative body. Anything beyond goes in the appendix or you have the wrong document.

The "prose forces thinking" principle (Bezos, Stripe, Larson) holds — but only at the page count where the prose is actually read. A six-pager that gets read 5 times beats a 20-pager that gets skimmed once.

**One accountable author, many contributors.**
Default: PM for product bets. Engineer or designer when they're the actual project lead. Trio (PM + design + tech lead) review every draft. The tech spec stays a separate document, owned by engineering. Committee prose is mush; one pen with structured input is the working model across the canon.

**Write the PRD when the riskiest assumptions have been tested enough to justify a build decision.**
Not before discovery (Cagan's failure mode: documentation replacing validation). Not as discovery (Amazon does this with PR/FAQ but it's a specific operational practice, not a generalizable rule). The threshold is *tested enough to justify build* — not *fully validated* (which never happens) and not *intuited* (which fails predictably).

**Lo-fi visuals by default. Hi-fi only when interaction detail IS the decision.**
Flows, breadboards, fat-marker sketches. Hi-fi mockups belong in the design doc — except when the precise interaction detail is itself the decision being made (e.g., a payment confirmation step where pixel-level affordances drive conversion). In every other case, bringing hi-fi into the PRD prematurely constrains the solution before the approach is settled.

**Prose-first for sections that contain reasoning. Bullets for sections that contain lists.**
Reasoning sections (problem, solution sketch, alternatives) lose causal logic when bulleted. List sections (goals, non-goals, metrics, open questions) lose nothing as bullets and gain scannability.

**Process is non-negotiable: at least one review round and one substantive rewrite before sign-off.**
A first-draft PRD is thinking on paper, not a specification. Bezos: *"the great memos are written and re-written, shared with colleagues who are asked to improve the work, set aside for a couple of days, and then edited again with a fresh mind."*

---

## The template

Nine sections. Order matters. Section 1 is read first, section 9 is reference.

### 1. Problem and why now

Prose, 1–3 paragraphs. State observable user pain in concrete terms — a specific user in a specific situation, what they're trying to do, where the current world fails them, what that failure costs. The single most diagnostic test: this section cannot name your proposed feature except as a workaround being currently used and found wanting.

"Why now" in the same section, not separate. What changed in the world that makes this the right moment? Regulation, market shift, technical capability, internal strategy. If "why now" reads as marketing copy, it's wrong.

### 2. Goals

Bulleted list, 3–5 items maximum. Each goal must imply a tradeoff. The test: if two senior engineers reading the goal could independently make opposite implementation decisions while both claiming alignment, the goal is too vague. *"Improve user experience"* fails this test. *"Reduce time from sign-up to first useful action below 2 minutes for the median new user, accepting higher first-day churn from users who would have stalled on multi-step onboarding"* passes.

### 3. Non-goals

Bulleted list. Required, not optional. State things that *could reasonably be considered in scope* but are explicitly excluded. The test: if a reviewer cannot imagine someone arguing for the item to be included, it's not a useful non-goal — it's noise. Every non-goal you list should sting a little.

### 4. Scope, constraints, appetite

Prose, short. The bounded territory the team operates in. Includes:
- Time appetite (how much time is this problem worth — Shape Up's framing)
- Resource constraints (how many people, what skill mix, what they can't be pulled from)
- Hard technical or regulatory constraints (must work within existing X, must comply with Y)
- Decision boundaries (which choices are the team's, which require escalation)

Without this section, the PRD becomes an aspiration essay instead of a bounded decision document.

### 5. Solution sketch

Prose-first, with lo-fi visuals where they reduce ambiguity. Describe the chosen approach at the level of user-visible behavior and the structural choices that produce it. Flow diagrams, breadboards (Shape Up), and fat-marker sketches belong here. Hi-fi mockups stay out of the PRD unless the precise interaction detail is itself the decision being made — in that narrow case, include exactly the one hi-fi artifact that carries the decision and nothing more.

This section answers *what we're building and how the user encounters it*, not *how we implement it*. Implementation belongs in a separate engineering tech spec linked from the appendix.

If a designer reading this section would have to invent the basic interaction model from scratch, the section is too thin. If they would feel they have no design freedom left, it's too thick.

### 6. Alternatives considered

Prose-first. List the status quo plus at least one plausible rejected alternative. For each: what it is, why it was considered, why it lost. This is the section that most reliably distinguishes senior from junior work — its presence signals the writer has done the intellectual labor of considering the design space; its absence signals they may have committed to the first solution that came to mind.

The reviewer test: would a critic with relevant expertise be able to add an alternative the author missed? If yes, the section needs more work.

### 7. Success metrics and guardrails

Table or structured bullets. Required: at least one usage/adoption metric AND at least one business metric (revenue, retention, conversion, cost-to-serve, regulatory compliance — something a leadership review actually cares about). Both with baselines and time windows.

Doshi's distinction is non-negotiable here: usage metrics measure whether the feature is being used in the way assumed; business metrics measure whether that use produces the intended business outcome (revenue, retention, conversion, cost-to-serve, regulatory compliance — something a leadership review actually cares about). Teams that include only one of the two fail to detect features that are used but don't move the business, and features that move the business but aren't being used as designed.

Add guardrail metrics: things that must NOT degrade. ("First-render performance must not regress beyond 200ms p99.") Without guardrails, success metrics are an offence-only model.

### 8. Risks, dependencies, open questions

Table format, mandatory columns: `Question` / `Owner` / `Resolution date` / `Blocking`.

An open question without a named human and a date is decoration. It signals acknowledgment of uncertainty without a plan to resolve it. Reviewers should reject any PRD where this section contains anonymous or undated rows.

Risks: what could cause this to fail or cause harm if it succeeds in the wrong way. Dependencies: what other teams or systems must do or be true.

### 9. Appendix

Linked references, supporting research, raw data, longer artifacts that would bloat the body. Background context goes here as links, not reproduced text. The body assumes the reader will follow links if they need depth.

---

## Worked example

A complete PRD written through this template lives at [`./PRD.md`](./PRD.md) — Postnatal Pulse, an adjunct triage tool for the NHS 6-week postnatal call. Read it before writing your first PRD with this guide. Pattern-matching from a complete artifact converges faster than building from the abstract description, especially for the sections that are hardest to write well (Section 1's no-solution discipline, Section 6's real rejected alternatives, Section 7's business metrics with baselines, Section 8's named owners + dates).

---

## Review rubric

A one-page checklist. Run before sending the PRD for review and before approving someone else's. Each item ties to a specific failure mode in the canon.

### Structural

- [ ] Section 1 contains no version of the proposed solution — not by feature name, not by paraphrase, not by mechanism description. The solution-as-such first appears in Section 5. Smuggled solutions ("we will catch the cases X misses") count as failure.
- [ ] Section 1 includes evidence (linked research, interview notes, prototype learnings, or instrumentation data). If absent, the PRD is not ready — discovery is incomplete.
- [ ] Section 3 (non-goals) contains items that *could reasonably be in scope* and would sting a little to omit. If every non-goal is obviously not-this-project, it's noise.
- [ ] Section 4 explicitly states time appetite, resource constraint, and decision boundary. Not "ASAP" or "team has bandwidth" — concrete numbers.
- [ ] Section 5 specifies key user flow, states, and constraints in lo-fi form. Not pixel-perfect, not a blank slate handed to design.
- [ ] Section 6 contains the status quo plus at least one plausible rejected alternative. The author can defend the rejection on each.
- [ ] Section 7 contains at least one usage/adoption metric AND at least one **business** metric (revenue, retention, conversion, cost-to-serve, regulatory compliance — something a leadership review actually cares about, not just an operational ratio). Both with baselines and time windows. At least one guardrail metric is also listed.
- [ ] Section 8 is a table with columns `Question` / `Owner` / `Resolution date` / `Blocking`. Owners are named humans (or named external roles like "Thymia CTO"), not anonymous functions like "Builder" or "Team."

### Style

- [ ] Sections 1, 5, 6 are prose. Reasoning lives in causal sentences, not bullet points.
- [ ] Sections 2, 3, 7, 8 use bullets or tables — they're lists, not arguments.
- [ ] Body length matches blast radius: 1–2 pages for incremental work, 3–6 for cross-functional bets. Hard cap at 6 pages of body.
- [ ] Every goal in section 2 implies a tradeoff. The two-engineer-opposite-decision test passes.
- [ ] PRD does not contain implementation choices that belong in a tech spec. If you're describing data structures or service boundaries, those go elsewhere.

### Process

- [ ] At least one review round has been completed AND at least one substantive rewrite has happened since the first draft. (A first-draft PRD is thinking on paper, not a specification.)
- [ ] The review was a discussion that produced changes — not a circulation that produced sign-offs. If the only response was "LGTM," the review didn't happen.
- [ ] One named accountable author, with structured input from PM + design + tech-lead trio. No committee authorship.
- [ ] The PRD has been read in full by at least one reviewer who could push back on the chosen approach. Compliance reviewers don't count for this.

### Fail-conditions (any one → reject)

- [ ] Problem statement contains the proposed solution in any form — by name, paraphrase, or mechanism description
- [ ] No alternatives considered section, or section contains only the chosen solution
- [ ] Goals are generic enough that two engineers could make opposite decisions while both claiming alignment
- [ ] Section 7 has only operational/usage metrics and no real business outcome metric, or any metric lacks a baseline
- [ ] Open questions without named human owners or resolution dates
- [ ] Mixed PRD and tech spec content in one document
- [ ] First-draft document being shipped without revision
- [ ] Review process produced sign-offs but no document changes (approval theater)

If any fail-condition triggers, the PRD goes back to the author. Approval theater — circulating without genuine push-back — is itself an anti-pattern that defeats the entire purpose of the document.

---

## What to do with this

1. Use the template structure for any PRD you write going forward. Don't invent a new format per project.
2. Read [`PRD.md`](./PRD.md) before starting your first PRD with this template — pattern-matching from a complete artifact is faster than building from the abstract description.
3. Run the review rubric against your draft before sending it out, and against every PRD someone sends you for approval. Reject anything that fails a structural or fail-condition item.
4. If the structure feels constraining for a particular project, that's the structure doing its job. Follow it anyway. The order and section list exist to prevent specific failure modes documented in the canon; deviating because a section is uncomfortable to write is precisely the signal that the section is needed. Structural deviation requires arguing against a named anti-pattern, not against personal preference.
