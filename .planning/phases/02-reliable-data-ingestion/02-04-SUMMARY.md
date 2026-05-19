---
phase: 02-reliable-data-ingestion
plan: "04"
subsystem: ingestion
tags: [scheduler, apscheduler, sqlite, bcb, cvm, b3, news_hunter, subprocess, cron]

# Dependency graph
requires:
  - phase: 02-reliable-data-ingestion/02-01
    provides: db.py (init_db, get_connection), cvm_downloader (parse_and_store, parse_and_store_ipe)
  - phase: 02-reliable-data-ingestion/02-02
    provides: bcb.py (ingest_all_series), b3_scraper (B3Scraper.fetch_and_store)
  - phase: 02-reliable-data-ingestion/02-03
    provides: news_sync.py (sync_news_to_ingestion_db)
provides:
  - "job_cvm_ingest(): registered in _JOB_REGISTRY, runs DFP/ITR/IPE per active ticker"
  - "job_bcb_macro(): registered in _JOB_REGISTRY, fetches 5 BCB SGS macro series"
  - "job_b3_prices(): DB-writing replacement of Parquet stub, registered in _JOB_REGISTRY"
  - "job_news_ingest(): subprocess bridge to news_hunter + sync to ingestion.db"
  - "4 cron entries in schedules.yaml: bcb_macro(08:00), news_ingest(07:00), b3_prices(19:00), cvm_ingest(19:00)"
  - "D-15 structured summary log per job: source, records_inserted, duration_ms, status, last_ingested_at"
