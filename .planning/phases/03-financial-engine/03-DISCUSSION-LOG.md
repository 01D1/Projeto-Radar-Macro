# Phase 3: Financial Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-11
**Phase:** 3-financial-engine
**Areas discussed:** Output storage for Phase 4, LTM normalization strategy, Live WACC vs static config, Existing engine reuse scope

---

## Output Storage for Phase 4

### Q1 — Where should Financial Engine write outputs?

| Option | Description | Selected |
|--------|-------------|----------|
| New tables in ingestion.db | Add financial_ltm/multiples/dcf/signals tables. Single DB for all data. | ✓ |
| New financials.db | Separate file for clean phase boundary. Phase 4 needs two DBs. | |
| JSON files in data/output/ | Keep existing auto_dcf.py pattern. Inconsistent with ingestion.db approach. | |

**User's choice:** New tables in ingestion.db

### Q2 — Schema structure for financial tables?

| Option | Description | Selected |
|--------|-------------|----------|
| One table per output type | financial_ltm, financial_multiples, financial_dcf, financial_signals — directly queryable. | ✓ |
| One wide JSON blob per ticker | financial_results(ticker, computed_at, payload JSON). Simple write, complex read. | |
| You decide | Claude picks. | |

**User's choice:** One table per output type

### Q3 — When does the Financial Engine run?

| Option | Description | Selected |
|--------|-------------|----------|
| Scheduled job after ingestion | job_financial_engine() in scheduler.py. Satisfies FIN-01. | |
| On-demand function only | No scheduler wiring in Phase 3. | |
| Both: scheduled + on-demand API | job_financial_engine() + run_ticker() callable from Phase 4. | ✓ |

**User's choice:** Both: scheduled + on-demand API

### Q4 — Overwrite behavior on re-run?

| Option | Description | Selected |
|--------|-------------|----------|
| INSERT OR REPLACE keyed by (ticker, computed_date) | One row per ticker per day. Prior days preserved. | ✓ |
| Always INSERT, keep full history | Full history, table grows fast, Phase 4 always filters to latest. | |
| You decide | Claude picks. | |

**User's choice:** INSERT OR REPLACE keyed by (ticker, computed_date)

---

## LTM Normalization Strategy

### Q1 — How to populate normalized_name?

| Option | Description | Selected |
|--------|-------------|----------|
| Back-fill in DB via AccountMapper | One-time UPDATE on cvm_statements. Fast, no re-download. Queryable. | ✓ |
| Normalize on-read in LTM engine | Don't touch DB. Normalize in Python at query time. Every query pays normalization cost. | |
| Re-run CVM ingestion with normalization | Add AccountMapper to cvm_downloader.py, re-ingest. Slower to unblock Phase 3. | |

**User's choice:** Back-fill normalized_name in DB via AccountMapper

### Q2 — Should future ingestion also populate normalized_name?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — wire AccountMapper into cvm_downloader.py | Permanent fix. normalized_name always populated going forward. | ✓ |
| No — back-fill only, normalize on future reads | Two code paths for normalization. More maintenance surface. | |

**User's choice:** Yes — wire AccountMapper into cvm_downloader.py

### Q3 — DFP vs ITR reconciliation?

| Option | Description | Selected |
|--------|-------------|----------|
| ITR authoritative for LTM; DFP validates | LTM = 4 trailing ITR quarters. DFP cross-check at >5% divergence → flag. | ✓ |
| DFP preferred when available; ITR fills gaps | DFP as base year, ITR fills quarters. Simpler but DFP lags Q4 filing. | |
| You decide | Claude picks. | |

**User's choice:** ITR quarters authoritative for LTM; DFP validates

### Q4 — Bank (COSIF) normalization?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate ACCOUNT_MAP via bank_account_mapper.py | Separate mappers for COSIF and IFRS. SectorConfig.is_bank_model routes. | ✓ |
| Single shared mapper with bank overrides | Extend AccountMapper to handle both. Regex conflict risk. | |
| You decide | Claude picks. | |

