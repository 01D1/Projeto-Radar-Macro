# Phase 1: Foundation & Cleanup - Research

**Researched:** 2026-05-06
**Domain:** Python infrastructure — credentials security, codebase consolidation, retry/logging
**Confidence:** HIGH (all findings verified by direct codebase inspection)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**pipeline banco completo/ Disposition**
- D-01: Freeze `pipeline banco completo/` in place — add a `DEPRECATED.md` notice, stop new development. Do NOT archive or delete it: it still runs in production generating Excel valuation outputs.
- D-02: Fix the stale Windows Task Scheduler entry (currently pointing to `C:\Users\55819\Downloads\...`) to the correct vault path as part of Plan 1. Verify it points to the active `pipeline banco completo/scheduler.py`.
- D-03: Migrate `pipeline banco completo/` credentials to `.env` along with `src/` and `news_hunter/` — all three sub-systems read from the same `.env` file. Do NOT modify any other `pipeline banco completo/` logic.

**Logging Framework**
- D-04: Keep `loguru` — do NOT migrate to `structlog`. The roadmap's "structlog" requirement is satisfied by loguru's structured JSON output capability. `get_logger()` in `src/utils/logger.py` is the canonical logging entry point for `src/`.
- D-05: Run ID injection via `contextvars` + `loguru.contextualize()`: bind `run_id` at scheduler job start; all downstream log calls in that execution context automatically include the run ID. Zero changes to existing log call sites.
- D-06: Log rotation: 7-day retention in `logs/`. Configure via loguru's `rotation="1 day"` + `retention="7 days"`.
- D-07: `pipeline banco completo/` keeps its existing stdlib `logging` as-is — frozen, do not modify.

**news_hunter/ Credentials Scope**
- D-08: Audit ALL `news_hunter/` files for hardcoded values (not just `config.py`) — migrate every hardcoded token, path, and key to `.env`. The live Telegram token at `news_hunter/config.py:60–61` is the known blocker; treat it as the minimum but scan the full directory.
- D-09: All three sub-systems (`src/`, `news_hunter/`, `pipeline banco completo/`) share the same `.env` file. No per-subsystem env files.
- D-10: `news_hunter/main.py` gets a startup guard: fail loudly if `TELEGRAM_ATIVO=True` but `TELEGRAM_BOT_TOKEN` is unset in `.env`. Consistent with the `src/main.py` startup guard.
- D-11: No scheduler integration of `news_hunter/` into `src/` in Phase 1 — that belongs in Phase 2. Phase 1 only fixes credentials and adds the startup guard.

**Retry Infrastructure**
- D-12: Extend the existing `src/utils/retry.py` decorator — do NOT migrate to `tenacity`. The existing `@retry` interface is already in use across `src/`; extend it with exponential backoff + jitter rather than swapping the library.
- D-13: Retry behavior: 3 attempts, exponential backoff (2s → 4s → 8s), with jitter. Applied to all external API calls in `src/`: CVM, BCB, yfinance, Anthropic, Telegram.
- D-14: After all retry attempts exhaust: raise `IngestionError` with a structured log entry (module name, source, last known timestamp). No silent fallback to hardcoded data.
- D-15: Retry decorator applied to `src/` only. `pipeline banco completo/` is frozen.

### Claude's Discretion
(None specified — all major decisions locked)

### Deferred Ideas (OUT OF SCOPE)
- news_hunter/ scheduler integration into src/scheduler.py (Phase 2)
- tenacity migration
- structlog migration
- pipeline banco completo/ full archival (Phase 5)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOUND-01 | Duplicate codebases archived — single canonical source under `src/`; `_ARQUIVO_Analista_vs_code/` and `Meu segundo Cerébro/12_PYTHON/` removed from active use | Directory audit completed; 4 divergent copies confirmed; active copy identified |
| FOUND-02 | All credentials and paths migrated from source code to `.env` file; python-dotenv + pydantic-settings loads config on startup; `.env` added to `.gitignore` | Live token confirmed in news_hunter/config.py:60–61; env file structure verified; gitignore audit done |
| FOUND-03 | Retry logic applied to all external API calls (CVM, BCB, yfinance, Anthropic, Telegram) using exponential backoff; no uncaught API failures crash the pipeline | @retry usage map built; 5 call sites without decorator identified; IngestionError pattern defined |
| FOUND-04 | Structured logging via loguru across all modules; each log entry includes module name, ticker (when relevant), and ingestion run ID; logs persisted to `logs/` with daily rotation | logger.py code verified; stdlib logging in 7 files identified; contextvars pattern confirmed available |
</phase_requirements>

