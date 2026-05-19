# Phase 1: Foundation & Cleanup - Pattern Map

**Mapped:** 2026-05-06
**Files analyzed:** 13 (8 extend/create + 5 test files)
**Analogs found:** 11 / 13

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/utils/retry.py` (extend) | utility | request-response | `src/utils/retry.py` itself | self (extend in place) |
| `src/utils/logger.py` (extend) | utility | event-driven | `src/utils/logger.py` itself | self (extend in place) |
| `src/utils/errors.py` (create) | utility | — | `src/content/llm_client.py` (custom RuntimeError pattern) | partial |
| `config/settings.py` (extend) | config | — | `config/settings.py` itself | self (extend in place) |
| `src/main.py` (extend) | config | request-response | `src/main.py` itself | self (extend in place) |
| `src/scheduler.py` (extend) | service | event-driven | `src/scheduler.py` itself | self (extend in place) |
| `news_hunter/config.py` (extend) | config | — | `news_hunter/config.py` itself | self (extend in place) |
| `pipeline banco completo/DEPRECATED.md` (create) | docs | — | none | no analog |
| `tests/__init__.py` (create) | test | — | none in codebase | no analog (empty file) |
| `tests/test_retry.py` (create) | test | request-response | `src/utils/retry.py` | role-adjacent |
| `tests/test_logger.py` (create) | test | event-driven | `src/utils/logger.py` | role-adjacent |
| `tests/test_settings.py` (create) | test | — | `config/settings.py` | role-adjacent |
| `tests/test_consolidation.py` (create) | test | — | `src/main.py` (import pattern) | role-adjacent |
| `tests/test_news_hunter_config.py` (create) | test | — | `news_hunter/config.py` | role-adjacent |

---

## Pattern Assignments

### `src/utils/retry.py` (utility — extend with jitter + IngestionError)

**Analog:** `src/utils/retry.py` (lines 1–36, read in full above)

**Current imports pattern** (lines 1–8):
```python
import time
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

from src.utils.logger import get_logger

log = get_logger(__name__)
F = TypeVar("F", bound=Callable)
```

**Add to imports** (new line after `import time`):
```python
import random
```

**Current signature** (lines 12–14):
```python
def retry(
    attempts: int = 3, delay: float = 2.0, backoff: float = 2.0, exceptions: tuple = (Exception,)
):
```

**New signature** — add `jitter` param and change final raise:
```python
def retry(
    attempts: int = 3,
    delay: float = 2.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
    jitter: float = 0.5,
):
    """Decorator de retry com backoff exponencial e jitter."""
```

**Current core loop** (lines 19–34) — two changes needed:

Change 1 — replace `time.sleep(wait)` (line 31) with jitter-aware sleep:
```python
actual_wait = wait + random.uniform(0, jitter)
log.warning(
    f"{func.__name__} tentativa {attempt}/{attempts} falhou: {exc}. "
    f"Aguardando {actual_wait:.1f}s"
)
time.sleep(actual_wait)
```

Change 2 — replace bare `raise` on final attempt (lines 26–27) with `IngestionError`:
```python
if attempt == attempts:
    log.error(f"{func.__name__} falhou após {attempts} tentativas: {exc}")
    from src.utils.errors import IngestionError  # deferred import — avoids circular
    raise IngestionError(
        source=func.__module__,
        func=func.__name__,
        cause=str(exc),
    ) from exc
