# Phase 2: Reliable Data Ingestion - Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 14
**Analogs found:** 14 / 14

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/ingestion/db.py` | utility | CRUD | `news_hunter/banco.py` | role-match |
| `src/ingestion/bcb.py` | service | request-response | `pipeline banco completo/modules/03_coletor_macro.py` | exact |
| `src/ingestion/news_sync.py` | service | CRUD | `news_hunter/banco.py` | role-match |
| `src/ingestion/cvm_downloader.py` (EXTEND) | service | file-I/O | self (existing file) | exact |
| `src/ingestion/b3_scraper.py` (EXTEND) | service | request-response | self (existing file) | exact |
| `src/scheduler.py` (EXTEND) | service | event-driven | self (existing file) | exact |
| `config/schedules.yaml` (EXTEND) | config | — | self (existing file) | exact |
| `pyproject.toml` (EXTEND) | config | — | self (existing file) | exact |
| `tests/test_cvm_ingestion.py` | test | CRUD | (no tests exist — first test file) | no-analog |
| `tests/test_ipe_ingestion.py` | test | file-I/O | (no tests exist) | no-analog |
| `tests/test_bcb_ingestion.py` | test | request-response | (no tests exist) | no-analog |
| `tests/test_b3_ingestion.py` | test | request-response | (no tests exist) | no-analog |
| `tests/test_news_sync.py` | test | CRUD | (no tests exist) | no-analog |
| `tests/test_scheduler_ingestion.py` | test | event-driven | (no tests exist) | no-analog |

---

## Pattern Assignments

### `src/ingestion/db.py` (utility, CRUD)

**Analog:** `Analista de Investimentos/12_PYTHON/news_hunter/banco.py`

**Imports pattern** (banco.py lines 1-17):
```python
import sqlite3
import hashlib
import logging
from datetime import datetime, timedelta, date

import config

logger = logging.getLogger("news_hunter.banco")
```

**New file imports (adapt to src/ conventions):**
```python
from __future__ import annotations

