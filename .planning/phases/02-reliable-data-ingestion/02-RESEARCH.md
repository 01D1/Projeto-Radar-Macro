# Phase 2: Reliable Data Ingestion - Research

**Researched:** 2026-05-10
**Domain:** Python data ingestion — CVM, BCB SGS, yfinance/B3, news_hunter integration, SQLite schema
**Confidence:** HIGH (codebase read directly; APIs probed live; pyproject.toml and installed packages verified)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**news_hunter/ Integration**
- D-01: Subprocess bridge — `src/scheduler` adds a job that calls `news_hunter/main.py` via subprocess. `news_hunter/` internals are NOT refactored.
- D-02: `src/scheduler` takes over scheduling for news_hunter. Disable `news_hunter/agendador.py`. Single scheduler, single `run_id` per pipeline run.
- D-03: `news_hunter/banco.db` stays separate — do NOT migrate into `ingestion.db`. `src/` reads news articles from `banco.db` via direct SQL query.

**SQLite Schema**
- D-04: Create unified `data/ingestion.db` with 4 source tables: `cvm_statements`, `macro_series`, `price_ohlcv`, `news_articles`. All tables include `ingested_at` (UTC) and `ticker` where applicable.
- D-05: `news_articles` in `ingestion.db` populated by reading from `news_hunter/banco.db` — NOT by redirecting news_hunter writes.
- D-06: Schema designed for SQLite→Supabase migration: no SQLite-specific types, ISO strings for dates, avoid AUTOINCREMENT where UUID is more portable.

**CVM Raw Format**
- D-07: Keep CSV format from CVM ZIP downloads. No switch to XML endpoint.
- D-08: Store raw CSVs for watchlist-only tickers. Lean `data/raw/cvm/` directory.
- D-09: Raw CSV extraction is the "preserve raw" step. Store at `data/raw/cvm/{year}/{ticker}_{period}.csv`.

**BCB SGS Ingestion**
- D-10: Lift-and-adapt from `pipeline banco completo/modules/03_coletor_macro.py`.
- D-11: Series: Selic (11), IPCA (433), PTAX USD (1), CDS Brazil (29039 — VERIFIED available in BCB SGS), PIB (4380).
- D-12: Freshness threshold: >1 Brazilian business day = stale. Use `pandas_market_calendars` with `BMFBOVESPA`. Log WARNING for stale, not ERROR.

**Retry and Logging**
- D-13: All new ingestion functions decorated with `@retry(attempts=3, delay=2.0, backoff=2.0, jitter=0.5, exceptions=(RequestException, ...))`.
- D-14: Each scheduler job starts with `with bind_run_id("ingest") as run_id:`.

**Scheduler Health Summary**
- D-15: After each full ingestion run, emit structured summary log: source, records inserted/updated, duration_ms, status, last_ingested_at. INFO level. No separate health DB table in Phase 2.

### Claude's Discretion
(None specified — all Phase 2 implementation decisions are locked via D-01 through D-15.)

### Deferred Ideas (OUT OF SCOPE)
- news_hunter/ full refactor into src/ingestion/ — Phase 5
- SQLAlchemy ORM layer — v2 milestone
- FOCUS forecast integration — v2 milestone
- Event-driven thesis refresh on IPE — Phase 4

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ING-01 | CVM DFP downloaded, parsed from CSV, stored with account code normalization; raw CSV preserved | `cvm_downloader.py` + `dfp_parser.py` already implement this; extend with `ingestion.db` write and D-09 raw storage |
| ING-02 | CVM ITR downloaded, parsed, stored; reconciled with DFP for overlapping periods | Same CSV pipeline as ING-01; `ITR` directory mirrors `DFP` directory; reconciliation = dedup by `(ticker, account_code, reference_date)` keeping `ÚLTIMO` period |
| ING-03 | CVM IPE ingested, classified by event type; PDF text extracted | IPE CSV has `Categoria`, `Tipo`, `Especie` columns for classification; `Link_Download` provides PDF URL; pdfplumber 0.11.9 is installed |
| ING-04 | BCB macro series (Selic, IPCA, PTAX, CDS Brazil, PIB) via SGS API with freshness timestamps | All 5 series confirmed available in BCB SGS API — verified live. CDS = series 29039, last value 94.47 bp (2026-04-01) |
| ING-05 | B3 OHLCV with corporate action adjustment; gaps flagged not interpolated | yfinance 1.3.0 installed; `auto_adjust=True` handles corporate actions; gap detection = check date sequence vs trading calendar |
| ING-06 | News RSS feeds ingested, deduplicated by URL, ticker-tagged | news_hunter/banco.db already populated with `noticias` table; `hash` column is SHA-256 of title+link = dedup key; ticker tagging via PALAVRAS_CHAVE |
| ING-07 | Ingestion scheduler runs daily; each run logged with duration, records updated, failures | APScheduler 3.11.2 installed; `IntelligenceScheduler` class exists; 4 new job functions to add to `_JOB_REGISTRY` |

</phase_requirements>

---

## Summary

Phase 2 connects four external data sources to a unified `data/ingestion.db` SQLite database using an existing scheduler and retry infrastructure already built in Phase 1. The implementation is primarily **extension of existing code**, not net-new architecture. The key work is: (1) adding `db.py` to create the ingestion.db schema, (2) extending `cvm_downloader.py` to also write parsed records into the DB and handle IPE, (3) creating `src/ingestion/bcb.py` adapted from the legacy `03_coletor_macro.py`, (4) redirecting `b3_scraper.py` output from Parquet files to `price_ohlcv` table with gap detection, and (5) wiring four new jobs into the existing `IntelligenceScheduler`.

The most significant discovery from live API probes: **CDS Brasil is confirmed available in BCB SGS as series 29039** (last data point: 94.47 bp as of 2026-04-01). The CONTEXT.md flag "may not be in SGS" is resolved — D-11 series list is fully implementable without ANBIMA/ipeadata fallback. `pandas_market_calendars` is NOT installed in the venv (needed for D-12 freshness check) — this is a required dependency to add.