```

**Existing @retry call site pattern** (from `src/ingestion/cvm_downloader.py` line 193):
```python
@retry(attempts=3, delay=2.0, backoff=2.0, exceptions=(requests.RequestException,))
def _fetch(self, url: str, label: str) -> bytes:
```

**Existing @retry call site pattern** (from `src/ingestion/b3_scraper.py` line 131):
```python
@retry(attempts=3, delay=3.0, backoff=2.0)
def _download(self, ticker: str, since: str) -> pd.DataFrame:
```

---

### `src/utils/errors.py` (utility — new file)

**Analog:** `src/content/llm_client.py` (lines 179) — current bare `RuntimeError` that this replaces

**Pattern from RESEARCH.md** (verified against D-14):
```python
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class IngestionError(Exception):
    """Raised when a retried external call permanently fails."""
    source: str       # func.__module__  e.g. "src.ingestion.cvm_downloader"
    func: str         # func.__name__    e.g. "_fetch"
    cause: str        # str(exc)

    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(tz=timezone.utc)
        super().__init__(f"[{self.source}] {self.func} falhou: {self.cause}")
```

**Module header pattern** — copy from `src/utils/retry.py` lines 1–8 style:
```python
"""
errors.py
---------
Exceções estruturadas para falhas de ingestão e API externos.
"""
```

**LLM client final-attempt update** (`src/content/llm_client.py` line 179) — replace:
```python
# OLD:
raise RuntimeError(f"[LLM] falha após {self.max_retries} tentativas")

# NEW:
from src.utils.errors import IngestionError
raise IngestionError(
    source=__name__,
    func="generate",
    cause=f"falha após {self.max_retries} tentativas Anthropic",
)
```

---

### `src/utils/logger.py` (utility — extend with bind_run_id + 7-day retention + run_id format)

**Analog:** `src/utils/logger.py` (lines 1–39, read in full above)

**Current file structure:**
- `configure_logging(logs_dir, level)` — single public function, guards with `_configured`
- `get_logger(name)` — returns `_logger.bind(name=name)`
- No run_id support; retention is `"30 days"`; rotation uses `"00:00"` (midnight) not `"1 day"`

**Add to imports** (after existing imports):
```python
import uuid
from contextlib import contextmanager
```

**Change 1 — file handler in `configure_logging()`** (lines 26–33): update format + retention:
```python
_logger.add(
    logs_dir / "intelligence_{time:YYYY-MM-DD}.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {name} | run={extra[run_id]:8} — {message}",
    rotation="1 day",        # was "00:00"
    retention="7 days",      # was "30 days"
    encoding="utf-8",
)
```

**Change 2 — add run_id patcher** (after `_logger.add()` calls, before `_configured = True`):
```python
# Prevents KeyError when run_id not set (e.g., CLI calls outside scheduler)
_logger = _logger.patch(lambda r: r["extra"].setdefault("run_id", "-"))
```

**Change 3 — add `bind_run_id()` context manager** (new function, after `get_logger`):
```python
@contextmanager
def bind_run_id(prefix: str = ""):
    """Context manager: bind a short run_id to all log calls in scope.

    Usage in scheduler job functions:
        with bind_run_id("pipeline") as run_id:
            log.info(f"[scheduler] job iniciado — run_id={run_id}")
    """
    run_id = (prefix + "-" if prefix else "") + str(uuid.uuid4())[:8]
    with _logger.contextualize(run_id=run_id):
        yield run_id
```

---

### `config/settings.py` (config — extend with model_post_init startup validation)

**Analog:** `config/settings.py` (lines 1–64, read in full above)

**Current `model_post_init`** (lines 48–50) — only creates directories:
```python
def model_post_init(self, __context) -> None:
    for path in (self.data_raw, self.data_processed, self.data_output, self.logs_dir):
        path.mkdir(parents=True, exist_ok=True)
```

**Extend after the `mkdir` loop:**
```python
REQUIRED_IN_PRODUCTION = ["anthropic_api_key", "telegram_bot_token", "telegram_chat_id"]

def model_post_init(self, __context) -> None:
    # Existing: create directories
    for path in (self.data_raw, self.data_processed, self.data_output, self.logs_dir):
        path.mkdir(parents=True, exist_ok=True)

    # New: startup validation for production
    if self.env == "production":
        missing = [k for k in REQUIRED_IN_PRODUCTION if not getattr(self, k, "")]
        if missing:
            import sys
            print(f"[CONFIG] Variáveis obrigatórias ausentes no .env: {missing}")
            sys.exit(1)
