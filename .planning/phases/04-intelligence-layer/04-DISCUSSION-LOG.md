# Phase 4: Intelligence Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** 04-intelligence-layer
**Areas discussed:** Thesis schema shape, instructor wiring, Prompt template location, Opportunity signals scope

---

## Thesis Schema Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Flat strings | drivers: list[str], risks: list[str]. Simple, fast to validate, easy to render. | |
| Structured sub-objects | class Driver(BaseModel): title, description, impact. class Risk(BaseModel): title, description, severity. More granular — Phase 5 renders each field separately. | ✓ |

**User's choice:** Structured sub-objects

### Sub-question: Fields in Driver/Risk

| Option | Description | Selected |
|--------|-------------|----------|
| title + description | 2-field, minimal, easy for instructor to enforce | |
| title + description + impact/severity | Adds explicit materiality rating (HIGH/MEDIUM/LOW). Phase 5 can filter/sort by impact. | ✓ |

**User's choice:** title + description + impact/severity

### Sub-question: summary_one_line field

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add summary_one_line | Phase 5 Telegram alert uses this directly. | ✓ |
| No — Phase 5 constructs summary | Keeps schema minimal. | |

**User's choice:** Yes — add summary_one_line field

---

## instructor Wiring

| Option | Description | Selected |
|--------|-------------|----------|
| New IntelligenceClient | Separate class in intelligence_layer.py. LLMClient stays unchanged. Clean separation. | ✓ |
| Extend LLMClient | Add generate_structured() to LLMClient. Reuses retry/caching but adds complexity. | |

**User's choice:** New IntelligenceClient

### Sub-question: Validation failure behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Hard-fail with IngestionError | No partial/empty thesis ever stored. Matches ROADMAP success criterion. | ✓ |
| Fallback to stub thesis | Pipeline continues for other tickers on failure. | |

**User's choice:** Hard-fail with IngestionError

---

## Prompt Template Location

| Option | Description | Selected |
|--------|-------------|----------|
| Jinja2 in Python src/ | Version-controlled alongside code. No vault path dependency. Testable. | ✓ |
| Vault 11_PROMPTS/ markdown | Existing LLMClient pattern. Editable without deploy but creates a non-code dependency. | |

**User's choice:** Jinja2 template in src/templates/thesis_prompt.j2

### Sub-question: Data injection level

| Option | Description | Selected |
|--------|-------------|----------|
| Full snapshot | LTM + multiples + DCF + macro + signals + last 3 news + ticker metadata. | ✓ |
| Valuation-only | DCF fair value + multiples + positioning only. | |

**User's choice:** Full snapshot injection

---

## Opportunity Signals Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Same intelligence_layer.py | compute_opportunity_signals() called after thesis generation. Single job. | ✓ |
| Separate signals module | src/opportunity_signals.py. More modular but adds another file and job. | |

**User's choice:** Same intelligence_layer.py

### Sub-question: Conviction score formula

| Option | Description | Selected |
|--------|-------------|----------|
| Weighted sum | DCF divergence (40pts) + momentum alignment (30pts) + event catalyst (30pts). Score 0-100. Signals shown if >=40. | ✓ |
| Boolean flags only | Present/absent per signal type, ranked by priority. No numeric score. | |

**User's choice:** Weighted sum

### Sub-question: IPE event recency

| Option | Description | Selected |
|--------|-------------|----------|
| Last 30 days only | Prevents stale events from generating stale signals. | ✓ |
| Any IPE event for ticker | Broader coverage but risks flagging old catalysts. | |

**User's choice:** Last 30 days only

---

## Claude's Discretion

- `instructor.Mode.ANTHROPIC_TOOLS` — Claude chose this over `instructor.Mode.JSON` based on Anthropic best practices (tool-use mode preserves the validation retry loop).
- `version_num` auto-increment per ticker (via MAX query) — Claude chose this over global auto-increment for Supabase portability.

## Deferred Ideas

- Multi-scenario thesis (bull/base/bear DCF comparison) — v2 requirement
- Peer comparison section in thesis — cross-sector multiples, v2
- LLM-enriched insights in insight_engine.py — Phase 4 focuses on structured thesis; insight enrichment is a follow-on
- Thesis quality scoring / feedback loop — future phase
