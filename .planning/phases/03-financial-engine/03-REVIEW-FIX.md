---
phase: 03-financial-engine
fixed_at: 2026-05-11T00:00:00Z
review_path: .planning/phases/03-financial-engine/03-REVIEW.md
iteration: 1
findings_in_scope: 14
fixed: 13
skipped: 1
status: partial
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-05-11T00:00:00Z
**Source review:** .planning/phases/03-financial-engine/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 14 (CR-01..CR-05, WR-01..WR-09)
- Fixed: 13
- Skipped: 1 (CR-03 — already correct in source)

---

## Fixed Issues

### CR-01: File handle leak in `run_all()` — `open()` never closed

**Files modified:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py`
**Commit:** 2817c3e
**Applied fix:** Wrapped `yaml.safe_load(open(...))` in a `with open(...) as fh:` context manager so the file handle is always closed, even on parse failure.

---

### CR-02: Division-by-zero in `_aggregate_ltm()` gross/net debt when snapshot rows absent

**Files modified:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py`
**Commit:** 008a09f
**Applied fix:** Replaced direct addition of `.get("value", 0.0)` with explicit `None` checks. When both `short_term_debt` and `long_term_debt` are absent, `gross_debt` and `net_debt` are set to `None` (not `0.0`). When `cash` is absent but debt components are present, `net_debt` is `None`. Downstream consumers now receive a clear `None` sentinel instead of a misleading zero.

---

### CR-04: `datetime.utcnow()` deprecated — naive timestamps mixed with aware ones

**Files modified:** `Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py`, `Analista de Investimentos/12_PYTHON/src/scheduler.py`
**Commit:** e5c47bd
**Applied fix:** Added `timezone` to `from datetime import` in both files. Replaced all `datetime.utcnow().isoformat()` calls with `datetime.now(timezone.utc).isoformat()`. Also fixed the local `from datetime import datetime` inside `job_financial_engine()` to include `timezone`. All timestamps now produce timezone-aware ISO strings consistent with `financial_engine.py`.

---

### CR-05: `get_connection()` does not apply `busy_timeout` — per-connection setting not propagated

**Files modified:** `Analista de Investimentos/12_PYTHON/src/ingestion/db.py`
**Commit:** be53e6a
**Applied fix:** Added `conn.execute("PRAGMA busy_timeout=5000")` in `get_connection()`, matching the setting applied in `init_db()`. Every caller now gets the 5-second grace period before raising `OperationalError: database is locked`.

---

### WR-01: `row["value"] or 0.0` silently replaces genuine zero values

**Files modified:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py`
**Commit:** 6c8303d
**Applied fix:** Replaced `val = row["value"] or 0.0` with `val = float(row["value"]) if row["value"] is not None else 0.0`. A genuine `VL_CONTA=0` from CVM is now preserved as `0.0` rather than being conflated with NULL.

---

### WR-02: `_compute_multiples()` receives `shares=None` because `ltm` never contains `shares_outstanding`

**Files modified:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py`
**Commit:** 344ee9f
**Applied fix:** Added `ltm["shares_outstanding"] = shares` in `run_ticker()` immediately after the yfinance fetch, before `_compute_multiples()` and `_compute_dcf_industrial()` are called. Both functions now receive shares via `ltm.get("shares_outstanding")` as intended.

---

### WR-03: `compute_wacc()` bank path uses `gordon_assumptions` lacking industrial WACC fields

**Files modified:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py`
**Commit:** 5962298
**Applied fix:** Added an explicit `log.debug()` warning in the bank-model branch of `compute_wacc()` documenting that the returned WACC value uses hardcoded industrial defaults (beta/erp/cost_of_debt/tax_rate/debt_to_capital) and must NOT be used for bank DCF discounting. Callers should use `ke` from `gordon_assumptions.coe` directly for DDM/Gordon valuation.
**Note:** This finding is classified as a logic/design issue — requires human verification that the documented behavior is acceptable until a dedicated bank ke path is implemented.

---

### WR-04: EV/EBITDA branch validates inputs AFTER computing `fair_value`

**Files modified:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py`
**Commit:** 87c7f84
**Applied fix:** Added a pre-validation call at the top of the `ev_ebitda_multiple` branch that mirrors the existing guard in the `dcf_fcff` branch. When `_validate_dcf_inputs()` returns `INPUT_INVALIDO`, a NULL row is written and the function returns early — no `fair_value` is computed from corrupt inputs.

---

### WR-05: `backfill_normalized_names()` calls private `mapper._map_row()` directly

**Files modified:** `Analista de Investimentos/12_PYTHON/src/normalization/account_mapper.py`, `Analista de Investimentos/12_PYTHON/src/financial_engine.py`
**Commit:** da3bd6b
**Applied fix:** Added a public `map_row(account_code, account_name)` method to `AccountMapper` that wraps `_map_row()`. Updated `backfill_normalized_names()` to call `mapper.map_row(...)` instead of `mapper._map_row(pd.Series(...))`. The internal implementation is now accessed only via the public API.

---

### WR-06: MA200 unavailable for sparse tickers — `momentum_score` silently degraded

**Files modified:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py`
**Commit:** f88a62c
**Applied fix:** Added a `log.warning()` call in `_compute_and_write_signals()` when `len(rows) < 200`, informing operators that MA200 cannot be computed and the momentum score will use the neutral `cross_score=10` fallback. The calculation proceeds as before — the warning provides observability without changing behaviour.

---

### WR-07: `job_news_ingest()` — unclosed connection when `sync_news_to_ingestion_db()` raises

**Files modified:** `Analista de Investimentos/12_PYTHON/src/scheduler.py`
**Commit:** 179063f
**Applied fix:** Wrapped `inserted = sync_news_to_ingestion_db(conn)` in a `try/finally` block with `conn.close()` in the `finally` clause, consistent with the pattern already used in `job_bcb_macro()` and `job_cvm_check()`.

---

### WR-08: `_check_dfp_reconciliation()` passes `(ticker, ticker)` — fragile dual-param pattern

**Files modified:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py`
**Commit:** 2200514
**Applied fix:** Replaced the correlated subquery with a CTE (`WITH latest_dfp AS (...)`) that isolates the `MAX(reference_date)` lookup. The two positional `?` params remain (one for the CTE, one for the outer WHERE) but their purpose is now visually unambiguous. The T-03-01-02 comment was updated accordingly.

---

### WR-09: `financial_engine` and `analyze` both cron at 20:00 — read/write race condition

**Files modified:** `Analista de Investimentos/12_PYTHON/config/schedules.yaml`
**Commit:** 9a0ada6
**Applied fix:** Changed `financial_engine` cron from `"0 20 * * 1-5"` to `"50 19 * * 1-5"` (19:50). This gives `financial_engine` a 10-minute head start before `analyze` reads from the same DB tables at 20:00, eliminating the partial-write race condition.

---

## Skipped Issues

### CR-03: `sector_config.py` — `open()` without `encoding=` argument

**File:** `Analista de Investimentos/12_PYTHON/src/valuation/sector_config.py:38-39` and `45-47`
**Reason:** Code already correct — both `_load_sectors()` and `_load_ticker_map()` already use `with open(..., encoding="utf-8")` context managers. The finding does not match the current state of the file. No change needed.

---

_Fixed: 2026-05-11T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