The CVM IPE ZIP format closely mirrors DFP/ITR: one CSV file with columns `CNPJ_Companhia`, `Nome_Companhia`, `Codigo_CVM`, `Data_Referencia`, `Categoria`, `Tipo`, `Especie`, `Assunto`, `Link_Download`. PDF text extraction uses pdfplumber (already installed at 0.11.9) — no PyMuPDF needed.

**Primary recommendation:** Build the four ingestion modules and DB schema in parallel (Plans 1-4 per ROADMAP), with the scheduler wiring (Plan 4) coming last, after individual modules are tested independently.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| CVM DFP/ITR CSV download | Local Filesystem (script) | — | ZIP files are bulk downloads; no API key; downloaded once and cached locally |
| CVM IPE event classification | Local script | — | Classification uses `Categoria`/`Tipo`/`Especie` fields from CSV — pure local logic |
| IPE PDF text extraction | Local script (pdfplumber) | — | PDFs downloaded from `Link_Download` URL; text extracted locally |
| BCB SGS macro fetch | BCB API (external) | Local cache (ingestion.db) | Live API, daily pull; freshness tracked per series in `macro_series.ingested_at` |
| B3 price fetch | yfinance (external) | ingestion.db | yfinance wraps Yahoo Finance; incremental download from last date |
| Gap detection (prices) | Local script | ingestion.db | Compare trading-day sequence from B3 calendar vs stored dates |
| News ingestion | news_hunter subprocess | banco.db → ingestion.db sync | D-01/D-03: subprocess bridge; cross-DB read from banco.db |
| Scheduler | src/scheduler.py (APScheduler) | — | Existing daemon; add 4 new jobs to `_JOB_REGISTRY` |
| Data persistence | ingestion.db (SQLite) | — | All 4 sources write to unified DB for Phase 3 consumption |
| Freshness validation | Local script | pandas_market_calendars | BMFBOVESPA calendar determines "stale" threshold |

---

## Standard Stack

### Core (already installed — verified via `pip list`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| sqlite3 | built-in | ingestion.db access | Zero-dependency; SQLite→Supabase compatible schema (D-06) |
| requests | 2.33.1 | CVM ZIP download, BCB SGS, IPE PDF download | Already used in `cvm_downloader.py` |
| yfinance | 1.3.0 | B3 OHLCV prices | Already used in `b3_scraper.py`; `auto_adjust=True` handles corporate actions |
| pdfplumber | 0.11.9 | IPE PDF text extraction | Already in pyproject.toml; simpler API than PyMuPDF for text extraction |
| apscheduler | 3.11.2 | Job scheduling | Already wired in `src/scheduler.py`; `BlockingScheduler` + `CronTrigger` |
| pandas | 2.3.3 | Data manipulation, CSV parsing | Already used throughout |
| loguru | 0.7.3 | Structured logging with `bind_run_id` | Phase 1 infrastructure |
| pyyaml | 6.0.3 | `tickers.yaml`, `schedules.yaml` loading | Already used |

### To Add (not yet installed)

| Library | Version | Purpose | Installation |
|---------|---------|---------|-------------|
| pandas-market-calendars | latest | BMFBOVESPA trading calendar for D-12 freshness check | `pip install pandas-market-calendars` |

**Version verification:**
```bash
# Confirmed installed packages (probed 2026-05-10):
# requests 2.33.1, yfinance 1.3.0, pdfplumber 0.11.9, apscheduler 3.11.2
# pandas 2.3.3, loguru 0.7.3, pyyaml 6.0.3
# sqlite3 — built-in Python module, no install needed
# pandas-market-calendars — NOT installed, must add to pyproject.toml
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| sqlite3 (raw) | sqlite-utils | sqlite-utils is not installed and adds a dependency; raw sqlite3 is built-in and sufficient for well-defined schema |
| pdfplumber | PyMuPDF (fitz) | PyMuPDF is faster on large PDFs but not installed; pdfplumber already installed and simpler API |
| pandas-market-calendars | dateutil + manual holiday list | PMC has authoritative BMFBOVESPA calendar; manual list is maintenance burden and error-prone |
| APScheduler BlockingScheduler | BackgroundScheduler | BlockingScheduler is already the pattern in `IntelligenceScheduler` — stay consistent |

**Installation command (new dependency only):**
```bash
pip install pandas-market-calendars
# Also add to pyproject.toml dependencies
```

---

## Architecture Patterns

### System Architecture Diagram

```
tickers.yaml ──────────────────────────────────────────────────────────────┐
cvm_codes.yaml ──────┐                                                     │
                     │                                                     │
CVM dados.cvm.gov.br │──► cvm_downloader.py ──► data/raw/cvm/{year}/     │
(DFP/ITR ZIP)        │         │                 {ticker}_{period}.csv    │
                     │         ▼                                           │
CVM dados.cvm.gov.br │──► IPE CSV + PDF ──► pdfplumber ──► text          │
(IPE ZIP)            │         │                                           │
                     │         ▼                                           │
                     │    src/ingestion/db.py ──► data/ingestion.db       │
                     │         ▲  ▲  ▲  ▲                                 │
BCB api.bcb.gov.br   │    bcb.py│  │  │  │ b3_scraper.py  news sync      │
(series 11,433,1,    │──────────┘  │  │  └──────────────┐  job          │
29039, 4380)         │             │  └──────────────────│──────────┐    │
                     │             │         yfinance     │          │    │
B3 via yfinance ─────┘─────────────┘         OHLCV       │          │    │
                                                          │          │    │
news_hunter/banco.db ─────────────────────────────────────┘          │    │
(noticias table)                                                      │    │
                                                                      │    │
