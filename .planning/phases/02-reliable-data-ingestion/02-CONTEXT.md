# Phase 2: Reliable Data Ingestion - Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire all four ingestion channels (CVM filings, BCB macro, B3 prices, news) into `src/` with daily scheduling, freshness timestamps, deduplication, and gap detection. Output: a unified `data/ingestion.db` SQLite database that the Financial Engine (Phase 3) can trust as authoritative. `news_hunter/` stays structurally intact but its scheduling is absorbed by `src/scheduler`.

</domain>

<decisions>
## Implementation Decisions

### news_hunter/ Integration
- **D-01:** Subprocess bridge — `src/scheduler` adds a job that calls `news_hunter/main.py` via subprocess. `news_hunter/` internals are NOT refactored. Satisfies ING-06/ING-07 without rewriting a working system.
- **D-02:** `src/scheduler` takes over scheduling for news_hunter. Disable `news_hunter/agendador.py` (or leave it disabled by not launching it). Single scheduler, single `run_id` per pipeline run via `bind_run_id`.
- **D-03:** `news_hunter/banco.db` stays separate — do NOT migrate into `ingestion.db`. `src/` reads news articles from `banco.db` via direct SQL query when needed by downstream phases.

### SQLite Schema
- **D-04:** Create unified `data/ingestion.db` with 4 source tables: `cvm_statements`, `macro_series`, `price_ohlcv`, `news_articles`. All tables include `ingested_at` (UTC timestamp) and `ticker` (where applicable). This is the canonical data store for Phase 3+.
- **D-05:** `news_articles` in `ingestion.db` is populated by reading from `news_hunter/banco.db` (cross-DB query or periodic sync) — NOT by redirecting news_hunter writes. Keeps D-03 intact.
- **D-06:** Schema designed for SQLite→Supabase migration: no SQLite-specific types, use ISO strings for dates, avoid AUTOINCREMENT where UUID is more portable.

### CVM Raw Format
- **D-07:** Keep CSV format from CVM ZIP downloads (current `cvm_downloader.py` approach). "Raw XML" in ING-01 was aspirational — CSV covers all required fields. No switch to CVM XML endpoint.
- **D-08:** Store raw CSVs for watchlist-only tickers (not all companies in the ZIP). Lean `data/raw/cvm/` directory. Adding new tickers to `tickers.yaml` requires re-extract but not re-download if the ZIP is cached.
- **D-09:** Raw CSV extraction is the "preserve raw" step for ING-01 compliance. Store in `data/raw/cvm/{year}/{ticker}/` before parsing into `cvm_statements` table.

### BCB SGS Ingestion
- **D-10:** Lift-and-adapt from `pipeline banco completo/modules/03_coletor_macro.py` — extract BCB SGS API calls and adapt to `src/` patterns (`@retry`, `IngestionError`, `get_logger`). Do not copy module-level logic, only the API fetch pattern.
- **D-11:** Series to ingest: Selic (código 11), IPCA (código 433), PTAX USD (código 1), CDS Brazil (external source — note: BCB SGS may not carry CDS; verify during implementation), PIB (código 4380).
- **D-12:** Freshness threshold: >1 Brazilian business day = stale. Use `pandas_market_calendars` with `BMFBOVESPA` calendar to compute business day offset. Log WARNING for any stale series — not ERROR (stale ≠ failure).

### Retry & Logging (from Phase 1)
- **D-13:** All new ingestion functions decorated with `@retry(attempts=3, delay=2.0, backoff=2.0, jitter=0.5, exceptions=(RequestException, ...))`. Exhaustion raises `IngestionError` (already implemented in Phase 1).
- **D-14:** Each scheduler job starts with `with bind_run_id("ingest") as run_id:` — all log calls within the job carry `run_id`. This is ING-07's "each run logged" requirement.

### Scheduler Health Summary (ING-07)
- **D-15:** After each full ingestion run, emit a structured summary log: source name, records inserted/updated, duration_ms, status (ok/failed), last_ingested_at. Log at INFO level. No separate health DB table needed in Phase 2.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §ING-01 through ING-07 — acceptance criteria for this phase
- `.planning/ROADMAP.md` §Phase 2 — goal, success criteria, 4 plans
- `.planning/PROJECT.md` — constraints (Python-only, reuse existing logic, SQLite→Supabase-compatible schema, no overengineering)

### Prior Phase Decisions
- `.planning/phases/01-foundation-and-cleanup/01-CONTEXT.md` — D-11 (news_hunter/ integration deferred to Phase 2), D-12/D-13/D-14 (retry infrastructure decisions), D-04/D-05 (loguru + contextvars for run_id)