---

## Summary

Phase 1 is a pure infrastructure hardening phase with no new features. The codebase is functional but has four specific landmines that block safe construction of subsequent phases: hardcoded live credentials, four divergent code copies, partial retry coverage, and stdlib logging mixed into `src/` modules that should use loguru.

All four requirements have clear, bounded scopes. The research confirms the locked decisions in CONTEXT.md are correctly calibrated against the actual codebase state. The existing `src/utils/retry.py` decorator is competent but missing jitter — extension is straightforward. The existing `src/utils/logger.py` loguru wrapper is well-structured — adding `contextvars`-based run ID binding is a small, localized change. The credentials problem is fully scoped: one known live token in `news_hunter/config.py:60–61`, one env file rename (`env` → `.env`), and a `pipeline banco completo/config/settings.py` that has no hardcoded API tokens (only local path defaults).

**Primary recommendation:** Execute in three clean plans: (1) codebase consolidation + Task Scheduler fix, (2) credentials migration, (3) retry/logging infrastructure. Plans 2 and 3 have no dependencies on Plan 1 and can be sequenced independently.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Credential loading | Config layer (`config/settings.py`) | `news_hunter/config.py` (parallel sub-system) | pydantic-settings owns config for `src/`; news_hunter has its own loader |
| Retry/backoff | `src/utils/retry.py` (cross-cutting utility) | — | Decorator applied at external call sites; utility layer owns the logic |
| Structured logging | `src/utils/logger.py` (cross-cutting utility) | `src/scheduler.py` (run_id injection point) | Logger config lives in utils; run_id binding happens in scheduler job wrappers |
| Codebase boundary | `Analista de Investimentos/12_PYTHON/` root | — | Single canonical root; duplicates are filesystem artifacts to be removed |
| Error surfacing | `IngestionError` (new, in `src/utils/`) | Calling module's log context | Exception carries module/source/timestamp; upstream job wrapper catches and logs |

---

## Standard Stack

### Core (already installed, no changes needed)

| Library | Verified Version | Purpose | Status |
|---------|-----------------|---------|--------|
| loguru | `>=0.7.0` (pyproject.toml) [VERIFIED: pyproject.toml] | Structured logging with contextualize() | Already in use in `src/utils/logger.py` |
| pydantic-settings | `>=2.2.0` [VERIFIED: pyproject.toml] | Settings singleton loading `.env` | Already in use in `config/settings.py` |
| python-dotenv | `1.2.2` [VERIFIED: pip3 list] | `.env` file loading | Already imported in `news_hunter/config.py` (optional import) |
| requests | `2.33.1` [VERIFIED: pip3 list] | HTTP calls for CVM/BCB/Telegram | Already in use |
| yfinance | `1.2.2` [VERIFIED: pip3 list] | B3 price data | Already in use in `src/ingestion/b3_scraper.py` |

### Not Installed on Current Python (blocker)

| Library | Required By | Action |
|---------|------------|--------|
| loguru | `src/utils/logger.py` | Install: `pip install loguru>=0.7.0` |
| pydantic-settings | `config/settings.py` | Install: `pip install pydantic-settings>=2.2.0` |
| anthropic | `src/content/llm_client.py` | Install: `pip install anthropic>=0.40.0` |
| apscheduler | `src/scheduler.py` | Install: `pip install apscheduler>=3.10.0` |

> [VERIFIED: pip3 list] — loguru, pydantic-settings, anthropic, apscheduler are NOT in the Windows Python 3.10 site-packages. The project's `pyproject.toml` defines `requires-python = ">=3.11"` but the system has Python 3.10.11. The `.venv` directory exists but is a macOS artifact (pyvenv.cfg shows `home = /Library/Developer/CommandLineTools/usr/bin`, Python 3.9.6) and does not work on Windows. Phase 1 must include a Wave 0 task to create a working Windows venv.

---

## Architecture Patterns

### System Architecture Diagram