import sqlite3
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)
```

**Core schema creation pattern** (banco.py lines 41-83):
```python
def inicializar():
    """Cria as tabelas se ainda não existirem e migra colunas novas."""
    conn = _conectar()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS noticias (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            hash        TEXT    UNIQUE NOT NULL,
            ...
        );
        CREATE INDEX IF NOT EXISTS idx_hash ON noticias(hash);
    """)
    conn.commit()
    conn.close()
```

**Key adaptation notes for db.py:**
- Replace `INTEGER PRIMARY KEY AUTOINCREMENT` with `TEXT PRIMARY KEY` (UUID) per D-06 Supabase portability
- Replace `INTEGER` date with `TEXT NOT NULL` ISO 8601 strings per D-06
- Use `conn.executescript(CREATE_SQL)` for the full 4-table DDL (same pattern as `inicializar()`)
- DB_PATH: `Path(__file__).parent.parent.parent / "data" / "ingestion.db"`
- Function signature: `def init_db(db_path: Path = DB_PATH) -> None:`

**Safe migration pattern** (banco.py lines 27-37):
```python
def _coluna_existe(conn, tabela: str, coluna: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({tabela})").fetchall()
    return any(row[1] == coluna for row in rows)

def _adicionar_coluna_se_nao_existe(conn, tabela: str, coluna: str, definicao: str):
    if not _coluna_existe(conn, tabela, coluna):
        conn.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")
```

**Helper function pattern** (banco.py lines 86-127):
```python
def gerar_hash(titulo: str, link: str) -> str:
    return hashlib.sha256(f"{titulo}{link}".encode()).hexdigest()

def salvar(...) -> bool:
    conn = _conectar()
    try:
        conn.execute("INSERT INTO noticias (...) VALUES (?,...)", (...,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
```

**Adapt for db.py:** Add helper `get_connection(db_path) -> sqlite3.Connection` (mirrors `_conectar()`). Add `upsert_*` helpers (INSERT OR IGNORE) for each of the 4 tables. Use parameterized queries with `?` placeholders throughout.

---

### `src/ingestion/bcb.py` (service, request-response)

**Analog:** `Analista de Investimentos/12_PYTHON/pipeline banco completo/modules/03_coletor_macro.py`

**Imports pattern** (03_coletor_macro.py lines 1-21):
```python
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
import pandas as pd

logger = logging.getLogger("pipeline.macro")
```

**New file imports (adapt to src/ conventions):**
```python
from __future__ import annotations

import time
import uuid
from datetime import date, datetime
from pathlib import Path

import requests

from src.utils.errors import IngestionError
from src.utils.logger import get_logger
from src.utils.retry import retry

log = get_logger(__name__)
```

**BCB URL and series registry** (03_coletor_macro.py lines 30-46):
```python
BCB_URL   = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados"
TIMEOUT   = 30
DATE_FMT  = "%d/%m/%Y"

SERIES = {
    "di":           12,
    "selic_meta":   432,
    "selic_over":   11,
    "ipca_12m":     433,
    "ipca_mensal":  13522,
    "pib_nominal":  4380,
    "cambio_dolar": 1,
    "cds_br":       29039,   # CDS Brasil 5Y (pontos-base) — VERIFIED in SGS
}
```

**Adapt for bcb.py** — use only the 5 D-11 series:
```python
BCB_SGS_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados"
BCB_SERIES: dict[str, int] = {
    "selic_over":  11,
    "ipca_12m":   433,
    "ptax_usd":     1,
    "cds_brasil": 29039,
    "pib_nominal": 4380,
}
```

**Core fetch pattern** (03_coletor_macro.py lines 67-122):
```python
def baixar_serie(self, codigo: int, inicio: str = "01/01/2010",
                 fim: str = None) -> pd.Series:
    fim = fim or datetime.now().strftime(self.DATE_FMT)
    url = self.BCB_URL.format(cod=codigo)
    params = {"formato": "json", "dataInicial": inicio, "dataFinal": fim}

    resp = self.session.get(url, params=params, timeout=self.TIMEOUT)
    resp.raise_for_status()
    dados = resp.json()

    df = pd.DataFrame(dados)
    df["data"]  = pd.to_datetime(df["data"], format=self.DATE_FMT, errors="coerce")
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.dropna().set_index("data")["valor"]
    return df
```

**Adapt for bcb.py** — add `@retry`, change return to `list[dict]`, add `IngestionError`:
```python
@retry(attempts=3, delay=2.0, backoff=2.0, jitter=0.5,
       exceptions=(requests.RequestException,))
def fetch_series(cod: int, inicio: str = "01/01/2019") -> list[dict]:
    """Returns list of {'data': 'dd/mm/yyyy', 'valor': str}."""
    url = BCB_SGS_URL.format(cod=cod)
    params = {
        "formato": "json",
        "dataInicial": inicio,
        "dataFinal": datetime.now().strftime("%d/%m/%Y"),
    }
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()
```

**CDS conversion** (03_coletor_macro.py lines 201-220):
```python
def cds_por_ano(self, anos):
    # CDS em pontos-base → decimal
    resultado[ano] = round(float(dados_ano.mean()) / 10_000, 6)
```

Apply same conversion: divide CDS values by 10,000 before storing in `macro_series`.

**Error handling pattern** — the legacy file has bare `except Exception` without retry. Replace with:
```python
try:
    data = fetch_series(series_code, inicio=last_date_str)
except IngestionError as exc:
    log.error(f"[bcb] falha: série {series_code}: {exc}")
    failed.append(series_name)
    continue
```

---

### `src/ingestion/news_sync.py` (service, CRUD)

**Analog:** `Analista de Investimentos/12_PYTHON/news_hunter/banco.py` (source schema) + `src/ingestion/b3_scraper.py` (incremental pattern)

**Imports pattern:**
```python
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger(__name__)
```

**Source schema** (banco.py lines 43-83 — the `noticias` table):
```python
# Table: noticias
# Columns: id, hash, titulo, link, fonte, categoria, data_coleta,
#          data_pub, conteudo, alertado, score, subcategoria, urgente,
#          resumo_curto, motivo_score
# Dedup key: hash = SHA-256(titulo + link)
# Query columns for sync:
#   hash, titulo, link, fonte, categoria, data_pub, score
```

**Cross-DB connect pattern** (banco.py lines 18-22):
```python
def _conectar():
    conn = sqlite3.connect(config.ARQUIVO_BANCO)
    conn.row_factory = sqlite3.Row
    return conn
```

**Adapt for news_sync.py** — use absolute path instead of config:
```python
BANCO_DB = Path(__file__).parent.parent.parent / "news_hunter" / "banco.db"

def _connect_source() -> sqlite3.Connection:
    conn = sqlite3.connect(BANCO_DB)
    conn.row_factory = sqlite3.Row
    return conn
```

**INSERT OR IGNORE dedup pattern** (banco.py lines 100-117):
```python
try:
    conn.execute(
        "INSERT INTO noticias (hash, titulo, link, ...) VALUES (?, ?, ?, ...)",
        (hash_, titulo, link, ...),
    )
    conn.commit()
    return True
except sqlite3.IntegrityError:
    return False
```

**Adapt for news_sync.py** — use `INSERT OR IGNORE` and `changes()` to count new inserts:
```python
conn.execute(
    """INSERT OR IGNORE INTO news_articles
       (id, url, title, published_at, source, score, ingested_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)""",
    (str(uuid.uuid4()), row["link"], row["titulo"],
     row["data_pub"], row["fonte"], row["score"], now)
)
inserted += conn.execute("SELECT changes()").fetchone()[0]
```

---

### `src/ingestion/cvm_downloader.py` (EXTEND — existing file)

**Analog:** self — `Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py`

**Existing imports to preserve** (lines 25-40):
```python
from __future__ import annotations

import io
import time
import zipfile
from datetime import date
from pathlib import Path
from typing import Literal

import requests
import yaml

from src.utils.logger import get_logger
from src.utils.retry import retry

log = get_logger(__name__)
```

**Existing download pattern to replicate for IPE** (lines 100-111):
```python
def download_dfp(self, year: int, force: bool = False) -> list[Path]:
    url = f"{BASE_URL}/DFP/DADOS/dfp_cia_aberta_{year}.zip"
    dest = self.output_dir / "DFP" / str(year)
    return self._download_and_extract(url, dest, label=f"DFP {year}", force=force)
```

**Add `download_ipe()` following the exact same pattern:**
```python
def download_ipe(self, year: int, force: bool = False) -> list[Path]:
    """Baixa e extrai o CSV de IPE para o ano. Pula se já existir."""
    url = f"{BASE_URL}/IPE/DADOS/ipe_cia_aberta_{year}.zip"
    dest = self.output_dir / "IPE" / str(year)
    return self._download_and_extract(url, dest, label=f"IPE {year}", force=force)
```

**Rate limit pattern to preserve** (lines 128-130, 257):
```python
time.sleep(RATE_LIMIT_SECONDS)  # RATE_LIMIT_SECONDS = 1.5
```

**Existing retry pattern to preserve** (lines 193-199):
```python
@retry(attempts=3, delay=2.0, backoff=2.0, exceptions=(requests.RequestException,))
def _fetch(self, url: str, label: str) -> bytes:
    resp = self.session.get(url, timeout=self.timeout)
    if resp.status_code == 404:
        raise FileNotFoundError(f"[{label}] Não encontrado na CVM (404): {url}")
    resp.raise_for_status()
    return resp.content
```

**CD_CVM zero-padding pattern** (lines 59-68):
```python
def get_cvm_code(ticker: str) -> str:
    codes = _load_cvm_codes()
    code = codes.get(ticker.upper())
    if not code:
        raise KeyError(...)
    return str(code).zfill(6)
```

Use same `.zfill(6)` normalization on `Codigo_CVM` column when filtering IPE CSV.

**New `write_to_db()` addition — follow banco.py's `salvar()` try/except/finally:**
```python
def write_to_db(self, records: list[dict], conn: sqlite3.Connection) -> int:
    """Upsert records into cvm_statements. Returns insert count."""
    inserted = 0
    for rec in records:
        try:
            conn.execute(
                """INSERT OR IGNORE INTO cvm_statements
                   (id, ticker, cvm_code, year, period_type, account_code,
                    account_name, normalized_name, value, reference_date, ingested_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (str(uuid.uuid4()), rec["ticker"], rec["cvm_code"], ...)
            )
            inserted += conn.execute("SELECT changes()").fetchone()[0]
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return inserted
```

---

### `src/ingestion/b3_scraper.py` (EXTEND — existing file)

**Analog:** self — `Analista de Investimentos/12_PYTHON/src/ingestion/b3_scraper.py`

**Existing imports to preserve** (lines 21-30):
```python
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from src.utils.logger import get_logger
from src.utils.retry import retry

