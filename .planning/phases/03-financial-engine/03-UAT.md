---
status: complete
phase: 03-financial-engine
source: [03-01-SUMMARY.md, 03-02-SUMMARY.md, 03-03-SUMMARY.md, 03-04-SUMMARY.md, 03-05-SUMMARY.md]
started: 2026-05-11T00:00:00Z
updated: 2026-05-11T03:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: From `Analista de Investimentos/12_PYTHON/`, run `python -m pytest tests/ -q`. Suite boots without import errors. DB schema fixtures initialize cleanly. Result shows 93+ tests passing, 0 failures.
result: pass

### 2. Financial DB Schema — 8 Tables
expected: After calling `init_db()`, the SQLite database has exactly 8 tables: `cvm_statements`, `macro_series`, `price_ohlcv`, `news_articles`, `financial_ltm`, `financial_multiples`, `financial_dcf`, `financial_signals`. All 4 financial tables have `(ticker, computed_date)` as composite primary key.
result: pass

### 3. LTM Aggregation — 4-Quarter Rolling Sum
expected: For an industrial ticker with 4 ITR quarters of CVM data, `_aggregate_ltm()` returns a dict with `net_revenue`, `ebitda`, `fcf`, `gross_debt`, `net_debt` — all numbers (not None). EBITDA = EBIT + D&A. FCF = CFO − |capex|. If a D&A or capex row is absent, those fields are `None`, not `0`.
result: pass

### 4. Bank EBITDA = NULL in LTM
expected: For a bank ticker (e.g. ITUB4), `_aggregate_ltm(is_bank=True)` returns a dict where `ebitda` is `None` (never a number). The `financial_ltm` row written to DB has `ebitda` = NULL. This prevents nonsensical EBITDA-based multiples for COSIF-accounting entities.
result: pass

### 5. Industrial Multiples Written
expected: For an industrial ticker with a valid price in `price_ohlcv` (is_gap=0, adj_close not null), `_compute_multiples()` writes a `financial_multiples` row with non-null P/E, EV/EBITDA, and P/BV. If price is missing, the function exits silently without crashing — no `financial_multiples` row is written.
result: pass

### 6. Bank EV/EBITDA = NULL
expected: For a bank ticker, the `financial_multiples` row has `ev_ebitda` = NULL (explicitly set, never propagated from BankMetrics). P/E and P/BV may still be computed if net_income and book_value are available.
result: pass

### 7. DCF Input Validation — Blocks Bad Inputs
expected: When `terminal_growth >= wacc` or `wacc <= 0.05`, `_validate_dcf_inputs()` returns `"INPUT_INVALIDO"`. The `financial_dcf` row is written with `fair_value` = NULL and `confidence_flag = 'INPUT_INVALIDO'`. `run_dcf()` is never called — no division-by-zero, no negative fair value written.
result: pass

### 8. WACC Derivation — Macro + Fallback
expected: `compute_wacc()` queries `macro_series` for Selic (series_code=11) and CDS Brasil (series_code=29039). If both are fresh (within 5 days), returns a live WACC with `used_fallback=False`. If macro data is stale or absent, logs a WARNING and returns the `risk_free` + `country_risk` from `sectors.yaml`, with `used_fallback=True`.
result: pass

### 9. Bank DDM Fair Value
expected: For a bank ticker, `_compute_bank_model()` calls `run_ddm()` with `cost_of_equity = gordon_assumptions.coe` (e.g. 0.135) and `terminal_growth_rate = gordon_assumptions.terminal_growth`. Writes `financial_dcf` row with `valuation_method='ddm'` and a non-null `fair_value`. The guard `ke > terminal_growth AND ke > 0.05` prevents Gordon model explosion.
result: pass

### 10. Technical Signals — RSI / MACD / MA / Momentum
expected: For a ticker with 200+ price rows in `price_ohlcv` (is_gap=0), `_compute_and_write_signals()` writes a `financial_signals` row with: `rsi_14` between 0 and 100, MACD histogram = macd_line − macd_signal, `ma_50` and `ma_200` non-null, and `momentum_score` that is a multiple of 10. For tickers with fewer than 200 rows, a warning is logged and `ma_200` = NULL but the row is still written.
result: pass

### 11. Scheduler Wiring — Job Registered + Cron
expected: In `scheduler.py`, `"financial_engine"` appears in `_JOB_REGISTRY`. In `config/schedules.yaml`, the `financial_engine` job has cron `"50 19 * * 1-5"` (19:50, before `analyze` at 20:00). Running `job_financial_engine()` manually should call `run_all()` and return a summary string containing `"financial_engine:"`, record count, and duration.
result: pass

## Summary

total: 11
passed: 11
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