```
[.env file]
    │
    ▼
[config/settings.py]  ←── pydantic-settings loads all keys at startup
    │                        validates required keys in model_post_init (NEW)
    │
    ├──► [src/main.py]  ←── startup guard: fail if production + missing keys (NEW)
    │         │
    │         ▼
    │    [src/scheduler.py]  ←── job_*() functions: bind run_id via loguru.contextualize() (NEW)
    │         │
    │         ▼
    │    [src/ingestion/]  ←── @retry on _fetch(), _download()  (EXISTING + extend)
    │    [src/content/]    ←── @retry on LLMClient._call_with_retry()  (EXISTING, standardize)
    │    [src/delivery/]   ←── @retry on TelegramBot._post()  (EXISTING, standardize)
    │         │
    │         ▼
    │    [IngestionError]  ←── raised on retry exhaustion (NEW, in src/utils/errors.py)
    │
    └──► [src/utils/logger.py]  ←── configure_logging(), get_logger(), run_id context (EXTEND)
              │
              ▼
         [logs/intelligence_{date}.log]  ←── rotation="1 day", retention="7 days" (CHANGE from 30)


[news_hunter/config.py]
    │   reads TELEGRAM_TOKEN from os.getenv() with empty-string fallback (CHANGE)
    │
    └──► [news_hunter/main.py]  ←── startup guard: fail if TELEGRAM_ATIVO + no token (NEW)


[pipeline banco completo/config/settings.py]  ←── FROZEN; add DEPRECATED.md only
    └──► [DEPRECATED.md]  ←── notice file added (NEW)
```

### Recommended Project Structure (no changes — existing is correct)

```
12_PYTHON/
├── .env                    # RENAME from 'env' (no dot)
├── .env.example            # already exists
├── config/settings.py      # extend with startup validation
├── src/
│   ├── main.py             # add startup guard
│   ├── scheduler.py        # add run_id binding
│   └── utils/
│       ├── logger.py       # extend: add bind_run_id() helper
│       ├── retry.py        # extend: add jitter param
│       └── errors.py       # NEW: IngestionError
├── news_hunter/
│   └── config.py           # remove hardcoded token fallbacks
└── pipeline banco completo/
    └── DEPRECATED.md       # NEW: freeze notice
```

### Pattern 1: loguru contextvars Run ID Binding

**What:** Each scheduler job generates a UUID run_id and binds it to the loguru context. All log calls in that execution context (same thread/async context) automatically include `run_id` without any changes to existing log call sites.

**When to use:** At the start of each `job_*()` function in `src/scheduler.py`.

**Example:**
```python
# Source: loguru docs — contextualize() [CITED: loguru.readthedocs.io]
import uuid
from loguru import logger

def job_pipeline():
    run_id = str(uuid.uuid4())[:8]
    with logger.contextualize(run_id=run_id):
        # All log.info/warning/error calls inside here include run_id automatically
        _run_pipeline_impl()
```

To surface `run_id` in log output, update the loguru format string in `configure_logging()`:
```python
# Add {extra[run_id]} to format — defaults to empty string when not set
format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name} | run={extra[run_id]:8} — {message}"
```

### Pattern 2: Retry Decorator Extension (add jitter)

**What:** Extend `src/utils/retry.py` to add a `jitter` parameter that adds random noise to each sleep interval. Prevents thundering herd when multiple tickers retry simultaneously.

**When to use:** All external API calls — CVM, yfinance, Anthropic, Telegram.

**Example:**
```python
# Source: src/utils/retry.py [VERIFIED: direct read]
import random
import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

F = TypeVar("F", bound=Callable)


def retry(
    attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    jitter: float = 0.5,  # NEW: max random seconds added to each wait
):
    """Decorator de retry com backoff exponencial e jitter."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            wait = delay
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == attempts:
                        from src.utils.errors import IngestionError
                        log.error(f"{func.__name__} falhou após {attempts} tentativas: {exc}")
                        raise IngestionError(
                            source=func.__module__,
                            func=func.__name__,
                            cause=str(exc),
                        ) from exc
                    actual_wait = wait + random.uniform(0, jitter)
                    log.warning(
                        f"{func.__name__} tentativa {attempt}/{attempts} falhou: {exc}. "
                        f"Aguardando {actual_wait:.1f}s"
                    )
                    time.sleep(actual_wait)
                    wait *= backoff
        return wrapper  # type: ignore
    return decorator
```

### Pattern 3: IngestionError Custom Exception

**What:** New exception class in `src/utils/errors.py`. Carries structured context: source module, function name, cause.

**When to use:** Raised by `retry` decorator on final attempt exhaustion. Caught in scheduler job wrappers.

