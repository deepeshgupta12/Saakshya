# Steps · 11 · V6 — Agentic AI Workflows
> Read first: [SPEC.md](../../SPEC.md) (§1, §6.6–6.9 AI constraints, §6.7 AI-use disclosure, §4 agentic row) · [Roadmap](../02-product-roadmap.md) (§9 V6) · [AI/LLM agent architecture](../14-ai-llm-agent-architecture.md) · [Compliance & guardrails](../21-compliance-risk-and-guardrails.md) · [Data ingestion](../12-data-ingestion-and-market-data.md)

**Maps to:** Roadmap V6 · SPEC Phase 2+ (agents land incrementally; deeper orchestration in Phase 4–5)
**Status:** Not started — partially Mode-A buildable   |   **Regulatory mode:** A (with N/A infrastructure; the compliance-review agent is required infrastructure)
**Gate (must be met before build):** The **AI explanation layer foundation must exist** — structured payload contract, runtime verification harness, output-time guardrail pipeline, and AI audit log ([SPEC §6.6, §6.9](../../SPEC.md), [docs/14 §0, §4, §6, §7](../14-ai-llm-agent-architecture.md)). No agent ships until **its** underlying data + guardrails exist, and **every agent output passes verification → guardrail → compliance review** before reaching a user.
**Prerequisites:** `04-ai-explanation-layer.md` (payload contract, grounding harness, audit log, guardrails), `02-indicators-and-scanners.md` (scanner payloads), and the per-agent data sources as they land (news sentiment, portfolio/risk engine, backtesting). [Phase 0](00-phase-0-derisk.md) cleared.

## Overview
V6 consolidates the **agentic platform**: orchestrating the documented agents ([docs/14 §5](../14-ai-llm-agent-architecture.md)) — Market Brief, Stock Research, Portfolio Risk, News Impact, Scanner Explanation, Strategy Builder, Backtest Interpreter, and the **Compliance Review** agent — under a single intent-routed, multi-step orchestration graph (LangGraph or equivalent), with prompt-versioning ops and an eval harness over golden datasets.

This is **not a single big-bang phase** ([Roadmap §9](../02-product-roadmap.md), [SPEC §4 agentic row](../../SPEC.md)). Individual agents land when their data exists (Market Brief + Stock Research in Phase 2; Scanner Explanation + News Impact + Portfolio Risk in Phase 2; Strategy Builder + Backtest Interpreter in Phase 4). **This file owns the platform that ties them together** — orchestration, routing, the mandatory compliance pass, evals, and prompt ops — so each agent drops into one disciplined harness rather than re-implementing grounding/guardrails ad hoc.

**Mode-A discipline is absolute here:** an agent is just a longer generation path, so **every** intermediate and final output passes the same §0 principles ([docs/14 §0](../14-ai-llm-agent-architecture.md)) — explains never invents, structured-payload-only, runtime-verified, suppress-not-guess, output-time guardrails, no directive/RA-gated content. None of these agents may emit per-stock entry/target/stop, buy-leans, or ranked "what to buy" ([SPEC §3.2](../../SPEC.md)).

## Exit gate (Definition of Done)
- [ ] All documented agents run under **one orchestration graph** with a deterministic intent router; each agent has a versioned prompt + output schema ([docs/14 §5](../14-ai-llm-agent-architecture.md)).
- [ ] **No user-visible agent output reaches the user without passing** runtime verification → guardrail → Compliance Review ([docs/14 §1, §6](../14-ai-llm-agent-architecture.md), [compliance §9](../21-compliance-risk-and-guardrails.md)); enforced in the output path and tested in CI.
- [ ] The **Compliance Review agent is operational as required infrastructure** and **fail-closed** (errors → REJECT) ([docs/14 §5.8](../14-ai-llm-agent-architecture.md)).
- [ ] An **eval harness over golden datasets** gates every prompt/model/graph change; a change cannot ship unless grounding / guardrail / suppression / Mode-A gates pass ([SPEC §6.6](../../SPEC.md), [docs/14 §8](../14-ai-llm-agent-architecture.md)).
- [ ] Every generation (published or suppressed), at every agent step, writes an **audit record** with prompt+version, payload hash, model+tier, grounding/guardrail/compliance verdicts ([docs/14 §7](../14-ai-llm-agent-architecture.md), [compliance §10.1](../21-compliance-risk-and-guardrails.md)).
- [ ] Cost/latency discipline holds at agent depth: AI-spend ceiling, regenerate-on-change, tiering, latency budget, provider abstraction ([SPEC §6.8](../../SPEC.md), [docs/14 §3](../14-ai-llm-agent-architecture.md)).

