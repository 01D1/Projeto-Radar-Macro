# Investment Intelligence Platform

## What This Is

An AI-powered investment decision engine for Brazilian financial markets. The platform combines quantitative analysis (DCF, multiples, technical signals), macro intelligence (BCB/CVM data), and news synthesis to generate real-time, actionable investment thesis per asset — bull/bear case, key drivers, risks, fair value vs price, and suggested positioning. Outputs are institutional-quality and client-ready. It replaces hours of manual analysis with seconds of AI synthesis.

## Core Value

Each asset gets an AI-generated investment thesis — bull/bear case, key drivers, risks, fair value, and suggested positioning — delivered client-ready in seconds. Bloomberg tells you what's happening; this platform tells you what to do and why.

## Requirements

### Validated

- ✓ CVM financial statements ingestion (DFP/ITR/IPE) — existing
- ✓ BCB macroeconomic data ingestion (Selic, IPCA, PIB, CDS, PTAX) — existing
- ✓ Yahoo Finance price series ingestion (B3 equities) — existing
- ✓ News aggregation via RSS feeds (17+ sources) — existing
- ✓ Telegram delivery pipeline — existing
- ✓ Claude API integration (claude-sonnet-4-6 / claude-haiku) — existing
- ✓ SQLite local data persistence — existing
- ✓ Obsidian vault output delivery — existing

### Active

- [ ] Unified ingestion pipeline (deduplicate CVM + bank + macro collectors into single src/)
- [ ] Configuration via .env (remove all hardcoded paths, tokens, and API keys)
- [ ] Financial Engine: automated DCF + multiples + projections per asset
- [ ] Market Data Engine: unified price + macro + indicator layer with reliability guarantees
- [ ] News & Qualitative Engine: earnings parser (PDF + IPE/CVM + RSS), corporate event detection
- [ ] Intelligence Layer: AI-generated investment thesis (bull/bear, drivers, risks, fair value, positioning)
- [ ] Opportunity detection: mispricing signals, momentum shifts, macro-driven trades, event-driven plays
- [ ] Risk panel: portfolio monitoring and scenario analysis
- [ ] Streamlit institutional dashboard: multi-screen layout (watchlist, valuation, signals, macro, news)
- [ ] Client-ready PDF report generation per asset or portfolio
- [ ] Logging, monitoring and error handling layer across all modules
- [ ] Versioned data outputs with historical tracking

### Out of Scope

- Real-time trading / order execution — regulatory and scope boundary
- Multi-user authentication system — single-analyst tool in v1
- Bloomberg API integration — cost and complexity; public data sources sufficient
- Cloud deployment (Supabase persistence) — local-first in v1, migration path designed in
- Real-time streaming prices — polling cadence sufficient for current use case

## Context

**Existing codebase** under `Analista de Investimentos/12_PYTHON/` — functional but fragmented:
- Three parallel code copies exist: `Analista de Investimentos/12_PYTHON/`, `Meu segundo Cerébro/12_PYTHON/`, and `_ARQUIVO_Analista_vs_code/12_PYTHON/` — the last two appear to be archives/backups
- Two separate pipeline implementations: `src/` (newer, modular) and `pipeline banco completo/` (older, bank-focused)
- Claude API already wired in `src/content/llm_client.py` with prompt caching
- Telegram delivery works via both `src/delivery/telegram_bot.py` and `news_hunter/telegram_client.py`
- CVM ingestion, BCB macro, and Yahoo Finance all functional but scattered
- Hardcoded paths and tokens present (see `news_hunter/config.py`) — migration to .env required
- Supabase declared as dependency but not yet integrated

**Market focus**: Brazilian equities (B3), fixed income, macro (Selic/IPCA/PIB/FX)

**Primary user**: Investment analyst; outputs delivered to clients (institutional-format reports, Telegram alerts, dashboard)

**Stack**: Python 3.x, pandas, yfinance, anthropic SDK, Streamlit (target), SQLite, ruff

## Constraints

- **Tech Stack**: Python ecosystem — all new code must remain in Python; no framework switches
- **Reuse**: Maximize reuse of existing ingestion and parsing logic; refactor don't rewrite
- **Config**: All credentials and paths via `.env` and `python-dotenv` — no hardcoded values anywhere
- **Modularity**: Clear boundaries between ingestion / processing / intelligence / delivery layers
- **Scalability**: Design for future Supabase migration without locking into SQLite-specific patterns
- **No overengineering**: First iteration ships working features; abstractions only when justified

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Consolidate to single `src/` under `Analista de Investimentos/12_PYTHON/` | Three parallel copies = maintenance nightmare; archive the others | — Pending |
| `.env` + `python-dotenv` for all configuration | Hardcoded tokens are a security risk and block team/cloud use | — Pending |
| Claude API as central intelligence layer (not a peripheral feature) | AI thesis generation is the core value prop; treat it as infrastructure | — Pending |
| SQLite as v1 persistence, Supabase-compatible schema design | Ship fast locally; schema designed for cloud lift-and-shift later | — Pending |
| Streamlit for dashboard (single-page institutional layout) | Already in ecosystem, fastest path to client-ready UI | — Pending |
| Unified ingestion abstraction over raw scrapers | Current scrapers are brittle; wrap them with retry/fallback logic | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-06 after initialization*
