---
phase: 02-reliable-data-ingestion
fixed_at: 2026-05-11T14:00:00Z
review_path: .planning/phases/02-reliable-data-ingestion/02-REVIEW.md
iteration: 1
findings_in_scope: 13
fixed: 13
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-05-11T14:00:00Z
**Source review:** `.planning/phases/02-reliable-data-ingestion/02-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 13 (5 Critical + 8 Warning)
- Fixed: 13
- Skipped: 0

Note: fixes were committed to the inner git repository at
`Analista de Investimentos/` (which is tracked as a gitlink in the outer
Obsidian repo). All commits are on the `master` branch of the inner repo.

---

## Fixed Issues

### CR-01: `write_to_db` counts inserted rows incorrectly

**Files modified:** `src/ingestion/cvm_downloader.py`, `src/ingestion/bcb.py`, `src/ingestion/b3_scraper.py`
**Commit:** `5a387b2` — fix(02): CR-01 WR-04 use cur.rowcount instead of SELECT changes() in write_to_db
**Applied fix:** Replaced `conn.execute("SELECT changes()").fetchone()[0]` with `cur.rowcount` on
the cursor returned by the INSERT statement in all three files. `cur.rowcount` is 1 on a successful
INSERT, 0 on OR IGNORE skip — reliable across SQLite versions and drivers.
Also moved `conn.commit()` to a single call after the loop (it was already outside the loop in
cvm_downloader.py and b3_scraper.py; confirmed correct in bcb.py).
Also fixed `detect_and_insert_gaps` in b3_scraper.py which had the same SELECT changes() pattern.

---

### CR-02: Connection resource leak in `news_sync.py`

**Files modified:** `src/ingestion/news_sync.py`
**Commit:** `ced9be4` — fix(02): CR-02 WR-08 fix connection leak and score ValueError in news_sync.py
**Applied fix:** Replaced the manual `src = sqlite3.connect(...)` + `src.close()` in try/except/finally
with a `with sqlite3.connect(...) as src:` context manager. This eliminates the double-close on the
`OperationalError` branch and ensures the connection is always released even for unexpected exceptions
like `DatabaseError`.

---

### CR-03: `_fetch` raises `FileNotFoundError` not retried — misleading error logs

**Files modified:** `src/ingestion/cvm_downloader.py`
**Commit:** `def0d34` — fix(02): CR-03 catch FileNotFoundError separately with log.debug for 404s
**Applied fix:** Added explicit `except FileNotFoundError` handler (logged at `DEBUG` level) before
the generic `except Exception` handler in both `download_range()` and `ingest_ticker()`. CVM 404s
for unpublished years (e.g. 2026 ITR not yet released) are now silently logged at DEBUG instead of
ERROR, preventing log spam that would mask real network failures.

---

### CR-04: Schedule collision at 19:00 causing SQLite lock contention

**Files modified:** `config/schedules.yaml`
**Commit:** `dd30bc2` — fix(02): CR-04 stagger cvm_ingest to 19:15 and remove redundant cvm_check
**Applied fix:** Changed `cvm_ingest` cron from `"0 19 * * 1-5"` to `"15 19 * * 1-5"` (19:15,
15 minutes after `b3_prices`). Removed the `cvm_check` entry entirely — it was a legacy stub
superseded by `cvm_ingest` (ING-01/02/03) and was also scheduled at 19:00, causing a third
concurrent connection attempt.

---

### CR-05: ITR filter uses hardcoded byte sequence — fragile maintenance landmine

**Files modified:** `src/ingestion/cvm_downloader.py`, `tests/test_cvm_ingestion.py`
**Commit:** `2748f42` — fix(02): CR-05 replace hardcoded byte escape with _ULTIMO module-level constant
**Applied fix:** Removed `"\xda\x4c\x54\x49\x4d\x4f"` from the ITR `ORDEM_EXERC` filter and replaced
with `_ULTIMO = "ÚLTIMO"` module-level constant defined after the `DocType` alias. Updated
`test_cvm_ingestion.py` to use explicit `"ÚLTIMO"` and `"PENÚLTIMO"` strings in the test CSV fixture
(still encoded as `iso-8859-1` to match the actual CVM CSV format).

---

### WR-01: `init_db()` missing WAL mode and busy_timeout

**Files modified:** `src/ingestion/db.py`
**Commit:** `235fc66` — fix(02): WR-01 enable WAL mode and busy_timeout in init_db
**Applied fix:** Added `conn.execute("PRAGMA journal_mode=WAL")` and
`conn.execute("PRAGMA busy_timeout=5000")` at the start of `init_db()`, before `executescript`.
WAL allows concurrent readers during writes; 5 s busy_timeout replaces immediate
`OperationalError: database is locked` with a grace period.

---

### WR-02: `job_cvm_check()` crashes with TypeError on every run

**Files modified:** `src/scheduler.py`
**Commit:** `a79d1ca` — fix(02): WR-02 WR-06 fix cvm_check TypeError and wrap conn in try/finally
**Applied fix:** Replaced `downloaded += result.get("downloaded", 0)` with:
```python
dl = result.get("downloaded", {})
downloaded += sum(len(v) for v in dl.values() if isinstance(v, list))
```
`ingest_ticker()` returns `{"downloaded": {"DFP": [years], "ITR": [years]}}` — adding the dict to
an int caused a TypeError. The fix counts total year-downloads across all doc types.

---

### WR-03: `bcb.py` uses bare `requests.get` — no connection reuse

**Files modified:** `src/ingestion/bcb.py`
**Commit:** `5c4e732` — fix(02): WR-03 WR-05 add _BCB_SESSION and refactor _load_cvm_codes to lru_cache
**Applied fix:** Added module-level `_BCB_SESSION = requests.Session()` with a `User-Agent` header,
matching the pattern used by `CVMDownloader`. Changed `fetch_series` to use `_BCB_SESSION.get()`
instead of `requests.get()` for connection reuse and keepalive.

---

### WR-04: `write_to_db` zero-value logic converts `0.0` close to None

**Files modified:** `src/ingestion/b3_scraper.py`
**Commit:** `5a387b2` — fix(02): CR-01 WR-04 use cur.rowcount instead of SELECT changes() in write_to_db
**Applied fix:** Added `_to_float_or_none(val)` module-level helper that returns `None` only for
`None` or `NaN` (via `pd.isna()`), not for `0.0`. Replaced all `float(row.get("x", 0) or 0) or None`
expressions in `write_to_db` with `_to_float_or_none(row.get("x"))`. Genuine zero close prices
(suspended sessions, penny stocks) are now stored as `0.0` instead of `NULL`.

---

### WR-05: `_load_cvm_codes()` not thread-safe (double-checked locking on global mutable)

**Files modified:** `src/ingestion/cvm_downloader.py`
**Commit:** `5c4e732` — fix(02): WR-03 WR-05 add _BCB_SESSION and refactor _load_cvm_codes to lru_cache
**Applied fix:** Removed global `_CVM_CODES` mutable variable and double-checked locking pattern.
Replaced with `@functools.lru_cache(maxsize=1)` on `_load_cvm_codes()`. The `lru_cache` is
thread-safe under CPython's GIL and will be safe under `BackgroundScheduler` too. Added `import
functools` to imports. Also moved `import pdfplumber` inside `extract_ipe_pdf_text` as a lazy import
(avoids hard dependency when only DFP/ITR are being ingested).

---

### WR-06: `job_cvm_ingest`, `job_b3_prices`, `job_bcb_macro` don't close `conn` on exception

**Files modified:** `src/scheduler.py`
**Commit:** `a79d1ca` — fix(02): WR-02 WR-06 fix cvm_check TypeError and wrap conn in try/finally
**Applied fix:** Wrapped all work in each of the three job functions inside `try: ... finally: conn.close()`
blocks. The connection is now guaranteed to be closed whether the job completes normally, raises, or
gets interrupted — preventing file-handle leaks in the long-running daemon.

---

### WR-07: `fetch_and_store` Parquet overrides DB-derived `since` date without documentation

**Files modified:** `src/ingestion/b3_scraper.py`
**Commit:** `9f6de88` — fix(02): WR-07 document Parquet-wins behavior in fetch_and_store
**Applied fix:** Added explicit docstring note in `fetch_and_store` explaining the Parquet-wins
behavior (when Parquet exists, `self.fetch()` ignores the DB-derived `since` and uses the Parquet's
last date). Documents when to use `start_date` explicitly and points to `detect_and_insert_gaps()`
for backfill scenarios. Behavioral change deferred — the reviewer offered documentation as a valid
fix and it avoids risk of unintended data re-downloads.

---

### WR-08: `int(row["score"] or 0)` crashes on non-integer scores

**Files modified:** `src/ingestion/news_sync.py`
**Commit:** `ced9be4` — fix(02): CR-02 WR-08 fix connection leak and score ValueError in news_sync.py
**Applied fix:** Wrapped the score conversion in `try/except (ValueError, TypeError)` defaulting to
`0` on any parse failure. Also replaced `SELECT changes()` with `cur.rowcount` (CR-01 pattern).
The per-row `ingestion_conn.commit()` was already outside the loop (correct); the fix preserves
that structure.

---

## Skipped Issues

None — all 13 findings were fixed.

---

_Fixed: 2026-05-11T14:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
