---
phase: 02-reliable-data-ingestion
plan: "03"
subsystem: database
tags: [sqlite, ingestion, news, cross-db, dedup, b3-ticker, tdd]

# Dependency graph
requires:
  - phase: 02-reliable-data-ingestion
    plan: "01"
    provides: "ingestion.db schema — news_articles table with UNIQUE INDEX on url, init_db(), get_connection()"
provides:
  - "sync_news_to_ingestion_db() — cross-DB bridge from news_hunter/banco.db to ingestion.db"
  - "BANCO_DB path constant pointing to news_hunter/banco.db"
  - "_is_b3_ticker() helper — regex-based B3 ticker detection for ticker_tags column"
affects:
  - "02-04-PLAN (job_news_ingest will call sync_news_to_ingestion_db after subprocess completes)"
  - "Phase 3 intelligence layer (news_articles is input to thesis generation)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Cross-DB read-only bridge: sqlite3.connect(source) → fetchall() → src.close() → write target"
    - "INSERT OR IGNORE dedup: UNIQUE INDEX on url guards all insert paths"
    - "SELECT changes() per-row: count actual new inserts, not rows attempted"
    - "B3 ticker regex gate: ^[A-Z]{4}[0-9]{1,2}$ — arbitrary strings stored as NULL ticker_tags"

key-files:
  created:
    - "Analista de Investimentos/12_PYTHON/src/ingestion/news_sync.py"
    - "Analista de Investimentos/12_PYTHON/tests/test_news_sync.py"
  modified: []

key-decisions:
  - "Cross-DB read pattern: open source connection, fetchall(), immediately close — no persistent handle to banco.db"
  - "SELECT changes() used per-row (not total_rows - total_before) to count inserts accurately under INSERT OR IGNORE"
  - "ticker_tags stores categoria as JSON list '[\"TICKER\"]' only when it matches B3 regex; NULL otherwise (Phase 4 enrichment deferred)"
  - "banco_db_path as parameter (not global) enables clean test isolation with tmp_path fixtures"

patterns-established:
  - "Read-only cross-DB access: open → fetchall → close immediately to prevent accidental writes"
  - "TDD RED/GREEN for DB modules: write failing tests first, verify ImportError, then implement"

requirements-completed: [ING-06]

# Metrics
duration: 3min
completed: 2026-05-10
---

# Phase 2 Plan 03: News Sync Summary

**Cross-DB bridge sync_news_to_ingestion_db() reads news_hunter/banco.db via parameterized SQL and upserts into ingestion.db news_articles using INSERT OR IGNORE URL deduplication and B3 ticker regex tagging**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-10T17:57:05Z
- **Completed:** 2026-05-10T18:00:00Z
- **Tasks:** 1 (TDD: 2 commits — RED + GREEN)
- **Files modified:** 2

## Accomplishments

- `sync_news_to_ingestion_db()` bridges banco.db (news_hunter) to ingestion.db without modifying news_hunter internals (D-01/D-03)
- URL-based deduplication via INSERT OR IGNORE on the UNIQUE INDEX from Plan 01 — idempotent sync confirmed by Test 2
- B3 ticker detection (`^[A-Z]{4}[0-9]{1,2}$`) populates `ticker_tags` as JSON array; non-ticker categoria stored as NULL
- Missing banco.db returns 0 with WARNING log — no exception raised (safe for scheduler)
- `limit` parameter caps source rows per sync run (default 500, T-02-14 DoS mitigation)
- All SQL uses parameterized `?` placeholders — no f-string SQL (T-02-12 satisfied)
- Source connection (`src`) has zero INSERT/UPDATE/DELETE calls — read-only enforced (T-02-13)

## Task Commits

1. **Task 1 RED: test_news_sync.py** - `6cc26eb` (test — 9 failing tests)
2. **Task 1 GREEN: news_sync.py** - `a93c4b9` (feat — 9/9 tests pass)

## Files Created/Modified

- `Analista de Investimentos/12_PYTHON/src/ingestion/news_sync.py` — sync_news_to_ingestion_db(), _is_b3_ticker(), BANCO_DB
- `Analista de Investimentos/12_PYTHON/tests/test_news_sync.py` — 9 tests covering all ING-06 behaviors

## Decisions Made

- Cross-DB pattern: `sqlite3.connect(banco_db_path)` → `fetchall()` → immediate `src.close()` — prevents any accidental write-back to source DB
- `SELECT changes()` per row after each INSERT OR IGNORE — counts only new inserts, not attempted rows
- `banco_db_path` as explicit parameter (default `BANCO_DB`) — enables `tmp_path` test isolation without monkeypatching
- Full ticker cross-tagging with tickers.yaml deferred to Phase 4 (Open Question 2 in RESEARCH.md)

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria satisfied.

## Known Stubs

None — `ticker_tags` is intentionally NULL for non-B3 categoria values. Phase 4 will enrich via tickers.yaml cross-reference (documented in RESEARCH.md Open Question 2).

## Threat Surface Scan

No new network endpoints, auth paths, or external access patterns introduced. All threats in plan's STRIDE register were mitigated:
- T-02-12: Parameterized SQL throughout — no f-string SQL
- T-02-13: Source connection has no INSERT/UPDATE/DELETE calls
- T-02-14: `limit=500` default caps rows per sync
- T-02-16: `_B3_TICKER_RE` exact-match regex rejects arbitrary categoria strings

## Self-Check

- [x] `src/ingestion/news_sync.py` exists
- [x] `tests/test_news_sync.py` exists
- [x] Commit `6cc26eb` exists (RED — test)
- [x] Commit `a93c4b9` exists (GREEN — feat)
- [x] 9/9 tests pass
- [x] `INSERT OR IGNORE INTO news_articles` present
- [x] `banco_db_path.exists()` guard present
- [x] No src writes (grep gate passed)
- [x] No f-string SQL (grep gate passed)

## Self-Check: PASSED
