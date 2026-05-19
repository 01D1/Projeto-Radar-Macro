---
phase: 02-reliable-data-ingestion
reviewed: 2026-05-11T12:37:38Z
depth: standard
files_reviewed: 14
files_reviewed_list:
  - Analista de Investimentos/12_PYTHON/src/ingestion/db.py
  - Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py
  - Analista de Investimentos/12_PYTHON/src/ingestion/bcb.py
  - Analista de Investimentos/12_PYTHON/src/ingestion/b3_scraper.py
  - Analista de Investimentos/12_PYTHON/src/ingestion/news_sync.py
  - Analista de Investimentos/12_PYTHON/src/scheduler.py
  - Analista de Investimentos/12_PYTHON/config/schedules.yaml
  - Analista de Investimentos/12_PYTHON/tests/test_db_schema.py
  - Analista de Investimentos/12_PYTHON/tests/test_cvm_ingestion.py
  - Analista de Investimentos/12_PYTHON/tests/test_ipe_ingestion.py
  - Analista de Investimentos/12_PYTHON/tests/test_bcb_ingestion.py
  - Analista de Investimentos/12_PYTHON/tests/test_b3_ingestion.py
  - Analista de Investimentos/12_PYTHON/tests/test_news_sync.py
  - Analista de Investimentos/12_PYTHON/tests/test_scheduler_ingestion.py
findings:
  critical: 5
  warning: 8
  info: 4
  total: 17
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-05-11T12:37:38Z
**Depth:** standard
**Files Reviewed:** 14
**Status:** issues_found

## Summary

Phase 02 delivers the reliable data ingestion pipeline: CVM (DFP/ITR/IPE), BCB SGS macro series, B3 OHLCV prices, and a news sync bridge. The test suite is thorough and well-structured. However, five blocker-level defects were found that can cause silent data loss, incorrect counting, a resource leak, a schedule collision, and a broken retry path. Eight warnings address robustness and correctness gaps that will cause hard-to-diagnose failures in production. Four info items are style/quality notes.

---

## Critical Issues

