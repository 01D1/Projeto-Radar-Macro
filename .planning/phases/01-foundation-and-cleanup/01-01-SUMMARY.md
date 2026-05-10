---
phase: 01-foundation-and-cleanup
plan: "01"
subsystem: infra
tags: [python, pytest, venv, windows, sys-path, task-scheduler, deprecated]

# Dependency graph
requires: []
provides:
  - "Working Windows venv (Python 3.10.11) at OBSIDIAN root"
  - "5 test stub files collected by pytest without import errors"
  - "Clean imports in src/processing/pipeline.py (no sys.path manipulation)"
  - "pipeline banco completo/DEPRECATED.md freeze notice"
  - "Windows Task Scheduler entries pointing to vault path"
  - "pyproject.toml with pythonpath=['.'] for pytest + hatchling build config"
affects: [01-02, 01-03]

# Tech tracking
tech-stack:
  added:
    - "pytest 9.0.3 (test framework)"
    - "pytest-cov 7.1.0 (coverage)"
    - "pyyaml 6.0.3 (config parsing — missing dep fixed)"
  patterns:
    - "src. prefix imports throughout src/ (no sys.path manipulation)"
    - "pytest with pythonpath=['.'] so src.X imports resolve from 12_PYTHON/"
    - "Test stubs as RED-phase scaffolding before implementation"

key-files:
  created:
    - "Analista de Investimentos/12_PYTHON/tests/__init__.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_consolidation.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_retry.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_logger.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_settings.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_news_hunter_config.py"
    - "Analista de Investimentos/12_PYTHON/pipeline banco completo/DEPRECATED.md"
  modified:
    - "Analista de Investimentos/12_PYTHON/src/processing/pipeline.py"
    - "Analista de Investimentos/12_PYTHON/pyproject.toml"

key-decisions:
  - "Venv recreated at OBSIDIAN root (.venv/) for Windows Python 3.10.11 — replacing stale macOS 3.9 artifact"
  - "pyproject.toml requires-python lowered to >=3.10 to match available Windows Python (3.11 was too strict)"
  - "hatchling build config added with packages=[src, config, news_hunter] to enable editable install"
  - "pyyaml added as explicit dependency — was implicit but missing from pyproject.toml"
  - "Both Task Scheduler tasks (ValuationBancario_Manha + ValuationBancario_Tarde) updated to vault path"

patterns-established:
  - "Canonical import pattern: from src.X.Y import Z (no sys.path manipulation)"
  - "Test discovery via pytest with pythonpath=['.'] from 12_PYTHON/ working directory"

requirements-completed:
  - FOUND-01

# Metrics
duration: 45min
completed: "2026-05-10"
---

# Phase 01 Plan 01: Bootstrap Test Infrastructure Summary

**Windows venv recreated with Python 3.10.11, 15 tests collected from 5 stub files, sys.path removed from pipeline.py, DEPRECATED.md added to pipeline banco completo/, and both Task Scheduler tasks redirected to vault path**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-05-10T18:00:00Z
- **Completed:** 2026-05-10T18:45:00Z
- **Tasks:** 2 (Task 0 + Task 1)
- **Files modified:** 9

## Accomplishments

- Windows venv recreated at OBSIDIAN root with Python 3.10.11 (replacing stale macOS 3.9 artifact)
- 5 test stub files created; pytest collects 15 tests without import errors
- src/processing/pipeline.py cleaned of all sys.path manipulation (FOUND-01)
- pipeline banco completo/DEPRECATED.md freeze notice created
- Both Windows Task Scheduler tasks (Manha + Tarde) updated from Downloads path to vault path (D-02)

## Task Commits

1. **Task 0: Bootstrap test infrastructure + Windows venv** - `51530cc` (chore)
2. **Task 1: Remove sys.path, add DEPRECATED.md, update Task Scheduler** - `d02a582` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `Analista de Investimentos/12_PYTHON/tests/__init__.py` - Empty pytest package marker
- `Analista de Investimentos/12_PYTHON/tests/test_consolidation.py` - FOUND-01: canonical src. imports, sys.path check
- `Analista de Investimentos/12_PYTHON/tests/test_retry.py` - FOUND-03: backoff + jitter + IngestionError (RED)
- `Analista de Investimentos/12_PYTHON/tests/test_logger.py` - FOUND-04: configure_logging, bind_run_id (RED)
- `Analista de Investimentos/12_PYTHON/tests/test_settings.py` - FOUND-02: startup guard dev/prod (RED)
- `Analista de Investimentos/12_PYTHON/tests/test_news_hunter_config.py` - FOUND-02: no hardcoded tokens (RED)
- `Analista de Investimentos/12_PYTHON/pipeline banco completo/DEPRECATED.md` - Freeze notice
- `Analista de Investimentos/12_PYTHON/src/processing/pipeline.py` - Removed sys.path block + _ensure_src_path(), fixed imports to src. prefix
- `Analista de Investimentos/12_PYTHON/pyproject.toml` - Added hatchling config, pythonpath, pyyaml, lowered requires-python

## Decisions Made

