# Phase 3: Financial Engine - Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 10 (3 new, 7 modified/bug-fix)
**Analogs found:** 10 / 10

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/financial_engine.py` | service / orchestrator | CRUD (read DB → compute → write DB) | `src/ingestion/bcb.py` | role-match (same read→compute→write shape) |
| `src/ingestion/db.py` | config / migration | batch (DDL extension) | `src/ingestion/db.py` itself (existing tables) | exact (extend `_CREATE_SQL`) |
| `src/ingestion/cvm_downloader.py` | service | CRUD | `src/ingestion/cvm_downloader.py` itself (wire AccountMapper) | exact (modify `parse_and_store()`) |
| `src/valuation/sector_config.py` | utility | request-response | `src/ingestion/cvm_downloader.py` (encoding pattern) | role-match (encoding bug fix only) |
| `src/normalization/account_mapper.py` | utility | transform | `src/normalization/account_mapper.py` itself (import fix) | exact (one-line import fix) |
| `src/scheduler.py` | service | event-driven | `src/scheduler.py` — `job_bcb_macro()` / `job_cvm_ingest()` | exact (same job pattern) |
| `config/schedules.yaml` | config | — | `config/schedules.yaml` existing entries | exact |
| `tests/test_financial_engine.py` | test | CRUD | `tests/test_bcb_ingestion.py` + `tests/test_scheduler_ingestion.py` | exact |
| `tests/test_financial_signals.py` | test | transform | `tests/test_b3_ingestion.py` | role-match |
| `tests/test_financial_db_schema.py` | test | batch | `tests/test_db_schema.py` | exact |

---

## Pattern Assignments

### `src/financial_engine.py` (orchestrator, CRUD: DB-read → compute → DB-write)

**Analog:** `src/ingestion/bcb.py` (same read→compute→write cycle, UUID PKs, INSERT OR IGNORE/REPLACE, structlog)

**Imports pattern** (`bcb.py` lines 1–22):
```python
from __future__ import annotations

import sqlite3
import time
import uuid
from datetime import date, datetime, timezone

import pandas as pd

from src.ingestion.db import get_connection
from src.utils.errors import IngestionError
from src.utils.logger import get_logger
from src.valuation.sector_config import SectorConfig
from src.valuation.valuation_dcf import run_dcf, run_ddm
from src.valuation.calculate_metrics import calculate_industrial_metrics, calculate_bank_metrics
from src.normalization.account_mapper import AccountMapper
from src.normalization.bank_account_mapper import BankAccountMapper

log = get_logger(__name__)
```

**Public API shape** (from CONTEXT D-12):
```python
def run_ticker(ticker: str) -> FinancialResult:
    """Called on-demand by Phase 4. Returns FinancialResult dataclass."""
    ...

def run_all() -> list[FinancialResult]:
    """Called by job_financial_engine(). Iterates watchlist, calls run_ticker()."""
    from config.settings import settings
    results = []
    for ticker in settings.active_tickers:
        try:
            results.append(run_ticker(ticker))
        except Exception as exc:
            log.warning(f"[{ticker}] run_ticker falhou: {exc}")
    return results