### CR-01: `write_to_db` counts inserted rows incorrectly — always overcounts

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py:194`

**Issue:** `conn.execute("SELECT changes()")` is called on a new cursor each time. SQLite `changes()` tracks changes made by the **last statement on that connection**, but creating a new cursor via `conn.execute()` on the same connection is fine — *however*, the same anti-pattern appears identically in `bcb.py` (line 157) and `b3_scraper.py` (line 201). The real bug is that `INSERT OR IGNORE` silently skips duplicates and `changes()` returns 0 for those rows, which is correct — *but* in `cvm_downloader.py:write_to_db` the `commit()` at line 195 is **inside the loop** per row. Each `commit()` flushes a WAL checkpoint. More critically: the `inserted` counter accumulates `changes()` results across all rows, but `commit()` between rows means `changes()` can be reset by the commit itself on some SQLite versions/drivers. The identical pattern in `b3_scraper.py:write_to_db` (line 200-201) has the same issue. The reliable pattern is to call `conn.execute("SELECT changes()")` immediately after the INSERT on the same cursor, without committing between rows.

**Fix:**
```python
def write_to_db(self, records: list[dict], conn: sqlite3.Connection) -> int:
    inserted = 0
    now = datetime.utcnow().isoformat()
    for rec in records:
        cur = conn.execute(
            """INSERT OR IGNORE INTO cvm_statements
               (id, ticker, cvm_code, year, period_type, account_code,
                account_name, normalized_name, value, reference_date, ingested_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (...),
        )
        inserted += cur.rowcount   # rowcount is 1 on insert, 0 on IGNORE — reliable
    conn.commit()   # single commit after all rows
    return inserted
```
Use `cur.rowcount` (always 1 for a successful INSERT, 0 for OR IGNORE skip) instead of a second `SELECT changes()` query. The same fix applies identically to `bcb.py:157` and `b3_scraper.py:201`.

---

### CR-02: Connection resource leak in `news_sync.py` when `fetchall()` raises

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/news_sync.py:58-74`

**Issue:** The `src` connection to `banco.db` is closed in the `finally` block (line 73), but only *after* `rows = src.execute(...).fetchall()` on lines 62-68. If the execute succeeds but `fetchall()` raises (e.g. large result OOM), `src.close()` is still called — so the finally *looks* correct. However, on the `except sqlite3.OperationalError` branch (lines 69-72), `src.close()` is called explicitly at line 71 **and then again** in the `finally` block at line 73. Closing a SQLite connection twice raises no exception in CPython today, but this is an unintentional double-close that is fragile across implementations. More importantly, if `src.execute(...)` itself raises something *other than* `OperationalError` (e.g., `sqlite3.DatabaseError`), the `except` block does not catch it, the `finally` still runs, but the calling function gets an unhandled exception — leaving `ingestion_conn` without a `commit()` for any rows already processed (there are none at that point, but the pattern is unsafe). Use a context manager (`with sqlite3.connect(...) as src:`) instead.

**Fix:**
```python
try:
    with sqlite3.connect(banco_db_path) as src:
        src.row_factory = sqlite3.Row
        rows = src.execute(
            """SELECT hash, titulo, link, fonte, categoria, data_pub, score
               FROM noticias ORDER BY data_coleta DESC LIMIT ?""",
            (limit,),
        ).fetchall()
except sqlite3.OperationalError as exc:
    log.error(f"[news_sync] erro ao ler banco.db: {exc}")
    return 0
```

---

### CR-03: `_fetch` raises `FileNotFoundError` which is not retried — retry decorator silently swallowed

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py:402-408`

**Issue:** `_fetch` raises `FileNotFoundError` for HTTP 404 responses (line 406). The `@retry` decorator on line 402 is configured with `exceptions=(requests.RequestException,)`. `FileNotFoundError` is **not** a subclass of `requests.RequestException`, so on a 404 the retry decorator will **not** retry — it will re-raise immediately. That is intentional for permanent 404s, which is fine. *However*, the `FileNotFoundError` is also not `requests.RequestException`, so callers in `download_range()` (line 338) catch `Exception` and log `results[year] = []` — that part is fine. The real problem is in `ingest_ticker()` (line 467): the catch is `except Exception`, which catches `FileNotFoundError`, logs it as an error, and silently returns a partial result. The CVM 404 for a future year (e.g., 2026 ITR not yet published) will appear as a transient error in logs rather than an expected, ignorable condition. This causes misleading `log.error` spam and can mask real errors. Additionally, the `@retry` decorator does **not** convert 3-attempt exhaustion into `IngestionError` for this decorator call (unlike the BCB version which documents `Raises: IngestionError`). Callers of `_fetch` that expect `IngestionError` after retries will instead get `requests.RequestException` — a type inconsistency.

**Fix:**
```python
@retry(attempts=3, delay=2.0, backoff=2.0,
       exceptions=(requests.RequestException,))
def _fetch(self, url: str, label: str) -> bytes:
    resp = self.session.get(url, timeout=self.timeout)
    if resp.status_code == 404:
        # Not retriable — raise a domain-specific exception callers can distinguish
        raise FileNotFoundError(f"[{label}] 404: {url}")
    resp.raise_for_status()
    return resp.content
```
And in `download_range` / `ingest_ticker`, catch `FileNotFoundError` separately and log at `DEBUG` level (expected for unpublished years):
```python
except FileNotFoundError as exc:
    log.debug(f"[{ticker}] {doc_type} {year}: arquivo não publicado — {exc}")
except Exception as exc:
    log.error(f"[{ticker}] {doc_type} {year}: {exc}")
```

---

### CR-04: `schedules.yaml` — `b3_prices` and `cvm_ingest` scheduled at the exact same time (19:00)

**File:** `Analista de Investimentos/12_PYTHON/config/schedules.yaml:12-15` and `44-47`

**Issue:** `b3_prices`, `cvm_check`, and `cvm_ingest` are all scheduled at `"0 19 * * 1-5"` (weekdays 19:00). Both `b3_prices` and `cvm_ingest` call `init_db()` and then `get_connection()` independently, opening **two concurrent write connections** to the same `ingestion.db` SQLite file. SQLite in WAL mode tolerates concurrent readers but only one writer at a time. Concurrent writes will cause `sqlite3.OperationalError: database is locked` errors at runtime. Furthermore, `cvm_check` (the legacy stub) and `cvm_ingest` (the new ING-01/02/03 job) both run at 19:00 and both attempt CVM downloads for overlapping tickers/years, creating redundant and potentially conflicting downloads.

**Fix:** Stagger the colliding jobs and remove the redundant `cvm_check` entry now that `cvm_ingest` is active:
```yaml
  - job: b3_prices
    cron: "0 19 * * 1-5"      # seg–sex 19:00
  - job: cvm_ingest
    cron: "15 19 * * 1-5"     # seg–sex 19:15  (staggered 15 min after b3_prices)
  # cvm_check removed — superseded by cvm_ingest (ING-01/02/03)
```

---

### CR-05: ITR reconciliation filter uses hardcoded byte sequence that is fragile and incorrect for non-latin1 environments

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py:242`

**Issue:** The ITR deduplication filter on line 242 compares `ORDEM_EXERC` to the byte sequence `"\xda\x4c\x54\x49\x4d\x4f"`. Decoded as latin-1, that is `"ÚLTIMO"` (U+00DA = 'Ú'). The CSV is read with `encoding="iso-8859-1"` (line 229), so the pandas string column will contain native Python `str` objects already decoded — `"ÚLTIMO"`. The comparison string in source code `"\xda\x4c\x54\x49\x4d\x4f"` in a UTF-8 Python 3 source file is parsed as: `\xda` = Unicode code point U+00DA (Ú), `\x4c` = L, etc — so it *happens* to produce `"ÚLTIMO"` correctly in CPython. However, this is a maintenance landmine: any developer reading the source sees raw bytes and cannot tell what word is intended. The test in `test_cvm_ingestion.py:87-88` also embeds the same byte sequence in the test CSV content. If the encoding ever changes or a linter normalizes the escape sequences, the filter silently stops working and all ITR data doubles (ÚLTIMO + PENÚLTIMO rows kept), corrupting financial calculations.

**Fix:**
```python
# Line 242 — replace opaque escape with explicit Unicode string
_ULTIMO = "ÚLTIMO"   # module-level constant, encoding-safe

# In parse_and_store:
if period_type == "ITR" and "ORDEM_EXERC" in filtered.columns:
    filtered = filtered[filtered["ORDEM_EXERC"].str.strip() == _ULTIMO]
```
Update the test CSV to use `encoding="utf-8"` and write `"ÚLTIMO"` directly.

---

## Warnings

### WR-01: `init_db()` does not enable WAL mode — concurrent access will cause lock errors

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/db.py:88-94`

**Issue:** `init_db()` never sets `PRAGMA journal_mode=WAL`. With the default DELETE journal mode, any two concurrent processes opening the database (e.g., the scheduler running `job_b3_prices` while `job_cvm_ingest` is still running) will get `database is locked` errors. Given CR-04 (schedule collision), WAL mode is a necessary mitigation even after rescheduling.

**Fix:**
```python
def init_db(db_path: Path = DB_PATH) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")   # 5s wait instead of immediate error
    conn.executescript(_CREATE_SQL)
    conn.commit()
    conn.close()
```

---

### WR-02: `job_cvm_check()` result counting is broken — `result.get("downloaded", 0)` returns a dict, not an int

**File:** `Analista de Investimentos/12_PYTHON/src/scheduler.py:121-127`

**Issue:** `ingest_ticker()` returns `{"ticker": ..., "cvm_code": ..., "downloaded": {"DFP": [...], "ITR": [...]}}`. The `"downloaded"` key is a `dict[str, list[int]]`. Line 124 calls `result.get("downloaded", 0)`, which returns the dict. Adding a dict to `downloaded` (an `int`) raises `TypeError: unsupported operand type(s) for +=: 'int' and 'dict'`. This will cause `job_cvm_check` to crash every time it runs.

**Fix:**
```python
def job_cvm_check() -> str:
    downloaded = 0
    for ticker in settings.active_tickers:
        try:
            result = ingest_ticker(ticker, doc_types=["DFP", "ITR"], force=False)
            dl = result.get("downloaded", {})
            # Count total years actually downloaded across all doc types
            downloaded += sum(len(v) for v in dl.values() if isinstance(v, list))
        except Exception as exc:
            log.warning(f"[cvm_check] [{ticker}] {exc}")
    return f"documentos novos: {downloaded}"
```

---

### WR-03: `bcb.py` — `fetch_series` uses module-level `requests.get` directly, bypassing the session and retry state

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/bcb.py:60`

**Issue:** `fetch_series` calls `requests.get(url, ...)` directly (bare `requests`, not a `Session`). This means each call opens a new TCP connection with no keepalive, no shared headers, and no connection pooling. More importantly, `CVMDownloader` uses `self.session` for connection reuse — BCB is inconsistent. While not a data-correctness bug, repeated cold TCP connects to BCB for 5 series every day will accumulate latency and increases the chance of transient failures not covered by the retry.

**Fix:** Create a module-level session (same pattern as `CVMDownloader`):
```python
_BCB_SESSION = requests.Session()
_BCB_SESSION.headers.update({"User-Agent": "FinancialIntelligencePlatform/1.0"})

@retry(attempts=3, delay=2.0, backoff=2.0, jitter=0.5,
       exceptions=(requests.RequestException,))
def fetch_series(cod: int, inicio: str = "01/01/2019") -> list[dict]:
    resp = _BCB_SESSION.get(url, params=params, timeout=30)
    ...
```

---

### WR-04: `b3_scraper.py` — `write_to_db` stores `close` in both `close` and `adj_close` columns, but the comment is misleading and the zero-value logic is wrong

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/b3_scraper.py:195-197`

**Issue:** Lines 195-197 compute `float(row.get("close", 0) or 0) or None`. The expression `float(x or 0) or None` converts a zero close price to `None`. For penny stocks or suspended trading sessions, a genuine `0.0` close would be incorrectly stored as `NULL`. Additionally `adj_close` is hardcoded to the same value as `close` (line 196 comment: "adj_close = close post auto_adjust") — this is architecturally fine since `auto_adjust=True` is set in `_download()`, but the inline comment on line 196 is misleading — it should state this clearly in the column DDL comment, not a code comment that looks like a workaround.

**Fix:**
```python
def _to_float_or_none(val) -> float | None:
    """Return None only if val is truly missing (None/NaN), not if it's zero."""
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except (TypeError, ValueError):
        return None

# In write_to_db loop:
conn.execute(
    "INSERT OR IGNORE INTO price_ohlcv ...",
    (
        str(uuid.uuid4()), ticker, date_str,
        _to_float_or_none(row.get("open")),
        _to_float_or_none(row.get("high")),
        _to_float_or_none(row.get("low")),
        _to_float_or_none(row.get("close")),
        _to_float_or_none(row.get("close")),  # adj_close = auto-adjusted close
        int(row.get("volume", 0) or 0) or None,
        now,
    ),
)
```

---

### WR-05: `cvm_downloader.py` — `_load_cvm_codes()` is not thread-safe

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py:86-95`

**Issue:** The global `_CVM_CODES` cache uses a double-checked locking pattern without a lock. If two threads call `get_cvm_code()` simultaneously when `_CVM_CODES is None`, both will enter the `if _CVM_CODES is None` branch and both will read and assign the YAML file. In CPython this is safe due to the GIL, but the APScheduler `BlockingScheduler` runs jobs sequentially in the main thread — so this is not currently a live risk. However, if APScheduler is ever switched to `BackgroundScheduler` (threaded), this becomes a race condition. The global mutable `_CVM_CODES` combined with the `global` keyword is also an anti-pattern that makes the module hard to test in isolation (as seen: tests that call `CVMDownloader()` directly will hit the real YAML file).

**Fix:** Use `functools.lru_cache` on a function that returns an immutable mapping:
```python
import functools

@functools.lru_cache(maxsize=1)
def _load_cvm_codes() -> dict[str, str]:
    path = Path(__file__).parent.parent.parent / "config" / "cvm_codes.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("cvm_codes", {})
```

---

### WR-06: `scheduler.py` — `job_cvm_ingest` does not close `conn` on exception

**File:** `Analista de Investimentos/12_PYTHON/src/scheduler.py:292-331`

**Issue:** `conn = get_connection()` is called at line 293. The subsequent loop (lines 298-314) is wrapped inside `with bind_run_id(...) as run_id:` but `conn.close()` at line 315 is only reached if no exception escapes the `with` block. If `bind_run_id` itself raises, or if `get_connection()` succeeds but an unhandled exception exits the `with` block, `conn` is never closed. The same issue exists in `job_b3_prices()` (line 79/95) and `job_bcb_macro()` (line 346/347). SQLite connections are file handles — leaking them causes "too many open files" errors in long-running daemon processes.

**Fix:** Use a try/finally or a context manager for the connection in all three job functions:
```python
conn = get_connection()
try:
    # ... all work ...
finally:
    conn.close()
```

---

### WR-07: `b3_scraper.py` — `fetch_and_store` uses `start_date` parameter as override but `self.fetch()` ignores it for existing Parquets

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/b3_scraper.py:253-285`

**Issue:** `fetch_and_store()` computes `since` from the DB's `MAX(date)` (lines 263-272), then calls `self.fetch(ticker, start_date=since)`. Inside `fetch()`, if the Parquet file already exists and is not empty, `since` is **overridden** by `last_date = existing.index.max().date()` (line 86-87). This means the DB-derived `since` date is silently discarded whenever a Parquet exists, and the Parquet's last date is used instead. If the Parquet and the DB are out of sync (e.g., Parquet was manually deleted and rebuilt), the DB can be populated with duplicate data or miss data. The `force=False` default in `fetch()` ensures the Parquet wins over the DB, making `fetch_and_store`'s DB-based incremental logic partially ineffective.

**Fix:** Either: (a) pass `force=True` from `fetch_and_store` when `since` is computed from DB to ensure the DB is authoritative, or (b) document the Parquet-wins behavior explicitly and ensure `detect_and_insert_gaps` covers the discrepancy. The cleanest fix is to make `fetch_and_store` call `_download` directly and bypass the Parquet caching layer, since DB is the canonical store for ING-05.

---

### WR-08: `news_sync.py` — no upper bound on `score` integer; malformed `score` from banco.db silently becomes 0

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/news_sync.py:106`

**Issue:** `int(row["score"] or 0)` converts `None` or falsy scores to `0`, which is correct. But if `banco.db` stores `score` as a string (e.g., `"high"` or a non-integer), `int("high")` raises `ValueError` which propagates uncaught through the `for row in rows` loop, crashing the entire sync and rolling back all rows processed so far (no `try/except` around the per-row processing). The `ingestion_conn.commit()` on line 112 is only reached after the full loop.

**Fix:**
```python
try:
    score = int(row["score"] or 0)
except (ValueError, TypeError):
    score = 0
```
Also move `ingestion_conn.commit()` inside a `try/finally` or commit in batches so partial progress is preserved.

---

## Info

### IN-01: TODO comment for `news_fetcher` job stub in scheduler

**File:** `Analista de Investimentos/12_PYTHON/src/scheduler.py:53`

**Issue:** `# TODO: implementar src/ingestion/news_fetcher.py` — `job_news_fetcher` is a stub. It is registered in `_JOB_REGISTRY` and scheduled at 06:00 weekdays, but does nothing useful. This will produce misleading success logs every weekday morning.

**Fix:** Either implement the job or add `enabled: false` support to `schedules.yaml` entries so it can be disabled without removing the registry entry.

---

### IN-02: `db.py` — `init_db` uses `executescript` which always commits any pending transaction

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/db.py:92`

**Issue:** `conn.executescript(_CREATE_SQL)` issues an implicit `COMMIT` before executing, per Python's sqlite3 docs. The explicit `conn.commit()` on line 93 is therefore a no-op. This is harmless but confusing to future readers. Also, `executescript` disables the `isolation_level` temporarily and re-enables it — if `init_db` is ever called with a connection that has an open transaction (it currently isn't, since it creates its own connection), it would silently commit that transaction.

**Fix:** Replace `executescript` with individual `execute` calls wrapped in a transaction, or keep `executescript` and remove the redundant `conn.commit()` with a comment explaining the implicit commit.

---

### IN-03: `cvm_downloader.py` — `pdfplumber` imported at module level for a feature used only in IPE ingestion

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py:38`

**Issue:** `import pdfplumber` is a top-level import. `pdfplumber` is a heavy dependency (pulls in `pdfminer.six`) needed only when `extract_ipe_pdf_text` is called. If a user runs DFP/ITR ingestion only (`doc_types=["DFP", "ITR"]`), the import still happens and fails with an `ImportError` if `pdfplumber` is not installed. This creates an unnecessary hard dependency.

**Fix:** Move `import pdfplumber` inside `extract_ipe_pdf_text`:
```python
def extract_ipe_pdf_text(pdf_url: str) -> str:
    try:
        import pdfplumber
        resp = requests.get(pdf_url, timeout=60)
        ...
```

---

### IN-04: Test `test_banco_db_not_modified` leaks open connections

**File:** `Analista de Investimentos/12_PYTHON/tests/test_news_sync.py:155-158`

**Issue:** Lines 155 and 157 call `sqlite3.connect(banco)` and `.fetchone()[0]` without storing the connection or closing it. These connections are leaked for the duration of the test process. On Windows (where the test environment runs), SQLite does not allow deletion of an open database file, which can cause teardown failures in `tmp_path` cleanup. The test passes but leaves dangling file handles.

**Fix:**
```python
with sqlite3.connect(banco) as check_conn:
    before = check_conn.execute("SELECT COUNT(*) FROM noticias").fetchone()[0]
sync_news_to_ingestion_db(conn, banco_db_path=banco)
with sqlite3.connect(banco) as check_conn:
    after = check_conn.execute("SELECT COUNT(*) FROM noticias").fetchone()[0]
```

---

_Reviewed: 2026-05-11T12:37:38Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