**Example:**
```python
# Source: CONTEXT.md D-14 [VERIFIED: 01-CONTEXT.md]
from dataclasses import dataclass
from datetime import datetime


@dataclass
class IngestionError(Exception):
    """Raised when a retried external call permanently fails."""
    source: str
    func: str
    cause: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()
        super().__init__(f"[{self.source}] {self.func} falhou: {self.cause}")
```

### Pattern 4: Startup Validation Guard

**What:** `config/settings.py` `model_post_init` raises `SystemExit` if `ENV=production` and required keys are empty strings.

**When to use:** Add to `Settings.model_post_init` — runs automatically on `settings = Settings()`.

**Example:**
```python
# Source: config/settings.py [VERIFIED: direct read]
REQUIRED_IN_PRODUCTION = ["anthropic_api_key", "telegram_bot_token", "telegram_chat_id"]

def model_post_init(self, __context) -> None:
    # Create directories (existing behavior)
    for path in (self.data_raw, self.data_processed, self.data_output, self.logs_dir):
        path.mkdir(parents=True, exist_ok=True)

    # NEW: Startup validation for production
    if self.env == "production":
        missing = [k for k in REQUIRED_IN_PRODUCTION if not getattr(self, k, "")]
        if missing:
            import sys
            print(f"[CONFIG] Variáveis obrigatórias ausentes no .env: {missing}")
            sys.exit(1)
```

### Anti-Patterns to Avoid

- **Changing news_hunter import structure**: `news_hunter/` is standalone and must remain runnable as `python news_hunter/main.py`. Do NOT change its `import config` pattern to `from config.settings import settings` — it would break standalone operation. Instead, keep its own `config.py` but remove hardcoded fallback values.
- **Renaming the `env` key in Settings**: `config/settings.py` already handles both `env` and `.env` filenames via `env_file=[ROOT / ".env", ROOT / "env"]`. Renaming the file to `.env` does not require code changes to the settings loader — it falls to the first match.
- **Adding @retry to non-external calls**: The decorator should only wrap HTTP/API calls — NOT file I/O, SQLite, or in-process computation. Misapplying it to file operations creates unexpected delays on permission errors.
- **Binding run_id outside scheduler**: Run ID should only be bound at the scheduler job boundary (`job_*()` functions). Binding it in individual module functions defeats the purpose — it would generate a new ID per function call.
- **Modifying pipeline banco completo/ logic**: D-01 and D-15 forbid this. Only `DEPRECATED.md` addition and `.env` migration (D-03) are permitted.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env file loading | Custom parser | `pydantic-settings` `SettingsConfigDict(env_file=...)` | Already configured in `config/settings.py` — zero new code |
| Log context propagation | Thread-local dict | `loguru.contextualize()` | Built-in context manager, propagates to all child calls |
| Exponential backoff | Custom sleep loop | Extend `src/utils/retry.py` | Already working — add jitter param only |
| Startup config validation | Manual key checks | `model_post_init` in `Settings` | Runs automatically at import time |

**Key insight:** All infrastructure primitives exist — this phase extends them, not replaces them.

---

## Runtime State Inventory

> This phase includes codebase restructuring and env file rename — runtime state audit required.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | No databases store subsystem names or paths as keys. SQLite DBs (`news_hunter/banco.db`, `pipeline banco completo/` SQLite) store news articles and run history — no path-keyed records | Code edit only (no data migration) |
| Live service config | Windows Task Scheduler: 1 task previously pointed to `C:\Users\55819\Downloads\pipeline_banco_completo\pipeline_banco\main.py` — confirmed stale from scheduler.log [VERIFIED: CONCERNS.md]. Current task destination unknown — must be verified and updated | Update task via `schtasks` to point to vault path |
| OS-registered state | Task Scheduler task for pipeline banco completo scheduler.py — exact current path requires verification via `schtasks /Query /FO LIST` | Re-register if pointing to stale path |
| Secrets/env vars | `env` file (no dot) at `12_PYTHON/env` — contains ANTHROPIC_API_KEY and TELEGRAM_BOT_TOKEN [VERIFIED: file read]. Will be renamed to `.env`. No code changes needed: `config/settings.py` already accepts both filenames | File rename only |
| Build artifacts | `.venv/` at OBSIDIAN root is a macOS artifact (Python 3.9, broken on Windows) [VERIFIED: pyvenv.cfg]. Must be recreated as Windows venv with Python 3.10/3.11 | Delete stale venv, create new: `python -m venv .venv && .venv/bin/pip install -e .` |

