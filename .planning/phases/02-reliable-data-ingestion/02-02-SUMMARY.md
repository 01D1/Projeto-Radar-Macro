---
phase: 02-reliable-data-ingestion
plan: "02"
subsystem: ingestion
tags: [bcb, sgs, macro, yfinance, b3, sqlite, pandas-market-calendars, retry, tdd]

# Dependency graph
requires:
  - phase: 02-reliable-data-ingestion/02-01
    provides: db.py with init_db(), get_connection(), price_ohlcv and macro_series tables
  - phase: 01-foundation-and-cleanup
    provides: retry decorator, IngestionError, get_logger

provides:
  - BCB SGS macro series ingestion (bcb.py): fetch_series, ingest_all_series, get_last_date_for_series, is_stale
  - B3 OHLCV DB persistence (b3_scraper.py extensions): write_to_db, detect_and_insert_gaps, fetch_and_store
  - Incremental ingestion pattern for both BCB and B3 data sources
  - Explicit gap markers (is_gap=1) for missing B3 trading days

affects:
  - 02-03 (news ingestion — same ingestion.db, same @retry pattern)
  - 02-04 (pipeline orchestrator — will call ingest_all_series + fetch_and_store)
  - 03-financial-engine (reads macro_series.value and price_ohlcv for WACC/DCF)

# Tech tracking
tech-stack:
  added: []  # all deps already installed in 02-01 (requests, pandas-market-calendars)
  patterns:
    - "Incremental ingestion: query MAX(date) before fetch, use as dataInicial"
    - "INSERT OR IGNORE + UNIQUE INDEX: dedup without overwriting ingested_at"
    - "is_gap=1 sentinel rows: mark missing trading days instead of interpolating"
    - "Basis-point-to-decimal conversion: CDS Brasil raw / 10_000 before storage"
    - "TDD RED/GREEN cycle: failing test commit → implementation commit"

key-files:
  created:
    - "Analista de Investimentos/12_PYTHON/src/ingestion/bcb.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_bcb_ingestion.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_b3_ingestion.py"
  modified:
    - "Analista de Investimentos/12_PYTHON/src/ingestion/b3_scraper.py"

key-decisions:
  - "BCB_SERIES dict contains exactly 5 series: selic_over(11), ipca_12m(433), ptax_usd(1), cds_brasil(29039), pib_nominal(4380)"
  - "CDS Brasil series 29039 stored in decimal not basis points: raw / 10_000 at insert time"
  - "Stale series logs WARNING (not ERROR) so ingestion continues for other series"
  - "adj_close = close column value after yfinance auto_adjust=True (no separate adj column)"
  - "Gap rows inserted with NULL OHLCV prices — never interpolated or estimated"
  - "fetch_and_store() starts from MAX(date)+1day for existing tickers, DEFAULT_START only for new"

patterns-established:
  - "BCB freshness: is_stale() uses BMFBOVESPA calendar; exceptions caught → False (safe default)"
  - "B3 gap detection: BMFBOVESPA schedule diff against actual df.index dates"
  - "SQL safety: all execute() calls use ? parameterized placeholders, zero f-string SQL"

requirements-completed: [ING-04, ING-05]

# Metrics
duration: 7min
completed: "2026-05-11"
---

# Phase 2 Plan 02: BCB SGS + B3 OHLCV Ingestion Summary

**BCB macro series ingestion (5 SGS series with CDS basis-point conversion) and B3 OHLCV price persistence with explicit gap markers using BMFBOVESPA calendar**

## Performance

- **Duration:** 7 min
- **Started:** 2026-05-11T02:05:08Z
- **Completed:** 2026-05-11T02:11:39Z
- **Tasks:** 2
- **Files modified:** 4 (3 created, 1 extended)

## Accomplishments

