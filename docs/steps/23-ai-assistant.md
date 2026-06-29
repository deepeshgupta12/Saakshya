# Steps · 23 · Conversational AI Assistant

> Read first: [SPEC.md](../../SPEC.md) (§1, §5 worked example, §6.6–6.9 AI constraints, §6.8 fallback) · [Roadmap](../02-product-roadmap.md) (V2/Phase 2) · [AI/LLM agent architecture](../14-ai-llm-agent-architecture.md) · [Feature Modules](../04-feature-modules.md) (§26 AI assistant) · [Screen-by-Screen](../08-screen-by-screen-documentation.md) (§11) · [API Contracts](../10-api-contracts.md) (§9 AI API) · [Compliance & guardrails](../21-compliance-risk-and-guardrails.md)

**Maps to:** Roadmap V2+ · SPEC Phase 2+ · Feature Modules §26 (AI assistant)
**Status:** Not started   |   **Regulatory mode:** A
**Prerequisites:** [04-ai-explanation-layer.md](04-ai-explanation-layer.md) (payload contract, runtime verification harness, output-time guardrail, audit log, suppression), [05-api-and-pipeline.md](05-api-and-pipeline.md) (endpoints + envelope), [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md) (compliance wrappers, evidence drawer). Routes the conversation through the orchestration + mandatory compliance pass in [11-v6-agentic-workflows.md](11-v6-agentic-workflows.md) ([14 §2, §5.8](../14-ai-llm-agent-architecture.md)).

## Overview
The **conversational AI assistant** ([04 §26](../04-feature-modules.md), [08 §11](../08-screen-by-screen-documentation.md)) is a chat dock (route `/ai`, plus a prefill-able dock surface) that answers **natural-language questions only from structured payloads** — computed metrics, scanner tags/sub-scores, entity-resolved news, risk markers ([14 §0.2, §4](../14-ai-llm-agent-architecture.md)). It is **not** a new generation path: it routes user intent through the documented agents ([11-v6-agentic-workflows.md](11-v6-agentic-workflows.md), [14 §5](../14-ai-llm-agent-architecture.md)), so every answer passes the **same** runtime verification → guardrail → **mandatory compliance-review** pipeline before reaching the user ([14 §1, §6, §5.8](../14-ai-llm-agent-architecture.md), [21 §9](../21-compliance-risk-and-guardrails.md)).

It exposes the assistant via `POST /api/ai/ask` ([10 §9](../10-api-contracts.md)): the user asks (optionally scoped to a `symbol`/scanner/sector); an **intent router** picks the right grounded agent (e.g. *"Why is TCS in the momentum scanner?"* → Scanner Explanation; *"What does the volume-breakout scanner show today?"* → Market/Scanner brief); the answer returns with **evidence/source/stock cards**, an `audit_id`, `model_version`, and a not-advice disclaimer. The hard behavior is **refusal/reframe for advice-seeking questions**: *"which should I buy?"* is **not** answered as advice — it is reframed to the evidence ("I explain signals; here is what the data shows for X…") or declined, and the refusal is tracked as a healthy signal ([24 §1.3 `refused`](../24-analytics-seo-and-growth.md), [SPEC §3.2](../../SPEC.md)). Missing critical data → **suppress / non-AI fallback**, never a fabricated answer ([SPEC §6.2, §6.8](../../SPEC.md)).

## Exit gate (Definition of Done)
- [ ] `POST /api/ai/ask` answers free-form questions **grounded strictly** in available structured data; every number/fact traces to the payload or the answer is regenerated/suppressed ([10 §9](../10-api-contracts.md), [SPEC §6.6](../../SPEC.md)).
- [ ] A **deterministic intent router** maps the question to a grounded agent; out-of-scope/advice-seeking intent is routed to **refuse/reframe**, never to a guessed answer ([14 §2](../14-ai-llm-agent-architecture.md)).
- [ ] **No path** produces a user-visible answer that skips verification → guardrail → compliance review ([11-v6-agentic-workflows.md](11-v6-agentic-workflows.md), [14 §1](../14-ai-llm-agent-architecture.md)); enforced and CI-tested.
- [ ] Advice-seeking asks ("which should I buy?", "target for X?", "should I sell?") are **refused/reframed to evidence**; the refusal is audited and analytics-flagged ([SPEC §3.2](../../SPEC.md), [24 §1.3](../24-analytics-seo-and-growth.md)).
- [ ] Answers render with **evidence/source/stock cards**, a `GroundingBadge`, suggested follow-ups, and a persistent not-advice banner; conversation history persists per user.
- [ ] Every turn (answered, refused, suppressed, fallback) writes an **audit record** ([14 §7](../14-ai-llm-agent-architecture.md)).
- [ ] `pytest` (grounding, refusal, suppression, intent routing) + frontend component/E2E green.

