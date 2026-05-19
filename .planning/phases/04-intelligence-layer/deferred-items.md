# Deferred Items — Phase 4 Intelligence Layer

## Out-of-Scope Issues Discovered During Plan 04-01

### 1. news_hunter/config.py — Hardcoded Telegram Token (FOUND-02 Regression)

**Discovered during:** Task 2 execution (full suite run)
**File:** `Analista de Investimentos/12_PYTHON/news_hunter/config.py`
**Issue:** The working-tree version of news_hunter/config.py has a hardcoded Telegram token
  (`TELEGRAM_TOKEN = '8283626758:AAEx-...'`) instead of loading from env vars.
  This causes `test_token_loaded_from_env` to fail because the monkeypatched env var is
  ignored — the config is just a literal assignment, not an os.getenv() call.
**Impact:** `tests/test_news_hunter_config.py::test_token_loaded_from_env` FAILS
**Root cause:** Pre-existing working-tree modification unrelated to Plan 04-01 changes.
  The committed version of news_hunter/config.py uses load_dotenv() correctly.
**Resolution:** Restore news_hunter/config.py to its committed state or re-apply FOUND-02 fix.
  This should be addressed before merging the intelligence-layer branch.
**Priority:** Security (hardcoded credential exposure) — HIGH
