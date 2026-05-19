---
phase: 02-reliable-data-ingestion
plan: "01"
subsystem: database
tags: [sqlite, cvm, dfp, itr, ipe, pdfplumber, pandas, ingestion, brazil]

# Dependency graph
requires:
  - phase: 01-foundation-and-cleanup
    provides: "retry decorator, IngestionError, get_logger, bind_run_id, settings, .env wiring"
provides:
  - "ingestion.db SQLite schema: cvm_statements, macro_series, price_ohlcv, news_articles"
  - "init_db() idempotent schema creation with TEXT UUID PKs and UNIQUE dedup indexes"
  - "get_connection() returning sqlite3.Connection with row_factory=sqlite3.Row"
  - "CVMDownloader.write_to_db() parameterized INSERT OR IGNORE into cvm_statements"
  - "CVMDownloader.parse_and_store() full DFP/ITR pipeline: download -> filter -> raw CSV save -> dedup -> DB write"
  - "CVMDownloader.parse_and_store_ipe() full IPE pipeline: download -> classify -> PDF extract -> DB write"
  - "classify_event() mapping CVM Categoria to internal event_type strings"
  - "extract_ipe_pdf_text() safe PDF extraction capped at 10 pages, returns '' on failure"
  - "pandas-market-calendars>=4.3.0 installed (BMFBOVESPA calendar support)"
affects: [02-02, 02-03, 02-04, financial-engine, intelligence-layer]

# Tech tracking
tech-stack:
  added:
    - "pandas-market-calendars>=4.3.0 (added to pyproject.toml, installed in venv)"
    - "pdfplumber (already installed, now wired into cvm_downloader.py)"
    - "sqlite3 stdlib (ingestion.db schema via db.py)"
  patterns:
    - "TEXT UUID PRIMARY KEY pattern (D-06 compliance: no AUTOINCREMENT, portable to Supabase)"
    - "INSERT OR IGNORE + UNIQUE INDEX for idempotent ingestion (no ON CONFLICT REPLACE)"
    - "Parameterized queries exclusively — no f-string SQL anywhere (T-02-01 mitigation)"
    - "TDD RED/GREEN cycle per task: failing tests committed first, then implementation"
    - "Module-level function + instance method delegation (get_cvm_code: module + CVMDownloader.get_cvm_code)"

key-files:
  created:
    - "Analista de Investimentos/12_PYTHON/src/ingestion/db.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_db_schema.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_cvm_ingestion.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_ipe_ingestion.py"
  modified:
    - "Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py"
    - "Analista de Investimentos/12_PYTHON/pyproject.toml"

key-decisions:
  - "TEXT PRIMARY KEY (UUID) on all 4 tables — not INTEGER AUTOINCREMENT (D-06: portability to Supabase)"
  - "INSERT OR IGNORE + UNIQUE INDEX for dedup — avoids ON CONFLICT REPLACE which could corrupt rows"
  - "extract_ipe_pdf_text() capped at 10 pages to mitigate T-02-03 (large PDF DoS)"
  - "normalized_name=None in parse_and_store() — Phase 3 enrichment will populate via ACCOUNT_MAP"
  - "get_cvm_code() added as CVMDownloader instance method delegating to module-level function (test compatibility)"
  - "pandas-market-calendars version pinned >=4.3.0 (installed as 5.3.2 — compatible)"

patterns-established:
  - "TDD cycle: test commit (RED) -> implementation commit (GREEN) per task"
  - "All DB writes use parameterized queries only — no string interpolation in SQL"
  - "Raw CSV preservation before DB insert: data/raw/cvm/{year}/{ticker}_{period}_{stem}.csv"
  - "Rate limiting: time.sleep(RATE_LIMIT_SECONDS) before every CVM HTTP request"

requirements-completed: [ING-01, ING-02, ING-03]

# Metrics
duration: 8min
completed: 2026-05-10
---

# Phase 2 Plan 01: Ingestion DB Schema + CVM Downloader Extension Summary

**SQLite ingestion.db with 4-table schema (TEXT UUID PKs, UNIQUE indexes) + CVMDownloader extended for DFP/ITR/IPE pipeline with raw CSV preservation, ITR deduplication, and pdfplumber IPE text extraction**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-11T01:51:33Z
- **Completed:** 2026-05-11T01:59:53Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 6

## Accomplishments

- Created `src/ingestion/db.py` with `init_db()` (idempotent, all 4 tables, UNIQUE indexes) and `get_connection()` (row_factory=sqlite3.Row)
- Extended `CVMDownloader` with `write_to_db()`, `parse_and_store()`, `parse_and_store_ipe()`, `download_ipe()`, `classify_event()`, `extract_ipe_pdf_text()`
- 19 tests green (5 db schema + 5 DFP/ITR ingestion + 9 IPE ingestion) — ING-01, ING-02, ING-03 satisfied
- pandas-market-calendars added to pyproject.toml and installed (5.3.2)

