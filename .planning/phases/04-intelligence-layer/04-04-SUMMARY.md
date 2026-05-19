---
phase: 04-intelligence-layer
plan: 04
subsystem: intelligence-layer
tags: [run_all, scheduler, cron, apscheduler, yaml, sqlite, tickers, intelligence-pipeline]

# Dependency graph
requires:
  - phase: 04-intelligence-layer
    plan: 03
    provides: run_ticker(), compute_opportunity_signals(), ThesisResult.signals, opportunity_signals table

provides:
  - run_all() — iterates all active tickers from tickers.yaml, calls run_ticker() per ticker, returns list[ThesisResult]
  - job_intelligence() fully operational — calls run_all() via lazy import, bind_run_id("intelligence"), D-15 structured summary log
  - schedules.yaml: intelligence cron entry "0 21 * * 1-5" (after financial_engine at 19:50)
  - Full INT-01..INT-06 test coverage with 0 xfail markers

affects:
  - Phase 5 (Telegram alerts + dashboard consume opportunity_signals; job_intelligence runs nightly at 21:00)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - run_all() mirrors financial_engine.run_all() — load tickers.yaml, loop with per-ticker try/except, structured summary log (D-20)
    - IngestionError isolated from generic Exception in run_all() — both paths produce ThesisResult(error=...) and continue
    - Lazy import pattern: job_intelligence() uses `from src.intelligence_layer import run_all` inside function body — consistent with all other scheduler jobs

key-files:
  modified:
    - Analista de Investimentos/12_PYTHON/src/intelligence_layer.py
    - Analista de Investimentos/12_PYTHON/config/schedules.yaml
    - Analista de Investimentos/12_PYTHON/tests/test_scheduler_intelligence.py

key-decisions:
  - "No changes needed to scheduler.py — job_intelligence() and _JOB_REGISTRY['intelligence'] were already wired by Plan 04-01; only run_all() implementation was missing"
  - "test_news_hunter_config.py failure (1 test) is pre-existing and out of scope — confirmed by stash-test; not caused by any Phase 4 changes"

requirements-completed: [INT-01, INT-02, INT-03, INT-04, INT-05, INT-06]

# Metrics
duration: 10min
completed: 2026-05-17
---

# Phase 4 Plan 4: Scheduler Wiring + run_all() — Summary

**run_all() implemented to iterate tickers.yaml, call run_ticker() per ticker with IngestionError isolation; job_intelligence() fully operational; intelligence cron "0 21 * * 1-5" added to schedules.yaml; 3/3 scheduler tests pass; 115 total tests pass**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-17T17:05:00Z
- **Completed:** 2026-05-17T17:11:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `run_all()` in `intelligence_layer.py` — loads active tickers from `config/tickers.yaml`, iterates with per-ticker `try/except IngestionError` isolation, returns `list[ThesisResult]` with error entries for failures; emits structured summary log with ok/skipped/failed/total counts
- `schedules.yaml` updated with intelligence cron entry `"0 21 * * 1-5"` — runs after `financial_engine` (19:50), completing the nightly pipeline: b3_prices (19:00) → cvm_ingest (19:15) → financial_engine (19:50) → intelligence (21:00)
- `test_scheduler_intelligence.py` xfail markers removed from `test_job_intelligence_calls_run_all` and `test_job_intelligence_summary_log` — both pass; 3/3 scheduler tests green
- INT-01 through INT-06 all covered by passing (non-xfail) tests: 18 intelligence layer + 3 scheduler + 7 db_schema = 28 INT-related tests pass
- Full suite: 115 passed (1 pre-existing out-of-scope failure in test_news_hunter_config.py)

## Task Commits

1. **Task 1: Implement run_all() in intelligence_layer.py** — `e9c2418` (feat)
2. **Task 2: Wire job_intelligence(), schedules.yaml, un-xfail tests** — `573e4fb` (feat)

## Files Created/Modified

- `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py` — `run_all()` stub replaced with full implementation (~45 lines): tickers.yaml load, active_tickers filter, per-ticker loop with IngestionError + generic Exception handling, structured summary log
- `Analista de Investimentos/12_PYTHON/config/schedules.yaml` — Added intelligence job entry with cron "0 21 * * 1-5" after financial_engine entry
- `Analista de Investimentos/12_PYTHON/tests/test_scheduler_intelligence.py` — Removed 2 `@pytest.mark.xfail(...)` decorators; all 3 tests now pass normally

## Decisions Made

- No changes needed to `scheduler.py` — `job_intelligence()` function and `_JOB_REGISTRY["intelligence"]` entry were already implemented by Plan 04-01; only the `run_all()` implementation was missing
- `test_news_hunter_config.py` single failure (`test_token_loaded_from_env`) confirmed pre-existing via stash test — unrelated to Phase 4 intelligence layer work; not fixed per scope boundary rules

## Deviations from Plan

None — plan executed exactly as written. `job_intelligence()` and `_JOB_REGISTRY` were already present from Plan 04-01 as documented in the plan's context; only `run_all()` and the 3 plan changes were needed.

## Issues Encountered

None — all three verification checks passed on first attempt.

## Known Stubs

None — all stubs from Plans 04-01 through 04-03 are now resolved:
- `run_all()` was the last NotImplementedError stub (now implemented)
- `job_intelligence()` was functional pending `run_all()` (now fully operational)

## Threat Surface Scan

No new network endpoints, auth paths, file access patterns, or schema changes.

- T-04-17: run_all() individually try/excepts each ticker — IngestionError on one ticker does not abort run; verified by implementation and existing tests
- T-04-18: `_JOB_REGISTRY["intelligence"]` confirmed present — `test_job_intelligence_registered` passes
- T-04-19: Cron 21:00 with financial_engine at 19:50 — 70-minute buffer; APScheduler coalesce=True prevents stacking
- T-04-20: D-15 summary log confirmed — `test_job_intelligence_summary_log` asserts source='intelligence' and duration_ms present

## Self-Check

Files exist:
- [x] `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py` — FOUND (contains run_all() implementation)
- [x] `Analista de Investimentos/12_PYTHON/config/schedules.yaml` — FOUND (contains intelligence cron entry)
- [x] `Analista de Investimentos/12_PYTHON/tests/test_scheduler_intelligence.py` — FOUND (3/3 pass, 0 xfail)

Commits exist:
- [x] `e9c2418` — feat(04-04) Task 1: run_all() implementation
- [x] `573e4fb` — feat(04-04) Task 2: scheduler wiring, schedules.yaml, un-xfail

## Self-Check: PASSED