---

## Feature: Ask endpoint, intent router & grounding  `(Mode A)`
**Objective:** Turn a natural-language question into a grounded answer by routing to the right agent, fetching only the structured payload, and passing the output through verify → guardrail → compliance. · **Backend dep:** orchestration graph + intent router + compliance pass ([11-v6-agentic-workflows.md](11-v6-agentic-workflows.md)); payload contract + harness + guardrail + audit ([04-ai-explanation-layer.md](04-ai-explanation-layer.md)). · **Frontend dep:** none directly. · **Data dep:** scanner/indicator/news/risk payloads per subject.
### Steps
- [ ] 1. Implement `POST /api/ai/ask` per [10 §9](../10-api-contracts.md): body `{ question, symbol?, scanner?, sector? }` → `{ answer, evidence[], audit_id, model_version, disclaimer, grounded }`. AI rate bucket (10/min); errors `422 DATA_SUPPRESSED`, `429` ([10 §9, §0.3](../10-api-contracts.md)).
- [ ] 2. Build the **intent classifier/router** (`app/ai/assistant/router.py`): map the question to a `query_class` + agent — `explain` (Scanner Explanation / Stock Research), `compare` (Peer comparison context), `define` (glossary/learn lookup, [27-seo-learn-content.md](27-seo-learn-content.md)), `market` (Market Brief), and **`blocked`** (advice-seeking) → refuse/reframe. Routing is deterministic + **logged**; unknown intent → safe fallback, never a guessed agent ([14 §2](../14-ai-llm-agent-architecture.md), [24 §1.2 `query_class`](../24-analytics-seo-and-growth.md)).
- [ ] 3. Resolve the **subject scope** (symbol/scanner/sector) and build the structured payload via the contract builder — the model sees **only** `computed`/`signalTags`/`riskFlags`/`newsSummaries` ([14 §4](../14-ai-llm-agent-architecture.md)). `dataConfidence == LOW` or missing critical field → **suppress before any model call** ([SPEC §6.2](../../SPEC.md), [04 §1](04-ai-explanation-layer.md)).
- [ ] 4. Generate via the agent (cheap/Haiku default), then run **verify → guardrail → compliance review**; on FAIL/REJECT regenerate up to N then **suppress** with a safe fallback ([14 §6, §5.8, §12](../14-ai-llm-agent-architecture.md)).
- [ ] 5. Attach `evidence[]` (claim → `field`/`value`) so every cited fact maps to the payload; return `grounded=false` + the **non-AI templated fallback** when grounding/budget fails — never a fabricated answer ([SPEC §6.8](../../SPEC.md), [10 §0.6](../10-api-contracts.md)).
- [ ] 6. Write an **audit record** for every turn (answered/refused/suppressed/fallback) with prompt+version, payload hash, grounding/guardrail/compliance verdicts ([14 §7](../14-ai-llm-agent-architecture.md)).
### Tests
- [ ] `test_ask_grounded_answer` — a payload-faithful answer passes verify+guardrail, `grounded=true`, every cited fact in payload.
- [ ] `test_ask_blocks_injected_number` — an answer asserting a value absent from the payload is regenerated/suppressed (never returned).
- [ ] `test_ask_suppresses_on_low_confidence` — `dataConfidence=LOW` returns suppressed with **zero** model calls.
- [ ] `test_router_deterministic_and_logged` — same question → same route; route logged.
### Compliance gate
- [ ] Answers are grounded, runtime-verified, guardrailed, compliance-reviewed; no entry/target/SL, no ranked "what to buy", no directive tail ([SPEC §3.2, §6.6, §6.9](../../SPEC.md), [14 §0](../14-ai-llm-agent-architecture.md)).
### Acceptance criteria
- [ ] Every answer traces to the payload or is suppressed/fallback; no path bypasses verify → guardrail → compliance ([10 §14](../10-api-contracts.md), [11-v6-agentic-workflows.md](11-v6-agentic-workflows.md)).

