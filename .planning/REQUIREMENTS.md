# Requirements — Investment Intelligence Platform
*v1 scope defined 2026-05-06*

---

## v1 Requirements

### FOUND — Foundation & Cleanup

- [x] **FOUND-01**: Duplicate codebases archived — single canonical source under `Analista de Investimentos/12_PYTHON/src/`; `_ARQUIVO_Analista_vs_code/` and `Meu segundo Cerébro/12_PYTHON/` removed from active use *(completed: 01-01, 2026-05-10)*
- [ ] **FOUND-02**: All credentials and paths migrated from source code to `.env` file; `python-dotenv` + `pydantic-settings` loads config on startup; `.env` added to `.gitignore`
- [ ] **FOUND-03**: Retry logic applied to all external API calls (CVM, BCB, yfinance, Anthropic, Telegram) using `tenacity` with exponential backoff; no uncaught API failures crash the pipeline
- [ ] **FOUND-04**: Structured logging via `structlog` across all modules; each log entry includes module name, ticker (when relevant), and ingestion run ID; logs persisted to `logs/` with daily rotation

### ING — Data Ingestion

- [ ] **ING-01**: CVM DFP (annual financial statements) downloaded, parsed from XML, and stored with account code normalization; raw XML preserved for reprocessing
- [ ] **ING-02**: CVM ITR (quarterly financial statements) downloaded, parsed, and stored; reconciled with DFP for overlapping periods
- [ ] **ING-03**: CVM IPE (corporate events) ingested and classified by event type (earnings release, fato relevante, dividend, guidance); PDF text extracted from event attachments
- [ ] **ING-04**: BCB macro series (Selic, IPCA, PTAX, CDS Brazil, PIB) ingested via BCB SGS API with freshness timestamps; data freshness displayed in UI
- [ ] **ING-05**: B3 price series (OHLCV + adjusted close) ingested via yfinance for watchlist tickers; corporate actions adjusted; gaps flagged rather than interpolated
- [ ] **ING-06**: News RSS feeds (17+ sources) ingested on schedule; articles deduplicated by URL; each item tagged with relevant ticker from watchlist when detectable
- [ ] **ING-07**: Ingestion scheduler runs daily (configurable time via `.env`); each run logged with duration, records updated, and any failures

### FIN — Financial Engine

- [ ] **FIN-01**: LTM (Last Twelve Months) financial aggregation computed for all watchlist tickers: revenue, EBITDA, net income, FCF, net debt — rolling sum of trailing 4 ITR quarters, reconciled against latest DFP
- [ ] **FIN-02**: Standard valuation multiples computed for each ticker: P/E, EV/EBITDA, P/BV, dividend yield, EV/Revenue; updated daily with latest price + latest LTM financials
- [ ] **FIN-03**: DCF fair value model per ticker: WACC derived from Selic + CDS Brazil + equity risk premium; FCF projections over 5 years; terminal value with configurable terminal growth rate; output includes fair value in BRL and upside/downside % vs current price
- [ ] **FIN-04**: DCF model validates inputs before running (terminal growth < WACC; WACC > 5%); fair value outside 0.1x–5.0x current price flagged as "FORA DO INTERVALO CONFIÁVEL" rather than displayed
- [ ] **FIN-05**: Bank/financial sector tickers routed to alternative financial model (NIM-based instead of EBITDA-based; ROE instead of ROIC; dividend discount model instead of FCF DCF)
- [ ] **FIN-06**: Technical signals computed per ticker: RSI-14, MACD (12/26/9), 50-day and 200-day moving averages, MA crossover signal; composite momentum score (0–100)

### INT — Intelligence Layer

- [ ] **INT-01**: AI investment thesis generated per ticker using Claude API (`claude-sonnet-4-6`) via `instructor` with enforced Pydantic schema: bull case, bear case, key drivers (3–5), risks (3–5), fair value BRL, methodology disclosure, positioning (COMPRAR/MANTER/VENDER), confidence (ALTA/MEDIA/BAIXA), rationale; output in Portuguese
- [ ] **INT-02**: All numbers in AI thesis injected from Financial Engine outputs — LLM performs synthesis only, never calculation; post-generation validation cross-checks thesis fair value against computed DCF (tolerance ±10%)
- [ ] **INT-03**: Input hash computed per thesis (DCF result + top multiples + macro snapshot + top 3 news headlines + signals); thesis regenerated only when input hash changes; max 2 regenerations per ticker per day
- [ ] **INT-04**: Thesis stored in database with version history; each version records input hash, generation timestamp, and what changed from prior version
- [ ] **INT-05**: Opportunity signals computed per ticker: price vs DCF fair value divergence (flag if >20% mispriced), momentum shift detection (MA crossover + fundamental backing), event-driven signal (IPE event + thesis impact)
- [ ] **INT-06**: Opportunity signals ranked across watchlist by conviction score; top 3 opportunities available as structured output for Telegram and dashboard

