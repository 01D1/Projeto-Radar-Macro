---
phase: 01-foundation-and-cleanup
plan: "03"
subsystem: testing
tags: [loguru, tenacity, pydantic, structlog, retry, errors, logging]

requires:
  - phase: 01-02
    provides: settings.py startup guard (module-level, CR-04 bug) + .env wiring

provides:
  - IngestionError exception class with .cause attribute for structured failure capture
  - retry decorator with jitter parameter and IngestionError raise on exhaustion
  - bind_run_id context manager injecting run_id into all loguru records within scope
  - src/main.py importable without side effects — production guard inside app() only

affects: [02-data-layer, 03-financial-engine]

tech-stack:
  added: []
  patterns:
    - deferred import inside retry wrapper to avoid circular import (errors.py ← retry.py)
    - loguru contextualize for run_id injection; patcher for default "-" outside scope
    - startup guard inside app() body (not module scope) for safe pytest import

key-files:
  created:
    - Analista de Investimentos/12_PYTHON/src/utils/errors.py
  modified:
    - Analista de Investimentos/12_PYTHON/src/utils/retry.py
    - Analista de Investimentos/12_PYTHON/src/utils/logger.py
    - Analista de Investimentos/12_PYTHON/src/main.py

key-decisions:
  - "IngestionError uses __init__ (not dataclass) — test asserts .cause == str(exc) and str(err) contains func_name"
  - "jitter defaults to 0.5 per PATTERNS.md — added after exceptions param to preserve backward compat call sites"
  - "Deferred import of IngestionError inside wrapper function — avoids circular import at module load"
  - "bind_run_id uses f'{prefix}-{uuid4().hex[:8]}' — short, readable, prefixed run ID per CR-03 correction"
  - "run_id patcher uses setdefault so contextualize value takes precedence inside bind_run_id scope"
  - "src/main.py production guard moved entirely inside app() — module now importable without side effects"

patterns-established:
  - "Error hierarchy: IngestionError(Exception) for all retry exhaustions — callers catch IngestionError, not bare exceptions"
  - "Structured logging: bind_run_id as context manager in every scheduler job; run_id flows through all log records"
  - "Retry pattern: @retry(attempts=N, delay=X, jitter=0.5, exceptions=(SomeError,)) — jitter always included"

requirements-completed: [FOUND-03, FOUND-04]

duration: 25min
completed: 2026-05-10
---

# Phase 01-03: Gap Closure Summary

**IngestionError class + retry jitter + bind_run_id context manager + CR-04 module-level sys.exit fix — 15/15 tests green**

## Performance

- **Duration:** 25 min
- **Started:** 2026-05-10T20:30:00-03:00
- **Completed:** 2026-05-10T20:55:00-03:00
- **Tasks:** 2
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments
- Created `src/utils/errors.py` with `IngestionError(func_name, cause)` — `.cause = str(exc)`, func name in `str(err)`
- Extended `src/utils/retry.py` with `jitter` param and `IngestionError` raise on exhaustion (deferred import pattern)
- Added `bind_run_id()` context manager to `src/utils/logger.py` with loguru contextvars injection and run_id patcher
- Fixed CR-04: moved production startup guard from module scope into `app()` body — `src.main` now importable cleanly

## Task Commits

1. **Task 1: Create errors.py + extend retry.py (FOUND-03)** — `6110aef` (feat)
2. **Task 2: Add bind_run_id + move CR-04 guard inside app() (FOUND-04 + CR-04)** — `83e6107` (feat)

## Files Created/Modified
- `src/utils/errors.py` (NEW) — IngestionError exception with func_name, cause, timestamp attributes
- `src/utils/retry.py` — Added jitter param, IngestionError raise on exhaustion, deferred import
- `src/utils/logger.py` — Added bind_run_id(), run_id patcher, uuid import, updated file handler format + retention 7d
- `src/main.py` — Moved production startup guard from module scope into app() body

## Decisions Made
- IngestionError uses `__init__` (not dataclass) because test asserts `err.cause == "api down"` (str) and `"always_fails" in str(err)` — dataclass would require different serialization
- Deferred import of IngestionError inside retry wrapper avoids circular import at module load time (retry.py imports logger.py, errors.py has no imports)
- `_logger = _logger.patch(...)` reassigns module global — `global _logger` added to `configure_logging()` so `get_logger()` uses patched version
- File handler format updated to include `run={extra[run_id]:8}` — patcher ensures no KeyError

## Deviations from Plan
None — plan executed exactly as written.

## Issues Encountered
- Submodule structure: `Analista de Investimentos/` is a git submodule inside OBSIDIAN repo — committed inside the submodule repo directly (sequential, no worktree isolation, consistent with `.continue-here.md` decision)

## Self-Check: PASSED

All must-haves verified:
- `pytest tests/test_retry.py -v` → 4/4 passed ✓
- `pytest tests/test_logger.py -v` → 3/3 passed ✓
- `pytest tests/test_consolidation.py -v` → 3/3 passed ✓
- `pytest tests/ -v` → 15/15 passed ✓
- `python -c "from src.main import app; print('OK')"` → OK ✓
- `python -c "from src.utils.errors import IngestionError; e = IngestionError('fn','api down'); assert e.cause == 'api down'"` → OK ✓
- `python -c "from src.utils.logger import bind_run_id; print('OK')"` → OK ✓

## Next Phase Readiness
- Phase 1 gap closure complete — all 3 verified gaps closed (FOUND-03, FOUND-04, CR-04)
- Foundation ready: retry infrastructure, structured logging, and clean module imports all in place
- Phase 2 (data layer) can safely import src.main and use IngestionError + bind_run_id

---
*Phase: 01-foundation-and-cleanup*
*Completed: 2026-05-10*
