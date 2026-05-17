# Phase 4: Intelligence Layer - Pattern Map

**Mapped:** 2026-05-12
**Files analyzed:** 8
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/intelligence_layer.py` | service | request-response + CRUD | `src/financial_engine.py` | exact |
| `src/templates/thesis_prompt.j2` | config (template) | transform | `news_hunter/templates/boletim_mercado.j2` | role-match |
| `src/ingestion/db.py` | config (DDL) | CRUD | `src/ingestion/db.py` itself (`_CREATE_SQL` tail) | exact |
| `src/scheduler.py` | service (orchestrator) | event-driven | `job_financial_engine()` in `src/scheduler.py` | exact |
| `config/schedules.yaml` | config | — | existing entries in `config/schedules.yaml` | exact |
| `pyproject.toml` | config | — | existing `[project] dependencies` in `pyproject.toml` | exact |
| `tests/test_intelligence_layer.py` | test | CRUD + request-response | `tests/test_financial_engine.py` | exact |
| `tests/test_db_schema.py` | test | CRUD | `tests/test_db_schema.py` itself | exact (extend) |

---

## Pattern Assignments

### `src/intelligence_layer.py` (service, request-response + CRUD)

**Analog:** `src/financial_engine.py`

**Imports pattern** (financial_engine.py lines 16–36):
```python
from __future__ import annotations

import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from src.ingestion.db import get_connection
from src.utils.errors import IngestionError
from src.utils.logger import get_logger
from src.valuation.sector_config import SectorConfig

log = get_logger(__name__)
```

**Public dataclass pattern** (financial_engine.py lines 44–49):
```python
@dataclass
class FinancialResult:
    ticker: str
    success: bool
    error: Optional[str] = None
```
Phase 4 equivalent — `ThesisResult` (from CONTEXT.md D-20):
```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ThesisResult:
    ticker: str
    skipped: bool = False
    skip_reason: Optional[str] = None   # "hash_match", "daily_cap", "no_financial_data"
    thesis: Optional["InvestmentThesis"] = None
    signals: list["OpportunitySignal"] = field(default_factory=list)
    version_num: Optional[int] = None
    dcf_deviation_flag: bool = False
    error: Optional[str] = None
```

**`run_ticker()` core pattern** (financial_engine.py lines 324–413):
```python
def run_ticker(ticker: str) -> FinancialResult:
    conn = get_connection()
    try:
        # ... computation steps ...
        conn.execute("""INSERT OR REPLACE INTO financial_ltm ...""", (...,))
        conn.commit()
        log.info(f"[{ticker}] financial_ltm gravado — ...")
        return FinancialResult(ticker=ticker, success=True)
    except Exception as exc:
        log.warning(f"[{ticker}] run_ticker falhou: {exc}")
        return FinancialResult(ticker=ticker, success=False, error=str(exc))
    finally:
        conn.close()