affects: [03-financial-engine, scheduler-daemon, ING-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "bind_run_id('ingest') as context manager in every ingestion job — all log calls carry run_id"
    - "init_db() called idempotently at job entry point before any DB write"
    - "subprocess.run list form for external process launch (never shell=True)"
    - "D-15 structured summary log: _log.info(msg, source=, records_inserted=, duration_ms=, status=, last_ingested_at=)"
    - "Job function inner imports: from X import Y inside function body to avoid circular imports at module load"
    - "sys.modules['config.settings'] patch pattern for Pydantic Settings in tests"
    - "get_logger patch pattern for capturing internal _log variable in tests"

key-files:
  created:
    - "Analista de Investimentos/12_PYTHON/tests/test_scheduler_ingestion.py"
  modified:
    - "Analista de Investimentos/12_PYTHON/src/scheduler.py"
    - "Analista de Investimentos/12_PYTHON/config/schedules.yaml"

key-decisions:
  - "bind_run_id('ingest') used in all 4 new jobs — consistent run_id prefix for ingestion traceability"
  - "b3_prices cron updated from 07:00 to 19:00 (post-B3-close) matching cvm_ingest window"
  - "job_news_ingest: subprocess.run([sys.executable, main.py, --coletar], list form, cwd=news_hunter, timeout=300)"
  - "Test fix: patch get_logger at source for D-15 log capture (jobs use internal _log not module-level log)"
  - "Test fix: use sys.modules['config.settings'] for settings patch (Pydantic instance not patchable via config.settings.settings)"

patterns-established:
  - "All ingestion job functions follow: bind_run_id -> init_db -> get_connection -> run -> D-15 summary -> close"
  - "D-15 summary always includes: source, records_inserted, records_updated, duration_ms, status, last_ingested_at"

requirements-completed: [ING-07]

# Metrics
duration: 8min
completed: 2026-05-11
---

# Phase 2 Plan 04: Scheduler Ingestion Wiring Summary

**4 ingestion job functions wired into IntelligenceScheduler via _JOB_REGISTRY with bind_run_id, init_db, and D-15 structured summary logs; cron entries added to schedules.yaml; 65 tests green**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-11T02:25:36Z
- **Completed:** 2026-05-11T02:33:36Z
- **Tasks:** 2 (TDD: RED commit + GREEN commit)
- **Files modified:** 3

## Accomplishments
- Replaced the old Parquet-based `job_b3_prices` stub with a DB-writing version calling `B3Scraper.fetch_and_store()` with `init_db()` and `bind_run_id("ingest")`
- Added `job_cvm_ingest()`, `job_bcb_macro()`, and `job_news_ingest()` to `_JOB_REGISTRY` — each with run_id binding, idempotent DB init, and D-15 structured summary logs
- `job_news_ingest()` uses list-form `subprocess.run([sys.executable, "main.py", "--coletar"], cwd=news_hunter_dir, timeout=300)` then calls `sync_news_to_ingestion_db()` — D-01/D-02 compliant (news_hunter internals not touched, agendador.py never launched)
- Updated `schedules.yaml` with 4 cron entries (no b3_prices duplicate, b3_prices updated to 19:00 post-B3-close)
- 7 new tests covering registry, call order, D-15 log fields, subprocess list form, sync ordering, ticker iteration, yaml entries — all 65 tests green

## Task Commits

TDD cycle executed atomically:

1. **RED - test_scheduler_ingestion.py (failing)** - `5668fc7` (test)
2. **GREEN - scheduler.py + schedules.yaml + test fixes** - `05e3289` (feat)

## Files Created/Modified
- `Analista de Investimentos/12_PYTHON/src/scheduler.py` - Added subprocess/sys imports; replaced job_b3_prices stub; added job_cvm_ingest, job_bcb_macro, job_news_ingest; updated _JOB_REGISTRY with all 4 keys
- `Analista de Investimentos/12_PYTHON/config/schedules.yaml` - Updated b3_prices cron to 19:00; added bcb_macro (08:00), news_ingest (07:00), cvm_ingest (19:00)
- `Analista de Investimentos/12_PYTHON/tests/test_scheduler_ingestion.py` - 7 tests for ING-07 scheduler wiring coverage

## Decisions Made
- `bind_run_id("ingest")` prefix used in all 4 new jobs — consistent with Phase 1 logger infrastructure, allows filtering all ingestion runs in log files
- `b3_prices` cron updated from 07:00 to 19:00 to match `cvm_ingest` post-B3-close timing — both jobs write to `ingestion.db` after market close
- Test patch strategy: `sys.modules["config.settings"]` to access the real module and patch its `settings` attribute (Pydantic BaseSettings prevents attribute deletion, monkeypatch works via module dict)
- Test patch strategy: patch `src.utils.logger.get_logger` to capture `_log` calls inside job functions (jobs create local `_log = _get(__name__)` inside function body, not using module-level `log`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_job_bcb_macro_emits_summary_log — module-level log vs inner _log**
- **Found during:** Task 2 (GREEN verification run)
- **Issue:** Test patched `sched_mod.log` (module-level logger) but job functions use `_log = _get(__name__)` locally inside the function body; patching the module logger had no effect on `_log`
- **Fix:** Changed test to patch `src.utils.logger.get_logger` so the returned mock captures calls made through the internal `_log` variable
- **Files modified:** `tests/test_scheduler_ingestion.py`
- **Verification:** `pytest tests/test_scheduler_ingestion.py::test_job_bcb_macro_emits_summary_log` passes
- **Committed in:** 05e3289 (GREEN commit)

**2. [Rule 1 - Bug] Fixed test_job_b3_prices_iterates_active_tickers — Pydantic settings patch**
- **Found during:** Task 2 (GREEN verification run)
- **Issue:** `patch("config.settings.settings", mock_settings)` raises `AttributeError` because `config.settings` in the `with patch(...)` context resolves to the Settings instance (not the module), and Pydantic models don't have a `settings` attribute
- **Fix:** Used `sys.modules["config.settings"]` to get the module object and `monkeypatch.setattr(settings_module, "settings", mock_settings)` to replace the module-level instance
- **Files modified:** `tests/test_scheduler_ingestion.py`
- **Verification:** `pytest tests/test_scheduler_ingestion.py::test_job_b3_prices_iterates_active_tickers` passes
- **Committed in:** 05e3289 (GREEN commit)

---

**Total deviations:** 2 auto-fixed (2x Rule 1 - test design bugs discovered during GREEN verification)
**Impact on plan:** Both fixes required for green tests; implementation code is exactly as specified in plan. Test design adjusted to match actual Python/loguru/Pydantic import resolution behavior.

## Issues Encountered
- Loguru's `get_logger()` returns a new bound logger on each call — patching the module-level `log` variable doesn't intercept calls made to locally-created `_log` inside functions. The fix (patch at `get_logger` source) is the canonical approach for loguru test capture.

## User Setup Required
None - no external service configuration required. All jobs are scheduler-internal functions triggered by APScheduler cron entries.

## Known Stubs
- `job_news_fetcher()` (pre-existing, not modified): still uses placeholder logic. Out of scope for this plan; tracked in `deferred-items.md` if needed for Phase 3.

## Threat Flags
No new trust boundaries introduced. All threats covered by plan's STRIDE register:
- T-02-17 (subprocess list form): mitigated — `[sys.executable, "main.py", "--coletar"]`, no `shell=True`
- T-02-18 (subprocess timeout): mitigated — `timeout=300` in subprocess.run
- T-02-19 (schedules.yaml injection): accepted — IntelligenceScheduler only dispatches to `_JOB_REGISTRY` keys

## Next Phase Readiness
- ING-07 satisfied: all 4 ingestion sources scheduled and orchestrated via IntelligenceScheduler
- Phase 2 complete: ING-01 through ING-07 all satisfied (Plans 01-04)
- Phase 3 (Financial Engine) can now consume data from `ingestion.db` tables: `cvm_statements`, `macro_series`, `price_ohlcv`, `news_articles`
- `IntelligenceScheduler.run_job_now("cvm_ingest")` / `"bcb_macro"` / `"b3_prices"` / `"news_ingest"` available for CLI testing

## Self-Check: PASSED

- FOUND: scheduler.py
- FOUND: schedules.yaml
- FOUND: test_scheduler_ingestion.py
- FOUND: 02-04-SUMMARY.md
- FOUND commit: 5668fc7 (test RED phase)
- FOUND commit: 05e3289 (feat GREEN phase)