- Used Python 3.10.11 (Windows Store) since 3.11 not installed; lowered requires-python to >=3.10
- Added hatchling `packages` config to enable `pip install -e .` (hatchling couldn't auto-detect package layout)
- Added `pythonpath = ["."]` to pytest config so `from src.X` resolves from 12_PYTHON/ directory
- Both ValuationBancario tasks updated (plan only mentioned fixing stale path — two tasks found, both corrected)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] hatchling build config missing in pyproject.toml**
- **Found during:** Task 0 (venv creation)
- **Issue:** `pip install -e .` failed — hatchling couldn't auto-detect package layout for project named `intelligence-system` when src directory is named `src`
- **Fix:** Added `[tool.hatch.build.targets.wheel] packages = ["src", "config", "news_hunter"]` to pyproject.toml
- **Files modified:** Analista de Investimentos/12_PYTHON/pyproject.toml
- **Verification:** `pip install -e .[dev]` succeeds after fix
- **Committed in:** 51530cc (Task 0 commit)

**2. [Rule 3 - Blocking] requires-python = ">=3.11" incompatible with Windows Python 3.10.11**
- **Found during:** Task 0 (venv creation)
- **Issue:** pip refused to install because Python 3.10.11 doesn't satisfy `>=3.11`
- **Fix:** Changed requires-python to `>=3.10` in pyproject.toml
- **Files modified:** Analista de Investimentos/12_PYTHON/pyproject.toml
- **Verification:** Install succeeds with Python 3.10.11
- **Committed in:** 51530cc (Task 0 commit)

**3. [Rule 3 - Blocking] pyyaml not listed as dependency but required by config/settings.py**
- **Found during:** Task 1 (running test_consolidation.py)
- **Issue:** `from config.settings import settings` raised `ModuleNotFoundError: No module named 'yaml'`
- **Fix:** Added `pyyaml>=6.0.0` to dependencies in pyproject.toml + `pip install pyyaml`
- **Files modified:** Analista de Investimentos/12_PYTHON/pyproject.toml
- **Verification:** test_config_settings_importable passes
- **Committed in:** d02a582 (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (3 blocking dependency/config issues)
**Impact on plan:** All fixes necessary for venv creation and test execution. No scope creep.

## Issues Encountered

- Two git repositories discovered: OBSIDIAN root (for .planning/) and Analista de Investimentos/ (for code). All code commits were correctly directed to the `Analista de Investimentos/` repository.
- schtasks found two tasks (ValuationBancario_Manha and ValuationBancario_Tarde) both pointing to stale Downloads path — both updated to vault path.

## Known Stubs

The following test files are intentional RED-phase stubs that WILL fail until implementation:

| File | Tests | Waiting for |
|------|-------|------------|
| tests/test_retry.py | test_backoff_jitter, test_ingestion_error_raised_on_exhaustion, test_non_matching_exception_propagates | Plan 01-03: extend retry.py with jitter + IngestionError |
| tests/test_logger.py | test_run_id_binding | Plan 01-03: extend logger.py with bind_run_id() |
| tests/test_settings.py | test_startup_guard_production_missing_keys | Plan 01-02: extend config/settings.py with model_post_init validation |
| tests/test_news_hunter_config.py | test_no_hardcoded_telegram_token | Plan 01-02: remove hardcoded token fallbacks from news_hunter/config.py |

These stubs are intentional (RED phase) and correctly fail. They are NOT blocking Plan 01-01 success criteria — only collection without import errors is required.

## Threat Flags

No new threat surface introduced. All changes are import path cleanup, test scaffolding, and documentation.

## Next Phase Readiness

- Plan 01-02 (credentials migration) can proceed — test_settings.py and test_news_hunter_config.py stubs are ready
- Plan 01-03 (retry/logging infrastructure) can proceed — test_retry.py and test_logger.py stubs are ready
- pytest infrastructure is fully operational from Analista de Investimentos/12_PYTHON/ with the Windows venv

## Self-Check: PASSED

Files verified:
- `Analista de Investimentos/12_PYTHON/tests/__init__.py` - EXISTS
- `Analista de Investimentos/12_PYTHON/tests/test_consolidation.py` - EXISTS
- `Analista de Investimentos/12_PYTHON/tests/test_retry.py` - EXISTS
- `Analista de Investimentos/12_PYTHON/tests/test_logger.py` - EXISTS
- `Analista de Investimentos/12_PYTHON/tests/test_settings.py` - EXISTS
- `Analista de Investimentos/12_PYTHON/tests/test_news_hunter_config.py` - EXISTS
- `Analista de Investimentos/12_PYTHON/pipeline banco completo/DEPRECATED.md` - EXISTS
- `Analista de Investimentos/12_PYTHON/src/processing/pipeline.py` - MODIFIED (no sys.path)

Commits verified:
- 51530cc - Task 0 commit (bootstrap test infrastructure)
- d02a582 - Task 1 commit (pipeline.py + DEPRECATED.md + schtasks)

---
*Phase: 01-foundation-and-cleanup*
*Completed: 2026-05-10*