```

**`run_all()` pattern** (financial_engine.py lines 416–449):
```python
def run_all() -> list[FinancialResult]:
    import yaml
    from pathlib import Path

    tickers_path = Path(__file__).parent.parent / "config" / "tickers.yaml"
    try:
        with open(tickers_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        active_tickers = [
            t["ticker"]
            for t in data.get("tickers", [])
            if t.get("active", True)
        ]
    except Exception as exc:
        log.error(f"[run_all] falha ao carregar tickers.yaml: {exc}")
        return []

    results: list[FinancialResult] = []
    for ticker in active_tickers:
        try:
            result = run_ticker(ticker)
            results.append(result)
        except Exception as exc:
            log.warning(f"[{ticker}] run_ticker excecao nao capturada: {exc}")
            results.append(FinancialResult(ticker=ticker, success=False, error=str(exc)))

    ok = sum(1 for r in results if r.success)
    log.info(f"[run_all] concluido — ok={ok} falhas={len(results)-ok}")
    return results
```

**DB read pattern** (financial_engine.py lines 463–475 — `_get_current_price`):
```python
# Parameterized query — ticker NEVER in SQL string (T-DCF-02 pattern)
row = conn.execute(
    """
    SELECT adj_close FROM price_ohlcv
    WHERE ticker = ? AND is_gap = 0 AND adj_close IS NOT NULL
    ORDER BY date DESC
    LIMIT 1
    """,
    (ticker,),
).fetchone()
if row is None:
    log.warning(f"[{ticker}] sem dado disponível")
    return None
return float(row["adj_close"])
```

**INSERT OR REPLACE pattern** (financial_engine.py lines 567–588):
```python
conn.execute(
    """
    INSERT OR REPLACE INTO financial_multiples
    (id, ticker, computed_date, price, market_cap, pe_ratio, ev_ebitda,
     pb_ratio, dividend_yield, ev_revenue, ingested_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (
        str(uuid.uuid4()),
        ticker,
        computed_date,
        current_price,
        # ... other values ...
        datetime.now(timezone.utc).isoformat(),
    ),
)
conn.commit()
```

**Error handling pattern** (financial_engine.py lines 409–413):
```python
except Exception as exc:
    log.warning(f"[{ticker}] run_ticker falhou: {exc}")
    return FinancialResult(ticker=ticker, success=False, error=str(exc))
finally:
    conn.close()
```

**LLMClient lazy import pattern** (llm_client.py lines 64–75):
```python
def __init__(self):
    from config.settings import settings
    self._settings = settings
    self._client: Any = None  # lazy

@property
def client(self):
    """Anthropic client — inicializado sob demanda."""
    if self._client is None:
        import anthropic
        self._client = anthropic.Anthropic(
            api_key=self._settings.anthropic_api_key,
        )
    return self._client
```
Phase 4 `IntelligenceClient` uses same lazy pattern but wraps `instructor.from_anthropic()`.

**Retry pattern** (llm_client.py lines 145–178):
```python
def _call_with_retry(self, **kwargs) -> str:
    import anthropic
    delay = self.retry_delay
    for attempt in range(1, self.max_retries + 1):
        try:
            response = self.client.messages.create(**kwargs)
            return response.content[0].text
        except anthropic.RateLimitError as exc:
            log.warning(f"[LLM] rate limit (tentativa {attempt}/{self.max_retries}): {exc}")
        except anthropic.InternalServerError as exc:
            log.warning(f"[LLM] server error (tentativa {attempt}/{self.max_retries}): {exc}")
        except anthropic.APIStatusError as exc:
            if exc.status_code in (529,):
                log.warning(f"[LLM] overload 529 (tentativa {attempt}/{self.max_retries})")
            else:
                raise
        if attempt < self.max_retries:
            time.sleep(delay)
            delay = min(delay * 2, 120.0)
    raise RuntimeError(f"[LLM] falha após {self.max_retries} tentativas")
```
Phase 4 catches `Exception` broadly (D-05) and re-raises as `IngestionError`.

---

### `src/templates/thesis_prompt.j2` (template, transform)

**Analog:** `news_hunter/templates/boletim_mercado.j2`

**Jinja2 template structure pattern** (boletim_mercado.j2 lines 1–30):
```jinja2
{%- set local_var = value -%}         {# strip whitespace with -%} #}
{{ variable_name }}                   {# simple substitution #}
{%- if condition %}
...
{%- endif %}
{%- for item in list %}
{{ item.field }}{% if item.other %} - {{ item.other }}{% endif %}
{%- endfor %}
```

**Float formatting in Jinja2** (from RESEARCH.md Pattern 2):
```jinja2
{# Monetary value — use Python str.format #}
{{ "R$ %.2f" | format(fair_value_brl) }}

{# Percentage #}
{{ "%.1f%%" | format(upside_pct * 100) }}
```

**Jinja2 Environment loading** (from RESEARCH.md Pattern 2):
```python
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pathlib import Path

_TEMPLATE_DIR = Path(__file__).parent / "templates"

def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        undefined=StrictUndefined,   # raises on missing variable — catches bugs early
        autoescape=False,            # prompt is plain text, not HTML
    )

def render_thesis_prompt(data: dict) -> str:
    env = _get_jinja_env()
    template = env.get_template("thesis_prompt.j2")
    return template.render(**data)
```

**Template section structure for `thesis_prompt.j2`:**
The template must inject all fields listed in D-08. Recommended sections:
1. Ticker metadata block (sector, is_bank_model, ticker symbol)
2. LTM financials block (net_revenue, ebitda, net_income, fcf, net_debt)
3. Multiples block (P/E, EV/EBITDA, P/BV, dividend_yield)
4. DCF block (fair_value_brl, upside_pct, wacc, terminal_growth, confidence_flag)
5. Macro block (Selic, IPCA_12m, CDS_brasil)
6. Signals block (RSI, MACD trend, momentum_score)
7. News block (last 3 headlines with published_at)
8. Explicit instruction (Portuguese, per D-08): "O `fair_value_brl` na tese DEVE ser exatamente R$ {dcf_fair_value:.2f} — não crie nem altere este valor."

---

### `src/ingestion/db.py` — DDL extension (config, CRUD)

**Analog:** Existing `_CREATE_SQL` in `src/ingestion/db.py` (lines 29–154)

**Exact DDL append pattern** (db.py lines 29–154 — existing table blocks as model):
```python
_CREATE_SQL = """
... (existing 8 CREATE TABLE blocks) ...

CREATE TABLE IF NOT EXISTS thesis_versions (
    id                 TEXT PRIMARY KEY,
    ticker             TEXT NOT NULL,
    version_num        INTEGER NOT NULL,
    generated_at       TEXT NOT NULL,
    input_hash         TEXT NOT NULL,
    positioning        TEXT NOT NULL,
    confidence         TEXT NOT NULL,
    fair_value_brl     REAL NOT NULL,
    dcf_deviation_flag INTEGER DEFAULT 0,
    thesis_json        TEXT NOT NULL,
    diff_summary       TEXT,
    UNIQUE(ticker, version_num)
);
CREATE INDEX IF NOT EXISTS idx_thesis_ticker ON thesis_versions(ticker);
CREATE INDEX IF NOT EXISTS idx_thesis_hash   ON thesis_versions(ticker, input_hash);

CREATE TABLE IF NOT EXISTS opportunity_signals (
    id               TEXT PRIMARY KEY,
    ticker           TEXT NOT NULL,
    computed_date    TEXT NOT NULL,
    signal_type      TEXT NOT NULL,
    description      TEXT NOT NULL,
    conviction_score INTEGER NOT NULL,
    ingested_at      TEXT NOT NULL,
    UNIQUE(ticker, computed_date, signal_type)
);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON opportunity_signals(ticker);

CREATE VIEW IF NOT EXISTS thesis_latest AS
SELECT * FROM thesis_versions
WHERE (ticker, version_num) IN (
    SELECT ticker, MAX(version_num)
    FROM thesis_versions
    GROUP BY ticker
);
"""
```

**Critical ordering rule:** VIEW must come AFTER both tables in `_CREATE_SQL`. `executescript()` runs statements sequentially; `CREATE VIEW IF NOT EXISTS` is idempotent on subsequent `init_db()` calls.

**init_db() and get_connection() — copy unchanged** (db.py lines 157–183):
```python
def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(_CREATE_SQL)
    conn.commit()
    conn.close()

def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn
```

---

### `src/scheduler.py` — `job_intelligence()` addition (service, event-driven)

**Analog:** `job_financial_engine()` in `src/scheduler.py` (lines 427–453)

**Exact `job_financial_engine()` pattern** (scheduler.py lines 427–453):
```python
def job_financial_engine() -> str:
    """Calcula LTM, múltiplos, DCF e sinais técnicos para todos os tickers — FIN-01..06.
    D-03: daily scheduled job; D-12: public job API.
    """
    from src.financial_engine import run_all
    from src.utils.logger import bind_run_id, get_logger as _get
    from datetime import datetime, timezone

    _log = _get(__name__)
    with bind_run_id("financial") as run_id:
        _log.info(f"[financial_engine] iniciado — run_id={run_id}")
        t0 = time.time()
        results = run_all()
        ok = sum(1 for r in results if r.success)
        fail = len(results) - ok
        duration_ms = int((time.time() - t0) * 1000)
        _log.info(
            "[financial_engine] summary",
            source="financial_engine",
            records_inserted=ok,
            records_updated=0,
            duration_ms=duration_ms,
            status="ok" if fail == 0 else "partial",
            last_ingested_at=datetime.now(timezone.utc).isoformat(),
            failed_tickers=fail,
        )
        return f"financial_engine: ok={ok} failed={fail}"
```

**`_JOB_REGISTRY` extension pattern** (scheduler.py lines 458–472):
```python
_JOB_REGISTRY: dict[str, Callable] = {
    "news_fetcher":      job_news_fetcher,
    "morning_call":      job_morning_call,
    "b3_prices":         job_b3_prices,
    "cvm_check":         job_cvm_check,
    "pipeline":          job_pipeline,
    "analyze":           job_analyze,
    "content":           job_content,
    "health_check":      job_health_check,
    "weekly_review":     job_weekly_review,
    "cvm_ingest":        job_cvm_ingest,         # ING-01/02/03
    "bcb_macro":         job_bcb_macro,          # ING-04
    "news_ingest":       job_news_ingest,        # ING-06/07
    "financial_engine":  job_financial_engine,   # FIN-01..06
    # Phase 4 appends here:
    "intelligence":      job_intelligence,       # INT-01..06
}
```

**`job_intelligence()` shape** (mirrors job_financial_engine, adapted for ThesisResult):
```python
def job_intelligence() -> str:
    """Gera teses estruturadas + sinais de oportunidade para todos os tickers — INT-01..06."""
    from src.intelligence_layer import run_all
    from src.utils.logger import bind_run_id, get_logger as _get
    from datetime import datetime, timezone

    _log = _get(__name__)
    with bind_run_id("intelligence") as run_id:
        _log.info(f"[intelligence] iniciado — run_id={run_id}")
        t0 = time.time()
        results = run_all()
        ok      = sum(1 for r in results if not r.skipped and r.thesis is not None)
        skipped = sum(1 for r in results if r.skipped)
        fail    = len(results) - ok - skipped
        duration_ms = int((time.time() - t0) * 1000)
        _log.info(
            "[intelligence] summary",
            source="intelligence",
            records_inserted=ok,
            records_updated=0,
            duration_ms=duration_ms,
            status="ok" if fail == 0 else "partial",
            last_ingested_at=datetime.now(timezone.utc).isoformat(),
            skipped_tickers=skipped,
            failed_tickers=fail,
        )
        return f"intelligence: ok={ok} skipped={skipped} failed={fail}"
```

---

### `config/schedules.yaml` — cron entry addition (config)

**Analog:** `financial_engine` entry in `config/schedules.yaml` (lines 46–48):
```yaml
  - job: financial_engine
    cron: "50 19 * * 1-5"     # seg–sex 19:50 — antes do analyze (20:00) para evitar race (WR-09)
    description: Calcular LTM, múltiplos, DCF e sinais técnicos para watchlist
```

**Phase 4 addition — append after `financial_engine` entry:**
```yaml
  - job: intelligence
    cron: "0 21 * * 1-5"      # seg-sex 21:00 — após financial_engine (19:50)
    description: Gerar teses estruturadas e sinais de oportunidade
```

**Comment convention:** Use `# seg-sex HH:MM — note` format matching existing entries.

---

### `pyproject.toml` — dependency additions (config)

**Analog:** Existing `[project] dependencies` in `pyproject.toml` (lines 11–52)

**Exact insertion point** (after `"anthropic>=0.39.0"` on line 41):
```toml
dependencies = [
    # ... existing dependencies ...

    # AI / Content
    "anthropic>=0.39.0",
    "instructor>=1.0.0",    # structured LLM output (latest: 1.15.1) — INT-01
    "jinja2>=3.1.0",        # prompt template rendering — INT-01

    # ... remaining dependencies ...
]
```

**Formatting rule:** Two-space indentation, one entry per line, inline comment with rationale and phase reference (matches project style observed in dev extras block on lines 58–62).

---

### `tests/test_intelligence_layer.py` (test, request-response + CRUD)

**Analog:** `tests/test_financial_engine.py`

**In-memory DB fixture pattern** (test_financial_engine.py lines 20–107):
```python
_FULL_SCHEMA = """
CREATE TABLE cvm_statements (...);
CREATE TABLE financial_ltm (...);
...
"""

def make_db() -> sqlite3.Connection:
    """Return an in-memory SQLite connection with full schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(_FULL_SCHEMA)
    return conn
```
Phase 4 `make_db()` must include all 8 existing tables PLUS `thesis_versions`, `opportunity_signals`, and the `thesis_latest` VIEW.

**Helper insert function pattern** (test_financial_engine.py lines 110–139):
```python
def _insert_itr_row(conn, ticker, ref_date, year, normalized_name, value):
    """Helper: insert a single ITR row into cvm_statements."""
    conn.execute(
        """INSERT OR IGNORE INTO cvm_statements
           (id, ticker, cvm_code, year, period_type, ...)
           VALUES (?, ?, ?, ?, ?, ...)""",
        (str(uuid.uuid4()), ticker, ...),
    )
    conn.commit()
```

**Monkeypatching LLM client** (test_financial_engine.py lines 471–538 — mock run_ddm pattern):
```python
def mock_run_ddm(*args, **kwargs):
    ddm_call_count.append(1)
    return mock_ddm_result

monkeypatch.setattr("src.financial_engine.run_ddm", mock_run_ddm)
```
Phase 4 equivalent — mock `instructor.from_anthropic`:
```python
from unittest.mock import MagicMock, patch

def test_generate_thesis_returns_valid_schema(monkeypatch):
    mock_thesis = InvestmentThesis(
        bull_case="Upside significativo...",
        bear_case="Riscos de...",
        drivers=[Driver(title="Receita", description="Crescendo", impact="HIGH")],
        risks=[Risk(title="Macro", description="Selic alta", severity="MEDIUM")],
        fair_value_brl=48.30,
        methodology_disclosure="DCF FCFF",
        positioning="COMPRAR",
        confidence="ALTA",
        rationale="Upside de 20%...",
        summary_one_line="PETR4 com upside de 20% — COMPRAR.",
    )
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_thesis
    monkeypatch.setattr("instructor.from_anthropic", lambda *a, **k: mock_client)
    # ... test body ...
```

**Scheduler registration test pattern** (test_financial_engine.py lines 859–864):
```python
def test_job_registered():
    """D-12: job_financial_engine is registered in _JOB_REGISTRY under key 'financial_engine'."""
    from src.scheduler import _JOB_REGISTRY
    assert "financial_engine" in _JOB_REGISTRY, (
        f"'financial_engine' not found in _JOB_REGISTRY. Keys: {list(_JOB_REGISTRY.keys())}"
    )
```

**D-15 summary log test pattern** (test_financial_engine.py lines 867–905):
```python
def test_job_summary_log(monkeypatch):
    logged = []
    mock_log = MagicMock()
    mock_log.info = lambda msg, **kw: logged.append({"msg": str(msg), "kw": kw})

    monkeypatch.setattr("src.utils.logger.get_logger", lambda *a, **k: mock_log)

    @contextmanager
    def mock_bind(prefix):
        yield f"{prefix}-test-run"

    monkeypatch.setattr("src.utils.logger.bind_run_id", mock_bind)
    monkeypatch.setattr("src.intelligence_layer.run_all", lambda: [])

    from src.scheduler import job_intelligence
    result = job_intelligence()

    summary = [r for r in logged if "summary" in r["msg"]]
    assert len(summary) >= 1
    s = summary[-1]
    assert s["kw"].get("source") == "intelligence"
    assert "duration_ms" in s["kw"]
```

**Imports block for test file** (modeled on test_financial_engine.py lines 1–13):
```python
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Literal
from unittest.mock import MagicMock, patch

import pytest
```

---

### `tests/test_db_schema.py` — update existing test (test, CRUD)

**Analog:** `tests/test_db_schema.py` itself (read-only — extend two assertions)

**Test to update — `test_init_db_is_idempotent`** (test_db_schema.py lines 36–51):
```python
def test_init_db_is_idempotent(tmp_path):
    """Calling init_db() twice raises no error and table count remains 8."""
    from src.ingestion.db import init_db

    db = tmp_path / "ingestion.db"
    init_db(db)
    init_db(db)  # second call — must not raise

    conn = sqlite3.connect(db)
    count = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
    ).fetchone()[0]
    conn.close()

    assert count == 8   # <-- CHANGE to: assert count >= 10
```

**Change `count == 8` to `count >= 10`** (2 new tables; VIEW appears with `type='view'`, not `type='table'`).

**Test to extend — `test_all_tables_have_text_pk`** (test_db_schema.py lines 70–84):
```python
tables = ["cvm_statements", "macro_series", "price_ohlcv", "news_articles"]
# ADD: "thesis_versions", "opportunity_signals"
```

**Two new tests to add:**
```python
def test_phase4_schema(tmp_path):
    """init_db() creates thesis_versions and opportunity_signals tables (Phase 4)."""
    from src.ingestion.db import init_db

    db = tmp_path / "ingestion.db"
    init_db(db)
    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    assert {"thesis_versions", "opportunity_signals"}.issubset(tables)


def test_thesis_latest_view(tmp_path):
    """init_db() creates thesis_latest VIEW visible in sqlite_master with type='view'."""
    from src.ingestion.db import init_db

    db = tmp_path / "ingestion.db"
    init_db(db)
    conn = sqlite3.connect(db)
    views = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'"
    ).fetchall()}
    conn.close()
    assert "thesis_latest" in views, f"thesis_latest VIEW not found. Views: {views}"