### DEL — Delivery Layer

- [ ] **DEL-01**: Streamlit multi-page dashboard with pages: Watchlist overview (all tickers: price, multiples, signals, thesis positioning), Asset detail (per ticker: valuation, financials, macro context, news, full thesis), Macro panel (Selic, IPCA, PTAX, CDS, PIB charts), Opportunities (ranked signals)
- [ ] **DEL-02**: Streamlit dashboard uses `st.cache_data` with TTL for all data loading; data displayed with freshness timestamp; page renders in <5 seconds for watchlist of up to 50 tickers
- [ ] **DEL-03**: Telegram bot sends thesis summary alert when thesis positioning changes (e.g., MANTER → COMPRAR); message includes ticker, new positioning, confidence, 1-sentence rationale, and top opportunity
- [ ] **DEL-04**: Telegram bot sends daily morning brief (configurable time): macro snapshot (Selic, IBOV % change, PTAX), top 3 movers in watchlist, top opportunity of the day
- [ ] **DEL-05**: PDF report generated per ticker on demand: institutional format with sections — thesis summary, valuation (DCF + multiples), financial highlights (LTM), macro context, risks, and CVM IN 598 disclaimer; generated in <30 seconds; downloadable from Streamlit dashboard

---

## v2 Requirements (Deferred)

These are valuable but not blocking v1. Schedule for next milestone.

- **Peer/sector comparison** — multi-ticker multiples table, sector relative valuation heatmap
- **Earnings transcript parsing** — PDF parsing of CVM earnings call documents with AI summary
- **Scenario analysis** — base/bull/bear DCF scenarios with probability weighting
- **Supabase cloud migration** — lift-and-shift SQLite schema to PostgreSQL/Supabase
- **Event-driven thesis refresh** — automatic thesis regeneration triggered by CVM IPE events
- **FOCUS forecast integration** — BCB weekly consensus forecasts for macro scenarios
- **Sector rotation signals** — macro-to-sector transmission model
- **SQLAlchemy ORM layer** — full ORM migration for Supabase readiness
- **Pre-commit secret scanning** — `detect-secrets` hook to prevent credential commits

---

## Out of Scope

- **Order execution / trading** — regulatory (CVM CTVM/DTVM licensing) and product boundary
- **Multi-user authentication** — single-analyst tool in v1; schema designed to be multi-tenant-ready
- **Real-time streaming prices** — B3 DMA licensing required; polling cadence sufficient for investment analysis
- **Bloomberg / Refinitiv API** — $20K+/year cost; public data sources cover 95% of needs
- **Options / derivatives analytics** — separate domain, separate pricing models
- **ESG scoring engine** — no authoritative Brazilian ESG data source; ISE B3 membership used as proxy
- **Backtesting engine** — 2-4 month standalone project; out of scope until core thesis is validated
- **Fixed income analytics** — ANBIMA data, different valuation models; separate product expansion
- **Social sentiment / Twitter scraping** — noisy, legally ambiguous, not trusted by institutional clients
- **Mobile native app** — Streamlit responsive enough for tablet; Telegram covers mobile alerting

---

## Traceability

*Populated by roadmapper — maps each REQ-ID to the phase that implements it.*

| REQ-ID | Phase | Status |
|--------|-------|--------|
| FOUND-01 | Phase 1 | Pending |
| FOUND-02 | Phase 1 | Pending |
| FOUND-03 | Phase 1 | Pending |
| FOUND-04 | Phase 1 | Pending |
| ING-01 | Phase 2 | Pending |
| ING-02 | Phase 2 | Pending |
| ING-03 | Phase 2 | Pending |
| ING-04 | Phase 2 | Pending |
| ING-05 | Phase 2 | Pending |
| ING-06 | Phase 2 | Pending |
| ING-07 | Phase 2 | Pending |
| FIN-01 | Phase 3 | Pending |
| FIN-02 | Phase 3 | Pending |
| FIN-03 | Phase 3 | Pending |
| FIN-04 | Phase 3 | Pending |
| FIN-05 | Phase 3 | Pending |
| FIN-06 | Phase 3 | Pending |
| INT-01 | Phase 4 | Pending |
| INT-02 | Phase 4 | Pending |
| INT-03 | Phase 4 | Pending |
| INT-04 | Phase 4 | Pending |
| INT-05 | Phase 4 | Pending |
| INT-06 | Phase 4 | Pending |
| DEL-01 | Phase 5 | Pending |
| DEL-02 | Phase 5 | Pending |
| DEL-03 | Phase 5 | Pending |
| DEL-04 | Phase 5 | Pending |
| DEL-05 | Phase 5 | Pending |

---
*Requirements defined: 2026-05-06*
*Traceability populated: 2026-05-06*
