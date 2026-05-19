# Coding Conventions

**Analysis Date:** 2026-05-06

## Naming Patterns

**Files:**
- `snake_case` throughout: `metrics_engine.py`, `risk_engine.py`, `cvm_downloader.py`, `bank_parser.py`
- Legacy pipeline modules use numbered prefixes: `01_coletor_cvm.py`, `02_coletor_mercado.py`
- Private/internal helpers prefixed with underscore: `_helpers.py`, `_ensure_src_path()`
- Test files always prefixed `test_`: `test_strategy.py`, `test_indicators.py`, `test_risk_models.py`

**Classes:**
- `PascalCase` strictly: `MetricsEngine`, `RiskEngine`, `CVMDownloader`, `LLMClient`, `InsightEngine`, `ProcessedStore`
- Dataclasses follow same convention: `PeriodResult`, `RiskReport`, `Risk`, `Insight`
- Pydantic models: `ExtractionMetadata`, `IncomeStatement`, `BalanceSheet`, `FinancialStatements`
- Enums use `PascalCase` class names with `UPPER_SNAKE` members: `Consolidation.CONSOLIDATED`, `DocType.DFP`

**Functions:**
- `snake_case` for all public functions: `run_metrics()`, `assess_risk()`, `ingest_ticker()`, `configure_logging()`
- Private helpers prefixed `_`: `_calc_bank()`, `_check_common()`, `_load_metrics()`, `_ensure_src_path()`
- High-level "entry point" wrappers are slim one-liners delegating to a class: `run_metrics()` → `MetricsEngine().run()`

**Variables:**
- `snake_case` for all locals and module-level vars: `output_dir`, `target_years`, `cvm_code`
- Short single-letter aliases used in tight computation blocks: `inc`, `bal`, `a`, `liab`
- Module-level logger always named `log` (not `logger`): `log = get_logger(__name__)`
- Exception in `pipeline banco completo/`: uses stdlib `logging` with `logger = logging.getLogger(...)` 

**Constants:**
- `UPPER_SNAKE_CASE` at module level: `BASE_URL`, `RATE_LIMIT_SECONDS`, `_SEV_ORDER`, `_METRIC_LABELS`
- Private module-level singletons prefixed `_`: `_CVM_CODES`, `_configured`, `_PROMPT_ANALISTA`

**Type Aliases:**
- Simple aliases declared at module scope: `Severity = str`, `DocType = Literal["DFP", "ITR"]`, `F = TypeVar("F", bound=Callable)`

## Code Style

**Formatting:**
- Tool: `ruff format` (configured in `pyproject.toml`)
- Line length: 100 characters (configured in `[tool.ruff]`)
- Target: Python 3.11+ (`target-version = "py311"`)

**Linting (Ruff):**
- Config file: `Analista de Investimentos/12_PYTHON/pyproject.toml`
- Rule sets enabled: `E` (pycodestyle errors), `F` (pyflakes), `I` (isort), `UP` (pyupgrade)
- `E501` (line too long) is explicitly ignored — line-length rule only applies to formatter
- `from __future__ import annotations` used consistently in `src/` modules for deferred evaluation

**Section Dividers:**
- Visual separators used liberally with `# ── Section name ────` style dashes
- Example pattern from `risk_engine.py`:
  ```python
  # ── Regras bancos ─────────────────────────────────────────────────────────────
  # ── Helpers ───────────────────────────────────────────────────────────────────
  ```
- This is a project-wide convention; match it when adding new sections to existing files

## Import Organization

**Order (enforced by ruff `I` rules):**
1. `from __future__ import annotations` (first, when present)
2. Standard library: `json`, `sys`, `pathlib`, `datetime`, `dataclasses`, etc.
3. Third-party: `pandas`, `numpy`, `pydantic`, `loguru`, `requests`
4. Internal `src.*` imports: `from src.utils.logger import get_logger`
5. Deferred local imports inside methods (used to avoid circular imports): `from config.settings import settings`

**Path Aliases:**
- No `__init__.py`-based re-exports in `src/` — imports use full module paths
- `config.settings` is imported as `from config.settings import settings` (no alias)
- Legacy `pipeline banco completo/` modules use `sys.path.insert` workarounds

**Deferred Imports Pattern:**
Used inside `__init__` and methods to break circular dependencies:
```python
def __init__(self, output_dir: Path | None = None):
    from config.settings import settings
    self.output_dir = output_dir or settings.data_output
```
This is intentional and acceptable — do not move these to module level.

## Error Handling

**General Strategy:** Catch broadly, log specifically, re-raise only at boundaries.

**Pattern — silent fallback (cache miss):**
```python
try:
    results[year] = json.loads(output_path.read_text())
    log.info(f"[{ticker}] {year}: métricas carregadas do cache")
    continue
except Exception:
    pass  # fall through to recalculate
```
Used in: `src/analysis/metrics_engine.py`, `src/analysis/risk_engine.py`