```

**Note:** `REQUIRED_IN_PRODUCTION` is a module-level constant placed before the class, following the existing `ROOT = Path(...)` module-level constant pattern (line 8).

**Existing field pattern that validation keys match** (lines 33–37):
```python
anthropic_api_key: str = ""
supabase_url: str = ""
supabase_key: str = ""
telegram_bot_token: str = ""
telegram_chat_id: str = ""
```

---

### `src/main.py` (config/entry point — extend with startup guard)

**Analog:** `src/main.py` (lines 15–23, read in full above)

**Current startup block** (lines 19–23):
```python
from config.settings import settings
from src.utils.logger import configure_logging, get_logger

configure_logging(settings.logs_dir, level="DEBUG" if settings.env == "development" else "INFO")
log = get_logger(__name__)
```

**Add startup guard** immediately after `log = get_logger(__name__)`:
```python
# Startup guard: fail loudly if production + missing required keys
if settings.env == "production":
    missing = []
    for key in ("anthropic_api_key", "telegram_bot_token", "telegram_chat_id"):
        if not getattr(settings, key, ""):
            missing.append(key)
    if missing:
        log.error(f"[startup] variáveis obrigatórias ausentes: {missing}")
        sys.exit(1)
    log.info("[startup] configuração de produção validada")
```

**Note:** `sys` is already imported on line 17. The guard duplicates the `model_post_init` check intentionally — it provides a log entry before exit (Settings init happens before logger is configured).

**Existing error logging pattern** (line 55):
```python
log.error(f"[{ticker}] falha na ingestão CVM: {exc}")
```

---

### `src/scheduler.py` (service — extend job functions with bind_run_id)

**Analog:** `src/scheduler.py` (lines 38–41 and job function bodies)

**Current import block** (lines 30–40):
```python
from __future__ import annotations

import time
import traceback
from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)
```

**Add to import** (change `get_logger` import line):
```python
from src.utils.logger import bind_run_id, get_logger
```

**Current job function pattern** (lines 46–53, `job_news_fetcher` as representative):
```python
def job_news_fetcher() -> str:
    """Coleta notícias financeiras overnight (placeholder até news_fetcher.py)."""
    from config.settings import settings

    tickers = settings.active_tickers
    log.info(f"[news_fetcher] verificando notícias para {len(tickers)} tickers...")
    return f"{len(tickers)} tickers verificados (news stub)"
```

**Updated job pattern** — wrap body with `bind_run_id`:
```python
def job_news_fetcher() -> str:
    """Coleta notícias financeiras overnight (placeholder até news_fetcher.py)."""
    with bind_run_id("news_fetcher") as run_id:
        from config.settings import settings

        tickers = settings.active_tickers
        log.info(f"[news_fetcher] verificando notícias para {len(tickers)} tickers...")
        return f"{len(tickers)} tickers verificados (news stub)"
```

**Apply this same pattern to all 8 `job_*()` functions** (lines 46, 56, 64, 82, 97, 114, 140, 162, 209).
The prefix string for each: `"news_fetcher"`, `"morning_call"`, `"b3_prices"`, `"cvm_check"`, `"pipeline"`, `"analyze"`, `"content"`, `"health_check"`, `"weekly_review"`.

---

### `news_hunter/config.py` (config — remove hardcoded token fallbacks, fix load_dotenv path)

**Analog:** `news_hunter/config.py` (lines 1–11 and 59–61, read in full above)

**Current `load_dotenv` block** (lines 7–11):
```python
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
```

**Updated `load_dotenv` block** — explicit path to shared `.env`:
```python
try:
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")
except ImportError:
    pass
