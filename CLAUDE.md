# Investment Intelligence Platform — Project Guide

## Project Context

AI-powered investment decision engine for Brazilian financial markets. Combines quantitative analysis (DCF, multiples, signals), macro intelligence (BCB/CVM), and news synthesis to generate real-time, actionable investment thesis per asset — client-ready in seconds.

**Core value:** "Bloomberg tells you what's happening. This platform tells you what to do and why."

See: `.planning/PROJECT.md` for full context, `.planning/ROADMAP.md` for execution phases.

---

## GSD Workflow

This project uses the Get Shit Done (GSD) framework.

### Standard phase workflow
```
/gsd-discuss-phase N    → gather context, clarify approach
/gsd-plan-phase N       → create execution plan
/gsd-execute-phase N    → execute all plans in the phase
/gsd-verify-work N      → verify deliverables match phase goal
```

### Current state
- Phase 1: Foundation & Cleanup — **Not started**
- Start with: `/clear` then `/gsd-discuss-phase 1`

---

## Architecture Principles

This project follows a strict layered pipeline:

```
Ingestion → Storage (SQLite) → Financial Engine → Intelligence Layer → Delivery
```

**Hard rules:**
1. LLM (Claude API) synthesizes — it never calculates. All numbers injected as inputs.
2. `.env` for all credentials. No hardcoded tokens anywhere.
3. `tenacity` retry on every external API call (CVM, BCB, yfinance, Anthropic, Telegram).
4. `instructor` + Pydantic schema enforces AI thesis structure — no free-form parsing.
5. Input hash gates thesis regeneration — only call Claude API when data actually changes.
6. Canonical source: `Analista de Investimentos/12_PYTHON/src/`. No other copies are active.

---

## Key Technical Decisions

| Decision | Rationale |
|---|---|
| SQLite (local-first) | Zero-ops, single-user v1; schema designed for SQLite→Supabase migration |
| `instructor` over raw Claude API | Guaranteed structured thesis output (Pydantic model) |
| `structlog` for logging | Structured JSON logs with ticker + run ID — traceable end-to-end |
| Jinja2 for prompts + PDF templates | Prompts are data, not code; easy to iterate without deploys |
| Bank/industrial model bifurcation | Banks use COSIF (NIM/ROE/DDM), not IFRS EBITDA/DCF |

---

## Critical Pitfalls to Avoid

- **P1 — LLM hallucinated numbers**: Never ask LLM to compute or look up values. Inject all numbers from Financial Engine. Add post-generation cross-check against DCF (±10%).
- **P3 — Hardcoded credentials**: Already present in `news_hunter/config.py`. Phase 1 blocker.
- **P7 — DCF terminal value explosion**: Validate `terminal_growth < WACC` before running. Flag output outside 0.1x–5.0x current price.
- **P13 — Bank COSIF accounting**: ITUB4, BBDC4, BBAS3 etc. use COSIF, not IFRS. Route to separate model.
- **P4 — LLM cost runaway**: Hash inputs, gate regeneration, cap at 2×/day per ticker.

---

## Brazilian Market Specifics

- CVM filings: DFP (annual), ITR (quarterly), IPE (events) — all XML + PDF
- B3 tickers: append `.SA` for yfinance; handle ON (PETR3) vs PN (PETR4) share classes
- Holiday calendar: use `pandas_market_calendars` with `BMFBOVESPA` — not US business days
- Client output: Portuguese language; include CVM IN 598 disclaimer on all reports
- Macro: Selic + CDS Brazil → WACC; PTAX → USD-revenue company adjustments

---
*Generated: 2026-05-06*