---
## Feature: Orchestration graph + intent router  `(N/A infrastructure)`
**Objective:** Stand up the LangGraph-style orchestration that selects an agent from an intent, fetches that agent's computed data, builds the structured payload, generates via the model abstraction, and routes every output through the verification → guardrail → compliance gates with bounded regeneration/suppression ([docs/14 §1–2](../14-ai-llm-agent-architecture.md)). · **Backend dep:** model abstraction layer, payload builder, grounding harness, guardrail layer ([04-ai-explanation-layer.md]) · **Frontend dep:** none directly (agents serve existing AI surfaces) · **Data dep:** per-agent computed payloads (scanner / risk / sentiment / backtest).
### Steps
- [ ] 1. Define the **agent graph + node contract**: each node is `(intent, fetch_data, build_payload, generate, verify, guardrail, compliance, audit)`; shared verify/guardrail/compliance/audit nodes are reused by all agents — no agent bypasses them ([docs/14 §1–2](../14-ai-llm-agent-architecture.md)).
- [ ] 2. Build the **deterministic intent router**: map user intent / scheduled job → agent (e.g. `explain_scanner_result` → Scanner Explanation; `daily_brief` → Market Brief). Routing is rule/classifier-based and **logged**; unknown intent → safe fallback, never a guessed agent ([docs/14 §2](../14-ai-llm-agent-architecture.md)).
- [ ] 3. Implement the **payload-builder node** enforcing the contract invariants ([docs/14 §4](../14-ai-llm-agent-architecture.md)): the model sees only `computed` / `signalTags` / `riskFlags` / `newsSummaries`; `dataConfidence == LOW` or a missing critical field → **suppress** before any model call ([SPEC §6.2](../../SPEC.md)).
- [ ] 4. Wire **bounded regeneration + suppression** into the graph: verification FAIL / guardrail hit / compliance REJECT → regenerate up to N, then suppress with a safe fallback ([docs/14 §6, §12](../14-ai-llm-agent-architecture.md)).
- [ ] 5. Make **multi-step workflows** composable (e.g. brief = breadth + sector + scanner-delta sub-fetches → synthesis): each sub-step that emits user-visible text is independently grounded/guardrailed; intermediate computed data is not free-text.
- [ ] 6. Attach the **audit node** to every step so each generation (and each suppression) is recorded ([docs/14 §7](../14-ai-llm-agent-architecture.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] Router is deterministic and logged; unknown intents fall back safely (unit tests).
- [ ] **No path produces user-visible text that skips verify → guardrail → compliance** (CI path test); a synthetic agent emitting a fabricated number is blocked end-to-end.
- [ ] `dataConfidence == LOW` suppresses before a model call (no spend, no guess) ([SPEC §6.2](../../SPEC.md)).
- [ ] Every node writes exactly one audit record per generation/suppression ([docs/14 §7](../14-ai-llm-agent-architecture.md)).

---
## Feature: Mandatory compliance-review pass on every answer  `(N/A required infrastructure)`
**Objective:** Make the **Compliance Review agent** the non-bypassable final Mode-A gate on every user-visible AI output, catching directive/advisory **substance** that escapes literal patterns (implied buy-leans, allocation hints, exaggerated impact), and fail-closed on error ([docs/14 §5.8](../14-ai-llm-agent-architecture.md), [compliance §9 Stage 3](../21-compliance-risk-and-guardrails.md)). · **Backend dep:** guardrail layer (regex + grounding stages), versioned compliance prompt ([compliance §9](../21-compliance-risk-and-guardrails.md)) · **Frontend dep:** none · **Data dep:** candidate output text + payload + intent + mode context.
### Steps
- [ ] 1. Implement the agent's three-stage placement: it runs **after** Stage-1 regex/pattern and Stage-2 number-grounding, and **its own output also passes Stages 1–2** — no agent is above the guardrail ([compliance §9](../21-compliance-risk-and-guardrails.md)).
- [ ] 2. Encode the decision schema `{decision: APPROVE|REJECT, reasons, blockedPhrases, directiveLanguageHits, ungroundedClaims}` ([docs/14 §5.8](../14-ai-llm-agent-architecture.md)); REJECT routes back to regeneration then suppression.
- [ ] 3. Enforce **fail-closed**: any agent/provider error or timeout → REJECT (never publish unreviewed AI text) ([docs/14 §5.8, §12](../14-ai-llm-agent-architecture.md)).
- [ ] 4. Load the compliance prompt **by version** from the admin console, hot-reloadable; stamp the version into the audit log ([compliance §9 backend dep](../21-compliance-risk-and-guardrails.md)).
- [ ] 5. Tie REJECT outcomes to the escalation rules: repeated REJECT on a prompt version pauses it for compliance review ([compliance §11](../21-compliance-risk-and-guardrails.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] **Substance** test set: outputs that are literally clean but advisory-in-substance (implied buy-lean, allocation hint, exaggerated impact) are **REJECTED** ([compliance §9 Stage 3](../21-compliance-risk-and-guardrails.md)).
- [ ] Fail-closed verified: injected agent error → REJECT, never publish (CI).
- [ ] Every decision is in the AI audit log with the compliance prompt version ([compliance §10.1](../21-compliance-risk-and-guardrails.md)).

---
## Feature: Per-agent onboarding under one harness  `(Mode A)`
**Objective:** Bring each documented agent ([docs/14 §5.1–5.7](../14-ai-llm-agent-architecture.md)) onto the orchestration graph as its data lands, each with purpose · input data · tools · output schema · guardrails · failure behavior — Market Brief, Stock Research, Portfolio Risk, News Impact, Scanner Explanation, Strategy Builder, Backtest Interpreter. · **Backend dep:** orchestration graph; per-agent data services · **Frontend dep:** the AI surfaces that already exist per phase · **Data dep:** scanner / risk / sentiment / backtest payloads, as each lands.
### Steps
- [ ] 1. **Scanner Explanation** (highest-volume, cheap tier): membership language only ("appears in / matches this filter"); suppress if any cited fact absent from payload ([docs/14 §5.5](../14-ai-llm-agent-architecture.md)).
- [ ] 2. **Stock Research** (cheap tier): descriptive, traceable summary; drop directive tails ("before fresh action" → "is a level to watch"); no entry/target/stop ([docs/14 §5.2](../14-ai-llm-agent-architecture.md), [SPEC §5 worked example](../../SPEC.md)).
- [ ] 3. **Market Brief** (premium tier, synthesis): indices/breadth/sector leaders-laggards/scanner deltas; **never** a ranked "what to buy"; "to monitor" is event-framed ([docs/14 §5.1](../14-ai-llm-agent-architecture.md)).
- [ ] 4. **News Impact** (cheap): entity-resolved items above confidence threshold only; no price-impact prediction ([docs/14 §5.4](../14-ai-llm-agent-architecture.md), [SPEC §6.4](../../SPEC.md)).
- [ ] 5. **Portfolio Risk** (cheap/premium): factual holding/portfolio notes ("closed below its 50-DMA"); never "sell/reduce/rebalance" ([docs/14 §5.3](../14-ai-llm-agent-architecture.md)).
- [ ] 6. **Strategy Builder** (Phase 4, premium): NL → scanner rule spec producing a **list**; rejects target/stop fields (RA-gated) ([docs/14 §5.6](../14-ai-llm-agent-architecture.md)).
- [ ] 7. **Backtest Interpreter** (Phase 4, premium): narrates only if the integrity audit passed; restates assumptions + past-performance caveat; no extrapolation to future returns ([docs/14 §5.7](../14-ai-llm-agent-architecture.md), [SPEC §6.3](../../SPEC.md)).
- [ ] 8. Each agent ships with its **output JSON schema + per-agent guardrails + failure behavior**, all inheriting §0 ([docs/14 §5](../14-ai-llm-agent-architecture.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] Per-agent golden cases prove: grounded facts pass; fabricated facts blocked; directive phrasing rejected; missing inputs suppress ([docs/14 §8](../14-ai-llm-agent-architecture.md)).
- [ ] No agent emits per-stock levels, buy-leans, or ranked picks ([SPEC §3.2](../../SPEC.md)); design-review checklist run per agent ([compliance §12](../21-compliance-risk-and-guardrails.md)).
- [ ] Strategy Builder rejects requests for target/stop fields; Backtest Interpreter refuses to narrate an un-audited backtest.

---
## Feature: Eval harness + golden datasets  `(Mode A)`
**Objective:** A regression suite that gates every prompt/model/graph change, proving grounding, fabrication-blocking, suppression, and Mode-A language hold before any version ships ([SPEC §6.6](../../SPEC.md), [docs/14 §8](../14-ai-llm-agent-architecture.md)). · **Backend dep:** prompt registry, grounding harness · **Frontend dep:** none · **Data dep:** curated payload→expected-properties cases per agent.
### Steps
- [ ] 1. Build the **golden dataset**: curated payload→expected-properties cases (grounded facts present, fabricated facts blocked, directive phrasing rejected, suppression on missing inputs) per agent ([docs/14 §8](../14-ai-llm-agent-architecture.md)).
- [ ] 2. Define eval **metrics**: grounding pass-rate, fabrication block-rate, false-suppression rate, directive-leak rate ([docs/14 §8](../14-ai-llm-agent-architecture.md)).
- [ ] 3. Gate releases: a prompt/model/graph change **cannot ship** unless all gates pass; emit a diff report on block ([docs/14 §8](../14-ai-llm-agent-architecture.md)).
- [ ] 4. Maintain **adversarial cases** including prompt-injection-via-news (injected directives must not ground) ([docs/23 §8 prompt-injection note](../23-security-auth-and-privacy.md), [SPEC §6.6](../../SPEC.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] The suite **blocks injected fabricated numbers/targets** and directive leaks; a change failing any gate is blocked from release (CI) ([docs/14 §8](../14-ai-llm-agent-architecture.md)).
- [ ] Injected news directives cannot introduce ungrounded/directive output ([docs/23 §8](../23-security-auth-and-privacy.md)).

---
## Feature: Prompt-versioning ops + four-eyes  `(N/A infrastructure)`
**Objective:** Operationalize prompt lifecycle — registry, versioning, four-eyes approval, eval-gating, audit stamping — so changes to agent behavior are controlled and reproducible ([docs/14 §8](../14-ai-llm-agent-architecture.md), [compliance §10.2](../21-compliance-risk-and-guardrails.md)). · **Backend dep:** admin console prompt registry, audit log · **Frontend dep:** admin UI · **Data dep:** none.
### Steps
- [ ] 1. **Prompt registry**: every prompt has `promptId` + `promptVersion`, hot-reloadable by version; the version is stamped into every audit record ([docs/14 §7–8](../14-ai-llm-agent-architecture.md)).
- [ ] 2. **Four-eyes** on every prompt publish: author (data-admin) ≠ approver (compliance-officer/super-admin); self-approval rejected; gated on a passing eval run ([compliance §10.2](../21-compliance-risk-and-guardrails.md)).
- [ ] 3. Log each change: actor, role, approver, before/after diff, eval result, version ID, timestamp ([compliance §10.2](../21-compliance-risk-and-guardrails.md)).
- [ ] 4. Provide rollback: a prompt version can be paused/rolled back on repeated REJECT/regenerate ([compliance §11](../21-compliance-risk-and-guardrails.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] Author == approver is rejected (`self_approval_forbidden`) ([compliance §10.2](../21-compliance-risk-and-guardrails.md)).
- [ ] A prompt cannot publish without a passing eval run; the published version appears in subsequent audit records.

---
## Feature: Cost / latency discipline at agent depth  `(N/A infrastructure)`
**Objective:** Keep agentic (multi-step, premium-tier) workflows inside the AI-spend ceiling and latency budget ([SPEC §6.8](../../SPEC.md), [docs/14 §3](../14-ai-llm-agent-architecture.md)). · **Backend dep:** provider abstraction, AI-spend meter, cache · **Frontend dep:** none · **Data dep:** signal-change detection.
### Steps
- [ ] 1. **Provider abstraction / tiering**: cheap (Haiku, `claude-haiku-4-5-20251001`) for repetitive summarization; premium reserved for synthesis (brief, multi-signal portfolio, strategy/backtest interpretation) ([docs/14 §3](../14-ai-llm-agent-architecture.md)).
- [ ] 2. **Regenerate-on-change**: re-run an agent only when its signal category changes; otherwise serve cached ([SPEC §6.8](../../SPEC.md)).
- [ ] 3. **AI-spend ceiling** with alerting and graceful degradation (fall back to non-AI templated facts on overrun); ties to the AI-spend meter ([SPEC §6.8](../../SPEC.md), [docs/22 infra]).
- [ ] 4. **Latency budget**: scheduled agentic passes finish inside the overnight window; on-demand has a P95 target with a non-AI fallback ([docs/14 §3](../14-ai-llm-agent-architecture.md), [docs/12 §5](../12-data-ingestion-and-market-data.md)).
### Tests / Compliance gate / Acceptance criteria
- [ ] Spend stays within ceiling at projected scale; overrun degrades gracefully (no failed user request).
- [ ] Multi-step briefs complete inside the overnight window; on-demand meets P95 or falls back to non-AI facts.

---
## Done-when
- [ ] All documented agents run under one intent-routed orchestration graph, each with a versioned prompt and output schema ([docs/14 §5](../14-ai-llm-agent-architecture.md)).
- [ ] Every user-visible answer passes verification → guardrail → **mandatory Compliance Review** (fail-closed); no path bypasses it (CI-tested) ([docs/14 §6, §5.8](../14-ai-llm-agent-architecture.md), [compliance §9](../21-compliance-risk-and-guardrails.md)).
- [ ] The eval harness gates every prompt/model/graph change on golden datasets; prompt ops are four-eyes + audited ([SPEC §6.6](../../SPEC.md), [compliance §10.2](../21-compliance-risk-and-guardrails.md)).
- [ ] No agent emits per-stock levels, buy-leans, or ranked picks; the RA-gated layer remains in [14-v9-advisory-ra-gated.md](14-v9-advisory-ra-gated.md) ([SPEC §3.2, §4](../../SPEC.md)).
- [ ] Cost/latency stays within the SPEC §6.8 budget at agent depth; every generation is audited ([docs/14 §7](../14-ai-llm-agent-architecture.md)).