```

**Current hardcoded fallbacks** (lines 60–61):
```python
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN",   "8283626758:AAEx-rPwbFczQV3SoTCNnlC3Lj1SQo8bGVU")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-5236754554")
```

**Updated — empty string fallbacks:**
```python
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN",   "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
```

**No other logic changes** — `import config` standalone usage pattern preserved. D-11 explicitly prohibits restructuring `news_hunter/` imports.

---

### `tests/test_retry.py` (test — unit tests for retry behavior)

**Analog:** `src/utils/retry.py` (the module under test)

**pytest pattern** — follows pyproject.toml `testpaths = ["tests"]` config; import from `src.` prefix:

```python
"""Tests for src/utils/retry.py — exponential backoff + jitter + IngestionError."""
import time
import pytest
from unittest.mock import MagicMock, patch

from src.utils.retry import retry
from src.utils.errors import IngestionError


def test_success_on_first_attempt():
    """Decorated function succeeds first try — no sleeps."""
    call_count = 0

    @retry(attempts=3, delay=0.01, jitter=0.0)
    def flaky():
        nonlocal call_count
        call_count += 1
        return "ok"

    assert flaky() == "ok"
    assert call_count == 1


def test_backoff_jitter(monkeypatch):
    """Failed attempts sleep with exponential backoff + jitter."""
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda s: sleeps.append(s))

    @retry(attempts=3, delay=2.0, backoff=2.0, jitter=0.5, exceptions=(ValueError,))
    def always_fails():
        raise ValueError("boom")

    with pytest.raises(IngestionError):
        always_fails()

    assert len(sleeps) == 2          # 2 sleeps before 3rd (final) attempt
    assert sleeps[0] >= 2.0          # first sleep >= delay
    assert sleeps[1] >= 4.0          # second sleep >= delay * backoff


def test_ingestion_error_raised_on_exhaustion():
    """Final attempt raises IngestionError (not bare exception)."""
    @retry(attempts=2, delay=0.0, jitter=0.0, exceptions=(RuntimeError,))
    def always_fails():
        raise RuntimeError("api down")

    with pytest.raises(IngestionError) as exc_info:
        always_fails()

    err = exc_info.value
    assert "always_fails" in str(err)
    assert err.cause == "api down"


def test_non_matching_exception_propagates():
    """Exception NOT in exceptions tuple propagates immediately (no retry)."""
    @retry(attempts=3, delay=0.0, jitter=0.0, exceptions=(ValueError,))
    def raises_type_error():
        raise TypeError("wrong type")

    with pytest.raises(TypeError):
        raises_type_error()
```

---

### `tests/test_logger.py` (test — unit tests for logging)

**Analog:** `src/utils/logger.py` (the module under test)

```python
"""Tests for src/utils/logger.py — configure_logging, bind_run_id, retention."""
import pytest
from pathlib import Path
from loguru import logger as _loguru_logger

from src.utils.logger import configure_logging, get_logger, bind_run_id


def test_get_logger_returns_bound_logger(tmp_path):
    configure_logging(tmp_path, level="DEBUG")
    log = get_logger("test.module")
    assert log is not None


def test_run_id_binding(tmp_path, capsys):
    configure_logging(tmp_path, level="DEBUG")
    log = get_logger("test.run_id")

    captured_extras = []

    def capture_sink(message):
        captured_extras.append(message.record["extra"])

    _loguru_logger.add(capture_sink, level="DEBUG")

    with bind_run_id("pytest") as run_id:
        log.info("inside context")
        assert run_id.startswith("pytest-")

    log.info("outside context")

    # Inside context: run_id bound
    inside = captured_extras[-2]
    assert inside.get("run_id", "-") != "-"
    # Outside context: run_id defaults to "-"
    outside = captured_extras[-1]
    assert outside.get("run_id", "-") == "-"


def test_configure_logging_idempotent(tmp_path):
    """configure_logging() called twice does not add duplicate handlers."""
    configure_logging(tmp_path, level="INFO")
    configure_logging(tmp_path, level="INFO")  # second call should be no-op