---

## Feature: Refusal / reframe of advice-seeking questions  `(Mode A)`
**Objective:** Detect advice-seeking intent ("which should I buy?", "target/SL for X?", "should I sell?") and **refuse or reframe to evidence** rather than answering as advice — a first-class, tested behavior. · **Backend dep:** intent router, guardrail/compliance layer, blocked-phrase list ([04-ai-explanation-layer.md](04-ai-explanation-layer.md), [21 §9](../21-compliance-risk-and-guardrails.md)). · **Frontend dep:** refusal message rendering. · **Data dep:** none beyond subject payload (for the reframe).
### Steps
- [ ] 1. Classify advice-seeking intent in the router (`query_class="blocked"`): buy/sell/hold asks, "what should I do", target/stop/entry-price asks, allocation/position-sizing asks ([14 §10 prohibited table](../14-ai-llm-agent-architecture.md), [SPEC §3.3](../../SPEC.md)).
- [ ] 2. Produce a **Mode-A reframe**, not a refusal-only dead end: *"I explain signals, not buy/sell calls. Here's what the data shows for X: it appears in the momentum scanner, is trading above its 50-DMA, and RSI is elevated so short-term risk is higher."* — assembled **only** from grounded payload facts (so it still passes verify + guardrail + compliance). When no valid subject exists, decline and ask for valid context ([04 §26 states](../04-feature-modules.md), [08 §11](../08-screen-by-screen-documentation.md)).
- [ ] 3. Ensure the reframe text itself passes the **full** pipeline — it is generated/templated text, never above the guardrail ([11 §41 substance test](11-v6-agentic-workflows.md), [21 §9 Stage 3](../21-compliance-risk-and-guardrails.md)).
- [ ] 4. Mark the turn `refused=true` in the response/audit/analytics; this is a **healthy** compliance signal, deliberately tracked ([24 §1.3, §2 T5](../24-analytics-seo-and-growth.md)).
- [ ] 5. Never let a reframe smuggle a directive: no "but it looks strong", no implied buy-lean — the compliance-review agent rejects advisory **substance**, not just literal phrases ([14 §5.8](../14-ai-llm-agent-architecture.md), [11 §41](11-v6-agentic-workflows.md)).
### Tests
- [ ] `test_refuses_which_should_i_buy` — "which of these should I buy?" → reframed-to-evidence/declined, `refused=true`, no buy-lean.
- [ ] `test_refuses_target_and_sell_asks` — "what's the target for X?" / "should I sell X?" → refused/reframed; no target/SL/sell instruction emitted.
- [ ] `test_reframe_passes_compliance` — the reframe text passes verify + guardrail + compliance (substance check).
### Compliance gate
- [ ] No advice-seeking question yields a buy/sell/hold call, target, SL, or allocation; reframes contain only grounded, descriptive facts ([SPEC §3.2, §3.3](../../SPEC.md), [14 §10](../14-ai-llm-agent-architecture.md)).
### Acceptance criteria
- [ ] Advice asks are refused/reframed and audited as `refused=true`; the reframe is grounded and compliance-clean ([24 §2 T5](../24-analytics-seo-and-growth.md)).

---