**User's choice:** Separate ACCOUNT_MAP for COSIF — use bank_account_mapper.py

---

## Live WACC vs Static Config

### Q1 — How to pull live macro data into WACC?

| Option | Description | Selected |
|--------|-------------|----------|
| Live Selic + CDS, static everything else | risk_free = Selic from macro_series, CDS = country risk. Beta/ERP/tax stay in sectors.yaml. | ✓ |
| Fully dynamic WACC — all inputs from DB or config | All inputs from macro_series + new wacc_config table. More work, sectors.yaml redundant. | |
| Keep sectors.yaml static, add override function | Static WACC + get_live_wacc() swap. Planner decides wiring. | |

**User's choice:** Live Selic + CDS, static everything else

### Q2 — Stale macro fallback behavior?

| Option | Description | Selected |
|--------|-------------|----------|
| Fall back to sectors.yaml values + log WARNING | Stale = use static fallback. DCF still runs. Never silently breaks. | ✓ |
| Raise IngestionError — block DCF until macro is fresh | Hard blocker. BCB API outage = all DCF blocked. | |
| Use stale data, annotate the output | Run DCF with stale data, tag with macro_stale flag. | |

**User's choice:** Fall back to sectors.yaml values + log WARNING

### Q3 — WACC formula for Selic + CDS?

| Option | Description | Selected |
|--------|-------------|----------|
| risk_free = Selic + CDS Brazil spread | Risk-free = Selic + CDS. Standard Brazilian DCF approach. | |
| risk_free = Selic only; CDS = explicit country risk premium | Selic is base risk-free. CDS is added separately to Ke formula alongside ERP. | ✓ |
| You decide | Claude picks. | |

**User's choice:** risk_free = Selic only; CDS is separate country-risk premium
**Notes:** Ke = Selic + beta × ERP + CDS_Brazil. Theoretically cleaner — consistent with Damodaran country risk premium methodology.

---

## Existing Engine Reuse Scope

### Q1 — How to adapt existing valuation code?

| Option | Description | Selected |
|--------|-------------|----------|
| New financial_engine.py orchestrator + keep compute modules | New file handles DB I/O; valuation_dcf.py, calculate_metrics.py stay as pure-compute. auto_dcf.py becomes legacy. | ✓ |
| Refactor auto_dcf.py to accept ingestion.db data | Replace _load_latest_metrics() with DB queries. Riskier — changing working module's data layer. | |
| You decide | Claude picks safest path. | |

**User's choice:** New financial_engine.py orchestrator + keep pure-compute modules

### Q2 — Module location and public API?

| Option | Description | Selected |
|--------|-------------|----------|
| src/financial_engine.py with run_ticker() + run_all() | Top-level module. run_ticker() per ticker, run_all() for watchlist. scheduler.py calls run_all(). | ✓ |
| src/financial/ package with sub-modules | More granular. May be premature for Phase 3. | |
| You decide | Claude picks. | |

**User's choice:** src/financial_engine.py with run_ticker(ticker) + run_all()

### Q3 — Technical signals implementation?

| Option | Description | Selected |
|--------|-------------|----------|
| pandas-based on price_ohlcv adj_close | Query DB, compute RSI/MACD/MA in pandas. No new dependencies. | ✓ |
| Use ta-lib or pandas-ta library | Built-in signal functions. ta-lib requires C compilation (Windows issue). | |
| You decide | Claude picks. | |

**User's choice:** pandas-based on price_ohlcv data from ingestion.db

---

## Claude's Discretion

None — user engaged with all decisions.

## Deferred Ideas

- **Multi-scenario DCF storage** (base/bull/bear) — auto_dcf.py supports 3 scenarios; Phase 3 stores base only; v2 requirement.
- **Peer/sector relative valuation** — multiples comparison across sector — v2.
- **Shares outstanding data source** — researcher should confirm whether to pull from yfinance metadata or CVM BP filings.
- **SQLAlchemy ORM layer** — v2.