```

---

### `tests/test_settings.py` (test — startup guard)

**Analog:** `config/settings.py` (the module under test) + `src/main.py` (startup guard pattern)

```python
"""Tests for config/settings.py — model_post_init startup validation."""
import pytest
from unittest.mock import patch


def test_startup_guard_development_mode(tmp_path, monkeypatch):
    """Development mode: missing keys do NOT trigger sys.exit."""
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    # Should not raise — development mode skips validation
    from config.settings import Settings
    s = Settings()
    assert s.env == "development"


def test_startup_guard_production_missing_keys(monkeypatch):
    """Production mode + missing required key: sys.exit(1) called."""
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")

    with pytest.raises(SystemExit) as exc_info:
        from config.settings import Settings
        Settings()

    assert exc_info.value.code == 1


def test_startup_guard_production_all_keys_set(monkeypatch, tmp_path):
    """Production mode + all required keys: no exit."""
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100")

    from config.settings import Settings
    s = Settings()
    assert s.env == "production"
```

---

### `tests/test_consolidation.py` (test — import path assertions)

**Analog:** `src/main.py` (imports from `src.` prefix pattern, lines 19–31)

```python
"""
Tests for FOUND-01: canonical src/ imports work; sys.path hacks removed.
All imports must resolve via 'src.' prefix, not via sys.path manipulation.
"""
import pytest


def test_src_utils_importable():
    """src.utils modules import without sys.path manipulation."""
    from src.utils.retry import retry
    from src.utils.logger import get_logger, configure_logging, bind_run_id
    from src.utils.errors import IngestionError
    assert callable(retry)
    assert callable(get_logger)
    assert callable(bind_run_id)


def test_config_settings_importable():
    """config.settings resolves from project root."""
    from config.settings import settings
    assert settings is not None


def test_no_sys_path_manipulation_in_pipeline():
    """src/processing/pipeline.py no longer uses sys.path.insert/append."""
    import ast
    from pathlib import Path
    pipeline_src = (
        Path(__file__).parent.parent
        / "src" / "processing" / "pipeline.py"
    )
    tree = ast.parse(pipeline_src.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "sys"
                and node.attr in ("path",)
            ):
                pytest.fail(
                    f"sys.path manipulation found in pipeline.py at line {node.lineno}. "
                    "Remove it and use src. prefix imports."
                )
```

---

### `tests/test_news_hunter_config.py` (test — no hardcoded token)

**Analog:** `news_hunter/config.py` (lines 59–61, the hardcoded token location)

```python
"""
Tests for FOUND-02: news_hunter/config.py has no hardcoded token fallbacks.
Token must default to empty string when env var is unset.
"""
import os
import importlib
import pytest


def test_no_hardcoded_telegram_token(monkeypatch):
    """TELEGRAM_TOKEN defaults to empty string when env var not set."""
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    # Force re-import
    import sys
    sys.modules.pop("news_hunter.config", None)
    sys.modules.pop("config", None)  # news_hunter uses bare 'import config'
    # Adjust path if needed — news_hunter/config.py is a standalone module
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "news_hunter_config",
        Path(__file__).parent.parent / "news_hunter" / "config.py",
    )
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)

    assert cfg.TELEGRAM_TOKEN == "", (
        f"TELEGRAM_TOKEN should be empty string, got: {cfg.TELEGRAM_TOKEN!r}. "
        "Remove hardcoded fallback from news_hunter/config.py line 60."
    )
    assert cfg.TELEGRAM_CHAT_ID == "", (
        f"TELEGRAM_CHAT_ID should be empty string, got: {cfg.TELEGRAM_CHAT_ID!r}. "
        "Remove hardcoded fallback from news_hunter/config.py line 61."
    )