log = get_logger(__name__)
```

**Add imports for DB write:**
```python
import sqlite3
import uuid
from datetime import datetime
```

**Existing `_download()` column normalization to preserve** (lines 132-161):
```python
@retry(attempts=3, delay=3.0, backoff=2.0)
def _download(self, ticker: str, since: str) -> pd.DataFrame:
    symbol = ticker.upper() + _SA_SUFFIX
    raw = yf.download(symbol, start=since, end=str(date.today() + timedelta(days=1)),
                      auto_adjust=True, progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    raw.columns = [c.lower().replace(" ", "_") for c in raw.columns]
    raw.index.name = "date"
    raw.index = pd.to_datetime(raw.index)
    expected = {"open", "high", "low", "close", "volume"}
    raw = raw[[c for c in raw.columns if c in expected]]
    return raw.dropna(how="all")
```

**New `write_to_db()` pattern — mirrors banco.py INSERT OR IGNORE:**
```python
def write_to_db(self, ticker: str, df: pd.DataFrame,
                conn: sqlite3.Connection) -> int:
    """Insert OHLCV rows into price_ohlcv. Returns inserted count."""
    inserted = 0
    now = datetime.utcnow().isoformat()
    for dt, row in df.iterrows():
        conn.execute(
            """INSERT OR IGNORE INTO price_ohlcv
               (id, ticker, date, open, high, low, close, volume, is_gap, ingested_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
            (str(uuid.uuid4()), ticker, dt.date().isoformat(),
             row.get("open"), row.get("high"), row.get("low"),
             row.get("close"), row.get("volume"), now)
        )
        inserted += conn.execute("SELECT changes()").fetchone()[0]
    conn.commit()
    return inserted
```

**New `detect_gaps()` addition — uses pandas_market_calendars (see Shared Patterns).**

---

### `src/scheduler.py` (EXTEND — existing file)

**Analog:** self — `Analista de Investimentos/12_PYTHON/src/scheduler.py`

**Existing job function shape to replicate exactly** (lines 64-79):
```python
def job_b3_prices() -> str:
    """Atualiza preços de todos os tickers ativos."""
    from config.settings import settings
    from src.ingestion.b3_scraper import B3Scraper

    scraper = B3Scraper()
    ok = fail = 0
    for ticker in settings.active_tickers:
        try:
            df = scraper.fetch(ticker)
            if not df.empty:
                ok += 1
        except Exception as exc:
            log.warning(f"[b3_prices] [{ticker}] {exc}")
            fail += 1
    return f"preços: ok={ok} falhas={fail}"
```

**Naming convention:** All new ingestion jobs follow `job_<name>()` returning `str`.

**Registry pattern to extend** (lines 249-259):
```python
_JOB_REGISTRY: dict[str, Callable] = {
    "news_fetcher": job_news_fetcher,
    "morning_call": job_morning_call,
    "b3_prices":    job_b3_prices,
    "cvm_check":    job_cvm_check,
    # ... existing jobs ...
}
```

**Add 4 new entries:**
```python
    "cvm_ingest":  job_cvm_ingest,   # replaces/extends cvm_check
    "bcb_macro":   job_bcb_macro,
    "b3_prices":   job_b3_prices,    # REPLACE existing stub with DB-writing version
    "news_ingest": job_news_ingest,
```

**bind_run_id pattern** (logger.py lines 48-66):
```python
@contextmanager
def bind_run_id(prefix: str = "run"):
    run_id = f"{prefix}-{uuid.uuid4().hex[:8]}"
    with _logger.contextualize(run_id=run_id):
        yield run_id
```

**D-14 usage at top of each new job:**
```python
def job_bcb_macro() -> str:
    import time
    from src.utils.logger import bind_run_id, get_logger
    from src.ingestion.bcb import ingest_all_series
    from src.ingestion.db import init_db

    log = get_logger(__name__)
    with bind_run_id("ingest") as run_id:
        log.info(f"[bcb_macro] iniciado — run_id={run_id}")
        init_db()
        ...
```

**D-15 summary log pattern** (follow scheduler.py `_run_job()` timing at lines 265-296):
```python
t0 = time.time()
result = ingest_all_series()
log.info(
    "[bcb_macro] summary",
    source="bcb_macro",
    records_inserted=result["inserted"],
    records_updated=result["updated"],
    duration_ms=int((time.time() - t0) * 1000),
    status="ok" if not result["failed"] else "partial",
    last_ingested_at=datetime.utcnow().isoformat(),
)
return f"bcb_macro: inserted={result['inserted']}"
```

**Subprocess bridge for news** (news_hunter/main.py lines 84-128 confirm `--coletar` flag):
```python
def job_news_ingest() -> str:
    import subprocess, sys
    from pathlib import Path
    from src.ingestion.news_sync import sync_news_to_ingestion_db
    from src.ingestion.db import init_db, get_connection

    log = get_logger(__name__)
    with bind_run_id("ingest") as run_id:
        news_hunter_dir = Path(__file__).parent.parent / "news_hunter"
        result = subprocess.run(
            [sys.executable, "main.py", "--coletar"],
            cwd=news_hunter_dir,
            timeout=300,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log.warning(f"[news_ingest] subprocess stderr: {result.stderr[:500]}")
        init_db()
        conn = get_connection()
        inserted = sync_news_to_ingestion_db(conn)
        conn.close()
        return f"news_ingest: inserted={inserted}"
```

---

### `config/schedules.yaml` (EXTEND — existing file)

**Analog:** self — `Analista de Investimentos/12_PYTHON/config/schedules.yaml`

**Existing cron entry shape** (lines 3-6):
```yaml
- job: news_fetcher
  cron: "0 6 * * 1-5"       # seg–sex 06:00
  description: Coletar notícias overnight
```

**Add 4 new entries following the exact same shape:**
```yaml
  - job: cvm_ingest
    cron: "0 19 * * 1-5"    # seg–sex 19:00 (after B3 close)
    description: Ingestão CVM DFP/ITR/IPE para watchlist

  - job: bcb_macro
    cron: "0 8 * * 1-5"     # seg–sex 08:00 (BCB publishes morning)
    description: Ingestão séries macro BCB SGS

  - job: b3_prices
    cron: "0 19 * * 1-5"    # seg–sex 19:00 (replace existing entry)
    description: Atualizar preços OHLCV em ingestion.db

  - job: news_ingest
    cron: "0 7 * * 1-5"     # seg–sex 07:00
    description: Coleta notícias + sincronizar para ingestion.db
```

**Note:** The existing `b3_prices` entry at `"0 7 * * 1-5"` must be replaced or its job function must now write to DB. Update in-place rather than adding a duplicate key.

---

### `pyproject.toml` (EXTEND — existing file)

**Analog:** self — `Analista de Investimentos/12_PYTHON/pyproject.toml`

**Existing dependency entry shape** (lines 11-51):
```toml
dependencies = [
    # Core
    "pandas>=2.1.0",
    # Ingestion
    "requests>=2.31.0",
    "yfinance>=0.2.0",
    # Parsing
    "pdfplumber>=0.10.0",
    # Scheduling
    "apscheduler>=3.10.0",
    ...
]
```

**Add under `# Ingestion` section:**
```toml
    "pandas-market-calendars>=4.3.0",
```

---

## Test File Patterns

No tests currently exist in the project. All 6 test files are net-new. Use the following pattern derived from pytest conventions (pyproject.toml lines 78-80 confirm `testpaths = ["tests"]`, `pythonpath = [".""]`).

### All test files: universal imports and fixture shape

```python
"""
test_<module>.py
----------------
Tests for <description>.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
```

### `tests/test_cvm_ingestion.py` (test, CRUD)

**Covers:** ING-01 (DFP filtered by CD_CVM), ING-02 (ITR dedup)

**Analog for internal pattern:** `src/ingestion/cvm_downloader.py` — the `ingest_ticker()` function and `CVMDownloader.download_dfp()` provide the contract to test.

**Key test cases to implement:**
```python
def test_get_cvm_code_returns_zero_padded():
    """get_cvm_code('BBAS3') returns 6-char zero-padded string."""
    ...

def test_download_dfp_skips_if_csv_exists(tmp_path):
    """download_dfp() skips HTTP when CSVs already present."""
    # Create dummy CSV at expected path
    # Assert _fetch not called (mock requests.Session.get)
    ...

def test_write_to_db_inserts_filtered_rows(tmp_path):
    """Only rows matching CD_CVM from cvm_codes.yaml are written."""
    # Build minimal CSV DataFrame with mixed CD_CVM values
    # Call write_to_db()
    # Assert only watchlist rows in cvm_statements
    ...

def test_itr_dedup_keeps_ultimo(tmp_path):
    """ITR reconciliation: duplicate (ticker, account_code, reference_date)
    keeps ORDEM_EXERC='ÚLTIMO', drops 'PENÚLTIMO'."""
    ...
```

---

### `tests/test_ipe_ingestion.py` (test, file-I/O)

**Covers:** ING-03 (IPE CSV filter, event_type classification, PDF text extraction)

**Analog:** `src/ingestion/cvm_downloader.py` download pattern; `news_hunter/banco.py` `inicializar()` for DB state in tests.

**Key test cases:**
```python
def test_download_ipe_constructs_correct_url():
    """download_ipe(2024) calls correct CVM IPE URL."""
    with patch("requests.Session.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.content = b"<empty zip>"
        ...

def test_ipe_csv_filtered_by_cvm_code():
    """IPE rows filtered to watchlist tickers via Codigo_CVM.zfill(6)."""
    # Create mock IPE CSV DataFrame with multiple Codigo_CVM values
    # Assert only watchlist rows returned
    ...

def test_ipe_event_type_classification():
    """Categoria column maps to expected event_type enum values."""
    # assert classify_event("Resultados") == "earnings"
    # assert classify_event("Fato Relevante") == "material_fact"
    ...

def test_ipe_pdf_extraction_returns_empty_on_failure():
    """extract_ipe_pdf_text() returns empty string when pdfplumber fails."""
    with patch("pdfplumber.open", side_effect=Exception("bad pdf")):
        result = extract_ipe_pdf_text("http://example.com/doc.pdf")
        assert result == ""
    ...
```

---

### `tests/test_bcb_ingestion.py` (test, request-response)

**Covers:** ING-04 (BCB series fetched, freshness, stale WARNING)

**Analog:** `pipeline banco completo/modules/03_coletor_macro.py` — the `baixar_serie()` API contract.

**Key test cases:**
```python
def test_fetch_series_parses_bcb_response():
    """fetch_series() returns list of dicts with 'data' and 'valor' keys."""
    mock_data = [{"data": "08/05/2026", "valor": "0.053400"}]
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = mock_data
        mock_get.return_value.raise_for_status = lambda: None
        result = fetch_series(11)
        assert result[0]["data"] == "08/05/2026"
    ...

def test_cds_value_divided_by_10000():
    """CDS values stored as decimal (94.47 bp → 0.009447)."""
    ...

def test_stale_series_logs_warning(caplog):
    """is_stale() returns True and WARNING logged when last_date is old."""
    ...

def test_incremental_fetch_uses_max_date():
    """get_last_date_for_series() returns last ingested date, not 2019."""
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE macro_series (series_code INT, date TEXT)")
    conn.execute("INSERT INTO macro_series VALUES (11, '2026-04-01')")
    result = get_last_date_for_series(conn, 11)
    assert result == "01/04/2026"
    ...
```

---

### `tests/test_b3_ingestion.py` (test, request-response)

**Covers:** ING-05 (OHLCV in price_ohlcv, gaps flagged with is_gap=1)

**Analog:** `src/ingestion/b3_scraper.py` — `B3Scraper._download()` and `fetch_prices()`.

**Key test cases:**
```python
def test_write_to_db_inserts_ohlcv_rows(tmp_path):
    """B3Scraper.write_to_db() inserts price rows with is_gap=0."""
    # Create in-memory ingestion.db
    # Build minimal DataFrame with 3 rows
    # Assert 3 rows inserted, all is_gap=0
    ...

def test_detect_gaps_inserts_gap_rows(tmp_path):
    """detect_gaps() inserts is_gap=1 rows for missing trading days."""
    # Mock pandas_market_calendars to return 5 expected days
    # Provide DataFrame with only 3 of those days
    # Assert 2 gap rows inserted with is_gap=1
    ...

def test_multiindex_columns_normalized():
    """yfinance MultiIndex columns are flattened to lowercase strings."""
    # Construct MultiIndex DataFrame matching yfinance 1.3.x output
    # Assert _download() returns single-level lowercase columns
    ...
```

---

### `tests/test_news_sync.py` (test, CRUD)

**Covers:** ING-06 (articles synced, deduplicated by URL)

**Analog:** `news_hunter/banco.py` `salvar()` + `gerar_hash()` for the source schema.

**Key test cases:**
```python
def test_sync_copies_articles_from_banco_db(tmp_path):
    """sync_news_to_ingestion_db() copies rows from banco.db to ingestion.db."""
    # Create temp banco.db with 3 noticias rows
    # Create temp ingestion.db with news_articles table
    # Call sync_news_to_ingestion_db()
    # Assert 3 rows in news_articles
    ...

def test_sync_deduplicates_by_url(tmp_path):
    """Second sync call inserts 0 rows when all URLs already present."""
    # After first sync, run sync again
    # Assert 0 new rows inserted
    ...

def test_sync_maps_categoria_to_ticker_tags(tmp_path):
    """categoria from banco.db stored as single-item ticker_tags JSON."""
    ...
```

---

### `tests/test_scheduler_ingestion.py` (test, event-driven)

**Covers:** ING-07 (jobs in registry, summary log emitted)

**Analog:** `src/scheduler.py` `_JOB_REGISTRY` and `_run_job()`.

**Key test cases:**
```python
def test_new_jobs_registered_in_registry():
    """All 4 new jobs present in _JOB_REGISTRY."""
    from src.scheduler import _JOB_REGISTRY
    for name in ("cvm_ingest", "bcb_macro", "b3_prices", "news_ingest"):
        assert name in _JOB_REGISTRY

def test_job_bcb_macro_calls_init_db(monkeypatch):
    """job_bcb_macro() calls init_db() before any DB write."""
    init_db_calls = []
    monkeypatch.setattr("src.ingestion.db.init_db",
                        lambda: init_db_calls.append(1))
    # patch ingest_all_series to return stub result
    ...
    assert len(init_db_calls) == 1

def test_d15_summary_log_emitted(caplog):
    """job_bcb_macro() emits summary log at INFO with required keys."""
    # Run job with mocked ingest_all_series
    # Assert log contains: source, records_inserted, duration_ms, status
    ...
```

---

## Shared Patterns

### Retry Decorator
**Source:** `Analista de Investimentos/12_PYTHON/src/utils/retry.py` (lines 13-55)
**Apply to:** All external fetch functions in `bcb.py`, `cvm_downloader.py`, `b3_scraper.py`
```python
from src.utils.retry import retry

@retry(attempts=3, delay=2.0, backoff=2.0, jitter=0.5,
       exceptions=(requests.RequestException,))
def _fetch_external(...):
    ...
```
The decorator raises `IngestionError` on exhaustion (lines 45-46 in retry.py). Callers catch `IngestionError`, log `f"[{name}] falha: {exc}"`, and continue to next item.

### Logging
**Source:** `Analista de Investimentos/12_PYTHON/src/utils/logger.py` (lines 43-66)
**Apply to:** All new `src/` files
```python
from src.utils.logger import get_logger, bind_run_id

log = get_logger(__name__)  # module-level
```
Log message format: `f"[{ticker}] message"` for ticker-scoped ops; `f"[job_name] message"` for job-level.

### Error Class
**Source:** `Analista de Investimentos/12_PYTHON/src/utils/errors.py` (lines 9-22)
**Apply to:** All new ingestion modules when raising or catching exhausted retries
```python
from src.utils.errors import IngestionError
# IngestionError has .cause, .func_name, .timestamp attributes
```

### SQLite Parameterized Queries
**Source:** `news_hunter/banco.py` throughout (e.g., lines 103-107, 120-123)
**Apply to:** All sqlite3 `execute()` calls in `db.py`, `news_sync.py`, `cvm_downloader.py`, `b3_scraper.py`, `bcb.py`
```python
# CORRECT — parameterized
conn.execute("SELECT * FROM t WHERE ticker = ?", (ticker,))
# NEVER — f-string SQL (SQL injection risk)
conn.execute(f"SELECT * FROM t WHERE ticker = '{ticker}'")
```

### UUID Primary Key (D-06)
**Source:** RESEARCH.md Pattern 1, enforced by D-06
**Apply to:** All `INSERT` statements in the 4 ingestion tables
```python
import uuid
row_id = str(uuid.uuid4())
# Use TEXT PRIMARY KEY, not AUTOINCREMENT INTEGER
```

### Config Loading
**Source:** `src/ingestion/cvm_downloader.py` (lines 48-56, 86-91)
**Apply to:** All new ingestion modules that need `settings.data_raw`, `settings.active_tickers`
```python
from config.settings import settings
output_dir = settings.data_raw / "cvm"
tickers = settings.active_tickers
```

### CVM CSV Encoding
**Source:** `src/parsers/dfp_parser.py` (confirmed pattern — `iso-8859-1` + `sep=";"`)
**Apply to:** All `pd.read_csv()` calls on CVM files (DFP, ITR, IPE)
```python
df = pd.read_csv(csv_path, encoding="iso-8859-1", sep=";")
# CD_CVM zero-padding (cvm_downloader.py line 68):
df["CD_CVM"] = df["CD_CVM"].astype(str).str.strip().str.zfill(6)
# IPE uses Codigo_CVM column:
df["Codigo_CVM"] = df["Codigo_CVM"].astype(str).str.strip().str.zfill(6)
```

### Incremental Download Guard
**Source:** `src/ingestion/b3_scraper.py` (lines 77-88) + `src/ingestion/cvm_downloader.py` (lines 172-176)
**Apply to:** `bcb.py` (incremental fetch) and any cache-first pattern
```python
# b3_scraper.py pattern:
existing = self._load_existing(parquet_path)
if force or existing.empty:
    since = start_date or DEFAULT_START
else:
    last_date = existing.index.max().date()
    since = str(last_date + timedelta(days=1))
```

---

## No Analog Found

All 6 test files have no analog — this is the first test code in the project.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/test_cvm_ingestion.py` | test | CRUD | No existing tests anywhere in the project |
| `tests/test_ipe_ingestion.py` | test | file-I/O | No existing tests anywhere in the project |
| `tests/test_bcb_ingestion.py` | test | request-response | No existing tests anywhere in the project |
| `tests/test_b3_ingestion.py` | test | request-response | No existing tests anywhere in the project |
| `tests/test_news_sync.py` | test | CRUD | No existing tests anywhere in the project |
| `tests/test_scheduler_ingestion.py` | test | event-driven | No existing tests anywhere in the project |

**Planner guidance for test files:** Use pytest 9.0.3 (confirmed in `pip list`). `pyproject.toml` sets `testpaths = ["tests"]` and `pythonpath = ["."]` — no conftest.py needed for basic imports. Use `sqlite3.connect(":memory:")` for in-memory DB tests and `tmp_path` pytest fixture for file I/O tests. Mock external HTTP calls with `unittest.mock.patch("requests.get")`.

---

## Metadata

**Analog search scope:** `Analista de Investimentos/12_PYTHON/src/`, `Analista de Investimentos/12_PYTHON/news_hunter/`, `Analista de Investimentos/12_PYTHON/pipeline banco completo/modules/`, `Analista de Investimentos/12_PYTHON/config/`
**Files scanned:** 13 source files read in full
**Pattern extraction date:** 2026-05-10

---

## PATTERN MAPPING COMPLETE