```

---

## Shared Patterns

### IngestionError — hard-fail pattern
**Source:** `src/utils/errors.py` (lines 9–22)
**Apply to:** `intelligence_layer.py` — `IntelligenceClient.generate_thesis()` catch block

```python
class IngestionError(Exception):
    def __init__(self, func_name: str, cause: "str | Exception"):
        self.cause = str(cause)
        self.func_name = func_name
        self.timestamp = datetime.now(tz=timezone.utc)
        super().__init__(f"{func_name} falhou após todas as tentativas: {self.cause}")
```

Usage (D-05 hard-fail):
```python
except Exception as exc:
    # Catches InstructorRetryException + any anthropic API errors
    raise IngestionError("generate_thesis", exc) from exc
```

### bind_run_id + D-15 summary log
**Source:** `src/utils/logger.py` (lines 47–66) + `scheduler.py` `job_financial_engine()` (lines 427–453)
**Apply to:** `job_intelligence()` in `scheduler.py`

```python
with bind_run_id("intelligence") as run_id:
    _log.info(f"[intelligence] iniciado — run_id={run_id}")
    # ... job body ...
    _log.info(
        "[intelligence] summary",
        source="intelligence",
        records_inserted=ok,
        records_updated=0,
        duration_ms=duration_ms,
        status="ok" if fail == 0 else "partial",
        last_ingested_at=datetime.now(timezone.utc).isoformat(),
        skipped_tickers=skipped,
        failed_tickers=fail,
    )