**Critical finding:** The existing `.venv` is non-functional on Windows. Any task that requires importing `src/` modules must first recreate the venv. This is a Wave 0 blocker.

---

## Common Pitfalls

### Pitfall 1: news_hunter/config.py token replacement breaks standalone mode

**What goes wrong:** If a developer replaces `os.getenv("TELEGRAM_TOKEN", "8283626758:...")` with `from config.settings import settings; settings.telegram_bot_token`, the `news_hunter/` module will fail to import when run from the `news_hunter/` directory — because `config.settings` is not on its Python path.

**Why it happens:** `news_hunter/` runs standalone via `python news_hunter/main.py` with its own `import config`. It has no `sys.path` manipulation to reach the parent `config/settings.py`.

**How to avoid:** Keep `os.getenv("TELEGRAM_TOKEN", "")` pattern — change only the fallback from the live token string to `""`. The `python-dotenv` `load_dotenv()` at the top of `news_hunter/config.py` already loads from the `.env` file.

**Warning signs:** If `TELEGRAM_TOKEN` resolves as empty string when the env file exists, the `load_dotenv()` call is pointing to the wrong path. Add `load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")` to ensure it finds the shared `.env` at `12_PYTHON/.env`.

### Pitfall 2: loguru format string breaks when run_id not bound

**What goes wrong:** If the log format string includes `{extra[run_id]}` but a log call happens outside a `logger.contextualize(run_id=...)` block (e.g., during startup, or in a module called directly via CLI), loguru raises `KeyError: 'run_id'`.

**Why it happens:** Loguru's `{extra[key]}` does not have a built-in default value mechanism.

**How to avoid:** Use `opt(lazy=True)` or add a `patch` function that sets a default:
```python
# In configure_logging() — add a patcher that defaults run_id to "-"
_logger = _logger.patch(lambda r: r["extra"].setdefault("run_id", "-"))
```

**Warning signs:** `KeyError` in log format after adding run_id to format string.

### Pitfall 3: `env` file not matched by gitignore — credentials committed

**What goes wrong:** The `.gitignore` at `Analista de Investimentos/` level lists `.env` and `*.env` — but the actual file is named `env` (no dot). The unmodified gitignore would allow `git add env` to succeed silently.

**Why it happens:** The file was named without the leading dot. After rename to `.env`, the existing gitignore already covers it. But during transition, if someone runs `git add .` before the rename, the old `env` file could be staged.

**How to avoid:** As part of Plan 2, add `env` (no dot, no wildcard) to the `.gitignore` before renaming the file. Verify `git check-ignore env` returns a match. [VERIFIED: env file is currently untracked but NOT in gitignore — confirmed by `git ls-files` returning empty for that path].

**Warning signs:** `git status` shows `env` as untracked with no `!` prefix.

### Pitfall 4: IngestionError raised inside @retry wraps existing exceptions incorrectly

**What goes wrong:** If `IngestionError` inherits from `Exception` and the caller's `except (requests.RequestException,)` clause does NOT catch `IngestionError`, the error surface changes — callers that expect `requests.RequestException` will see unhandled `IngestionError` instead.

**Why it happens:** After wrapping, the function no longer raises the original exception type — it raises `IngestionError`. Callers that catch specific exception types will miss it.

**How to avoid:** In `scheduler.py` job wrappers, catch `IngestionError` explicitly. The `_run_job()` wrapper already catches `Exception` broadly and logs the traceback — `IngestionError` will be caught there. For specific callers in `src/`, add `IngestionError` to the imports.

### Pitfall 5: LLMClient retry is custom (not using @retry decorator)

**What goes wrong:** `LLMClient._call_with_retry()` implements its own retry loop inline. D-13 says to apply `@retry` to "all external API calls in src/" — but naively removing the custom loop and adding `@retry` would lose Anthropic-specific behavior (rate limit 429, overload 529 handling).

**Why it happens:** The Anthropic SDK raises specific exception types (`RateLimitError`, `InternalServerError`, `APIStatusError`) that the generic `@retry` decorator needs to know about.

