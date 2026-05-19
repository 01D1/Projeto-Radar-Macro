---
phase: 01-foundation-and-cleanup
plan: "02"
subsystem: infra
tags: [python, dotenv, pydantic-settings, credentials, security, gitignore, telegram, startup-guard]

# Dependency graph
requires:
  - phase: 01-foundation-and-cleanup
    plan: "01"
    provides: "Working Windows venv, 5 test stub files (including test_settings.py and test_news_hunter_config.py in RED state)"
provides:
  - "Zero hardcoded credential values in any Python source file under 12_PYTHON/"
  - "Shared .env file at 12_PYTHON/.env (renamed from env); both env and .env patterns in .gitignore"
  - "news_hunter/config.py loads from explicit dotenv_path pointing to shared 12_PYTHON/.env"
  - "config/settings.py REQUIRED_IN_PRODUCTION constant + model_post_init startup validation"
  - "src/main.py startup guard: logs key names and exits 1 if production + missing required keys"
  - "news_hunter/main.py startup guard: exits 1 if TELEGRAM_ATIVO=True but TELEGRAM_BOT_TOKEN unset"
  - "pipeline banco completo/config/settings.py wired to load from shared 12_PYTHON/.env"
  - "test_settings.py 3/3 green (startup guard dev/prod tests)"
  - "test_news_hunter_config.py 2/2 green (no hardcoded tokens, env var loaded correctly)"