**Pattern — log-and-continue in loops:**
```python
try:
    metrics = self._calc_bank(...)
    ...
except Exception as exc:
    log.error(f"[{ticker}] {year}: erro ao calcular métricas — {exc}", exc_info=True)
```
`exc_info=True` is used for errors that may need tracebacks; omitted for expected/routine failures.

**Pattern — raise on missing config:**
```python
def get_cvm_code(ticker: str) -> str:
    code = codes.get(ticker.upper())
    if not code:
        raise KeyError(f"Ticker '{ticker}' não encontrado em config/cvm_codes.yaml.")
    return str(code).zfill(6)
```
Used in: `src/ingestion/cvm_downloader.py`

**Pattern — @retry decorator:**
```python
@retry(attempts=3, delay=2.0, backoff=2.0, exceptions=(requests.RequestException,))
def _fetch(self, url: str, label: str) -> bytes:
    ...
```
Decorator lives in `src/utils/retry.py`. Use it for any HTTP call; pass a specific `exceptions` tuple.

**Pydantic validation:**
- `@field_validator` for field-level checks
- `@model_validator(mode="after")` for cross-field derived calculations
- Assertion errors used inside validators: `assert v in (1, 1_000, 1_000_000), f"..."`

## Logging

**Framework:** `loguru` via a thin wrapper in `src/utils/logger.py`

**Setup:**
```python
from src.utils.logger import get_logger

log = get_logger(__name__)   # module-level, always named 'log'
```
Configure once at application startup via `configure_logging(settings.logs_dir, level=...)` in `src/main.py`.

**Log Levels in use:**
- `log.debug(...)` — detailed internal state (written to file only in production)
- `log.info(...)` — normal progress: `f"[{ticker}] {year}: métricas calculadas [{cfg.sector_type}]"`
- `log.warning(...)` — expected-but-notable conditions: `f"[{ticker}] sem dados processados"`
- `log.error(..., exc_info=True)` — unexpected failures with traceback
- `log.success(...)` — loguru-specific level for completed operations: `f"[{ticker}] {len(results)} períodos calculados"`

**Message Format Convention:**
- Ticker always in brackets prefix: `f"[{ticker}] message"`
- Dash separator before error detail: `f"[{ticker}] falha: {exc}"`

**Exception:** `pipeline banco completo/` uses stdlib `logging` (`logging.getLogger(...)` / `logger = logging.getLogger("pipeline.helpers")`). New code in `src/` must use loguru via the wrapper.

## Comments

**Module Docstrings:**
All `src/` modules have a structured header docstring:
```python
"""
metrics_engine.py
-----------------
One-line description.

Fluxo:
  1. Step one
  2. Step two

Uso:
    from src.analysis.metrics_engine import run_metrics
    result = run_metrics("BBAS3")
"""
```
Follow this pattern for any new module.

**Inline Comments:**
- Portuguese used for domain-logic comments (financial terminology): `# Carregar todos de uma vez para ter acesso a períodos anteriores`
- English used for technical implementation notes: `# pass cfg into each period calculation`
- Mixed is acceptable but avoid mid-sentence mixing

**Class/Method Docstrings:**
- `Args:` / `Returns:` sections used when signature alone is insufficient
- Short one-liners acceptable for private helpers

## Function Design

**Size:** Public methods tend to be 15–40 lines. Larger methods (e.g., `_check_bank`) are acceptable when they implement a coherent ruleset.

**Parameters:**
- Optional parameters default to `None` with `| None` union type: `output_dir: Path | None = None`
- `force: bool = False` is a universal parameter across all engine methods — include it on any method that reads from cache

**Return Values:**
- Engines return typed dicts or dataclasses: `dict[int, dict]`, `RiskReport`
- Methods that may fail silently return `None` explicitly: `def _get_latest_price(...) -> float | None`
- 0.0 used as safe fallback for financial float extraction (not None): see `_f()` helper in `src/analysis/metrics_engine.py`

## Module Design

**Exports:**
- Each module exposes a high-level function alongside the class:
  ```python
  def run_metrics(ticker, ...) -> dict:
      return MetricsEngine().run(ticker, ...)
  ```
  Callers should use the function form; the class is for when you need to pass custom `output_dir`.

**Barrel Files:**
- `__init__.py` files are present but empty in `src/` packages (`src/ingestion/__init__.py`, etc.)
- Do not add re-exports to `__init__.py` — import from the concrete module path

**Settings Singleton:**
- `config/settings.py` exposes a module-level `settings = Settings()` singleton
- Access settings inside methods via deferred import to avoid import-time side effects

---

*Convention analysis: 2026-05-06*
