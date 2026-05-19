---
phase: 3
slug: financial-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-11
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing, 65/65 green) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/ -q -k "financial"` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds (full suite) |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -q -k "financial"`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green (65 existing + new Phase 3 tests)
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-W0-bug01 | W0 | 0 | BUG-01 | — | sector_config.py opens YAML with encoding='utf-8' | unit | `python -m pytest tests/test_financial_engine.py::test_sector_config_loads_on_windows -x` | ❌ W0 | ⬜ pending |
| 03-W0-bug02 | W0 | 0 | GAP-02 | — | account_mapper.py import path works from project root | unit | `python -m pytest tests/test_financial_engine.py::test_account_mapper_import -x` | ❌ W0 | ⬜ pending |
| 03-01-01 | 01 | 1 | FIN-01 | — | N/A | unit | `python -m pytest tests/test_financial_engine.py::test_ltm_aggregates_four_quarters -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | FIN-01 | — | N/A | unit | `python -m pytest tests/test_financial_engine.py::test_ltm_dfp_reconciliation_warning -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | FIN-01 | — | N/A | unit | `python -m pytest tests/test_financial_engine.py::test_normalized_name_backfill -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | FIN-01 | — | N/A | unit | `python -m pytest tests/test_financial_engine.py::test_account_mapper_wired_in_downloader -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | D-01/D-02 | — | financial_* tables queryable without JSON parsing | unit | `python -m pytest tests/test_financial_db_schema.py::test_financial_tables_created -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | FIN-02 | — | N/A | unit | `python -m pytest tests/test_financial_engine.py::test_industrial_multiples_computed -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | FIN-02 | — | Missing price produces flagged record not zero-division | unit | `python -m pytest tests/test_financial_engine.py::test_multiples_handles_missing_price -x` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | FIN-03 | — | N/A | unit | `python -m pytest tests/test_financial_engine.py::test_dcf_fair_value_industrial -x` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 3 | FIN-03 | — | N/A | unit | `python -m pytest tests/test_financial_engine.py::test_wacc_from_macro_series -x` | ❌ W0 | ⬜ pending |
| 03-03-03 | 03 | 3 | FIN-03 | — | Stale macro logs WARNING and uses sectors.yaml fallback | unit | `python -m pytest tests/test_financial_engine.py::test_wacc_stale_macro_fallback -x` | ❌ W0 | ⬜ pending |
| 03-03-04 | 03 | 3 | FIN-04 | T-DCF-01 | DCF skipped + INPUT_INVALIDO flag when terminal_growth >= WACC | unit | `python -m pytest tests/test_financial_engine.py::test_dcf_input_validation_blocks_run -x` | ❌ W0 | ⬜ pending |
| 03-03-05 | 03 | 3 | FIN-04 | T-DCF-02 | FORA DO INTERVALO CONFIAVEL flag when outside 0.1x-5.0x | unit | `python -m pytest tests/test_financial_engine.py::test_dcf_confidence_flag_out_of_range -x` | ❌ W0 | ⬜ pending |
| 03-04-01 | 04 | 3 | FIN-05 | — | Bank ticker uses DDM path not DCF | unit | `python -m pytest tests/test_financial_engine.py::test_bank_routing_uses_ddm -x` | ❌ W0 | ⬜ pending |
| 03-04-02 | 04 | 3 | FIN-05 | — | Bank multiples include NIM and efficiency_ratio | unit | `python -m pytest tests/test_financial_engine.py::test_bank_metrics_include_nim -x` | ❌ W0 | ⬜ pending |
| 03-05-01 | 05 | 4 | FIN-06 | — | N/A | unit | `python -m pytest tests/test_financial_signals.py::test_rsi_14_computation -x` | ❌ W0 | ⬜ pending |
| 03-05-02 | 05 | 4 | FIN-06 | — | N/A | unit | `python -m pytest tests/test_financial_signals.py::test_macd_12_26_9 -x` | ❌ W0 | ⬜ pending |
| 03-05-03 | 05 | 4 | FIN-06 | — | N/A | unit | `python -m pytest tests/test_financial_signals.py::test_ma_crossover_detection -x` | ❌ W0 | ⬜ pending |
| 03-05-04 | 05 | 4 | FIN-06 | — | N/A | unit | `python -m pytest tests/test_financial_signals.py::test_momentum_score_range -x` | ❌ W0 | ⬜ pending |
| 03-05-05 | 05 | 4 | FIN-06 | — | Gap rows (is_gap=1) excluded from signal computation | unit | `python -m pytest tests/test_financial_signals.py::test_gap_rows_excluded -x` | ❌ W0 | ⬜ pending |
| 03-05-06 | 05 | 4 | D-03/D-12 | — | job_financial_engine registered in _JOB_REGISTRY | unit | `python -m pytest tests/test_financial_engine.py::test_job_registered -x` | ❌ W0 | ⬜ pending |
| 03-05-07 | 05 | 4 | D-12 | — | job_financial_engine emits D-15 summary log | unit | `python -m pytest tests/test_financial_engine.py::test_job_summary_log -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_financial_engine.py` — stubs/implementations covering FIN-01 through FIN-05, D-12 job wiring, BUG-01 fix verification
- [ ] `tests/test_financial_signals.py` — FIN-06: RSI-14, MACD (12/26/9), MA50/MA200, crossover, momentum score (0-100), gap row exclusion
- [ ] `tests/test_financial_db_schema.py` — D-01, D-02, D-04: financial_* table creation, column types, INSERT OR REPLACE dedup behavior
- [ ] BUG-01 fix: `src/valuation/sector_config.py` — add `encoding='utf-8'` to both `open()` calls before any SectorConfig test can pass on Windows
- [ ] GAP-02 fix: `src/normalization/account_mapper.py` — fix bare `from parsers.dfp_parser import` to `from src.parsers.dfp_parser import`
- [ ] `pip install apscheduler>=3.10.0` if scheduler integration tests needed (already in pyproject.toml)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| LTM runs automatically after ingestion cycle | FIN-01 | Requires live ingestion.db with real CVM data | Run `python -m src.main` after ingestion; check financial_ltm table populated with today's date |
| DCF fair value plausible for real ticker (e.g., PETR4) | FIN-03 | Requires real macro_series data | Query `SELECT fair_value_brl, upside_pct FROM financial_dcf WHERE ticker='PETR4'`; verify non-NULL, positive value |
| Bank tickers ITUB4/BBDC4 show NULL ebitda in financial_ltm | FIN-05 | Schema validation with real data | `SELECT ebitda FROM financial_ltm WHERE ticker IN ('ITUB4','BBDC4')` — must be NULL |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING (❌ W0) references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