```

### Parameterized SQL
**Source:** `financial_engine.py` (multiple locations — e.g., `_get_current_price` line 463–475, `_compute_multiples` line 567–588)
**Apply to:** ALL SQL in `intelligence_layer.py` — read and write paths

```python
# CORRECT — positional params
conn.execute("SELECT * FROM thesis_versions WHERE ticker = ?", (ticker,))

# FORBIDDEN — ticker in SQL string (T-DCF-02 anti-pattern)
conn.execute(f"SELECT * FROM thesis_versions WHERE ticker = '{ticker}'")  # NEVER
```

### TEXT UUID primary key + ISO timestamps
**Source:** `financial_engine.py` lines 361–388 (INSERT into financial_ltm)
**Apply to:** All INSERT statements in `intelligence_layer.py`

```python
str(uuid.uuid4())                          # id column
date.today().isoformat()                   # computed_date / generated_at
datetime.now(timezone.utc).isoformat()    # ingested_at
```

### Lazy imports inside job functions
**Source:** `scheduler.py` `job_financial_engine()` (lines 431–432), `job_b3_prices()` (lines 68–72)
**Apply to:** `job_intelligence()` in `scheduler.py`

```python
def job_intelligence() -> str:
    from src.intelligence_layer import run_all          # lazy — avoids circular import
    from src.utils.logger import bind_run_id, get_logger as _get  # lazy
    # ... body ...
