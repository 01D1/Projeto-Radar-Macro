# Phase 3: Financial Engine - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a new `src/financial_engine.py` orchestrator that reads from `ingestion.db` (Phase 2 output), computes LTM financials, standard multiples, DCF fair value (with bank/industrial bifurcation), and technical momentum signals per watchlist ticker — then writes structured results to new `financial_*` tables in `ingestion.db` for Phase 4's AI layer to consume.

Also includes a one-time back-fill of `normalized_name` in `cvm_statements` and a permanent wire of `AccountMapper` into `cvm_downloader.py` to ensure future CVM ingestion always populates normalized names.

</domain>

<decisions>
## Implementation Decisions

### Output Storage (financial_* tables in ingestion.db)
- **D-01:** Financial Engine writes to **new tables in `ingestion.db`** — `financial_ltm`, `financial_multiples`, `financial_dcf`, `financial_signals`. Single DB for all data; Phase 4 has one connection string. Consistent with Phase 2's canonical data store decision.
- **D-02:** **One table per output type** — structured like `macro_series` and `price_ohlcv` (not JSON blobs). Fields are directly queryable by Phase 4 without Python-side JSON parsing.
- **D-03:** **Both scheduled + on-demand API.** `job_financial_engine()` added to `scheduler.py` (triggered daily after ingestion jobs). `run_ticker(ticker)` callable on-demand from Phase 4. Satisfies FIN-01 "runs automatically after each ingestion cycle" and Phase 4 single-ticker regeneration.
- **D-04:** **INSERT OR REPLACE keyed by `(ticker, computed_date)`.** One row per ticker per day. Re-running overwrites today's row, prior days preserved. Phase 4 queries `MAX(computed_date)` for latest results.

### LTM Normalization
- **D-05:** **Back-fill `normalized_name` in `cvm_statements` via `AccountMapper`.** Run a one-time UPDATE at Phase 3 startup using `AccountMapper.map()` on existing `account_code` + `account_name`. Fast (pure SQL + Python, no re-download). Normalized names become directly queryable.
- **D-06:** **Wire `AccountMapper` into `cvm_downloader.py` `parse_and_store()`** permanently — future ingestion always populates `normalized_name` at write time. This closes the deferred gap from Phase 2 (normalized_name=None decision).
- **D-07:** **ITR quarters are authoritative for LTM; DFP validates.** LTM = rolling sum of trailing 4 ITR quarters. DFP annual is used as a cross-check: if LTM revenue diverges from DFP annual by >5%, flag the ticker with a `ltm_reconciliation_warning` in `financial_ltm`. Matches Phase 2 ITR deduplication pattern and FIN-01 success criteria.
- **D-08:** **Separate mappers by accounting standard.** `AccountMapper` (`account_mapper.py`) for industrial tickers (IFRS CVM codes). `bank_account_mapper.py` for bank tickers (COSIF). `SectorConfig.is_bank_model` routes to the correct mapper. Do NOT merge into a single mapper — COSIF and IFRS account codes conflict.