## Task Commits

Each task was committed atomically with TDD cycle:

1. **Task 1 RED: db.py schema tests** - `70e9856` (test)
2. **Task 1 GREEN: db.py + pyproject.toml** - `2c8a940` (feat)
3. **Task 2 RED: CVM+IPE ingestion tests** - `1ac1268` (test)
4. **Task 2 GREEN: extended cvm_downloader.py** - `e0f6845` (feat)

Note: All commits are in the `Analista de Investimentos` submodule (git submodule of OBSIDIAN root).

## Files Created/Modified

- `src/ingestion/db.py` — SQLite schema module: `init_db()`, `get_connection()`, `DB_PATH`, `_CREATE_SQL`
- `src/ingestion/cvm_downloader.py` — Extended with 7 new functions/methods for DB write, IPE, PDF
- `pyproject.toml` — Added `pandas-market-calendars>=4.3.0` under Ingestion dependencies
- `tests/test_db_schema.py` — 5 tests for db.py schema (ING-01 schema requirements)
- `tests/test_cvm_ingestion.py` — 5 tests for DFP/ITR pipeline (ING-01, ING-02)
- `tests/test_ipe_ingestion.py` — 9 tests for IPE pipeline (ING-03)

## Decisions Made

- **TEXT UUID PRIMARY KEY** on all tables: ensures portability to Supabase UUID PKs (D-06), avoids SQLite-specific AUTOINCREMENT behavior
- **INSERT OR IGNORE + UNIQUE INDEX** for dedup: cleaner than ON CONFLICT REPLACE (which overwrites rows, losing ingested_at timestamps)
- **normalized_name=None** in parse_and_store(): intentional deferral to Phase 3 enrichment via ACCOUNT_MAP lookups
- **extract_ipe_pdf_text() capped at 10 pages**: mitigates T-02-03 (DoS via large CVM PDFs)
- **get_cvm_code() added as instance method**: delegates to module-level function; required by test_cvm_ingestion.py test pattern `downloader.get_cvm_code("BBAS3")`
- **pandas-market-calendars pinned >=4.3.0**, installed as 5.3.2 (compatible, tested)

## Deviations from Plan

None — plan executed exactly as written. The `write_to_db(self` grep check in acceptance criteria returned 0 because the method signature spans multiple lines (multi-line def), but the method exists and 14 tests confirm it works correctly.

## Issues Encountered

- `Analista de Investimentos` directory is a git submodule — commits must be made inside the submodule first, then the outer OBSIDIAN repo references the updated submodule pointer. Handled correctly throughout.
- `test_itr_reconciliation_keeps_ultimo` required careful encoding: "ÚLTIMO" in latin-1 is `\xda\x4c\x54\x49\x4d\x4f` (Ú = 0xDA). Test CSV written as bytes with `encode("latin-1")` to match CVM real-world encoding.

## User Setup Required

None — no external service configuration required. CVM is a public API with no authentication.

## Next Phase Readiness

- ING-01 (DFP/ITR ingestion), ING-02 (ITR dedup), ING-03 (IPE events) all satisfied
- `init_db()` and `get_connection()` ready for Plan 02-02 (BCB/SGS macro series) and Plan 02-03 (yfinance price OHLCV)
- `write_to_db()` parameterized pattern established for all future ingestion writers
- `pandas-market-calendars` available for BMFBOVESPA holiday calendar (Plan 02-03)

## Self-Check

### Files Exist

- `src/ingestion/db.py` — FOUND
- `src/ingestion/cvm_downloader.py` — FOUND (extended)
- `tests/test_db_schema.py` — FOUND
- `tests/test_cvm_ingestion.py` — FOUND
- `tests/test_ipe_ingestion.py` — FOUND
- `pyproject.toml` contains `pandas-market-calendars>=4.3.0` — FOUND

### Commits Exist (submodule)

- `70e9856` test(02-01): add failing tests for db.py schema — RED phase — FOUND
- `2c8a940` feat(02-01): create db.py schema module + add pandas-market-calendars — FOUND
- `1ac1268` test(02-01): add failing tests for CVM+IPE ingestion — RED phase — FOUND
- `e0f6845` feat(02-01): extend cvm_downloader — DB write, IPE download, PDF extraction — FOUND

## Self-Check: PASSED

---
*Phase: 02-reliable-data-ingestion*
*Completed: 2026-05-10*
