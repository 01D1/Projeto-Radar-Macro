# Research Summary — Investment Intelligence Platform

## Key Findings

### Stack
**Core additions to existing Python base:**
- `tenacity` — retry wrapper around all external APIs (CVM, BCB, yfinance) — CRITICAL
- `pydantic v2` + `instructor` — structured LLM output (guaranteed thesis schema) — CRITICAL
- `sqlalchemy` + `alembic` — dialect-neutral ORM enabling SQLite→Supabase migration — CRITICAL
- `streamlit` + `plotly` — dashboard layer
- `weasyprint` + `jinja2` — PDF report generation
- `structlog` — structured logging across all modules
- `pydantic-settings` — typed `.env` configuration on startup

Existing stack (anthropic, pandas, yfinance, ruff) stays. No framework switches.

### Table Stakes Features
Users expect before the AI layer is credible:
1. LTM financial aggregation (rolling 4-quarter from CVM ITR)
2. Standard multiples (P/E, EV/EBITDA, P/BV) vs. peers
3. DCF fair value with WACC from Selic + CDS Brazil
4. Macro panel (Selic, IPCA, PTAX, CDS, PIB)
5. News + corporate events feed per ticker
6. Data freshness timestamps on everything

### Core Differentiator
**AI Investment Thesis** is the product — not the data terminal. The thesis must be:
- Schema-enforced (Pydantic + instructor): bull case, bear case, 3-5 drivers, 3-5 risks, fair value, positioning, confidence
- Grounded in computed data (LLM only synthesizes — all numbers injected as inputs)
- Portuguese language output (client-facing, Brazilian market)
- Regenerated only when input data changes (hash-based invalidation for cost control)

### Architecture
**Layered pipeline: Ingestion → Storage → Engines → Intelligence → Delivery**

Build order (strict dependency chain):
1. Foundation: deduplicate codebase, `.env` config, SQLAlchemy schema, retry wrappers, logging
2. Reliable Ingestion: unified CVM/BCB/yfinance/news with retry + freshness tracking
3. Financial Engine: LTM, multiples, DCF, technical signals
4. Intelligence Layer: Claude API + instructor + thesis schema + cost controls ← core differentiator
5. Delivery: Streamlit dashboard + Telegram + PDF reports

### Watch Out For
Critical pitfalls to address immediately:

| # | Pitfall | When |
|---|---------|------|
| P3 | Hardcoded credentials in `news_hunter/config.py` — security risk | Phase 1 blocker |
| P8 | Three duplicate code copies — split-brain maintenance nightmare | Phase 1 blocker |
| P1 | LLM hallucinated numbers in client output — credibility killer | Phase 4 design |
| P4 | LLM cost runaway without input-hash invalidation | Phase 4 design |
| P2 | CVM format changes break ingestion silently | Phase 2 design |
| P7 | DCF terminal value explosion (when terminal growth ≥ WACC) | Phase 3 design |
| P13 | Banks use COSIF not IFRS — different account structure entirely | Phase 3 design |

### Brazilian Market Specifics
- CVM filings: DFP (annual), ITR (quarterly), IPE (events) — all need XML + PDF parsing
- Banks (Itaú, Bradesco, BB, Santander): COSIF accounting — requires separate financial model
- B3 tickers: ON/PN share class suffix handling (PETR3 vs PETR4); append ".SA" for yfinance
- PTAX is the official FX rate — use for USD-revenue company analysis (VALE, PETR, exporters)
- JCP (Juros sobre Capital Próprio) ≠ regular dividends — different tax treatment, affects yield
- Holiday calendar: use `pandas_market_calendars` with `BMFBOVESPA` calendar — not US business days
- Client output: Portuguese language, CVM IN 598 disclaimer required

---

## Recommended Phase Structure (Input for Roadmapper)

Suggested 6 phases mapped to research findings:

**Phase 1 — Foundation & Cleanup** (2-3 weeks)
Archive duplicate codebases, migrate to `.env`, SQLAlchemy schema with alembic, retry wrappers, structlog

**Phase 2 — Reliable Data Ingestion** (2-3 weeks)
Unified CVM (DFP/ITR/IPE), BCB macro, B3 prices, news RSS — all with retry, validation, freshness tracking

**Phase 3 — Financial Engine** (3-4 weeks)
LTM aggregation, multiples, DCF (with bank/industrial bifurcation), technical signals, peer comparison

**Phase 4 — Intelligence Layer** (2-3 weeks)
Pydantic thesis schema, instructor + Claude API, prompt templates, hash invalidation, thesis versioning

**Phase 5 — Delivery Layer** (2-3 weeks)
Streamlit dashboard, Telegram alerts/brief, PDF report generator, Obsidian integration cleanup

**Phase 6 — Advanced Features** (ongoing)
Event-driven thesis refresh, opportunity detection, scenario analysis, Supabase migration

---
*Synthesized: 2026-05-06*