## Feature: Chat dock UI — cards, follow-ups, history  `(Mode A)`
**Objective:** Build the conversational surface — message thread, composer with suggested prompts/follow-ups, evidence/source/stock cards, grounding badge, and persistent conversation history. · **Backend dep:** `/api/ai/ask`, conversation-history store ([10 §9](../10-api-contracts.md), [05 §3 `/ai`](../05-information-architecture-and-url-paths.md)). · **Frontend dep:** `GroundingBadge`, `NotAdviceBanner`, `EvidenceDrawer`/`EvidenceCitation`, `ScoreBadge` from [06-frontend-foundation-and-v1-screens.md](06-frontend-foundation-and-v1-screens.md). · **Data dep:** answer payload + evidence + threads.
### Steps
- [ ] 1. Build `app/(app)/ai/page.tsx` (`/ai`, auth, `noindex` per [05 §3](../05-information-architecture-and-url-paths.md)) composing `src/components/ai/`: `AiChatThread`, `AiMessage` (per-message `GroundingBadge`), composer with `SuggestedPrompts` ("Explain TCS's momentum signals", "What does the volume-breakout scanner show today?") ([08 §11](../08-screen-by-screen-documentation.md)).
- [ ] 2. Render answers with **evidence card** (`EvidenceCitation`/drawer mapping each claim → `field`/`value`), **source card** (news source link + timestamp + confidence, [14 §5.4](../14-ai-llm-agent-architecture.md)), and **stock card** (mini header → deep-link to `/stocks/[symbol]`). Numbers reveal as a block — **no typewriter on fabricated/streamed numbers** ([08 §11 animation](../08-screen-by-screen-documentation.md)).
- [ ] 3. **Suggested follow-ups:** after an answer, surface grounded next-question chips derived from the subject (e.g. "Show its risk flags", "How does it compare to peers?"); chips never propose an action ([04 §26](../04-feature-modules.md)).
- [ ] 4. **Conversation history:** persist threads via `GET /api/ai/threads`; new-thread, prefill-from-stock-page (`?prefill=`) per [08 §11 CTAs](../08-screen-by-screen-documentation.md); each message retains its `audit_id` for traceability.
- [ ] 5. States ([04 §26](../04-feature-modules.md)): **empty** (welcome + suggested prompts + capability/limits note "I explain signals; I don't give buy/sell advice"); **refusal** (the Mode-A reframe rendered distinctly); **suppressed/fallback** ("Couldn't generate a grounded answer" → retry / non-AI fallback, [SPEC §6.8](../../SPEC.md)); **loading** (thinking indicator, no fake number streaming). Persistent `NotAdviceBanner`.
- [ ] 6. Mobile: full-height chat, suggestions as chips, sticky composer ([08 §11 mobile](../08-screen-by-screen-documentation.md)).
- [ ] 7. Analytics ([24 §1.2](../24-analytics-seo-and-growth.md)): `ai_query{query_class, symbol?, grounded, model_version, audit_id, refused}`, plus `ai_chat_view`, `ai_message_send`, `ai_citation_open`, `ai_refusal{reason}`, `ai_fallback_served`.
### Tests
- [ ] Component: `AiMessage` renders the grounding badge + evidence card; a refusal renders the reframe distinctly; suppressed payload renders the fallback state.
- [ ] E2E (grounding): ask "Why is TCS in the momentum scanner?" → grounded answer + evidence card + grounding badge; assert **no** entry/target/SL element.
- [ ] E2E (refusal): ask "Which should I buy?" → reframe-to-evidence message, `refused` analytics event, **no** buy-lean in the DOM.
### Compliance gate
- [ ] Every AI message carries a grounding badge + not-advice; refusals never expose a buy-lean/target/SL; numbers never typewriter-streamed before grounding ([08 §11 acceptance](../08-screen-by-screen-documentation.md), [SPEC §6.6](../../SPEC.md)).
### Acceptance criteria
- [ ] The dock renders grounded answers with evidence/source/stock cards + follow-ups, persists history, and surfaces refusal/suppressed states correctly ([08 §11](../08-screen-by-screen-documentation.md)).

---

## Done-when
- [ ] `POST /api/ai/ask` answers natural-language questions grounded strictly in structured payloads, routed by a deterministic intent router through the documented agents ([10 §9](../10-api-contracts.md), [11-v6-agentic-workflows.md](11-v6-agentic-workflows.md)).
- [ ] No answer reaches a user without passing runtime verification → guardrail → **mandatory compliance review**; every turn is audited ([14 §1, §5.8, §7](../14-ai-llm-agent-architecture.md)).
- [ ] Advice-seeking questions are **refused/reframed to evidence** and tracked as `refused=true`; missing data suppresses to a non-AI fallback, never fabrication ([SPEC §3.2, §6.2, §6.8](../../SPEC.md)).
- [ ] The chat dock renders evidence/source/stock cards, suggested follow-ups, grounding badge + not-advice banner, and persistent conversation history ([08 §11](../08-screen-by-screen-documentation.md)).
- [ ] Grounding + refusal tests pass in CI; analytics carry `grounded`/`model_version`/`audit_id`/`refused` per [24](../24-analytics-seo-and-growth.md).