### Live WACC from macro_series
- **D-09:** **`risk_free` = Selic from `macro_series`; CDS Brazil = explicit country risk premium** (separate from ERP). WACC formula: `Ke = Selic + beta × ERP + CDS_Brazil_spread`; `WACC = Ke × equity_weight + Kd × (1-t) × debt_weight`. Beta, ERP, tax_rate, debt_to_capital remain in `sectors.yaml` (model assumptions). Selic and CDS Brazil are the only macro-sourced live inputs.
- **D-10:** **Stale macro fallback to `sectors.yaml` static values + log WARNING.** If Selic or CDS Brazil is not fresh (>1 B3 business day old per Phase 2's freshness rule), fall back to the static `risk_free` / `country_risk` values in `sectors.yaml`. Log WARNING with ticker and which series was stale. DCF still runs — no hard blocker on macro staleness.

### Financial Engine Architecture
- **D-11:** **New `src/financial_engine.py` orchestrator; existing compute modules stay as pure-compute helpers.** `financial_engine.py` handles all DB I/O (reads from `ingestion.db`, writes to `financial_*` tables). It calls `valuation_dcf.py`, `calculate_metrics.py`, and `sector_config.py` as pure-compute modules — no changes to those files. `auto_dcf.py` is legacy (kept but no longer in the hot path).
- **D-12:** **Public API: `run_ticker(ticker: str) -> FinancialResult` + `run_all() -> list[FinancialResult]`.** `scheduler.py` calls `run_all()` via `job_financial_engine()`. Phase 4 calls `run_ticker()` on demand. `bind_run_id("financial")` at the top of `job_financial_engine()` per Phase 1/2 patterns.
- **D-13:** **Technical signals computed in pandas from `price_ohlcv.adj_close`.** Query `price_ohlcv` for the ticker's adjusted close series. Compute RSI-14, MACD (12/26/9 standard), 50-day MA, 200-day MA, crossover signal, and composite momentum score (0–100) in pandas. No new library dependencies (`ta-lib` rejected — C compilation issues on Windows).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §FIN-01 through FIN-06 — acceptance criteria for this phase (LTM, multiples, DCF, validation, bank model, technical signals)
- `.planning/ROADMAP.md` §Phase 3 — goal, 5 planned deliverables, success criteria
- `.planning/PROJECT.md` — constraints (Python-only, reuse existing logic, SQLite→Supabase-compatible schema, no overengineering)

### Prior Phase Decisions
- `.planning/phases/01-foundation-and-cleanup/01-CONTEXT.md` — retry infrastructure, logging patterns, `bind_run_id`
- `.planning/phases/02-reliable-data-ingestion/02-CONTEXT.md` — D-04 (ingestion.db tables), D-06 (schema design for portability), D-12 (freshness threshold: >1 B3 business day), D-13 (retry decorator pattern), D-14 (bind_run_id job pattern)

### Existing Computation Modules to Reuse (pure-compute, no changes needed)
- `Analista de Investimentos/12_PYTHON/src/valuation/valuation_dcf.py` — `DCFAssumptions`, `run_dcf()`, `run_ddm()`, `DCFResult`, `DDMResult`
- `Analista de Investimentos/12_PYTHON/src/valuation/calculate_metrics.py` — `calculate_industrial_metrics()`, `calculate_bank_metrics()`, `IndustrialMetrics`, `BankMetricsCalc`
- `Analista de Investimentos/12_PYTHON/src/valuation/sector_config.py` — `SectorConfig.for_ticker()`, `is_bank_model`, `valuation_method`, `build_dcf_scenarios()`, `build_gordon_scenarios()`
- `Analista de Investimentos/12_PYTHON/src/valuation/auto_dcf.py` — **Legacy** (not in hot path). Reference only for existing scenario/result data structures.

### Normalization Modules to Wire
- `Analista de Investimentos/12_PYTHON/src/normalization/account_mapper.py` — `AccountMapper.map_df()`, `AccountMapper.to_dict()` — for industrial IFRS accounts
- `Analista de Investimentos/12_PYTHON/src/normalization/bank_account_mapper.py` — COSIF account normalization for bank tickers
- `Analista de Investimentos/12_PYTHON/src/parsers/dfp_parser.py` — `ACCOUNT_MAP` (CVM code → normalized field name, imported by AccountMapper)

### Database Schema
- `Analista de Investimentos/12_PYTHON/src/ingestion/db.py` — `init_db()`, `get_connection()`, `DB_PATH` — extend with `financial_*` table DDL
- `Analista de Investimentos/12_PYTHON/data/ingestion.db` — live database; existing tables: `cvm_statements`, `macro_series`, `price_ohlcv`, `news_articles`

### Existing Ingestion Code to Touch (Phase 3 modifies these)
- `Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py` — add `AccountMapper` call in `parse_and_store()` to populate `normalized_name`
- `Analista de Investimentos/12_PYTHON/src/scheduler.py` — add `job_financial_engine()` and register in `_JOB_REGISTRY`

### Configuration
- `Analista de Investimentos/12_PYTHON/config/tickers.yaml` — watchlist tickers + sector type (input for `SectorConfig.for_ticker()`)
- `Analista de Investimentos/12_PYTHON/config/sectors.yaml` — static WACC assumptions (beta, ERP, tax_rate, debt_to_capital, terminal_growth, static risk_free fallback)
- `Analista de Investimentos/12_PYTHON/config/schedules.yaml` — add `financial_engine` cron entry

### Utilities
- `Analista de Investimentos/12_PYTHON/src/utils/retry.py` — `@retry` decorator for any external data access
- `Analista de Investimentos/12_PYTHON/src/utils/logger.py` — `bind_run_id("financial")`, `get_logger()`
- `Analista de Investimentos/12_PYTHON/src/utils/errors.py` — `IngestionError`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `valuation_dcf.py` — `run_dcf()` takes `base_revenue`, `base_ebitda`, `DCFAssumptions` and returns full `DCFResult` with EV, equity value, price target. Computation-pure, no I/O.
- `valuation_dcf.py` — `run_ddm()` for bank DDM model (uses net income + payout ratio + COE).
- `calculate_metrics.py` — `calculate_industrial_metrics()` and `calculate_bank_metrics()` return dataclasses with all ratios pre-computed.
- `sector_config.py` — `SectorConfig.for_ticker(ticker)` reads `tickers.yaml` → `sectors.yaml` and returns sector assumptions, `is_bank_model`, `valuation_method`. Already has Gordon Growth / DDM / DCF / EV-EBITDA dispatch logic.
- `account_mapper.py` — `AccountMapper.to_dict(df)` returns `{normalized_field: value}` dict ready to feed into `calculate_industrial_metrics()` kwargs.

### Established Patterns
- Job functions: `job_<name>()` in `scheduler.py` with `bind_run_id("financial")` at top, summary log at end (D-15 pattern from Phase 2)
- DB schema: `TEXT PRIMARY KEY` UUIDs, ISO date strings, no AUTOINCREMENT, `INSERT OR REPLACE`/`INSERT OR IGNORE` for deduplication
- Freshness check: query `MAX(date)` from `macro_series` for `series_code IN (11, 29039)`, compare to `B3BusinessCalendar.today()` minus 1 day
- Logging: `f"[{ticker}] message"` format with structlog via `get_logger(__name__)`

### Integration Points
- `src/financial_engine.py` reads from: `cvm_statements` (LTM), `macro_series` (WACC), `price_ohlcv` (signals + multiples price), `news_articles` (none in Phase 3 — Phase 4)
- `src/financial_engine.py` writes to: `financial_ltm`, `financial_multiples`, `financial_dcf`, `financial_signals` (new tables added via `db.py` `_CREATE_SQL`)
- `cvm_downloader.py` `parse_and_store()`: add `AccountMapper` call before `conn.execute(INSERT)` to populate `normalized_name` column
- `scheduler.py`: add `job_financial_engine()` to `_JOB_REGISTRY`, add cron entry to `schedules.yaml`

</code_context>

<specifics>
## Specific Ideas

- **WACC computation function**: `compute_wacc(ticker, macro_conn) -> float` — queries `macro_series` for latest Selic (series_code=11) and CDS Brazil (series_code=29039). If stale: returns `sectors.yaml` static value + logs WARNING. Formula: `Ke = selic + beta × erp + cds_brazil`; `WACC = Ke × (1-D/V) + kd × (1-t) × (D/V)`.
- **financial_ltm schema**: `(id TEXT PK, ticker TEXT, computed_date TEXT, net_revenue REAL, ebitda REAL, net_income REAL, fcf REAL, net_debt REAL, shares_outstanding REAL, ltm_reconciliation_warning INTEGER DEFAULT 0, ingested_at TEXT)` — UNIQUE INDEX on `(ticker, computed_date)`.
- **financial_dcf schema**: `(id TEXT PK, ticker TEXT, computed_date TEXT, fair_value_brl REAL, upside_pct REAL, wacc REAL, terminal_growth REAL, confidence_flag TEXT, selic_used REAL, cds_used REAL, ingested_at TEXT)` — `confidence_flag` = "FORA DO INTERVALO CONFIAVEL" when fair_value outside 0.1x–5.0x current price.
- **Input validation guards** (FIN-04): validate BEFORE calling `run_dcf()`: `assert terminal_growth < wacc`, `assert wacc > 0.05`. On violation: log ERROR for ticker, skip DCF for that ticker, write NULL fair_value with `confidence_flag = "INPUT_INVALIDO"`.
- **Composite momentum score**: weighted sum of signals — RSI direction (above/below 50 = 30pts), MACD crossover (30pts), MA200 trend (price > MA200 = 20pts), MA50/200 golden/death cross (20pts). Score 0–100.
- **Bank LTM**: use `bank_account_mapper.py` to normalize COSIF accounts, then feed to `calculate_bank_metrics()`. LTM for banks = trailing 4 ITR quarters for NII, fee income, loan loss provisions, net income. No EBITDA for banks.

</specifics>

<deferred>
## Deferred Ideas

- **Scenario analysis (base/bull/bear DCF)** — `auto_dcf.py` already supports 3 scenarios via `build_dcf_scenarios()`. Phase 3 stores base scenario only in `financial_dcf`. Multi-scenario storage is a v2 requirement (REQUIREMENTS.md §v2).
- **Peer/sector relative valuation** — multiples comparison across tickers in same sector. v2 requirement.
- **Shares outstanding from CVM** — Phase 3 may need shares outstanding for price-target computation. This could come from B3/yfinance metadata or CVM BP. Researcher should verify the source during Phase 3 research.
- **SQLAlchemy ORM layer** — v2 requirement. Phase 3 uses raw sqlite3 (consistent with Phase 2).
- **FOCUS macro forecast integration** — BCB weekly consensus for macro scenarios. v2 requirement.

</deferred>

---

*Phase: 3-Financial Engine*
*Context gathered: 2026-05-11*