**How to avoid:** The resolution is NOT to wrap `_call_with_retry` with `@retry`. The existing custom loop already satisfies D-13's intent. The only change needed is to ensure it raises `IngestionError` on final failure instead of a bare `RuntimeError`. Update the final `raise RuntimeError(...)` to `raise IngestionError(source=..., func="generate", cause="...")`.

---

## Code Examples

Verified patterns from official sources and direct codebase inspection:

### Extend retry.py with jitter
```python
# Source: src/utils/retry.py [VERIFIED: direct read] — lines to add/change
import random

def retry(
    attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    jitter: float = 0.5,  # ADD this parameter
):
    # In the sleep line, change:
    # time.sleep(wait)
    # to:
    actual_wait = wait + random.uniform(0, jitter)
    time.sleep(actual_wait)
```

### Update configure_logging() for 7-day retention and run_id format
```python
# Source: src/utils/logger.py [VERIFIED: direct read] — changes to make
_logger.add(
    logs_dir / "intelligence_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name} | run={extra[run_id]:8} — {message}",
    rotation="1 day",       # unchanged
    retention="7 days",     # CHANGE: was "30 days"
    encoding="utf-8",
)

# Add patcher for default run_id (prevents KeyError outside contextualize blocks):
_logger = _logger.patch(lambda r: r["extra"].setdefault("run_id", "-"))
```

### Add bind_run_id helper to logger.py
```python
# Source: loguru docs — contextualize [CITED: loguru.readthedocs.io/contextualize]
import uuid
from contextlib import contextmanager

@contextmanager
def bind_run_id(prefix: str = ""):
    """Context manager: bind a short run_id to all log calls in scope."""
    run_id = (prefix + "-" if prefix else "") + str(uuid.uuid4())[:8]
    with _logger.contextualize(run_id=run_id):
        yield run_id
```

### Updated job wrapper in scheduler.py
```python
# Source: src/scheduler.py [VERIFIED: direct read] — pattern for each job_*() function
from src.utils.logger import bind_run_id

def job_pipeline() -> str:
    with bind_run_id("pipeline") as run_id:
        log.info(f"[scheduler] job_pipeline iniciado — run_id={run_id}")
        # ... existing job body unchanged
```