def test_token_loaded_from_env(monkeypatch):
    """TELEGRAM_TOKEN read from env when set."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "test-token-123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-999")

    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "news_hunter_config_env",
        Path(__file__).parent.parent / "news_hunter" / "config.py",
    )
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)

    assert cfg.TELEGRAM_TOKEN == "test-token-123"
    assert cfg.TELEGRAM_CHAT_ID == "-999"
```

---

### `tests/__init__.py` (test package marker)

Empty file. No pattern needed — pytest discovers it as a package boundary.

---

### `pipeline banco completo/DEPRECATED.md` (docs — freeze notice)

No analog. Template from CONTEXT.md D-01:

```markdown
# DEPRECATED — pipeline banco completo

Este diretório está **congelado**. Não iniciar novos desenvolvimentos aqui.

## Status
- **Produção:** Ainda ativo — gera outputs Excel para valuation
- **Task Scheduler:** Aponta para `scheduler.py` neste diretório
- **Substituição prevista:** Fase 5 (dashboard Streamlit + relatórios PDF em `src/`)

## O que não fazer
- Não adicionar novas funcionalidades
- Não migrar lógica nova para cá
- Não alterar `config/settings.py` além da migração de credenciais para `.env`

## Credenciais
Lê do arquivo `.env` compartilhado em `12_PYTHON/.env`.

---
*Congelado em: 2026-05-06 — Phase 1 Foundation & Cleanup*
```

---

## Shared Patterns

### Module-level logger declaration
**Source:** `src/utils/retry.py` line 8; `src/scheduler.py` line 40; `src/ingestion/cvm_downloader.py` line 40
**Apply to:** ALL new and modified `src/` modules
```python
from src.utils.logger import get_logger
log = get_logger(__name__)
```
**Rule:** Variable is always `log`, never `logger`. Never `logging.getLogger()`.

### Log message format
**Source:** `src/main.py` lines 48–55; `src/scheduler.py` lines 52, 77
**Apply to:** All log call sites
```python
log.info(f"[{ticker}] iniciando ingestão...")       # with ticker context
log.error(f"[{ticker}] falha na ingestão CVM: {exc}")  # error with dash before detail
log.warning(f"[scheduler] [{ticker}] {exc}")        # subsystem prefix in brackets
```

### Deferred imports inside functions
**Source:** `src/scheduler.py` lines 48, 58, 67; `src/main.py` lines 31–32
**Apply to:** All job functions and cmd_* functions
```python
def job_pipeline() -> str:
    from config.settings import settings          # deferred — avoids circular at module load
    from src.processing.pipeline import process_ticker
```

### Error handling in job wrappers
**Source:** `src/scheduler.py` lines 265–296 (`_run_job`)
**Apply to:** Scheduler job bodies — catch `IngestionError` explicitly
```python
try:
    result = fn()
    success = True
    detail = str(result)[:200] if result else ""
except Exception:
    detail = traceback.format_exc(limit=3)
    log.error(f"[scheduler] ✗ {name}:\n{detail}")
```

### Settings access in src/ modules
**Source:** `src/ingestion/cvm_downloader.py` line 88; `src/scheduler.py` line 48
**Apply to:** Any module that needs `settings`
```python
# Always deferred inside __init__ or function body:
from config.settings import settings
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `pipeline banco completo/DEPRECATED.md` | docs | — | No documentation files in codebase to copy from |
| `tests/__init__.py` | test marker | — | No existing tests anywhere; empty file by convention |

---

## Metadata

**Analog search scope:** `Analista de Investimentos/12_PYTHON/src/`, `config/`, `news_hunter/`
**Files read directly:** `src/utils/retry.py`, `src/utils/logger.py`, `config/settings.py`, `src/main.py`, `src/scheduler.py`, `news_hunter/config.py`, `src/ingestion/cvm_downloader.py` (partial), `src/delivery/telegram_bot.py` (partial), `src/content/llm_client.py` (partial)
**Pattern extraction date:** 2026-05-06