src/scheduler.py ─────────────────────────────────────────────────────┘    │
  job_cvm_ingest()    ◄─────────────────────────────────────────────────────┘
  job_bcb_macro()
  job_b3_prices()
  job_news_ingest()
       │
       ▼
  bind_run_id("ingest")
  D-15 structured summary log
       │
       ▼
  data/ingestion.db (authoritative for Phase 3)
  ├── cvm_statements
  ├── macro_series
  ├── price_ohlcv
  └── news_articles
```

### Recommended Project Structure

```
src/ingestion/
├── __init__.py
├── cvm_downloader.py    # EXTEND: add write_to_db(), download_ipe()
├── b3_scraper.py        # EXTEND: add write_to_db(), detect_gaps()
├── bcb.py               # NEW: adapted from 03_coletor_macro.py
├── news_sync.py         # NEW: reads banco.db, writes to ingestion.db news_articles
└── db.py                # NEW: schema creation + helper functions

data/
├── ingestion.db         # NEW: unified SQLite database
└── raw/
    └── cvm/
        └── {year}/
            └── {ticker}_{period}.csv   # watchlist-filtered raw CSVs (D-09)

config/
└── schedules.yaml       # EXTEND: add 4 ingestion job cron entries
```

### Pattern 1: SQLite Schema Creation (db.py)

**What:** Create `ingestion.db` with 4 tables on first run; idempotent via `CREATE TABLE IF NOT EXISTS`.
**When to use:** Called at start of any ingestion job that needs the DB.

```python
# Source: [VERIFIED: codebase — news_hunter/banco.py inicializar() pattern]
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "ingestion.db"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS cvm_statements (
    id           TEXT PRIMARY KEY,
    ticker       TEXT NOT NULL,
    cvm_code     TEXT NOT NULL,
    year         INTEGER NOT NULL,
    period_type  TEXT NOT NULL,       -- 'DFP' | 'ITR' | 'IPE'
    account_code TEXT,
    account_name TEXT,
    normalized_name TEXT,
    value        REAL,
    reference_date TEXT,              -- ISO YYYY-MM-DD
    ingested_at  TEXT NOT NULL        -- ISO UTC datetime
);
CREATE INDEX IF NOT EXISTS idx_cvm_ticker ON cvm_statements(ticker);
CREATE INDEX IF NOT EXISTS idx_cvm_period ON cvm_statements(period_type, year);