- Created `src/ingestion/bcb.py` with 5-series incremental BCB SGS fetch, stale detection, CDS basis-point conversion, and INSERT OR IGNORE deduplication into macro_series
- Extended `src/ingestion/b3_scraper.py` with `write_to_db()`, `detect_and_insert_gaps()`, and `fetch_and_store()` — all writing to price_ohlcv with proper gap markers
- 15/15 tests green across both test suites (9 BCB + 6 B3); verified with `-v` run

## Task Commits

Each task was committed atomically:

1. **Task 1: Create bcb.py + tests (TDD)** - `509f310` (feat)
2. **Task 2: Extend b3_scraper.py + tests (TDD)** - `5c1cd03` (feat)

_Note: Both tasks followed TDD RED/GREEN cycle. RED phase confirmed failure before implementation._

## Files Created/Modified

- `src/ingestion/bcb.py` — BCB SGS API fetch with @retry, incremental start, CDS /10000 conversion, stale WARNING, INSERT OR IGNORE into macro_series
- `src/ingestion/b3_scraper.py` — Extended with write_to_db (is_gap=0), detect_and_insert_gaps (BMFBOVESPA calendar diff, is_gap=1), fetch_and_store (incremental MAX(date)+1)
- `tests/test_bcb_ingestion.py` — 9 tests covering ING-04: fetch mock, CDS conversion, incremental start, stale detection, WARNING log
- `tests/test_b3_ingestion.py` — 6 tests covering ING-05: insert/dedup, gap flagging, NULL gap prices, MultiIndex normalization, incremental fetch

## Decisions Made

- CDS Brasil basis-point conversion done at insert time (`raw / 10_000`), not at read time — simpler downstream
- `_INTER_SERIES_SLEEP = 0.5s` between BCB series calls to respect BCB soft rate limit
- `adj_close` set equal to `close` column (post auto_adjust=True) — yfinance adjusted value is already in `close`
- gap rows use SQL `INSERT OR IGNORE INTO price_ohlcv (id, ticker, date, is_gap, ingested_at)` — no price columns, so OHLCV columns remain NULL naturally

## Deviations from Plan

None — plan executed exactly as written. Both files match the prescribed implementation in `<action>` blocks precisely.

## Issues Encountered

The `Analista de Investimentos` directory is a nested git repo (tracked as a gitlink in the OBSIDIAN root). All commits were made from within the nested repo at `Analista de Investimentos/`. This is consistent with Plan 02-01 behavior.

## User Setup Required

None — no external service configuration required. BCB SGS API is public (no auth). yfinance is already installed in the venv.

## Known Stubs

None. Both modules produce real data writes to ingestion.db. The only "mock" in tests is test infrastructure (mocked HTTP calls).

## Threat Surface Scan

All STRIDE threats from the plan's threat_model are mitigated:

- T-02-06: `bcb.py` uses `?` parameterized placeholders exclusively — confirmed by grep gate (0 f-string SQL matches)
- T-02-07: `float(str(item["valor"]).replace(",", "."))` in try/except — invalid values logged and skipped
- T-02-08: `b3_scraper.py` uses `?` parameterized placeholders exclusively — confirmed by grep gate
- T-02-09: `_INTER_SERIES_SLEEP = 0.5` between BCB calls; @retry handles 429
- T-02-10: @retry(attempts=3, delay=3.0, backoff=2.0) already on `_download()`
- T-02-11: `is_stale()` catches all exceptions, returns False (safe default)

No new unplanned security surface introduced.

## Next Phase Readiness

- `ingest_all_series(conn)` and `fetch_and_store(ticker, conn)` ready for the pipeline orchestrator (Plan 02-04)
- Both modules call `init_db()` pattern from db.py — safe to call standalone
- BCB freshness check (is_stale) and B3 gap detection in place for data quality monitoring
- Plan 02-03 (news ingestion) can use identical @retry + INSERT OR IGNORE pattern

---
*Phase: 02-reliable-data-ingestion*
*Completed: 2026-05-11*