```

### conn.close() in finally block
**Source:** `scheduler.py` `job_b3_prices()` (line 97), `job_cvm_ingest()` (line 320)
**Apply to:** `run_ticker()` in `intelligence_layer.py`

```python
conn = get_connection()
try:
    # ... reads and writes ...
finally:
    conn.close()  # always close — WR-06 pattern
```

---

## No Analog Found

No files in Phase 4 are fully without analog. All have strong matches. The only genuinely new capability is the `instructor` + Pydantic thesis schema — no existing file in the codebase wraps `instructor.from_anthropic()`. The RESEARCH.md Pattern 1 (lines 208–287) supplies the verified API signature for this.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none — all files have analogs) | — | — | — |

---

## Metadata

**Analog search scope:** `Analista de Investimentos/12_PYTHON/src/`, `tests/`, `config/`, `news_hunter/templates/`
**Files scanned:** 10 source files read in full; 2 config files read in full; 1 template file read in full
**Pattern extraction date:** 2026-05-12

**Key findings:**
- `financial_engine.py` is the exact structural template for `intelligence_layer.py` — same `run_ticker(ticker) -> Result` + `run_all() -> list[Result]` shape, same `get_connection()` → try/finally/close pattern, same `INSERT OR REPLACE` with UUID PK.
- `scheduler.py::job_financial_engine()` is the exact copy-from for `job_intelligence()` — only the import path, `bind_run_id` prefix, and summary log field names change.
- `db.py` DDL extension is purely additive: append 2 CREATE TABLE blocks + 1 CREATE VIEW block to `_CREATE_SQL`; no existing DDL changes.
- `test_financial_engine.py` supplies the `make_db()` fixture, monkeypatching style, and D-15 log assertion pattern that `test_intelligence_layer.py` must replicate.
- `test_db_schema.py` has one line to change (`count == 8` → `count >= 10`) and two new tests to add.
- No Jinja2 template exists in `src/` — `src/templates/` directory must be created. The `news_hunter/templates/boletim_mercado.j2` supplies Jinja2 syntax conventions (conditionals, loops, filters, whitespace control with `-%}`).
- `llm_client.py` is the reference for the lazy `_client` property pattern and the `from config.settings import settings` lazy import — `IntelligenceClient` mirrors this but wraps `instructor.from_anthropic()` instead of raw `anthropic.Anthropic()`.
