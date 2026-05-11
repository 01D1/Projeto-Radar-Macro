# Roadmap — Investment Intelligence Platform
*Created: 2026-05-06*

---

## Phases

- [x] **Phase 1: Foundation & Cleanup** — Secure credentials, consolidate codebases, wire retry/logging infrastructure (completed 2026-05-10)
- [ ] **Phase 2: Reliable Data Ingestion** — All data sources (CVM, BCB, B3, news) running with retry, validation, and freshness tracking
- [ ] **Phase 3: Financial Engine** — LTM aggregation, multiples, DCF (with bank bifurcation), and technical signals computed per ticker
- [ ] **Phase 4: Intelligence Layer** — AI investment thesis generated, validated, cost-controlled, and versioned per ticker
- [ ] **Phase 5: Delivery Layer** — Streamlit dashboard, Telegram alerts, and PDF reports operational end-to-end

---

## Phase Details

### Phase 1: Foundation & Cleanup
**Goal:** The codebase has a single canonical source, no credentials in source code, and every external call is wrapped with retry logic and structured logging — making all subsequent phases safe to build.
**Depends on:** —
**Requirements:** FOUND-01, FOUND-02, FOUND-03, FOUND-04
**UI hint:** no

**Success Criteria:**
1. Running `python -m src.main` from `Analista de Investimentos/12_PYTHON/` is the one and only way to execute the platform; the three duplicate directory trees are archived/deleted and no import path references them.
2. The platform refuses to start in production mode if `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, or any required credential is absent from `.env`; no token appears as a literal string anywhere in source code.
3. Any external API call (CVM, BCB, yfinance, Anthropic, Telegram) that fails due to a transient network error automatically retries with exponential backoff; a permanent failure surfaces a structured error log entry rather than an unhandled exception crash.
4. Every pipeline run produces structured log output (module name, ticker, run ID) in `logs/`; log files rotate daily; a developer can trace any execution path end-to-end from log output alone.

**Plans:** 3 plans
Plans:
- [x] 01-01-PLAN.md — Codebase consolidation: archive duplicate src/ trees, fix import paths, sys.path cleanup, venv rebuild
- [x] 01-02-PLAN.md — Credentials & config migration: remove hardcoded tokens, wire pydantic-settings + .env, startup validation
- [x] 01-03-PLAN.md — Gap closure: create errors.py (IngestionError), extend retry.py (jitter + IngestionError), add bind_run_id to logger.py, move CR-04 production guard inside app()

---

### Phase 2: Reliable Data Ingestion
**Goal:** All four data source categories (CVM filings, BCB macro, B3 prices, news feeds) ingest reliably on a daily schedule, with freshness timestamps, deduplication, and gap detection — so the Financial Engine always operates on trustworthy data.
**Depends on:** Phase 1
**Requirements:** ING-01, ING-02, ING-03, ING-04, ING-05, ING-06, ING-07
**UI hint:** no

**Success Criteria:**
1. A daily scheduler run ingests CVM DFP (annual), ITR (quarterly), and IPE (corporate events) for all watchlist tickers; parsed records are stored with account code normalization and raw XML preserved; ITR quarters are reconciled against DFP for overlapping periods.
2. BCB macro series (Selic, IPCA, PTAX, CDS Brazil, PIB) are fetched via the SGS API with per-series freshness timestamps; a stale or failed fetch produces a warning log entry with the last-known timestamp — not a silent fallback to hardcoded 2025 values.
3. B3 OHLCV price series for all watchlist tickers are downloaded daily; corporate actions are adjusted; data gaps are flagged with an explicit `GAP` marker rather than interpolated.
4. News articles from 17+ RSS sources are ingested, deduplicated by URL, and tagged with the relevant watchlist ticker where detectable; IPE event PDFs have their text extracted and stored.
5. Every scheduler run produces a structured summary log: duration, records updated per source, and any per-source failures — visible in `logs/`.

**Plans:** 4 plans (planned 2026-05-10)

**Wave 1** *(parallel — no file overlap)*
- [x] 02-01-PLAN.md — ingestion.db schema (db.py) + CVM DFP/ITR/IPE: CSV download, watchlist filtering, raw CSV preservation, ITR dedup, IPE classification + PDF extraction
- [x] 02-02-PLAN.md — BCB SGS macro ingestion (bcb.py) + B3 OHLCV prices (b3_scraper.py extension): freshness check, CDS bp conversion, gap detection

**Wave 2** *(blocked on Wave 1 — needs ingestion.db schema from 02-01)*
- [ ] 02-03-PLAN.md — News sync (news_sync.py): cross-DB bridge from news_hunter/banco.db to ingestion.db with URL deduplication and B3 ticker tagging

**Wave 3** *(blocked on Wave 2 — wires all three modules into scheduler)*
- [ ] 02-04-PLAN.md — Ingestion scheduler wiring: 4 job functions in scheduler.py, bind_run_id, D-15 summary logs, schedules.yaml cron entries

**Cross-cutting constraints:**
- @retry(attempts=3, delay=2.0, backoff=2.0, jitter=0.5) on every external API call (all plans)
- bind_run_id("ingest") at top of every scheduler job (Plan 04)
- TEXT UUID primary keys, ISO date strings, no AUTOINCREMENT (Plan 01 schema — D-06)

---

### Phase 3: Financial Engine
**Goal:** For every watchlist ticker, the platform computes LTM financials, standard valuation multiples, a DCF fair value (with bank/industrial bifurcation), and technical momentum signals — establishing the quantitative foundation the AI layer requires.
**Depends on:** Phase 2
**Requirements:** FIN-01, FIN-02, FIN-03, FIN-04, FIN-05, FIN-06
**UI hint:** no

**Success Criteria:**
1. LTM (Last Twelve Months) financials — revenue, EBITDA, net income, FCF, net debt — are computed for every watchlist ticker as a rolling sum of the trailing 4 ITR quarters, reconciled against the latest DFP annual; the computation runs automatically after each ingestion cycle.
2. Standard multiples (P/E, EV/EBITDA, P/BV, dividend yield, EV/Revenue) are updated daily using the latest LTM financials and current market price; stale or missing prices produce a flagged record rather than a zero-division error.
3. DCF fair value is computed per ticker with WACC derived from Selic + CDS Brazil + equity risk premium, 5-year FCF projections, and configurable terminal growth rate; output includes fair value in BRL and upside/downside percentage vs current price.
4. The DCF model rejects invalid inputs before running (terminal growth >= WACC, WACC <= 5%) and flags fair values outside the 0.1x–5.0x price range as "FORA DO INTERVALO CONFIAVEL" — no zero-value or astronomically wrong outputs reach downstream consumers.
5. Bank tickers (ITUB4, BBDC4, BBAS3, SANB11, BPAC11, etc.) are automatically routed to a NIM-based / ROE / dividend discount model; industrial tickers receive the standard EBITDA/FCFF DCF; technical signals (RSI-14, MACD, MA crossover, composite momentum score) are computed for all tickers.

**Plans:**
1. LTM aggregation engine — implement rolling 4-quarter ITR sum, DFP reconciliation, output schema; handle COSIF bank accounts separately from IFRS industrials
2. Multiples computation — implement P/E, EV/EBITDA, P/BV, dividend yield, EV/Revenue with daily price refresh and missing-data flagging
3. DCF engine (industrial) — implement WACC derivation, 5-year FCF projection, terminal value, input validation guards (terminal growth vs WACC), confidence interval check
4. Bank financial model — implement NIM-based model, ROE analysis, DDM for dividend-paying banks; wire sector routing via `SectorConfig`
5. Technical signals — implement RSI-14, MACD (12/26/9), 50/200-day MA, crossover signal, composite momentum score (0–100)

---

### Phase 4: Intelligence Layer
**Goal:** The platform generates a schema-enforced, data-grounded AI investment thesis (bull/bear case, drivers, risks, fair value, positioning, confidence) per ticker in Portuguese — regenerating only when input data changes, and storing versioned history.
**Depends on:** Phase 3
**Requirements:** INT-01, INT-02, INT-03, INT-04, INT-05, INT-06
**UI hint:** no

**Success Criteria:**
1. Running thesis generation for a ticker produces a structured Pydantic-validated output containing: bull case, bear case, 3–5 key drivers, 3–5 risks, fair value in BRL, methodology disclosure, positioning (COMPRAR / MANTER / VENDER), confidence (ALTA / MEDIA / BAIXA), and rationale — all in Portuguese; the schema is enforced by `instructor`; generation never silently returns a partial or empty thesis.
2. Every number in the thesis (fair value, multiples, macro rates) is injected from Financial Engine outputs — the LLM performs synthesis only; a post-generation cross-check confirms the thesis fair value matches the DCF output within ±10% tolerance, and flags any deviation.
3. Thesis regeneration is gated by an input hash (DCF result + top multiples + macro snapshot + top 3 headlines + signals); a ticker whose data has not changed since the last generation does not trigger a new Claude API call; maximum 2 regenerations per ticker per day are enforced.
4. Every thesis version is stored in the database with its input hash, generation timestamp, and a diff summary relative to the previous version; a developer can query any ticker's thesis history and see what changed and when.
5. Opportunity signals (price vs DCF divergence >20%, MA crossover with fundamental backing, IPE event impact) are computed per ticker and ranked by conviction score; the top 3 opportunities are available as a structured output for downstream delivery.

**Plans:**
1. Thesis schema & instructor wiring — define Pydantic thesis schema, wire `instructor` + Claude API (`claude-sonnet-4-6`), implement Portuguese prompt templates with data injection context
2. Data grounding & validation — implement number injection from Financial Engine, post-generation DCF cross-check (±10% tolerance), schema completeness guard
3. Hash-based invalidation & cost controls — implement input hash computation, regeneration gate, 2-per-day cap, cache storage
4. Thesis versioning — implement database storage with version history, input hash tracking, per-version diff summary
5. Opportunity signals & ranking — implement price-vs-DCF divergence detection, momentum shift signal, event-driven signal, conviction score ranking, top-3 structured output

---

### Phase 5: Delivery Layer
**Goal:** Analysis, thesis, and opportunity outputs are accessible through a Streamlit dashboard, Telegram alerts, and on-demand PDF reports — all client-ready in Portuguese with proper disclaimers.
**Depends on:** Phase 4
**Requirements:** DEL-01, DEL-02, DEL-03, DEL-04, DEL-05
**UI hint:** yes

**Success Criteria:**
1. The Streamlit dashboard loads with four pages — Watchlist overview, Asset detail, Macro panel, Opportunities — all populated with live data from the database; the watchlist page renders in under 5 seconds for up to 50 tickers using `st.cache_data` with TTL; every data item displays a freshness timestamp.
2. The Asset detail page for any ticker shows: current price, valuation multiples, DCF fair value vs price, LTM financial highlights, macro context, recent news, full AI investment thesis (bull/bear, drivers, risks, positioning, confidence) — all without leaving the page.
3. The Telegram bot sends an alert whenever a ticker's thesis positioning changes (e.g., MANTER → COMPRAR), including ticker, new positioning, confidence level, one-sentence rationale, and the top opportunity of the moment; the daily morning brief delivers macro snapshot, top 3 movers, and top opportunity at a configurable time.
4. A PDF report generated on demand for any ticker from the Streamlit dashboard contains: thesis summary, DCF + multiples valuation, LTM financial highlights, macro context, key risks, and the CVM IN 598 disclaimer; the report generates and is downloadable in under 30 seconds.

**Plans:**
1. Streamlit dashboard — implement multi-page layout (Watchlist, Asset detail, Macro panel, Opportunities), wire `st.cache_data` TTL, freshness timestamps, <5s render target
2. Asset detail page — implement per-ticker view with full thesis display, valuation section, LTM financials, macro context, news feed
3. Telegram delivery — implement thesis positioning change alert, daily morning brief (configurable time), wire opportunity top-3 into messages
4. PDF report generator — implement Jinja2 template + WeasyPrint pipeline, institutional format with all required sections, CVM IN 598 disclaimer, Streamlit download button

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Cleanup | 3/3 | Complete | 2026-05-10 |
| 2. Reliable Data Ingestion | 2/4 | Executing | — |
| 3. Financial Engine | 0/5 | Not started | — |
| 4. Intelligence Layer | 0/5 | Not started | — |
| 5. Delivery Layer | 0/4 | Not started | — |

---
*Roadmap created: 2026-05-06*