### Existing Ingestion Code to Adapt
- `Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py` — current CVM ZIP download + CSV extraction (extend, don't replace)
- `Analista de Investimentos/12_PYTHON/src/ingestion/b3_scraper.py` — current yfinance B3 price scraper (extend with gap detection + ingestion.db write)
- `Analista de Investimentos/12_PYTHON/pipeline banco completo/modules/03_coletor_macro.py` — BCB SGS API calls to lift-and-adapt into `src/ingestion/bcb.py`
- `Analista de Investimentos/12_PYTHON/news_hunter/main.py` — subprocess entry point for news ingestion job

### Configuration
- `Analista de Investimentos/12_PYTHON/config/tickers.yaml` — active ticker registry (input for watchlist-only CVM extraction)
- `Analista de Investimentos/12_PYTHON/config/cvm_codes.yaml` — ticker → CD_CVM mapping (required for CVM download)
- `Analista de Investimentos/12_PYTHON/config/schedules.yaml` — APScheduler cron config (add ingestion schedule here)

### Utilities (Phase 1 output)
- `Analista de Investimentos/12_PYTHON/src/utils/retry.py` — `@retry` with jitter + IngestionError
- `Analista de Investimentos/12_PYTHON/src/utils/logger.py` — `bind_run_id()`, `get_logger()`
- `Analista de Investimentos/12_PYTHON/src/utils/errors.py` — `IngestionError` class

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/ingestion/cvm_downloader.py` — `get_cvm_code(ticker)` + ZIP download logic; extend with `ingestion.db` write and freshness tracking
- `src/ingestion/b3_scraper.py` — yfinance fetch to Parquet; redirect output to `price_ohlcv` table in `ingestion.db`
- `pipeline banco completo/modules/03_coletor_macro.py` — BCB SGS fetch pattern (adapt API calls only)
- `news_hunter/banco.db` — already populated SQLite with articles; `src/` reads from it via SQL
- `src/utils/retry.py` + `src/utils/errors.py` + `src/utils/logger.py` — Phase 1 infrastructure, apply to all new ingestion code

### Established Patterns
- Job functions: `job_<name>()` in `src/scheduler.py` — new ingestion jobs follow this naming
- Schedule registration: add cron expressions to `config/schedules.yaml`
- `with bind_run_id("ingest") as run_id:` at top of each scheduler job function
- `@retry(attempts=3, delay=2.0, backoff=2.0, jitter=0.5, exceptions=(SpecificErrors,))` on every external fetch
- Log message format: `f"[{ticker}] message"` with `f"[{ticker}] falha: {exc}"` for errors

### Integration Points
- `src/scheduler.py` — add 4 new job functions: `job_cvm_ingest()`, `job_bcb_macro()`, `job_b3_prices()`, `job_news_ingest()`
- `data/ingestion.db` — new unified SQLite DB (create via `src/ingestion/db.py` schema migrations)
- `config/schedules.yaml` — add ingestion schedule entries
- `news_hunter/main.py` — called as `subprocess.run(["python", "news_hunter/main.py", "--modo", "agora"])` from `job_news_ingest()`

</code_context>

<specifics>
## Specific Ideas

- `ingestion.db` schema: `cvm_statements(id, ticker, year, period_type, account_code, account_name, value, ingested_at)`, `macro_series(id, series_code, series_name, date, value, ingested_at)`, `price_ohlcv(id, ticker, date, open, high, low, close, adj_close, volume, ingested_at)`, `news_articles(id, url, title, published_at, source, ticker_tags, ingested_at)` — synced from `banco.db`
- BCB CDS Brazil: BCB SGS may not carry CDS Brazil spread directly — verify during research phase. Fallback: pull from ANBIMA or use `ipeadata` Python library (IPEA has CDS series).
- Watchlist-only CVM extraction: after downloading full ZIP, filter rows by `CD_CVM` from `cvm_codes.yaml`. Store filtered CSVs at `data/raw/cvm/{year}/{ticker}_{period}.csv`.
- IPE text extraction (ING-03): use `pdfplumber` or `PyMuPDF` for PDF text; store extracted text in `cvm_statements` or a separate `ipe_events` table.

</specifics>

<deferred>
## Deferred Ideas

- **news_hunter/ full refactor into src/ingestion/** — not in Phase 2. Full refactor when `pipeline banco completo/` is archived (Phase 5).
- **SQLAlchemy ORM layer** — v2 requirement. Phase 2 uses raw sqlite3 or `sqlite-utils`. ORM migration in v2 milestone.
- **FOCUS forecast integration** — BCB weekly consensus forecasts (v2 requirement). Not in Phase 2 scope.
- **Event-driven thesis refresh on IPE** — INT-05 requirement, belongs in Phase 4 (Intelligence Layer).

</deferred>

---

*Phase: 2-Reliable Data Ingestion*
*Context gathered: 2026-05-10*