affects: [01-03, 02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env') for explicit path in standalone modules"
    - "REQUIRED_IN_PRODUCTION = [...] module-level constant + model_post_init validation in pydantic-settings"
    - "IsolatedSettings subclass pattern in tests — uses tmp_path .env to avoid real .env interference"
    - "patch('dotenv.load_dotenv') in test helpers to isolate env var loading from file system"

key-files:
  created:
    - "Analista de Investimentos/12_PYTHON/.env"
  modified:
    - "Analista de Investimentos/.gitignore"
    - "Analista de Investimentos/12_PYTHON/news_hunter/config.py"
    - "Analista de Investimentos/12_PYTHON/config/settings.py"
    - "Analista de Investimentos/12_PYTHON/src/main.py"
    - "Analista de Investimentos/12_PYTHON/news_hunter/main.py"
    - "Analista de Investimentos/12_PYTHON/pipeline banco completo/config/settings.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_settings.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_news_hunter_config.py"

key-decisions:
  - "Updated test_settings.py to use IsolatedSettings subclass with tmp_path — avoids env_ignore_empty=True interference from real .env file during test"
  - "Updated test_news_hunter_config.py helper to patch dotenv.load_dotenv — prevents .env loading during unit tests that test empty fallback behavior"
  - "Used git rm --cached to untrack env file from git index before renaming (file was previously committed)"
  - "Added load_dotenv with explicit dotenv_path to pipeline banco completo/config/settings.py for D-03 compliance"

patterns-established:
  - "Explicit dotenv_path pattern: load_dotenv(dotenv_path=Path(__file__).parent.parent / '.env') for any standalone sub-system module"
  - "IsolatedSettings test pattern: subclass pydantic-settings BaseSettings with tmp_path env_file for env-file-dependent tests"
  - "patch('dotenv.load_dotenv') in test helpers when the module under test loads .env at import time"

requirements-completed:
  - FOUND-02

# Metrics
duration: 60min
completed: "2026-05-10"
---

# Phase 01 Plan 02: Credential Migration Summary

**Hardcoded Telegram token removed from news_hunter/config.py, env renamed to .env with gitignore protection, and startup validation guards wired in config/settings.py, src/main.py, and news_hunter/main.py — 5/5 credential tests green**

## Performance

- **Duration:** ~60 min
- **Started:** 2026-05-10T19:00:00Z
- **Completed:** 2026-05-10T20:00:00Z
- **Tasks:** 2
- **Files modified:** 8 (+ 1 created: .env)

## Accomplishments

- Live Telegram token at news_hunter/config.py:60-61 removed — replaced with empty string fallback (P3 security blocker resolved)
- `env` file renamed to `.env`; `env` (no dot) and `.env` patterns both added to .gitignore; `env` untracked from git index (`git rm --cached`)
- `config/settings.py` extended with `REQUIRED_IN_PRODUCTION` constant and `model_post_init` startup validation for production mode
- `src/main.py` startup guard added: logs missing key names (never values) and calls `sys.exit(1)` before pipeline work executes
- `news_hunter/main.py` startup guard added: exits 1 if `TELEGRAM_ATIVO=True` but `TELEGRAM_BOT_TOKEN` is unset
- `pipeline banco completo/config/settings.py` now loads from shared `12_PYTHON/.env` via `load_dotenv(dotenv_path=...)`
- 5/5 tests green: `test_settings.py` (3) + `test_news_hunter_config.py` (2)

## Task Commits

1. **Task 1: Secure .env file, update .gitignore, fix news_hunter/config.py tokens** - `7fdcf5e` (feat)
2. **Task 2: Add startup validation to settings.py and src/main.py; wire pipeline to .env** - `21e8c01` (feat)

**Plan metadata:** (pending docs commit)

## Files Created/Modified

- `Analista de Investimentos/.gitignore` - Added `env` (no dot) to prevent credential file from being committed
- `Analista de Investimentos/12_PYTHON/.env` - Created from renamed `env` file; contains ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
- `Analista de Investimentos/12_PYTHON/news_hunter/config.py` - Fixed load_dotenv path (explicit dotenv_path); removed hardcoded token fallbacks → empty strings
- `Analista de Investimentos/12_PYTHON/config/settings.py` - Added REQUIRED_IN_PRODUCTION constant and model_post_init startup validation for production mode
- `Analista de Investimentos/12_PYTHON/src/main.py` - Added startup guard after logger init; logs key names (never values), exits 1 on missing production keys
- `Analista de Investimentos/12_PYTHON/news_hunter/main.py` - Added startup guard: fails loudly if TELEGRAM_ATIVO=True but TELEGRAM_TOKEN unset
- `Analista de Investimentos/12_PYTHON/pipeline banco completo/config/settings.py` - Added load_dotenv with explicit path to 12_PYTHON/.env (D-03)
- `Analista de Investimentos/12_PYTHON/tests/test_settings.py` - Updated to use IsolatedSettings subclass with tmp_path to avoid env_ignore_empty=True interference
- `Analista de Investimentos/12_PYTHON/tests/test_news_hunter_config.py` - Updated helper to patch dotenv.load_dotenv during test execution

## Decisions Made

- **IsolatedSettings test pattern** — The existing test stubs used `monkeypatch.setenv("ANTHROPIC_API_KEY", "")` but `SettingsConfigDict(env_ignore_empty=True)` caused pydantic-settings to ignore empty env vars and load from the real `.env`. Solution: create an `IsolatedSettings` subclass in each test pointing to a `tmp_path/.env` file with only the keys needed for that specific test.

- **Patch dotenv.load_dotenv in news_hunter tests** — When `news_hunter/config.py` is loaded via `importlib.util.spec_from_file_location`, the `load_dotenv()` call inside the `try/except` block runs before `monkeypatch.delenv` takes effect. Solution: `patch("dotenv.load_dotenv")` to no-op during test module loading.

- **git rm --cached for env file** — The `env` file was already committed to the git repository (confirmed via `git ls-files`). `git check-ignore` returns exit 1 for tracked files even if a gitignore rule matches them. Used `git rm --cached 12_PYTHON/env` to remove from tracking; the file was then renamed to `.env` and the old file deleted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_settings.py test helper incompatible with env_ignore_empty=True**
- **Found during:** Task 2 (running test_startup_guard_production_missing_keys)
- **Issue:** `monkeypatch.setenv("ANTHROPIC_API_KEY", "")` sets empty string, but `env_ignore_empty=True` causes pydantic-settings to ignore it and load the actual value from `12_PYTHON/.env`. The startup guard never triggered.
- **Fix:** Rewrote test_settings.py to use an `IsolatedSettings` subclass that overrides `model_config.env_file` to point to a `tmp_path/.env` containing only the keys needed for each test case.
- **Files modified:** `Analista de Investimentos/12_PYTHON/tests/test_settings.py`
- **Verification:** `pytest tests/test_settings.py -v` → 3/3 pass
- **Committed in:** `21e8c01` (Task 2 commit)

**2. [Rule 1 - Bug] test_news_hunter_config.py fails because load_dotenv re-populates deleted env vars**
- **Found during:** Task 1 (running test_no_hardcoded_telegram_token)
- **Issue:** `monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)` deletes the env var, but when `config.py` is loaded via `importlib`, `load_dotenv()` runs and re-sets `TELEGRAM_CHAT_ID=440136219` from `.env`. Test asserts empty string but gets the real value.
- **Fix:** Added `with patch("dotenv.load_dotenv"):` in the test helper `_load_news_hunter_config` to prevent `.env` loading during test module execution.
- **Files modified:** `Analista de Investimentos/12_PYTHON/tests/test_news_hunter_config.py`
- **Verification:** `pytest tests/test_news_hunter_config.py -v` → 2/2 pass
- **Committed in:** `7fdcf5e` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - Bug — test isolation failures caused by env_ignore_empty and load_dotenv ordering)
**Impact on plan:** Both fixes were necessary to make the tests correctly validate the credential removal. No scope creep — all changes are within test files for the same behavior being tested.