### Fix load_dotenv path in news_hunter/config.py
```python
# Source: news_hunter/config.py [VERIFIED: direct read] — lines 7-9
from pathlib import Path
from dotenv import load_dotenv

# Load from shared .env at 12_PYTHON/.env (one level up from news_hunter/)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

# THEN change token fallback from live string to empty string:
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")    # was: "8283626758:AAEx-..."
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "") # was: "-5236754554"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-run log files (`pipeline_YYYYMMDD_HHMMSS.log`) | Single rotating daily log | This phase | Eliminates 90+ file accumulation; 7-day auto-cleanup |
| Hardcoded token as `os.getenv()` fallback | Empty string fallback + startup guard | This phase | Security: token no longer in source; clear failure on misconfiguration |
| `env` (no dot) filename | `.env` (standard) | This phase | Matches `.env.example` naming; already covered by gitignore |
| Stdlib `logging` in 7 `src/` files | `loguru` via `get_logger()` | This phase | Consistent structured output; no split log streams |

**Deprecated/outdated:**
- `env` file name: rename to `.env`. The `config/settings.py` Settings class already reads both via `env_file=[ROOT / ".env", ROOT / "env"]` — no code change needed, just the file rename.
- `_ARQUIVO_Analista_vs_code/` and `Meu segundo Cerébro/12_PYTHON/`: archive as dead copies. The `Analista de Investimentos/.claude/12_PYTHON/` copy is also a stale snapshot and should be deleted (confirmed by CONCERNS.md).

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Windows Task Scheduler task for `pipeline banco completo/scheduler.py` is currently stale (pointing to Downloads) — needs re-registration to vault path | Runtime State Inventory | If it was already fixed, D-02 task is a no-op (harmless) |
| A2 | `news_hunter/crawler.py` and `news_hunter/agendador.py` do not contain additional hardcoded tokens beyond what's in `config.py` | FOUND-02 scope | Grep found 4 files in news_hunter/ matching token/hardcoded pattern; crawler.py is one of them — needs verification during implementation |
| A3 | `pipeline banco completo/config/settings.py` has no hardcoded API tokens — only path defaults and financial constants | FOUND-02 scope | Confirmed by direct read: no API keys or Telegram tokens visible. BCB URLs are public endpoints. [VERIFIED: direct read, HIGH confidence] |

> Note: A3 is VERIFIED HIGH confidence — included in Assumptions Log only because it was a stated research target.

---

## Open Questions

1. **Windows Task Scheduler actual current path**
   - What we know: Historical scheduler.log shows stale `Downloads` path; code was later updated to use `ROOT / "main.py"` (relative); CONCERNS.md flags this as unverified
   - What's unclear: Whether the Task Scheduler task was manually updated after code was moved to vault
   - Recommendation: Plan 1, Wave 1: run `schtasks /Query /FO LIST /TN "<task_name>"` to confirm current registration before writing the fix task

2. **`news_hunter/` additional hardcoded values in crawler.py**
   - What we know: Grep found `TELEGRAM_TOKEN` pattern in `crawler.py`
   - What's unclear: Whether it contains actual hardcoded values or just references config.TELEGRAM_TOKEN
   - Recommendation: Plan 2 must include a full read of `news_hunter/crawler.py` lines matching the token pattern before executing

3. **Working venv strategy for Phase 1 execution**
   - What we know: The existing `.venv` is a macOS 3.9 artifact that fails on Windows; system Python 3.10 lacks loguru, pydantic-settings, anthropic
   - What's unclear: Whether the executor will use a new venv or install into system Python
   - Recommendation: Wave 0 task should create a fresh `.venv` at OBSIDIAN root using Windows Python 3.10: `python -m venv .venv && .venv/Scripts/pip install -e "Analista de Investimentos/12_PYTHON/[dev]"` — or use `pyproject.toml`'s `hatchling` build system

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | All | ✓ | 3.10.11 (Windows) | — |
| loguru | `src/utils/logger.py` | ✗ | — | Install from requirements.txt |
| pydantic-settings | `config/settings.py` | ✗ | — | Install from requirements.txt |
| anthropic SDK | `src/content/llm_client.py` | ✗ | — | Install from requirements.txt |
| apscheduler | `src/scheduler.py` | ✗ | — | Install from requirements.txt |
| python-dotenv | `news_hunter/config.py` | ✓ | 1.2.2 | — |
| requests | `src/delivery/telegram_bot.py`, CVM | ✓ | 2.33.1 | — |
| yfinance | `src/ingestion/b3_scraper.py` | ✓ | 1.2.2 | — |
| schtasks CLI | Task Scheduler fix (D-02) | ✓ | Windows built-in | — |

**Missing dependencies with no fallback:**
- loguru, pydantic-settings, anthropic, apscheduler — required for `src/` to import at all. Must be installed in Wave 0 before any code changes are verified.

**Missing dependencies with fallback:**
- None.

**Blocker:** The existing `.venv` at OBSIDIAN root is non-functional (macOS Python 3.9 artifact). Wave 0 must recreate it with Windows Python 3.10 before any `src/` import can succeed.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (>= 7.4.0, listed in requirements.txt / pyproject.toml dev deps) |
| Config file | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` [VERIFIED] |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v --cov=src` |
| Tests directory | `tests/` (empty — no .py files currently) [VERIFIED: CONCERNS.md] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | Canonical path is only active code; duplicates not importable | Smoke (import) | `pytest tests/test_consolidation.py -x` | ❌ Wave 0 |
| FOUND-02 | Settings raises on missing required key in production mode | Unit | `pytest tests/test_settings.py::test_startup_guard -x` | ❌ Wave 0 |
| FOUND-02 | `news_hunter/config.py` token is empty string when env unset | Unit | `pytest tests/test_news_hunter_config.py::test_no_hardcoded_token -x` | ❌ Wave 0 |
| FOUND-03 | `@retry` applies exponential backoff with jitter on failure | Unit | `pytest tests/test_retry.py::test_backoff_jitter -x` | ❌ Wave 0 |
| FOUND-03 | Final retry exhaustion raises `IngestionError` | Unit | `pytest tests/test_retry.py::test_ingestion_error -x` | ❌ Wave 0 |
| FOUND-04 | `configure_logging()` sets 7-day retention | Unit | `pytest tests/test_logger.py::test_retention -x` | ❌ Wave 0 |
| FOUND-04 | `bind_run_id()` context manager injects run_id into log record | Unit | `pytest tests/test_logger.py::test_run_id_binding -x` | ❌ Wave 0 |
| FOUND-04 | Stdlib `logging` no longer imported in `src/` (except legacy files) | Static check | `ruff check src/ --select=ICN001` or grep assertion | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/ -x -q` (fast unit tests only, <10s)
- **Per wave merge:** `pytest tests/ -v --cov=src`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/__init__.py` — empty marker file
- [ ] `tests/test_settings.py` — covers FOUND-02 startup guard
- [ ] `tests/test_retry.py` — covers FOUND-03 backoff + IngestionError
- [ ] `tests/test_logger.py` — covers FOUND-04 retention + run_id binding
- [ ] `tests/test_consolidation.py` — covers FOUND-01 import path assertions
- [ ] `tests/test_news_hunter_config.py` — covers FOUND-02 news_hunter no-hardcoded-token
- [ ] Framework install: `pip install pytest pytest-cov` — required before any test runs
- [ ] Working `.venv` recreation — prerequisite for all above

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — single-user local tool |
| V3 Session Management | No | N/A — no session tokens |
| V4 Access Control | No | N/A — no multi-user |
| V5 Input Validation | Partial | Pydantic model validates all settings at startup |
| V6 Cryptography | No | API keys loaded from env, not stored/encrypted locally |
| V7 Error Handling | Yes | `IngestionError` pattern prevents silent credential exposure in error messages |
| V14 Configuration | Yes | No secrets in source; `.env` excluded from git; startup guard on production |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Hardcoded API token in source code | Information Disclosure | Remove fallback literal; empty string default; startup guard |
| `env` file committed to git | Information Disclosure | Add `env` (no dot) to gitignore; verify `git check-ignore env` |
| Credentials exposed in log output | Information Disclosure | Never log `settings.anthropic_api_key` or `settings.telegram_bot_token` — log only boolean presence |
| Retry loop exposes internal URLs in error logs | Information Disclosure | `IngestionError` message should log source module name, not full URL |

**Critical finding:** The live `env` file (VERIFIED: read directly) contains `ANTHROPIC_API_KEY=sk-ant-api03-...` and `TELEGRAM_BOT_TOKEN=8283626758:...` in plaintext. It is currently untracked by git (verified via `git ls-files`) but is NOT listed in any `.gitignore` under `Analista de Investimentos/`. The gitignore at the vault root (`Analista de Investimentos/.gitignore`) covers `.env` but not `env` (without dot). Phase 1 Plan 2 MUST add `env` to gitignore before renaming the file.

---

## Sources

### Primary (HIGH confidence — verified by direct file read)
- `src/utils/retry.py` — complete retry decorator code, current signature
- `src/utils/logger.py` — complete loguru wrapper, configure_logging(), get_logger()
- `config/settings.py` — pydantic-settings model, env_file config, all field defaults
- `news_hunter/config.py` — live token at lines 60–61, dotenv import structure
- `pipeline banco completo/config/settings.py` — no API tokens found (public URLs and math constants only)
- `src/scheduler.py` — complete job registry, _run_job() wrapper structure
- `src/main.py` — startup logging setup, cmd_* structure
- `.planning/codebase/CONCERNS.md` — security issues, tech debt items, stale Task Scheduler path
- `.planning/codebase/CONVENTIONS.md` — naming patterns, logging conventions
- `.planning/phases/01-foundation-and-cleanup/01-CONTEXT.md` — all locked decisions D-01 through D-15

### Secondary (MEDIUM confidence — verified in combination)
- `pip3 list` output — verified installed packages (python-dotenv 1.2.2, yfinance 1.2.2, requests 2.33.1, pydantic 2.13.1)
- `git ls-files` and git check-ignore — confirmed `env` file untracked and not gitignored at active gitignore level
- `.venv/pyvenv.cfg` — confirmed macOS Python 3.9 origin; non-functional on Windows

### Tertiary (LOW confidence — training knowledge, not verified in this session)
- loguru `contextualize()` API signature: `logger.contextualize(**kwargs)` returns context manager [ASSUMED] — standard loguru usage pattern, not verified by running code this session

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via pip3 list, requirements.txt, and direct import inspection
- Architecture: HIGH — all patterns derived from direct code reads of actual source files
- Pitfalls: HIGH — all pitfalls derived from actual code structure (confirmed token location, confirmed venv issue, confirmed gitignore gap)
- Security: HIGH — confirmed by reading the actual env file contents

**Research date:** 2026-05-06
**Valid until:** 2026-06-06 (stable infrastructure domain; unlikely to change)