CREATE TABLE IF NOT EXISTS macro_series (
    id           TEXT PRIMARY KEY,
    series_code  INTEGER NOT NULL,
    series_name  TEXT NOT NULL,
    date         TEXT NOT NULL,       -- ISO YYYY-MM-DD
    value        REAL NOT NULL,
    ingested_at  TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_macro_dedup ON macro_series(series_code, date);

CREATE TABLE IF NOT EXISTS price_ohlcv (
    id           TEXT PRIMARY KEY,
    ticker       TEXT NOT NULL,
    date         TEXT NOT NULL,       -- ISO YYYY-MM-DD
    open         REAL,
    high         REAL,
    low          REAL,
    close        REAL,
    adj_close    REAL,
    volume       INTEGER,
    is_gap       INTEGER DEFAULT 0,   -- 1 = trading day with no data (gap marker)
    ingested_at  TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_price_dedup ON price_ohlcv(ticker, date);
CREATE INDEX IF NOT EXISTS idx_price_ticker ON price_ohlcv(ticker);

CREATE TABLE IF NOT EXISTS news_articles (
    id           TEXT PRIMARY KEY,
    url          TEXT NOT NULL,
    title        TEXT NOT NULL,
    published_at TEXT,
    source       TEXT,
    ticker_tags  TEXT,                -- JSON array of tickers, e.g. '["PETR4","VALE3"]'
    score        INTEGER DEFAULT 0,
    ingested_at  TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_url ON news_articles(url);
"""

def init_db(db_path: Path = DB_PATH) -> None:
    """Create ingestion.db tables if not exist. Idempotent."""
    conn = sqlite3.connect(db_path)
    conn.executescript(CREATE_SQL)
    conn.commit()
    conn.close()
```

**Key design choices (D-06):**
- `id` as TEXT UUID (not AUTOINCREMENT INTEGER) for Supabase portability
- All dates as ISO 8601 strings, not SQLite DATE type
- `ticker_tags` stored as JSON string (TEXT column) — avoids array type incompatibility
- `UNIQUE INDEX` on natural keys prevents duplicate ingestion without application-level checks

### Pattern 2: BCB SGS Fetch (bcb.py)

**What:** Fetch a single BCB SGS series, return as list of `(date, value)` tuples.
**When to use:** `job_bcb_macro()` calls this for each series in D-11.

```python
# Source: [VERIFIED: codebase — 03_coletor_macro.py baixar_serie() + live API probe 2026-05-10]
BCB_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados"
BCB_SERIES = {
    "selic_over":  11,
    "ipca_12m":   433,
    "ptax_usd":     1,
    "cds_brasil": 29039,  # VERIFIED: returns 28 records for 2024–2026, last: 94.47bp
    "pib_nominal": 4380,
}

@retry(attempts=3, delay=2.0, backoff=2.0, jitter=0.5,
       exceptions=(requests.RequestException,))
def fetch_series(cod: int, inicio: str = "01/01/2019") -> list[dict]:
    """Returns list of {'data': 'dd/mm/yyyy', 'valor': str}."""
    url = BCB_URL.format(cod=cod)
    params = {"formato": "json", "dataInicial": inicio,
              "dataFinal": datetime.now().strftime("%d/%m/%Y")}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()
```

**CDS Brasil note:** D-11 flag "may not be in SGS" is resolved. Series 29039 returned 28 data points for 2024–2026 in live probe. Value is in basis points (e.g., 94.47 bp = 0.9447%). The legacy code in `03_coletor_macro.py` already divides by 10,000 to get decimal — replicate that conversion.

### Pattern 3: Freshness Check (bcb.py / db.py)

**What:** Compare last ingested date for a series against today's date, accounting for BMFBOVESPA non-business days.
**When to use:** At start of `job_bcb_macro()` and `job_b3_prices()` to decide whether to skip or warn.

```python
# Source: [VERIFIED: codebase — CONTEXT.md D-12; pandas-market-calendars docs]
# NOTE: pandas-market-calendars must be installed first
import pandas_market_calendars as mcal
from datetime import date

def is_stale(last_date: date, threshold_days: int = 1) -> bool:
    """Returns True if last_date is more than threshold_days B3 business days ago."""
    bmf = mcal.get_calendar("BMFBOVESPA")
    schedule = bmf.schedule(start_date=str(last_date), end_date=str(date.today()))
    # Number of trading days between last_date and today (exclusive of last_date)
    trading_days = len(schedule) - 1
    return trading_days > threshold_days
```

### Pattern 4: Gap Detection (b3_scraper.py extension)

**What:** After fetching new OHLCV data, identify trading days where no price data was returned, and insert explicit GAP marker rows.
**When to use:** After `yfinance.download()` returns data for a date range.

```python
# Source: [VERIFIED: codebase — b3_scraper.py + CONTEXT.md D-05 ING-05]
def detect_and_insert_gaps(
    ticker: str, df: pd.DataFrame, start_date: str, conn: sqlite3.Connection
) -> int:
    """
    Compares df.index (actual trading days with data) against
    BMFBOVESPA calendar for the same date range.
    Inserts is_gap=1 rows for any missing trading day.
    Returns count of gap rows inserted.
    """
    import pandas_market_calendars as mcal
    bmf = mcal.get_calendar("BMFBOVESPA")
    schedule = bmf.schedule(start_date=start_date, end_date=str(date.today()))
    expected_dates = set(schedule.index.normalize().date)
    actual_dates = set(df.index.normalize().date) if not df.empty else set()
    gap_dates = expected_dates - actual_dates

    gaps_inserted = 0
    for gap_date in sorted(gap_dates):
        row_id = str(uuid.uuid4())
        conn.execute(
            """INSERT OR IGNORE INTO price_ohlcv
               (id, ticker, date, is_gap, ingested_at)
               VALUES (?, ?, ?, 1, ?)""",
            (row_id, ticker, gap_date.isoformat(), datetime.utcnow().isoformat())
        )
        gaps_inserted += 1
    return gaps_inserted
```

### Pattern 5: Scheduler Job with bind_run_id and D-15 Summary

**What:** Template for all four new ingestion job functions.
**When to use:** All `job_*` functions in `src/scheduler.py`.

```python
# Source: [VERIFIED: codebase — src/scheduler.py _run_job() pattern + CONTEXT.md D-14/D-15]
def job_bcb_macro() -> str:
    import time
    from src.utils.logger import bind_run_id, get_logger
    from src.ingestion.bcb import ingest_all_series
    from src.ingestion.db import init_db

    log = get_logger(__name__)

    with bind_run_id("ingest") as run_id:
        log.info(f"[bcb_macro] iniciado — run_id={run_id}")
        init_db()
        t0 = time.time()
        result = ingest_all_series()  # returns {"inserted": N, "updated": N, "failed": [...]}

        # D-15: structured summary log
        log.info(
            "[bcb_macro] summary",
            source="bcb_macro",
            records_inserted=result["inserted"],
            records_updated=result["updated"],
            duration_ms=int((time.time() - t0) * 1000),
            status="ok" if not result["failed"] else "partial",
            last_ingested_at=datetime.utcnow().isoformat(),
            failed_series=result["failed"],
        )
        return f"bcb_macro: inserted={result['inserted']} updated={result['updated']}"
```

### Pattern 6: Cross-DB News Sync (news_sync.py)

**What:** Read from `news_hunter/banco.db` and upsert into `ingestion.db news_articles`. Dedup by URL.
**When to use:** `job_news_ingest()` calls subprocess for crawl, then calls this to sync.

```python
# Source: [VERIFIED: codebase — news_hunter/banco.py schema; CONTEXT.md D-03/D-05]
import sqlite3
from pathlib import Path
import uuid
from datetime import datetime

BANCO_DB = Path(__file__).parent.parent.parent / "news_hunter" / "banco.db"

def sync_news_to_ingestion_db(ingestion_conn: sqlite3.Connection,
                               limit: int = 500) -> int:
    """
    Read latest N articles from news_hunter/banco.db and upsert into
    ingestion.db news_articles. Returns count of new rows inserted.
    """
    src = sqlite3.connect(BANCO_DB)
    src.row_factory = sqlite3.Row

    rows = src.execute(
        """SELECT hash, titulo, link, fonte, categoria, data_pub, score
           FROM noticias
           ORDER BY data_coleta DESC
           LIMIT ?""",
        (limit,)
    ).fetchall()
    src.close()

    inserted = 0
    now = datetime.utcnow().isoformat()
    for row in rows:
        row_id = str(uuid.uuid4())
        try:
            ingestion_conn.execute(
                """INSERT OR IGNORE INTO news_articles
                   (id, url, title, published_at, source, score, ingested_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (row_id, row["link"], row["titulo"],
                 row["data_pub"], row["fonte"], row["score"], now)
            )
            if ingestion_conn.execute(
                "SELECT changes()"
            ).fetchone()[0] > 0:
                inserted += 1
        except Exception:
            pass
    ingestion_conn.commit()
    return inserted
```

**banco.db schema confirmed (from codebase read):**
- Table: `noticias`
- Columns: `id`, `hash`, `titulo`, `link`, `fonte`, `categoria`, `data_coleta`, `data_pub`, `conteudo`, `alertado`, `score`, `subcategoria`, `urgente`, `resumo_curto`, `motivo_score`
- Dedup key: `hash` = SHA-256 of `titulo + link`
- In ingestion.db, dedup is by `url` (UNIQUE INDEX on `news_articles.url`)

### Pattern 7: CVM IPE Download and PDF Extraction

**What:** Download IPE ZIP, filter for watchlist tickers, extract PDF text using pdfplumber.
**When to use:** `job_cvm_ingest()` after DFP/ITR download.

```python
# Source: [VERIFIED: live CVM API probe 2026-05-10 — confirmed IPE CSV structure]
# IPE CSV columns: CNPJ_Companhia, Nome_Companhia, Codigo_CVM, Data_Referencia,
#                  Categoria, Tipo, Especie, Assunto, Data_Entrega,
#                  Tipo_Apresentacao, Protocolo_Entrega, Versao, Link_Download
# Encoding: iso-8859-1 (same as DFP/ITR)

def download_ipe(year: int, output_dir: Path) -> list[Path]:
    """Download and extract IPE CSV for a year. Same pattern as download_dfp."""
    url = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/ipe_cia_aberta_{year}.zip"
    # ... same _download_and_extract pattern as CVMDownloader

def extract_ipe_pdf_text(pdf_url: str) -> str:
    """Download IPE PDF from Link_Download and extract text with pdfplumber."""
    import pdfplumber
    resp = requests.get(pdf_url, timeout=60)
    resp.raise_for_status()
    with pdfplumber.open(io.BytesIO(resp.content)) as pdf:
        return "\n".join(
            page.extract_text() or "" for page in pdf.pages[:10]  # cap at 10 pages
        )
```

**IPE classification via CSV columns:**
- `Categoria`: "Assembleia", "Comunicado ao Mercado", "Aviso aos Acionistas", "Fato Relevante", "Resultados", etc.
- `Tipo`: specific sub-type (e.g., "AGE", "ITR", "DFP")
- `Especie`: document type description
- Map `Categoria` to event_type enum: `{ "Resultados": "earnings", "Fato Relevante": "material_fact", "Assembleia": "meeting", ... }`

### Anti-Patterns to Avoid

- **Storing all companies from CVM ZIP**: ZIPs contain ALL Brazilian public companies (~600+). Filter by `CD_CVM` from `cvm_codes.yaml` immediately after reading CSV — never write unfiltered data to DB.
- **Using AUTOINCREMENT INTEGER as primary key**: Breaks Supabase migration. Use `TEXT PRIMARY KEY` with `str(uuid.uuid4())` as required by D-06.
- **Interpolating price gaps**: ING-05 is explicit — insert `is_gap=1` rows, never fill with estimated prices.
- **Calling BCB SGS with `inicio="01/01/2010"` every time**: This re-downloads years of history on every run. Do incremental: query `MAX(date)` from `macro_series` for the series, set `inicio` to that date.
- **Running news_hunter blocking in the scheduler process**: Use `subprocess.run()` with a timeout. The news_hunter process has its own logging/config and must not inherit the scheduler's loguru context.
- **Not calling `init_db()` at job start**: The `ingestion.db` may not exist on first run. Each job function must call `init_db()` (idempotent) before any DB write.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| B3 trading calendar | Custom holiday list | `pandas_market_calendars` with `BMFBOVESPA` | Handles all B3 holidays, carnaval, etc.; manual list is error-prone and stale |
| CDS Brasil time series | ANBIMA scraper | BCB SGS series 29039 | Confirmed available via live probe; 28 records 2024–2026; no auth required |
| PDF text extraction | Custom PDF parser | `pdfplumber.open()` | pdfplumber already installed; handles multi-page PDFs, encoding issues |
| Retry with backoff | Custom sleep loop | `@retry` from `src/utils/retry.py` | Already implements exponential backoff + jitter + IngestionError (Phase 1) |
| Deduplication logic | Application-level set tracking | `INSERT OR IGNORE` + `UNIQUE INDEX` | SQLite guarantees consistency across runs; no in-memory state needed |
| Job scheduling | `time.sleep()` loop | APScheduler `BlockingScheduler` | Already wired; handles timezone (America/Sao_Paulo), coalesce, misfire_grace_time |
| Run ID tracking | Global variable | `bind_run_id()` context manager | Already implemented in Phase 1; loguru contextualize carries run_id through call stack |

**Key insight:** The existing infrastructure from Phase 1 (`@retry`, `bind_run_id`, `IngestionError`) plus the existing ingestion classes (`CVMDownloader`, `B3Scraper`) already handle the hardest parts. Phase 2 is mostly connecting these to SQLite writes — not building new capabilities from scratch.

---

## Common Pitfalls

### Pitfall 1: CVM CSV Encoding
**What goes wrong:** `pd.read_csv()` with default `encoding='utf-8'` raises UnicodeDecodeError; CVM files use `iso-8859-1`.
**Why it happens:** CVM data portal generates CSVs in Windows-1252/latin-1 encoding. `dfp_parser.py` already handles this correctly (`encoding="iso-8859-1"`, `separator=";"`), but any new CSV reader must replicate this.
**How to avoid:** Always use `encoding="iso-8859-1"` and `sep=";"` for all CVM CSVs (DFP, ITR, and IPE confirmed via live probe).
**Warning signs:** Error message containing "codec can't decode byte" or garbled accented characters.

### Pitfall 2: yfinance 1.3.x API Changes
**What goes wrong:** yfinance 1.3.0 may return different column names than 0.2.x. The `b3_scraper.py` already handles `MultiIndex` columns from yfinance batch downloads, but single-ticker downloads can still return differently.
**Why it happens:** yfinance changed internal data format in 1.x to use MultiIndex for multi-ticker downloads.
**How to avoid:** Use the existing `_download()` method in `B3Scraper` which already normalizes columns. When extending, keep the `isinstance(raw.columns, pd.MultiIndex)` check.
**Warning signs:** `KeyError: 'Close'` or `KeyError: 'close'` when accessing columns after download.

### Pitfall 3: BCB SGS Rate Limits
**What goes wrong:** Rapid sequential calls to BCB SGS API trigger HTTP 429 or connection resets.
**Why it happens:** BCB imposes soft rate limits on the public API. The legacy `03_coletor_macro.py` does not have retry decorators.
**How to avoid:** Wrap each `fetch_series()` call with `@retry(attempts=3, delay=2.0, backoff=2.0)`. Add `time.sleep(0.5)` between series fetches as a courtesy rate limit.
**Warning signs:** `requests.exceptions.ConnectionError` or `HTTPError: 429` in the middle of a batch of 5 series fetches.

### Pitfall 4: news_hunter subprocess path issues
**What goes wrong:** `subprocess.run(["python", "news_hunter/main.py", "--coletar"])` fails with `No module named banco` because the working directory is not set to `news_hunter/`.
**Why it happens:** `news_hunter/main.py` uses bare `import banco` (not `news_hunter.banco`) — it expects to be run from within its own directory.
**How to avoid:** Set `cwd` in `subprocess.run()` to the news_hunter directory:
```python
subprocess.run(
    [sys.executable, "main.py", "--coletar"],
    cwd=Path(__file__).parent.parent / "news_hunter",
    timeout=300
)
```
**Warning signs:** `ModuleNotFoundError: No module named 'banco'` in subprocess stderr.

### Pitfall 5: CVM IPE ZIP is large — download rate limiting
**What goes wrong:** IPE ZIP for a full year (e.g., `ipe_cia_aberta_2025.zip`) is ~2.3 MB. Downloading yearly ZIPs for multiple years in a loop without rate limiting triggers the CVM server's rate limit.
**Why it happens:** CVM portal enforces a soft rate limit on bulk downloads (same as DFP/ITR). The existing `CVMDownloader` already has `RATE_LIMIT_SECONDS = 1.5` between downloads — replicate this for IPE.
**How to avoid:** Reuse the same `RATE_LIMIT_SECONDS = 1.5` pause between year downloads; check cache existence before re-downloading.
**Warning signs:** HTTP 403 or connection hangs after several consecutive downloads.

### Pitfall 6: pandas_market_calendars not installed
**What goes wrong:** `import pandas_market_calendars as mcal` raises `ModuleNotFoundError`. This affects D-12 freshness check and gap detection in ING-05.
**Why it happens:** `pandas-market-calendars` is referenced in CLAUDE.md and CONTEXT.md D-12 but is NOT in `pyproject.toml` and is NOT installed in the venv (confirmed via `pip show`).
**How to avoid:** Add `pandas-market-calendars` to `pyproject.toml` `[project.dependencies]` and run `pip install pandas-market-calendars` in the venv before implementing any freshness/gap logic. Include this as a Wave 0 task.
**Warning signs:** `ModuleNotFoundError: No module named 'pandas_market_calendars'` at runtime.

### Pitfall 7: CVM CD_CVM zero-padding
**What goes wrong:** Filtering CVM CSV by `CD_CVM` fails silently if zero-padding is not applied. CVM stores codes as e.g. `"1023"` (4 digits) but `get_cvm_code()` returns `"001023"` (6 digits with `.zfill(6)`).
**Why it happens:** CVM CSVs inconsistently pad the CD_CVM field. `dfp_parser.py` handles this correctly with `.str.zfill(6)`, but any new CSV reader that compares raw values will miss rows.
**How to avoid:** Always normalize: `df["CD_CVM"].str.strip().str.zfill(6)`. The IPE CSV uses `Codigo_CVM` (without leading zeros in the live probe: `"1023"` for Banco do Brasil). Apply the same normalization.
**Warning signs:** Zero rows returned when filtering by CVM code even though the company is known to be in the file.

---

## Code Examples

### CVM CSV Field Reference (verified via live IPE probe)

```
DFP/ITR CSV columns (from dfp_parser.py):
  CNPJ_CIA, DT_REFER, VERSAO, DENOM_CIA, CD_CVM, ESCALA_MOEDA, MOEDA,
  ORDEM_EXERC, DT_FIM_EXERC, CD_CONTA, DS_CONTA, VL_CONTA, ST_CONTA_FIXA

IPE CSV columns (verified 2026-05-10, ipe_cia_aberta_2025.zip):
  CNPJ_Companhia, Nome_Companhia, Codigo_CVM, Data_Referencia, Categoria,
  Tipo, Especie, Assunto, Data_Entrega, Tipo_Apresentacao,
  Protocolo_Entrega, Versao, Link_Download

Encoding: iso-8859-1  Separator: ;
```

### BCB SGS Series Verified (live probe 2026-05-10)

```
Series 11  (Selic Over):  last={'data': '08/05/2026', 'valor': '0.053400'}
Series 433 (IPCA 12m):    last={'data': '01/03/2026', 'valor': '0.88'}
Series 1   (PTAX USD):    last={'data': '08/05/2026', 'valor': '4.8999'}
Series 29039 (CDS Brasil): last={'data': '01/04/2026', 'valor': '94.47'}
Series 4380 (PIB nominal): last={'data': '01/03/2026', 'valor': '1153875.8'}

BCB API endpoint: https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados
Required params: formato=json, dataInicial=dd/mm/yyyy, dataFinal=dd/mm/yyyy
CDS nota: valores em pontos-base (94.47 bp). Divide por 10.000 para decimal.
```

### Adding a Job to scheduler.py

```python
# Source: [VERIFIED: codebase — src/scheduler.py _JOB_REGISTRY pattern]

# Step 1: Define the function
def job_bcb_macro() -> str:
    with bind_run_id("ingest") as run_id:
        log.info(f"[bcb_macro] run_id={run_id}")
        ...
        return "bcb_macro: inserted=N"

# Step 2: Register in _JOB_REGISTRY
_JOB_REGISTRY: dict[str, Callable] = {
    # ... existing jobs ...
    "cvm_ingest":  job_cvm_ingest,   # NEW
    "bcb_macro":   job_bcb_macro,    # NEW
    "b3_prices":   job_b3_prices,    # REPLACE existing stub
    "news_ingest": job_news_ingest,  # NEW
}

# Step 3: Add to config/schedules.yaml
# - job: cvm_ingest
#   cron: "0 19 * * 1-5"
#   description: Ingestão CVM DFP/ITR/IPE
```

### Incremental BCB Fetch Pattern

```python
# Source: [VERIFIED: codebase — bcb_coletor_macro pattern + ingestion.db schema]
import sqlite3
from datetime import datetime

def get_last_date_for_series(conn: sqlite3.Connection, series_code: int) -> str:
    """Returns 'dd/mm/yyyy' for the most recent date in macro_series, or 5 years ago."""
    row = conn.execute(
        "SELECT MAX(date) FROM macro_series WHERE series_code = ?",
        (series_code,)
    ).fetchone()
    if row and row[0]:
        d = datetime.fromisoformat(row[0])
        return d.strftime("%d/%m/%Y")
    return "01/01/2019"  # default history start
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw price data in Parquet files (`data/raw/prices/{TICKER}.parquet`) | Price data in `price_ohlcv` table in `ingestion.db` | Phase 2 (this phase) | Phase 3 reads from DB, not Parquet; Parquet files deprecated after migration |
| BCB macro data in cached Parquet files (`bcb_serie_{cod}.parquet`) | Macro data in `macro_series` table | Phase 2 | Same benefit: single source of truth for Phase 3 |
| news_hunter standalone daemon (`agendador.py`) | Absorbed into `src/scheduler` via subprocess bridge | Phase 2 D-02 | Single scheduler, unified run_id, `agendador.py` disabled |
| CVM data downloaded but never written to DB | CVM CSV → DB (`cvm_statements`) | Phase 2 | Phase 3 Financial Engine reads from DB via SQL, not from CSV files |

**Deprecated/outdated:**
- `data/raw/prices/*.parquet`: Deprecated after Phase 2. Keep files for backward compat but Phase 3 reads from `price_ohlcv` table.
- `news_hunter/agendador.py`: Disable (D-02). Do not delete — leave as dead code until Phase 5 refactor.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | IPE PDF text extraction with pdfplumber works for CVM's RAD format PDFs | Code Examples (Pattern 7) | PDFs may use image scanning (non-searchable) — text extraction returns empty string; store empty string, flag for manual review |
| A2 | `news_hunter/main.py --coletar` is the correct argument for running a collection cycle | Pattern 4 (subprocess bridge) | Different argument may be required; actual flags are `--coletar`, `--coletar-e-gerar`, `--coletar-gerar-enviar` — use `--coletar` for Phase 2 |
| A3 | `pandas_market_calendars` BMFBOVESPA calendar includes all B3 holidays through 2026 | Pattern 3 (freshness check) | Calendar may lag; minor impact — one extra WARNING log on holidays is acceptable |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

A1 is LOW risk (empty text is handled gracefully). A2 is VERIFIED (read main.py directly). A3 is LOW risk. No user confirmation needed for any assumption.

---

## Open Questions

1. **IPE PDF text extraction quality for CVM documents**
   - What we know: pdfplumber works for standard text PDFs; IPE PDFs are delivered via `Link_Download` on `rad.cvm.gov.br`
   - What's unclear: Whether RAD-generated PDFs are searchable-text or scanned images. CVM's older documents may be scanned.
   - Recommendation: Implement text extraction with fallback to empty string + `extraction_failed=True` flag; do not block ingestion if PDF text is empty.

2. **news_hunter ticker tagging**
   - What we know: `news_hunter/banco.db` has `categoria` (e.g., "BBAS3") and `classificador.py` does ticker detection; the `news_articles.ticker_tags` column in the design is a JSON array
   - What's unclear: Whether the existing classificador assigns tickers reliably, or whether the `ticker_tags` field in `ingestion.db` needs a separate pass over the synced articles using tickers.yaml
   - Recommendation: In Phase 2, sync without re-tagging. Store `categoria` from banco.db as a single-item `ticker_tags` where available. Full ticker tagging can be a Phase 4 enrichment.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| sqlite3 | ingestion.db | ✓ | built-in Python | — |
| requests | CVM, BCB, IPE PDF | ✓ | 2.33.1 | — |
| yfinance | B3 prices | ✓ | 1.3.0 | — |
| pdfplumber | IPE PDF text extraction | ✓ | 0.11.9 | Skip text extraction, store empty string |
| apscheduler | Job scheduling | ✓ | 3.11.2 | — |
| pandas | CSV parsing, data manipulation | ✓ | 2.3.3 | — |
| loguru | Logging | ✓ | 0.7.3 | — |
| pyyaml | Config loading | ✓ | 6.0.3 | — |
| pandas-market-calendars | D-12 freshness, gap detection | ✗ | — | Manual business day calculation (error-prone; not recommended) |

**Missing dependencies with no fallback:**
- `pandas-market-calendars`: Required for D-12 (BCB freshness check) and ING-05 (gap detection). Must be installed before implementing those features. Add to pyproject.toml and run `pip install pandas-market-calendars` in venv. **This is a Wave 0 blocker.**

**Missing dependencies with fallback:**
- None.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ --cov=src --cov-report=term-missing` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ING-01 | CVM DFP CSV filtered by CD_CVM, stored in cvm_statements | unit | `pytest tests/test_cvm_ingestion.py -x` | ❌ Wave 0 |
| ING-02 | CVM ITR parsed and reconciled with DFP (dedup by ticker+account_code+date) | unit | `pytest tests/test_cvm_ingestion.py::test_itr_dedup -x` | ❌ Wave 0 |
| ING-03 | IPE CSV filtered, event_type classified, PDF text extracted | unit | `pytest tests/test_ipe_ingestion.py -x` | ❌ Wave 0 |
| ING-04 | BCB series fetched, stored with freshness timestamp, stale triggers WARNING | unit + integration | `pytest tests/test_bcb_ingestion.py -x` | ❌ Wave 0 |
| ING-05 | B3 prices stored in price_ohlcv; gap dates have is_gap=1 | unit | `pytest tests/test_b3_ingestion.py -x` | ❌ Wave 0 |
| ING-06 | News articles synced from banco.db, deduplicated by URL | unit | `pytest tests/test_news_sync.py -x` | ❌ Wave 0 |
| ING-07 | Scheduler jobs exist in registry; summary log emitted after run | unit | `pytest tests/test_scheduler_ingestion.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ --cov=src --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cvm_ingestion.py` — covers ING-01, ING-02
- [ ] `tests/test_ipe_ingestion.py` — covers ING-03
- [ ] `tests/test_bcb_ingestion.py` — covers ING-04
- [ ] `tests/test_b3_ingestion.py` — covers ING-05
- [ ] `tests/test_news_sync.py` — covers ING-06
- [ ] `tests/test_scheduler_ingestion.py` — covers ING-07
- [ ] pyproject.toml: add `pandas-market-calendars` to dependencies

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Public APIs (CVM, BCB) require no auth; news_hunter uses no auth |
| V3 Session Management | no | CLI/daemon; no HTTP sessions |
| V4 Access Control | no | Single-user local tool |
| V5 Input Validation | yes | Validate BCB API responses before insert (numeric type check, date format); validate CVM CSV row count > 0 before processing |
| V6 Cryptography | no | No encryption needed for local SQLite; credentials in .env (Phase 1 resolved) |

### Known Threat Patterns for Data Ingestion Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via ticker names or CVM fields | Tampering | Use parameterized queries (`?` placeholders) in all sqlite3 execute calls — never f-string SQL |
| Subprocess injection (news_hunter) | Elevation of Privilege | Use `subprocess.run([sys.executable, "main.py", "--coletar"], ...)` with list form (not shell=True) |
| Unvalidated numeric data from BCB API | Tampering | `pd.to_numeric(..., errors="coerce")` + check for NaN before insert; log and skip invalid rows |

---

## Project Constraints (from CLAUDE.md)

- **Canonical source**: `Analista de Investimentos/12_PYTHON/src/`. No other copies.
- **No hardcoded credentials**: All API keys via `.env`; BCB and CVM are public APIs with no auth needed; no credentials to add.
- **`tenacity` retry on every external API call**: The project uses a custom `@retry` decorator from `src/utils/retry.py` (not tenacity directly), which satisfies the same requirement. Use the existing `@retry`.
- **`instructor` + Pydantic schema**: Only applies to AI thesis generation (Phase 4). Not applicable to ingestion.
- **Input hash gates thesis regeneration**: Phase 4 concern only.
- **SQLite local-first; schema designed for SQLite→Supabase**: Enforced via D-06 — TEXT UUID PKs, ISO date strings, no AUTOINCREMENT.
- **`structlog` for logging**: CLAUDE.md says structlog, but Phase 1 implemented loguru (FOUND-04 completed with loguru per STATE.md). All Phase 2 code uses loguru (`get_logger`, `bind_run_id`). No structlog added.
- **Jinja2 for prompts**: Phase 4 concern only.
- **Bank/industrial model bifurcation**: Phase 3 concern. Phase 2 ingests all tickers uniformly.
- **B3 `.SA` suffix for yfinance**: Already implemented in `b3_scraper.py` (`_SA_SUFFIX = ".SA"`).
- **`pandas_market_calendars` with `BMFBOVESPA`**: Required by CLAUDE.md; currently not installed — must be added.

---

## Sources

### Primary (HIGH confidence)
- `src/ingestion/cvm_downloader.py` — full code read; CVM ZIP URL pattern, `@retry` integration, `get_cvm_code()` API
- `src/ingestion/b3_scraper.py` — full code read; yfinance usage, `auto_adjust=True`, MultiIndex handling
- `pipeline banco completo/modules/03_coletor_macro.py` — full code read; BCB SGS URL, series codes, CDS handling
- `src/scheduler.py` — full code read; `IntelligenceScheduler`, `_JOB_REGISTRY`, `_run_job()` pattern
- `src/utils/retry.py`, `src/utils/logger.py`, `src/utils/errors.py` — full code read; Phase 1 infrastructure confirmed
- `news_hunter/banco.py` — full code read; banco.db schema, `noticias` table structure
- `news_hunter/main.py` — full code read; `--coletar` argument, subprocess entry point
- `src/parsers/dfp_parser.py` — full code read; `ACCOUNT_MAP`, CSV columns, encoding, SCALE_MAP
- `config/tickers.yaml` — full read; 80+ tickers, `active: true/false` pattern
- `config/cvm_codes.yaml` — partial read; ticker → CD_CVM mapping confirmed
- `config/schedules.yaml` — full read; existing cron pattern, 9 existing jobs
- `config/settings.py` — full read; `settings.active_tickers`, path configuration
- `pyproject.toml` — full read; installed dependencies confirmed

### Live API Probes (HIGH confidence, 2026-05-10)
- BCB SGS series 11, 433, 1, 29039, 4380 — all confirmed returning data, last values documented
- CVM IPE endpoint `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/` — HTTP 200
- CVM IPE CSV structure — downloaded and inspected `ipe_cia_aberta_2025.zip`

### Package Installation Verification (HIGH confidence)
- `pip list` output captured 2026-05-10: yfinance 1.3.0, pdfplumber 0.11.9, apscheduler 3.11.2, pandas 2.3.3, requests 2.33.1
- `pandas-market-calendars` confirmed NOT installed

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified via `pip list` probe
- CVM CSV structure: HIGH — live download and inspection of IPE ZIP
- BCB API availability: HIGH — live API probes with actual data values
- Architecture patterns: HIGH — derived directly from existing codebase
- Pitfalls: HIGH — derived from existing code patterns + known CVM data quirks

**Research date:** 2026-05-10
**Valid until:** 2026-06-10 (BCB series codes are stable; CVM CSV format rarely changes)

---

## RESEARCH COMPLETE