## Issues Encountered

- `env` file was tracked by git, so `git check-ignore` returned exit 1 even after updating `.gitignore`. Had to use `git rm --cached 12_PYTHON/env` to remove from index before the gitignore rule took effect.
- `del` command via `cmd.exe /c` did not work in the bash environment (working directory reset). Used Python's `os.remove()` to delete the original `env` file after creating `.env`.
- `pipeline banco completo` has no `load_dotenv` anywhere — alerts.py uses `os.getenv` but env vars were only populated from OS environment. Added `load_dotenv` to `pipeline banco completo/config/settings.py` to ensure `.env` is loaded at pipeline startup.

## Known Stubs

None — all tests that this plan was responsible for turning GREEN are now passing.

Test stubs still in RED state (waiting for plan 01-03):
- `tests/test_retry.py` — waiting for retry.py extension with jitter + IngestionError
- `tests/test_logger.py` — waiting for logger.py extension with bind_run_id()
- `tests/test_consolidation.py` — already GREEN (import assertions pass)

## Threat Flags

No new threat surface introduced. This plan only removes threat surface (hardcoded credentials eliminated, gitignore protection added, startup guards prevent silent credential failures).

Mitigations delivered for threats identified in plan's threat_model:
- T-02-01 MITIGATED: Telegram token removed from news_hunter/config.py
- T-02-02 MITIGATED: Both `env` and `.env` now in .gitignore; `env` untracked from git index
- T-02-03 MITIGATED: Startup guards log key names only (e.g., `["anthropic_api_key"]`), never values
- T-02-04 MITIGATED: model_post_init + src/main.py guard both call sys.exit(1) before pipeline work
- T-02-05 ACCEPTED: pipeline banco completo confirmed clean (no API tokens); load_dotenv path fix added per D-03

## Next Phase Readiness

- Plan 01-03 (retry/logging infrastructure) can proceed — test_retry.py and test_logger.py stubs ready
- FOUND-02 requirement fully satisfied: all three sub-systems load from shared `12_PYTHON/.env`
- Production startup failures are now loud (sys.exit(1)) not silent

## Self-Check: PASSED

Files verified:
- `Analista de Investimentos/12_PYTHON/.env` - EXISTS (created from renamed env)
- `Analista de Investimentos/12_PYTHON/news_hunter/config.py` - MODIFIED (no hardcoded tokens; dotenv_path explicit)
- `Analista de Investimentos/12_PYTHON/config/settings.py` - MODIFIED (REQUIRED_IN_PRODUCTION + model_post_init guard)
- `Analista de Investimentos/12_PYTHON/src/main.py` - MODIFIED (startup guard added)
- `Analista de Investimentos/12_PYTHON/news_hunter/main.py` - MODIFIED (startup guard for TELEGRAM_ATIVO)
- `Analista de Investimentos/12_PYTHON/pipeline banco completo/config/settings.py` - MODIFIED (load_dotenv added)
- `Analista de Investimentos/12_PYTHON/tests/test_settings.py` - MODIFIED (IsolatedSettings pattern)
- `Analista de Investimentos/12_PYTHON/tests/test_news_hunter_config.py` - MODIFIED (patch load_dotenv)

Commits verified:
- 7fdcf5e - Task 1 commit (gitignore + env rename + news_hunter/config.py)
- 21e8c01 - Task 2 commit (startup guards + test fixes)

Acceptance criteria:
- `git check-ignore -v "12_PYTHON/env"` → PASS (.gitignore:50:env 12_PYTHON/env)
- `git check-ignore -v "12_PYTHON/.env"` → PASS (.gitignore:52:*.env 12_PYTHON/.env)
- `grep -c "8283626758" news_hunter/config.py` → 0 (no hardcoded token)
- `grep -c "dotenv_path=Path" news_hunter/config.py` → 1 (explicit path)
- `grep -c "REQUIRED_IN_PRODUCTION" config/settings.py` → 1
- `grep -c "sys.exit" config/settings.py` → 1 (startup validation)
- `grep -c "TELEGRAM_ATIVO" news_hunter/main.py` → 1 (startup guard)
- `pytest tests/test_settings.py tests/test_news_hunter_config.py` → 5/5 PASSED

---
*Phase: 01-foundation-and-cleanup*
*Completed: 2026-05-10*
