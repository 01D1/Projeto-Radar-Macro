# Phase 1: Foundation & Cleanup - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the codebase safe to build on: single canonical source (`src/`), all credentials removed from source code and loaded from `.env`, every external API call in `src/` wrapped with retry + exponential backoff, and structured logging with run ID injection deployed across `src/`. Downstream phases can build without hitting credential, import, or crash-on-failure landmines.

</domain>

<decisions>
## Implementation Decisions

### pipeline banco completo/ Disposition
- **D-01:** Freeze `pipeline banco completo/` in place — add a `DEPRECATED.md` notice, stop new development. Do NOT archive or delete it: it still runs in production generating Excel valuation outputs.
- **D-02:** Fix the stale Windows Task Scheduler entry (currently pointing to `C:\Users\55819\Downloads\...`) to the correct vault path as part of Plan 1. Verify it points to the active `pipeline banco completo/scheduler.py`.
- **D-03:** Migrate `pipeline banco completo/` credentials to `.env` along with `src/` and `news_hunter/` — all three sub-systems read from the same `.env` file. Do NOT modify any other `pipeline banco completo/` logic.

### Logging Framework
- **D-04:** Keep `loguru` — do NOT migrate to `structlog`. The roadmap's "structlog" requirement is satisfied by loguru's structured JSON output capability. `get_logger()` in `src/utils/logger.py` is the canonical logging entry point for `src/`.
- **D-05:** Run ID injection via `contextvars` + `loguru.contextualize()`: bind `run_id` at scheduler job start; all downstream log calls in that execution context automatically include the run ID. Zero changes to existing log call sites.
- **D-06:** Log rotation: 7-day retention in `logs/`. Configure via loguru's `rotation="1 day"` + `retention="7 days"`.
- **D-07:** `pipeline banco completo/` keeps its existing stdlib `logging` as-is — frozen, do not modify.

### news_hunter/ Credentials Scope
- **D-08:** Audit ALL `news_hunter/` files for hardcoded values (not just `config.py`) — migrate every hardcoded token, path, and key to `.env`. The live Telegram token at `news_hunter/config.py:60–61` is the known blocker; treat it as the minimum but scan the full directory.
- **D-09:** All three sub-systems (`src/`, `news_hunter/`, `pipeline banco completo/`) share the same `.env` file. No per-subsystem env files.
- **D-10:** `news_hunter/main.py` gets a startup guard: fail loudly if `TELEGRAM_ATIVO=True` but `TELEGRAM_BOT_TOKEN` is unset in `.env`. Consistent with the `src/main.py` startup guard.
- **D-11:** No scheduler integration of `news_hunter/` into `src/` in Phase 1 — that belongs in Phase 2. Phase 1 only fixes credentials and adds the startup guard.

### Retry Infrastructure
- **D-12:** Extend the existing `src/utils/retry.py` decorator — do NOT migrate to `tenacity`. The existing `@retry` interface is already in use across `src/`; extend it with exponential backoff + jitter rather than swapping the library.
- **D-13:** Retry behavior: 3 attempts, exponential backoff (2s → 4s → 8s), with jitter. Applied to all external API calls in `src/`: CVM, BCB, yfinance, Anthropic, Telegram.
- **D-14:** After all retry attempts exhaust: raise `IngestionError` with a structured log entry (module name, source, last known timestamp). No silent fallback to hardcoded data — the Phase 1 success criterion explicitly requires surfacing permanent failures.
- **D-15:** Retry decorator applied to `src/` only. `pipeline banco completo/` is frozen — its existing retry-adjacent workarounds stay as-is.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements
- `.planning/REQUIREMENTS.md` — FOUND-01 through FOUND-04 are the acceptance requirements for this phase
- `.planning/ROADMAP.md` §Phase 1 — success criteria and the 3 locked plans (consolidation, credentials, retry/logging)
- `.planning/PROJECT.md` — constraints (Python-only, reuse existing logic, .env for all config, no overengineering)

### Codebase State
- `.planning/codebase/STRUCTURE.md` — full directory layout, entry points, where to add new code
- `.planning/codebase/CONCERNS.md` — security issues (hardcoded token at `news_hunter/config.py:60–61`), known bugs, tech debt list
- `.planning/codebase/CONVENTIONS.md` — logging patterns, import organization, error handling conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/utils/retry.py` — existing `@retry(attempts, delay, backoff, exceptions)` decorator: extend with jitter support, do not replace
- `src/utils/logger.py` — loguru wrapper with `get_logger(__name__)` and `configure_logging()`: add `contextvars`-based run ID binding here
- `config/settings.py` — Pydantic-Settings singleton (`settings = Settings()`): add `model_post_init` startup validation for required keys when `ENV=production`

### Established Patterns
- Module-level logger always `log = get_logger(__name__)` — never `logger`
- Log message format: `f"[{ticker}] message"` with dash before error detail: `f"[{ticker}] falha: {exc}"`
- `@retry` applied as decorator with specific `exceptions` tuple — already in use in `src/ingestion/cvm_downloader.py` and `src/delivery/telegram_bot.py`
- Deferred imports inside `__init__` to avoid circular dependencies — keep this pattern

### Integration Points
- `src/scheduler.py` — job functions are where `run_id` is generated and bound via `loguru.contextualize()`
- `src/main.py` — startup validation guard goes here (check required keys before any pipeline work)
- `news_hunter/main.py` — startup guard also needed here for TELEGRAM credentials
- `src/processing/pipeline.py:37–44` — `sys.path` manipulation that needs to be removed (normalize imports to `src.` prefix instead)

### Known Hardcoded Credential Locations
- `news_hunter/config.py:60–61` — live Telegram bot token + chat ID as string literals (security blocker)
- `config/settings.py` — `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `SUPABASE_KEY` are optional empty strings (no startup validation)
- `pipeline banco completo/config/settings.py` — check for hardcoded values, migrate to shared `.env`

</code_context>

<specifics>
## Specific Ideas

- The `.env` file unification means a single `.env` at the `12_PYTHON/` root covers `src/`, `news_hunter/`, and `pipeline banco completo/`. Each sub-system loads it via `python-dotenv` or `pydantic-settings` pointing to the same path.
- The current env file is named `env` (no dot). Phase 1 renames it to `.env` and updates all loaders accordingly. Add `.env` to `.gitignore` if not already present.
- The `src/processing/pipeline.py` `sys.path` manipulation block (lines 37–44) should be removed and all imports normalized to use `src.` prefix — this is part of the "fix all import paths" task in Plan 1.
- Windows Task Scheduler fix: update the scheduled task to point to `C:\Users\55819\OneDrive - EPEJUD\DIEGO\OBSIDIAN\Analista de Investimentos\12_PYTHON\pipeline banco completo\scheduler.py`.

</specifics>

<deferred>
## Deferred Ideas

- **news_hunter/ scheduler integration** — wiring `news_hunter` into `src/scheduler.py` to replace the `job_news_fetcher` stub belongs in Phase 2 (Reliable Data Ingestion).
- **tenacity migration** — replacing `src/utils/retry.py` with `tenacity` is a valid future cleanup. Deferred because the existing decorator is functional and migration is scope creep for Phase 1.
- **structlog migration** — formally adopting `structlog` instead of loguru deferred. Current loguru + contextvars satisfies the Phase 1 structured logging requirement.
- **pipeline banco completo/ full archival** — move `pipeline banco completo/` to `_ARQUIVO_*/` when Phase 5 delivers the Streamlit dashboard + PDF reports as replacements.

</deferred>

---

*Phase: 1-Foundation & Cleanup*
*Context gathered: 2026-05-06*
