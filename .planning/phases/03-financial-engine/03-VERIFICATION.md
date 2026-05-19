---
phase: 03-financial-engine
verified: 2026-05-11T16:10:00Z
status: passed
score: 18/18 must-haves verified
overrides_applied: 0
---

# Phase 3: Financial Engine Verification Report

**Phase Goal:** For every watchlist ticker, the platform computes LTM financials, standard valuation multiples, a DCF fair value (with bank/industrial bifurcation), and technical momentum signals — establishing the quantitative foundation the AI layer requires.
**Verified:** 2026-05-11T16:10:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | init_db() creates all four financial_* tables with UNIQUE indexes | VERIFIED | db.py lines 86-158: all four CREATE TABLE IF NOT EXISTS statements + UNIQUE INDEXes confirmed |
| 2 | SectorConfig.for_ticker() succeeds on Windows without UnicodeDecodeError | VERIFIED | sector_config.py lines 38, 45: both open() calls have encoding="utf-8"; `python -c` spot-check returned False with no error |
| 3 | AccountMapper imports without error from financial_engine.py context | VERIFIED | account_mapper.py line 32: `from src.parsers.dfp_parser import`; `python -c "from src.normalization.account_mapper import AccountMapper; print('OK')"` returned OK |
| 4 | _aggregate_ltm() sums 4 trailing ITR quarters; sets ltm_reconciliation_warning=1 when LTM-DFP revenue diverges > 5% | VERIFIED | financial_engine.py lines 103-206: full implementation with FLOW_ITEMS summation, SNAPSHOT_ITEMS latest-wins logic, divergence check; test_ltm_dfp_reconciliation_warning passes |
| 5 | parse_and_store() in cvm_downloader.py calls AccountMapper and populates normalized_name at write time | VERIFIED | cvm_downloader.py line 40 (import) + lines 235, 269 (mapper instantiated + _map_row called); test_account_mapper_wired_in_downloader passes |
| 6 | run_ticker() writes one financial_ltm row per ticker keyed by (ticker, computed_date) | VERIFIED | financial_engine.py lines 333-363: INSERT OR REPLACE with computed_date = date.today().isoformat() |
| 7 | Current price fetched from price_ohlcv MAX(date) WHERE is_gap=0 — never from a gapped row | VERIFIED | financial_engine.py lines 434-446: _get_current_price() SELECT with is_gap=0 AND adj_close IS NOT NULL ORDER BY date DESC LIMIT 1 |
| 8 | P/E, EV/EBITDA, P/BV, dividend_yield, EV/Revenue computed and written to financial_multiples for industrial tickers | VERIFIED | financial_engine.py lines 454-563: _compute_multiples() routes to calculate_industrial_metrics(); ev_revenue computed inline; test_industrial_multiples_computed passes |
| 9 | Missing price produces a flagged record (price=NULL) — never triggers zero-division | VERIFIED | financial_engine.py lines 469-471: None price passed to metric functions which handle it; test_multiples_handles_missing_price passes |
| 10 | Bank tickers receive bank-specific multiples (P/BV, P/E, NIM, efficiency_ratio) via calculate_bank_metrics(); EV/EBITDA is NULL for banks | VERIFIED | financial_engine.py lines 475-498: ev_ebitda_val = None explicitly; test_bank_multiples_ev_ebitda_null passes |
| 11 | WACC derived from live Selic (series_code=11) + CDS Brazil (series_code=29039) from macro_series; stale or missing macro falls back to sectors.yaml static values with a WARNING log | VERIFIED | financial_engine.py lines 729-794: compute_wacc() queries macro_series IN (11, 29039), calls _is_stale_date(), falls back with log.warning; spot-check confirmed WACC=0.1497 from live data, fallback=False |
| 12 | DCF input validation fires BEFORE run_dcf(): terminal_growth >= WACC or WACC <= 0.05 writes NULL fair_value with confidence_flag='INPUT_INVALIDO' | VERIFIED | financial_engine.py lines 802-835: _validate_dcf_inputs() returns INPUT_INVALIDO on these conditions; lines 895-902: pre_flag check blocks run_dcf() call; spot-check confirmed correct behavior |
| 13 | run_dcf() is never called when inputs are invalid | VERIFIED | financial_engine.py lines 895-902: early return with _write_dcf_row when INPUT_INVALIDO; test_dcf_invalid_input_writes_null_fair_value passes |
| 14 | fair_value outside [0.1x, 5.0x] current price gets confidence_flag='FORA DO INTERVALO CONFIAVEL' | VERIFIED | financial_engine.py lines 828-834: range check in _validate_dcf_inputs; test_dcf_confidence_flag_out_of_range passes |
| 15 | Bank tickers (COSIF) are routed via SectorConfig.is_bank_model=True — never receive EBITDA-based DCF | VERIFIED | financial_engine.py lines 370-374: if cfg.is_bank_model -> _compute_bank_model(); else -> _compute_dcf_industrial(); test_bank_routing_guard_prevents_dcf passes |
| 16 | run_ddm() is called for bank fair value; result written to financial_dcf with valuation_method='ddm' | VERIFIED | financial_engine.py lines 658-668: run_ddm() called with cost_of_equity, terminal_growth_rate, income_growth_rates; _write_dcf_row with "ddm"; test_bank_routing_uses_ddm passes |
| 17 | RSI-14 (Wilder's EWM com=13), MACD (12/26/9), MA50/200, golden/death cross, composite momentum score (multiple of 10) computed per ticker | VERIFIED | financial_engine.py lines 981-1064: compute_signals() with ewm(com=13) x2, ewm(span=12/26/9) x3, rolling means; spot-check returned RSI=49.38, momentum=30 (30 % 10 == 0 confirmed) |
| 18 | job_financial_engine() registered in _JOB_REGISTRY under 'financial_engine'; schedules.yaml has cron '0 20 * * 1-5'; D-15 summary log emitted | VERIFIED | scheduler.py line 468: "financial_engine": job_financial_engine; schedules.yaml line 47: cron "0 20 * * 1-5"; scheduler.py line 442: source="financial_engine" in D-15 log; test_job_registered and test_job_summary_log pass |

**Score:** 18/18 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/financial_engine.py` | Orchestrator with run_ticker(), run_all(), _aggregate_ltm(), backfill_normalized_names(), compute_wacc(), _compute_multiples(), _compute_dcf_industrial(), _compute_bank_model(), compute_signals() | VERIFIED | 1146-line file; all functions present and substantive |
| `src/ingestion/db.py` | financial_* table DDL in _CREATE_SQL | VERIFIED | Lines 86-158: all 4 tables + UNIQUE indexes |
| `src/valuation/sector_config.py` | encoding="utf-8" in both open() calls | VERIFIED | Lines 38, 45 confirmed |
| `src/normalization/account_mapper.py` | from src.parsers.dfp_parser import | VERIFIED | Line 32 confirmed |
| `src/ingestion/cvm_downloader.py` | AccountMapper import + _map_row usage | VERIFIED | Lines 40, 235, 269 confirmed |
| `src/scheduler.py` | job_financial_engine() + _JOB_REGISTRY entry | VERIFIED | Lines 424, 468 confirmed |
| `config/schedules.yaml` | financial_engine cron entry | VERIFIED | Line 46-47 confirmed |
| `tests/test_financial_db_schema.py` | 3 schema tests | VERIFIED | 3 tests pass |
| `tests/test_financial_engine.py` | 20 tests (FIN-01 through FIN-05 + D-12) | VERIFIED | All 20 tests present and passing |
| `tests/test_financial_signals.py` | 5 FIN-06 signal tests | VERIFIED | All 5 tests present and passing |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| financial_engine.py _aggregate_ltm() | cvm_statements table | parameterized SELECT with (ticker, *ref_dates) | WIRED | Lines 119-128 (date query) + 142-152 (accounts query); both parameterized |
| cvm_downloader.py parse_and_store() | AccountMapper._map_row() | _mapper instantiated, called per row | WIRED | Lines 235 (instantiate) + 269 (call); test passes |
| db.py _CREATE_SQL | financial_ltm table | init_db() executescript | WIRED | Line 86: CREATE TABLE IF NOT EXISTS financial_ltm |
| financial_engine.py _compute_multiples() | price_ohlcv table | _get_current_price() SELECT WHERE is_gap=0 | WIRED | Line 434: SELECT with is_gap=0 AND adj_close IS NOT NULL |
| financial_engine.py _compute_multiples() | calculate_industrial_metrics() / calculate_bank_metrics() | cfg.is_bank_model routing | WIRED | Lines 475-524: is_bank_model gate |
| run_ticker() | financial_multiples table | INSERT OR REPLACE via _compute_multiples() | WIRED | Line 366: _compute_multiples() called; lines 538-558: INSERT OR REPLACE |
| compute_wacc() | macro_series table | SELECT series_code IN (11, 29039) | WIRED | Lines 748-754: parameterized query |
| _compute_dcf_industrial() | valuation_dcf.run_dcf() | only after _validate_dcf_inputs() returns None | WIRED | Lines 895-902: pre-flight block; lines 933-941: run_dcf() call |
| run_ticker() | financial_dcf table | _write_dcf_row() INSERT OR REPLACE | WIRED | Lines 589-613: parameterized INSERT OR REPLACE |
| run_ticker() | _compute_bank_model() | if cfg.is_bank_model branch | WIRED | Lines 370-374: routing guard |
| _compute_bank_model() | valuation_dcf.run_ddm() | direct call with bank LTM fields | WIRED | Lines 658-668: run_ddm() call |
| compute_signals() | price_ohlcv table | SELECT WHERE is_gap=0 ORDER BY date ASC | WIRED | Lines 1090-1098 in _compute_and_write_signals() |
| run_ticker() | financial_signals table | _compute_and_write_signals() INSERT OR REPLACE | WIRED | Line 377: _compute_and_write_signals() called; lines 1118-1141: INSERT |
| scheduler.py _JOB_REGISTRY | job_financial_engine() | dict key 'financial_engine' | WIRED | Line 468: "financial_engine": job_financial_engine |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| SectorConfig.for_ticker('PETR4') no UnicodeDecodeError | python -c "from src.valuation.sector_config import SectorConfig; cfg = SectorConfig.for_ticker('PETR4'); print(cfg.is_bank_model)" | False | PASS |
| AccountMapper imports cleanly | python -c "from src.normalization.account_mapper import AccountMapper; print('OK')" | OK | PASS |
| compute_signals() RSI in [0,100] and momentum_score % 10 == 0 | python -c using make_price_series(250) | RSI=49.38 momentum=30 | PASS |
| _validate_dcf_inputs() blocks terminal_growth >= WACC, WACC <= 5%, and out-of-range fair value | python -c with 3 assertions | All 3 assertions pass | PASS |
| compute_wacc() from live macro_series returns fallback=False and 0.05 < WACC < 0.50 | python -c with in-memory DB + today's macro rows | WACC=0.1497, fallback=False | PASS |
| job_financial_engine() registered in _JOB_REGISTRY | python -c "from src.scheduler import _JOB_REGISTRY; print('financial_engine' in _JOB_REGISTRY)" | True | PASS |
| schedules.yaml has financial_engine cron '0 20 * * 1-5' | yaml.safe_load verification | ['0 20 * * 1-5'] confirmed | PASS |
| Full test suite — 93 tests | python -m pytest tests/ -q | 93 passed in 7.27s | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FIN-01 | 03-01 | LTM aggregation (revenue, EBITDA, net income, FCF, net debt) from 4 ITR quarters, DFP reconciled | SATISFIED | _aggregate_ltm() + _check_dfp_reconciliation() fully implemented; 6 tests pass |
| FIN-02 | 03-02 | P/E, EV/EBITDA, P/BV, dividend yield, EV/Revenue computed daily | SATISFIED | _compute_multiples() with bank/industrial routing; 3 tests pass |
| FIN-03 | 03-03 | DCF fair value: WACC from Selic+CDS, 5-year FCF projections, terminal value | SATISFIED | compute_wacc() + _compute_dcf_industrial() implemented; 5 tests pass |
| FIN-04 | 03-03 | DCF input validation (terminal_growth < WACC; WACC > 5%; fair value range guard) | SATISFIED | _validate_dcf_inputs() blocks run_dcf(); tested with 3 test functions |
| FIN-05 | 03-04 | Bank tickers route to NIM-based model + DDM instead of EBITDA DCF | SATISFIED | _compute_bank_model() with run_ddm(); is_bank_model gate in run_ticker(); 4 tests pass |
| FIN-06 | 03-05 | RSI-14, MACD (12/26/9), MA50/200, crossover signal, composite momentum score (0-100) | SATISFIED | compute_signals() with Wilder's EWM; 5 tests pass; spot-check confirmed |

**Note on REQUIREMENTS.md status:** The requirements file marks FIN-01 as unchecked `[ ]` in the description section (line 28) but marks it Complete (03-01) in the Traceability table (line 101). The traceability table reflects the correct state — FIN-01 is fully implemented.

---

### Anti-Patterns Found

No blockers or warnings found. The following observations are informational:

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| src/ingestion/bcb.py (pre-existing) | BMFBOVESPA not in pandas_market_calendars registry — is_stale() falls back to assuming not-stale | INFO | Pre-Phase-3 issue; bcb.py handles it gracefully with a warning log. compute_wacc() staleness check still works (assumes not-stale = conservative). Not a Phase 3 regression. |

No `NotImplementedError` stubs remain in financial_engine.py. All planned stub functions from Plans 01-04 were replaced with real implementations in their respective plans.

---

### Human Verification Required

None. All must-haves are programmatically verifiable and have been verified.

---

### Summary

Phase 3 goal is fully achieved. All six requirements (FIN-01 through FIN-06) are implemented, tested, and wired into the scheduler:

- **FIN-01**: LTM aggregation with FLOW/SNAPSHOT bifurcation, DFP reconciliation warning, and AccountMapper wire-up is live in `src/financial_engine.py`.
- **FIN-02**: Multiples computation routing industrial vs bank metrics, with is_gap=0 price guard, writes daily to financial_multiples.
- **FIN-03**: WACC derived from live macro_series Selic+CDS with sectors.yaml fallback; both dcf_fcff and ev_ebitda_multiple paths implemented.
- **FIN-04**: Input validation gate (_validate_dcf_inputs) blocks run_dcf() on invalid inputs before any division-by-zero risk; NULL fair_value + confidence_flag written.
- **FIN-05**: Bank/industrial bifurcation is clean — is_bank_model gates DDM vs DCF FCFF; ebitda=None enforced for all bank tickers; BankAccountMapper (COSIF) routing confirmed.
- **FIN-06**: RSI-14 (Wilder's EWM com=13), MACD (12/26/9), MA50/200, crossover detection, and composite score (always multiple of 10) implemented in pure pandas; gap rows excluded via is_gap=0 SQL filter.

The scheduler job (`job_financial_engine`) is registered in `_JOB_REGISTRY` and `schedules.yaml` with cron `0 20 * * 1-5`, D-15 structured log emitted. All 93 tests pass.

---

_Verified: 2026-05-11T16:10:00Z_
_Verifier: Claude (gsd-verifier)_