```

**DB write pattern — INSERT OR REPLACE with UUID PK** (`bcb.py` lines 154–164 + `cvm_downloader.py` lines 178–202):
```python
# Use uuid4 for PK; ISO datetime for ingested_at; INSERT OR REPLACE for dedup
conn.execute("""
    INSERT OR REPLACE INTO financial_ltm
    (id, ticker, computed_date, net_revenue, ebitda, net_income, fcf,
     net_debt, gross_debt, cash, shareholders_equity, shares_outstanding,
     ltm_reconciliation_warning, ltm_warning_detail, ingested_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    str(uuid.uuid4()), ticker, computed_date,
    ltm.get("net_revenue"), ltm.get("ebitda"), ltm.get("net_income"),
    ltm.get("fcf"), ltm.get("net_debt"), ltm.get("gross_debt"),
    ltm.get("cash"), ltm.get("total_equity"),
    ltm.get("shares_outstanding"),
    warning, warning_detail,
    datetime.now(timezone.utc).isoformat(),
))
conn.commit()
```

**DB read pattern — parameterized queries only** (`bcb.py` lines 114–128):
```python
# SECURITY: always parameterized — never f-string with user/ticker input
rows = conn.execute("""
    SELECT series_code, value, date FROM macro_series
    WHERE series_code IN (11, 29039)
    ORDER BY date DESC
""").fetchall()

# Access rows by column name (row_factory=sqlite3.Row set in get_connection())
macro = {r["series_code"]: (r["value"], r["date"]) for r in rows}
```

**Freshness check pattern** (`bcb.py` lines 81–97):
```python
# Copy is_stale() from bcb.py — same function, same BMFBOVESPA calendar
from src.ingestion.bcb import is_stale

def _is_stale(iso_date: str | None) -> bool:
    """Return True if date string is stale (> 1 B3 business day old)."""
    if not iso_date:
        return True
    try:
        d = datetime.fromisoformat(iso_date).date()
        return is_stale(d)   # reuse bcb.is_stale() — same threshold
    except ValueError:
        return True
```

**Error handling pattern** (`bcb.py` lines 129–135, `scheduler.py` lines 91–96):
```python
# Per-ticker try/except — never let one ticker crash the full run
for ticker in tickers:
    try:
        result = run_ticker(ticker)
        results.append(result)
    except Exception as exc:
        log.warning(f"[{ticker}] run_ticker falhou: {exc}")
        # append a FinancialResult with success=False for summary counting
```

---

### `src/ingestion/db.py` (config, DDL extension)

**Analog:** `src/ingestion/db.py` itself — extend the existing `_CREATE_SQL` string.

**Extension pattern** (`db.py` lines 29–85 — existing `_CREATE_SQL` block):
```python
# APPEND to _CREATE_SQL, after the news_articles block.
# Follow the exact same conventions: TEXT PRIMARY KEY, ISO dates,
# REAL for money, INTEGER for booleans/counts, no AUTOINCREMENT,
# UNIQUE INDEX named idx_<table>_dedup ON (ticker, computed_date).

_CREATE_SQL = """
... (existing tables) ...

CREATE TABLE IF NOT EXISTS financial_ltm (
    id                          TEXT PRIMARY KEY,
    ticker                      TEXT NOT NULL,
    computed_date               TEXT NOT NULL,
    net_revenue                 REAL,
    ebitda                      REAL,
    net_income                  REAL,
    fcf                         REAL,
    net_debt                    REAL,
    gross_debt                  REAL,
    cash                        REAL,
    shareholders_equity         REAL,
    shares_outstanding          REAL,
    ltm_quarters_used           INTEGER,
    ltm_reconciliation_warning  INTEGER DEFAULT 0,
    ltm_warning_detail          TEXT,
    ingested_at                 TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ltm_dedup ON financial_ltm(ticker, computed_date);

CREATE TABLE IF NOT EXISTS financial_multiples (
    id              TEXT PRIMARY KEY,
    ticker          TEXT NOT NULL,
    computed_date   TEXT NOT NULL,
    price           REAL,
    market_cap      REAL,
    pe_ratio        REAL,
    ev_ebitda       REAL,
    pb_ratio        REAL,
    dividend_yield  REAL,
    ev_revenue      REAL,
    ingested_at     TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_multiples_dedup ON financial_multiples(ticker, computed_date);

CREATE TABLE IF NOT EXISTS financial_dcf (
    id                  TEXT PRIMARY KEY,
    ticker              TEXT NOT NULL,
    computed_date       TEXT NOT NULL,
    valuation_method    TEXT,
    fair_value_brl      REAL,
    upside_pct          REAL,
    wacc                REAL,
    terminal_growth     REAL,
    selic_used          REAL,
    cds_used            REAL,
    used_fallback       INTEGER DEFAULT 0,
    confidence_flag     TEXT,
    ingested_at         TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dcf_dedup ON financial_dcf(ticker, computed_date);

CREATE TABLE IF NOT EXISTS financial_signals (
    id              TEXT PRIMARY KEY,
    ticker          TEXT NOT NULL,
    computed_date   TEXT NOT NULL,
    rsi_14          REAL,
    macd_line       REAL,
    macd_signal     REAL,
    macd_histogram  REAL,
    ma_50           REAL,
    ma_200          REAL,
    golden_cross    INTEGER,
    death_cross     INTEGER,
    momentum_score  INTEGER,
    ingested_at     TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_dedup ON financial_signals(ticker, computed_date);
"""
```

**`init_db()` pattern** (`db.py` lines 88–100) — idempotent, no change needed to function signature:
```python
# init_db() calls conn.executescript(_CREATE_SQL) — all new CREATE TABLE IF NOT EXISTS
# statements are idempotent. The existing init_db() function does NOT change.
# Only _CREATE_SQL string is extended.
```

---

### `src/ingestion/cvm_downloader.py` (service, CRUD modification)

**Analog:** `src/ingestion/cvm_downloader.py` itself — wire `AccountMapper` into `parse_and_store()`.

**Existing `parse_and_store()` target line** (`cvm_downloader.py` line 268):
```python
# BEFORE (line 268 — current code):
"normalized_name": None,  # Phase 3 enrichment
```

**After — call AccountMapper at row-build time:**
```python
# Import at top of file (add after existing imports):
from src.normalization.account_mapper import AccountMapper
from src.normalization.bank_account_mapper import BankAccountMapper

# In parse_and_store(), after account_code / account_name are extracted (line ~258):
_mapper = AccountMapper()   # instantiate once per parse_and_store call (outside the loop)

# Inside the row-building loop (replace the "normalized_name": None line):
"normalized_name": _mapper._map_row(
    pd.Series({"account_code": account_code, "account_name": account_name})
),
```

**Back-fill pattern (one-time UPDATE at startup, called from financial_engine.py):**
```python
# One-time back-fill: UPDATE cvm_statements SET normalized_name = ? WHERE id = ?
# Must use parameterized queries (SECURITY: never f-string)
def backfill_normalized_names(conn: sqlite3.Connection) -> int:
    """Back-fill normalized_name for existing cvm_statements rows where normalized_name IS NULL."""
    mapper = AccountMapper()
    rows = conn.execute("""
        SELECT id, account_code, account_name
        FROM cvm_statements
        WHERE normalized_name IS NULL
    """).fetchall()
    updated = 0
    for row in rows:
        norm = mapper._map_row(pd.Series({
            "account_code": row["account_code"] or "",
            "account_name": row["account_name"] or "",
        }))
        if norm:
            conn.execute(
                "UPDATE cvm_statements SET normalized_name = ? WHERE id = ?",
                (norm, row["id"]),
            )
            updated += 1
    conn.commit()
    log.info(f"[backfill] normalized_name preenchido: {updated} linhas")
    return updated
```

---

### `src/valuation/sector_config.py` (utility, bug fix only)

**Analog:** `src/ingestion/cvm_downloader.py` lines 99–101 (same `open(path)` → `open(path, encoding="utf-8")` pattern used in cvm_downloader for CSV reads).

**Bug fix — two occurrences in `sector_config.py`:**
```python
# BEFORE (sector_config.py lines 38–39):
@lru_cache(maxsize=1)
def _load_sectors() -> dict:
    with open(_SECTORS_PATH) as f:          # BUG: cp1252 on Windows
        return yaml.safe_load(f).get("sectors", {})

# AFTER:
@lru_cache(maxsize=1)
def _load_sectors() -> dict:
    with open(_SECTORS_PATH, encoding="utf-8") as f:   # FIX
        return yaml.safe_load(f).get("sectors", {})

# BEFORE (sector_config.py lines 43–47):
@lru_cache(maxsize=1)
def _load_ticker_map() -> dict[str, str]:
    with open(_TICKERS_PATH) as f:          # BUG: cp1252 on Windows
        data = yaml.safe_load(f)
    ...

# AFTER:
@lru_cache(maxsize=1)
def _load_ticker_map() -> dict[str, str]:
    with open(_TICKERS_PATH, encoding="utf-8") as f:   # FIX
        data = yaml.safe_load(f)
    ...
```

---

### `src/normalization/account_mapper.py` (utility, import bug fix only)

**Bug fix — line 32:**
```python
# BEFORE (account_mapper.py line 32):
from parsers.dfp_parser import ACCOUNT_MAP as CODE_MAP

# AFTER (makes import work from project root where src/ is a package):
from src.parsers.dfp_parser import ACCOUNT_MAP as CODE_MAP
```

No other changes to this file.

---

### `src/scheduler.py` (service, event-driven modification)

**Analog:** `src/scheduler.py` — `job_bcb_macro()` (lines 338–369) for the exact job pattern, and `_JOB_REGISTRY` (lines 426–439) for the registration pattern.

**Job function pattern** (copy from `job_bcb_macro()` / `job_cvm_ingest()`, lines 283–335):
```python
def job_financial_engine() -> str:
    """Calcula LTM, múltiplos, DCF e sinais técnicos para todos os tickers — FIN-01..06."""
    from src.financial_engine import run_all
    from src.utils.logger import bind_run_id, get_logger as _get

    _log = _get(__name__)
    with bind_run_id("financial") as run_id:
        _log.info(f"[financial_engine] iniciado — run_id={run_id}")
        t0 = time.time()
        results = run_all()
        ok = sum(1 for r in results if r.success)
        fail = len(results) - ok
        duration_ms = int((time.time() - t0) * 1000)

        # D-15: structured summary log — same kwargs as job_bcb_macro
        _log.info(
            "[financial_engine] summary",
            source="financial_engine",
            records_inserted=ok,
            records_updated=0,
            duration_ms=duration_ms,
            status="ok" if fail == 0 else "partial",
            last_ingested_at=datetime.utcnow().isoformat(),
            failed_tickers=fail,
        )
        return f"financial_engine: ok={ok} failed={fail}"
```

**Registry entry** (add to `_JOB_REGISTRY` dict, lines 426–439, after `"news_ingest"` entry):
```python
_JOB_REGISTRY: dict[str, Callable] = {
    ...
    "news_ingest":        job_news_ingest,   # ING-06/07
    "financial_engine":   job_financial_engine,  # FIN-01..06  ← ADD THIS
}
```

---

### `config/schedules.yaml` (config modification)

**Analog:** existing entries in `schedules.yaml`, specifically `cvm_ingest` entry (lines 42–44) for staggered daily timing.

**New entry to append** (after `cvm_ingest` entry, inside `schedules:` block):
```yaml
  - job: financial_engine
    cron: "0 20 * * 1-5"       # seg–sex 20:00 (after cvm_ingest + b3_prices)
    description: Calcular LTM, múltiplos, DCF e sinais técnicos para watchlist
```

Timing rationale: runs after `cvm_ingest` (19:15) and `b3_prices` (19:00) so that both CVM statements and price data are fresh.

---

### `tests/test_financial_engine.py` (test, CRUD)

**Analog:** `tests/test_bcb_ingestion.py` (in-memory DB helper, `patch()` + `monkeypatch`, caplog, incremental logic tests) + `tests/test_scheduler_ingestion.py` (D-15 summary log pattern, registry check, call-order assertions).

**In-memory DB helper pattern** (`test_bcb_ingestion.py` lines 24–41):
```python
def make_financial_db() -> sqlite3.Connection:
    """In-memory DB with all financial_* tables for unit tests."""
    from src.ingestion.db import init_db
    import tempfile, os
    # Use init_db() with tmp_path to get the real schema (including financial_* tables)
    # Alternatively: inline CREATE TABLE statements matching _CREATE_SQL extensions
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE cvm_statements (
            id TEXT PRIMARY KEY, ticker TEXT NOT NULL, cvm_code TEXT NOT NULL,
            year INTEGER NOT NULL, period_type TEXT NOT NULL,
            account_code TEXT, account_name TEXT, normalized_name TEXT,
            value REAL, reference_date TEXT, ingested_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX idx_cvm_dedup
            ON cvm_statements(ticker, period_type, year, account_code, reference_date);
        CREATE TABLE macro_series (
            id TEXT PRIMARY KEY, series_code INTEGER NOT NULL,
            series_name TEXT NOT NULL, date TEXT NOT NULL,
            value REAL NOT NULL, ingested_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX idx_macro_dedup ON macro_series(series_code, date);
        CREATE TABLE price_ohlcv (
            id TEXT PRIMARY KEY, ticker TEXT NOT NULL, date TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL, adj_close REAL,
            volume INTEGER, is_gap INTEGER DEFAULT 0, ingested_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX idx_price_dedup ON price_ohlcv(ticker, date);
        CREATE TABLE financial_ltm (
            id TEXT PRIMARY KEY, ticker TEXT NOT NULL, computed_date TEXT NOT NULL,
            net_revenue REAL, ebitda REAL, net_income REAL, fcf REAL,
            net_debt REAL, gross_debt REAL, cash REAL, shareholders_equity REAL,
            shares_outstanding REAL, ltm_quarters_used INTEGER,
            ltm_reconciliation_warning INTEGER DEFAULT 0, ltm_warning_detail TEXT,
            ingested_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX idx_ltm_dedup ON financial_ltm(ticker, computed_date);
        ... (repeat for financial_multiples, financial_dcf, financial_signals)
    """)
    return conn
```

**Patch pattern for unit tests** (`test_bcb_ingestion.py` lines 53–66, `test_scheduler_ingestion.py` lines 29–57):
```python
# Patch SectorConfig to avoid YAML file reads (encoding bug still present in Wave 0)
@pytest.fixture
def mock_sector_config(monkeypatch):
    mock_cfg = MagicMock()
    mock_cfg.is_bank_model = False
    mock_cfg.valuation_method = "dcf_fcff"
    mock_cfg.dcf_assumptions = {
        "beta": 1.0, "erp": 0.055, "cost_of_debt": 0.115,
        "tax_rate": 0.27, "debt_to_capital": 0.25,
        "terminal_growth": 0.04, "risk_free": 0.105, "country_risk": 0.015,
        "n_years": 5, "base_revenue_growth": [0.08]*5, "base_capex_pct": 0.06,
    }
    monkeypatch.setattr(
        "src.valuation.sector_config.SectorConfig.for_ticker",
        classmethod(lambda cls, t: mock_cfg),
    )
    return mock_cfg
```

**D-15 summary log test pattern** (`test_scheduler_ingestion.py` lines 62–98):
```python
def test_job_financial_engine_emits_summary_log(monkeypatch):
    """job_financial_engine() emits INFO log with source='financial_engine'."""
    logged_records = []
    mock_logger = MagicMock()
    def capture(msg, **kwargs):
        logged_records.append({"msg": str(msg), "kwargs": kwargs})
    mock_logger.info = capture
    mock_logger.warning = MagicMock()

    monkeypatch.setattr("src.utils.logger.get_logger", lambda *a, **k: mock_logger)
    monkeypatch.setattr("src.financial_engine.run_all", lambda: [])

    from src.scheduler import job_financial_engine
    job_financial_engine()

    summary_logs = [r for r in logged_records if "summary" in r["msg"]]
    assert len(summary_logs) >= 1
    s = summary_logs[-1]
    assert s["kwargs"].get("source") == "financial_engine"
    assert "duration_ms" in s["kwargs"]
    assert "status" in s["kwargs"]
```

**Registry check pattern** (`test_scheduler_ingestion.py` lines 19–24):
```python
def test_financial_engine_job_registered():
    from src.scheduler import _JOB_REGISTRY
    assert "financial_engine" in _JOB_REGISTRY
```

---

### `tests/test_financial_signals.py` (test, transform)

**Analog:** `tests/test_b3_ingestion.py` (pandas DataFrame construction for testing, floating-point assertions with tolerance, edge case tests).

**Pandas test data construction pattern** (`test_b3_ingestion.py` lines 36–48):
```python
import numpy as np
import pandas as pd

def make_price_series(n: int = 250, start: float = 100.0, trend: float = 0.001) -> pd.Series:
    """Build synthetic price series for signal tests. Ascending trend by default."""
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    prices = start * np.cumprod(1 + trend + np.random.default_rng(42).normal(0, 0.01, n))
    return pd.Series(prices, index=idx)

def test_rsi_14_range():
    """RSI-14 must always be in [0, 100]."""
    prices = make_price_series(250)
    from src.financial_engine import compute_signals
    result = compute_signals(prices)
    assert 0 <= result["rsi_14"] <= 100

def test_momentum_score_range():
    """Composite momentum score must be 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, or 100."""
    prices = make_price_series(250)
    from src.financial_engine import compute_signals
    result = compute_signals(prices)
    assert 0 <= result["momentum_score"] <= 100
    assert result["momentum_score"] % 10 == 0  # only valid weight combinations
```

---

### `tests/test_financial_db_schema.py` (test, batch/DDL)

**Analog:** `tests/test_db_schema.py` (exact same pattern — `tmp_path` fixture, `init_db()`, PRAGMA queries, UNIQUE index assertions).

**Schema test pattern** (`test_db_schema.py` lines 14–47):
```python
def test_financial_tables_created(tmp_path):
    """init_db() creates all 4 financial_* tables."""
    from src.ingestion.db import init_db
    db = tmp_path / "ingestion.db"
    init_db(db)
    conn = sqlite3.connect(db)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()
    # All 4 existing + 4 new financial tables
    assert "financial_ltm" in tables
    assert "financial_multiples" in tables
    assert "financial_dcf" in tables
    assert "financial_signals" in tables

def test_financial_ltm_columns(tmp_path):
    """financial_ltm has all required columns (directly queryable, no JSON blobs)."""
    from src.ingestion.db import init_db
    db = tmp_path / "ingestion.db"
    init_db(db)
    conn = sqlite3.connect(db)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(financial_ltm)").fetchall()}
    conn.close()
    required = {"id", "ticker", "computed_date", "net_revenue", "ebitda",
                "net_income", "fcf", "net_debt", "ltm_reconciliation_warning", "ingested_at"}
    assert required <= cols

def test_insert_or_replace_dedup(tmp_path):
    """INSERT OR REPLACE on (ticker, computed_date) overwrites same-day row."""
    from src.ingestion.db import init_db, get_connection
    db = tmp_path / "ingestion.db"
    init_db(db)
    conn = get_connection(db)
    # Insert twice with same ticker+computed_date, different values
    for val in (1000.0, 2000.0):
        conn.execute("""
            INSERT OR REPLACE INTO financial_ltm
            (id, ticker, computed_date, net_revenue, ingested_at)
            VALUES (?, 'PETR4', '2026-05-11', ?, '2026-05-11T00:00:00')
        """, (str(uuid.uuid4()), val))
        conn.commit()
    count = conn.execute(
        "SELECT COUNT(*) FROM financial_ltm WHERE ticker='PETR4'"
    ).fetchone()[0]
    net_rev = conn.execute(
        "SELECT net_revenue FROM financial_ltm WHERE ticker='PETR4'"
    ).fetchone()[0]
    conn.close()
    assert count == 1          # only one row
    assert net_rev == 2000.0   # second write wins (REPLACE)
```

---

## Shared Patterns

### Logging — `get_logger` + `bind_run_id`
**Source:** `src/utils/logger.py` (lines 43–66)
**Apply to:** `src/financial_engine.py` (module-level `log = get_logger(__name__)`), `job_financial_engine()` in `scheduler.py` (`with bind_run_id("financial") as run_id:`)
```python
from src.utils.logger import get_logger, bind_run_id

log = get_logger(__name__)   # module-level

# Inside job function:
with bind_run_id("financial") as run_id:
    log.info(f"[financial_engine] iniciado — run_id={run_id}")
```

### D-15 Structured Summary Log
**Source:** `src/scheduler.py` `job_bcb_macro()` lines 357–369 and `job_cvm_ingest()` lines 323–335
**Apply to:** `job_financial_engine()` in `scheduler.py`
```python
_log.info(
    "[financial_engine] summary",
    source="financial_engine",
    records_inserted=ok,
    records_updated=0,
    duration_ms=duration_ms,
    status="ok" if fail == 0 else "partial",
    last_ingested_at=datetime.utcnow().isoformat(),
    failed_tickers=fail,
)
```

### UUID Text PK + ISO datetime
**Source:** `src/ingestion/bcb.py` line 159, `src/ingestion/cvm_downloader.py` lines 178–200
**Apply to:** all `INSERT OR REPLACE INTO financial_*` calls in `src/financial_engine.py`
```python
import uuid
from datetime import datetime, timezone

str(uuid.uuid4())                          # id column
datetime.now(timezone.utc).isoformat()    # ingested_at column
```

### Parameterized SQL (no f-string with ticker)
**Source:** `src/ingestion/bcb.py` lines 114–118, `src/ingestion/cvm_downloader.py` lines 181–200
**Apply to:** ALL `conn.execute()` calls in `src/financial_engine.py`
```python
# CORRECT — parameterized:
conn.execute("SELECT ... WHERE ticker = ?", (ticker,))

# NEVER — shell injection risk:
conn.execute(f"SELECT ... WHERE ticker = '{ticker}'")
```

### WR-06: Always Close Connection
**Source:** `src/scheduler.py` lines 97 and 354 (both job functions use `try/finally: conn.close()`)
**Apply to:** `job_financial_engine()` in `scheduler.py`
```python
conn = get_connection()
try:
    results = run_all_with_conn(conn)
finally:
    conn.close()   # WR-06: always close even on exception
```

### In-Memory DB for Tests
**Source:** `tests/test_bcb_ingestion.py` lines 24–41
**Apply to:** `tests/test_financial_engine.py`, `tests/test_financial_db_schema.py`
```python
# Option A: minimal inline schema (for isolated unit tests)
conn = sqlite3.connect(":memory:")
conn.executescript("CREATE TABLE ...")

# Option B: use init_db() with tmp_path (preferred for schema tests — picks up DDL changes)
db = tmp_path / "ingestion.db"
init_db(db)
conn = sqlite3.connect(db)
```

### Encoding Fix Pattern
**Source:** `src/ingestion/cvm_downloader.py` line 235 (`encoding="iso-8859-1"`) and line 244 (`encoding="utf-8"`)
**Apply to:** `src/valuation/sector_config.py` (two `open()` calls — lines 38–39, 43–47)
```python
# Pattern: always specify encoding= when opening text files
with open(path, encoding="utf-8") as f:
    data = yaml.safe_load(f)
```

---

## No Analog Found

All 10 files have analogs in the existing codebase. No file requires RESEARCH.md fallback patterns.

---

## Metadata

**Analog search scope:**
- `Analista de Investimentos/12_PYTHON/src/` (all subdirectories)
- `Analista de Investimentos/12_PYTHON/tests/`
- `Analista de Investimentos/12_PYTHON/config/`

**Files read for pattern extraction:** 13
- `src/scheduler.py` (680 lines)
- `src/ingestion/db.py` (108 lines)
- `src/ingestion/bcb.py` (174 lines)
- `src/ingestion/cvm_downloader.py` (485 lines)
- `src/ingestion/b3_scraper.py` (first 80 lines)
- `src/valuation/sector_config.py` (226 lines)
- `src/normalization/account_mapper.py` (174 lines)
- `src/utils/logger.py` (66 lines)
- `src/utils/retry.py` (56 lines)
- `tests/test_bcb_ingestion.py` (154 lines)
- `tests/test_db_schema.py` (104 lines)
- `tests/test_scheduler_ingestion.py` (215 lines)
- `tests/test_b3_ingestion.py` (174 lines)

**Pattern extraction date:** 2026-05-11
