---
phase: 03-financial-engine
reviewed: 2026-05-11T00:00:00Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - Analista de Investimentos/12_PYTHON/src/financial_engine.py
  - Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py
  - Analista de Investimentos/12_PYTHON/src/ingestion/db.py
  - Analista de Investimentos/12_PYTHON/src/normalization/account_mapper.py
  - Analista de Investimentos/12_PYTHON/src/scheduler.py
  - Analista de Investimentos/12_PYTHON/src/valuation/sector_config.py
  - Analista de Investimentos/12_PYTHON/config/schedules.yaml
  - Analista de Investimentos/12_PYTHON/tests/test_db_schema.py
  - Analista de Investimentos/12_PYTHON/tests/test_financial_db_schema.py
  - Analista de Investimentos/12_PYTHON/tests/test_financial_engine.py
  - Analista de Investimentos/12_PYTHON/tests/test_financial_signals.py
findings:
  critical: 5
  warning: 9
  info: 5
  total: 19
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-11T00:00:00Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed the Phase 3 financial engine implementation: LTM aggregation, multiples, DCF/DDM, technical signals, scheduler wiring, DB schema, and the test suite. The code is structurally sound and does address many documented pitfalls (parameterized SQL, bank routing gate, terminal-growth guard). However, five blockers were found: an unclosed file handle in `run_all`, a division-by-zero in gross/net debt calculation when snapshot rows are absent, an unsafe `open()` call in `sector_config.py`, a `datetime.utcnow()` deprecation that silently produces wrong timestamps in Python 3.12+, and a resource leak in `get_connection()` (WAL/busy_timeout not applied). Nine warnings cover logic gaps, missing validation, test reliability issues, and misleading test assertions. Five info items flag quality concerns.

---

## Critical Issues

### CR-01: File handle leak in `run_all()` — `open()` never closed

**File:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py:399`
**Issue:** `yaml.safe_load(open(tickers_path, encoding="utf-8"))` opens a file but never closes it. The file handle leaks for the lifetime of the process. On Windows (the documented platform) this also holds an exclusive lock on the file, preventing external writes (e.g., a manual edit to `tickers.yaml` while the daemon is running). The `except Exception` block below only catches parse errors — the file will already be open by then.

**Fix:**
```python
with open(tickers_path, encoding="utf-8") as fh:
    data = yaml.safe_load(fh)
active_tickers = [
    t["ticker"]
    for t in data.get("tickers", [])
    if t.get("active", True)
]
```

---

### CR-02: Division-by-zero in `_aggregate_ltm()` gross/net debt calculation when snapshot rows are absent

**File:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py:198-202`
**Issue:** The gross_debt and net_debt computations use `.get("short_term_debt", {}).get("value", 0.0)` — this is safe only when both debt components are missing. However, if `snapshot` contains `short_term_debt` but NOT `long_term_debt` (or vice versa), the absent key returns `{}` which has no `"value"` key and silently defaults to `0.0`. The resulting `net_debt` may be negative or wrong when only one side is in the DB — there is no warning log or `None` marker to signal an incomplete calculation. Downstream DCF consumers receiving `net_debt=0.0` when the true value is unknown will produce meaningless fair values.

**Fix:**
Detect partial data and emit `None` rather than a misleadingly precise zero:
```python
std = snapshot.get("short_term_debt", {}).get("value")
ltd = snapshot.get("long_term_debt", {}).get("value")
csh = snapshot.get("cash", {}).get("value")

if std is None and ltd is None:
    result["gross_debt"] = None
    result["net_debt"] = None
else:
    result["gross_debt"] = (std or 0.0) + (ltd or 0.0)
    if csh is None:
        result["net_debt"] = None  # cannot compute without cash
    else:
        result["net_debt"] = result["gross_debt"] - csh
```

---

### CR-03: `sector_config.py` — `open()` without `encoding=` argument (platform-dependent corruption)

**File:** `Analista de Investimentos/12_PYTHON/src/valuation/sector_config.py:38-39` and `45-47`
**Issue:** Both `_load_sectors()` and `_load_ticker_map()` call `open(...) ` without an `encoding` argument. On Windows the system locale encoding (cp1252 on most Brazilian Windows installations) is used rather than UTF-8. The YAML files contain Portuguese characters (accents, cedillas). Depending on how the YAML files were saved, this will silently corrupt text values or raise a `UnicodeDecodeError` at runtime — both outcomes are silent failures in a cached function (results are memoized by `lru_cache` so the corruption persists for the process lifetime).

**Fix:**
```python
# _load_sectors()
with open(_SECTORS_PATH, encoding="utf-8") as f:
    return yaml.safe_load(f).get("sectors", {})

# _load_ticker_map()
with open(_TICKERS_PATH, encoding="utf-8") as f:
    data = yaml.safe_load(f)
```

---

### CR-04: `datetime.utcnow()` deprecated — produces naive UTC timestamp in Python 3.12+

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py:180`, `src/scheduler.py:109,330,366,447`
**Issue:** `datetime.utcnow()` was deprecated in Python 3.12 and will be removed in a future version. More critically, it returns a *naive* `datetime` with no tzinfo. The `ingested_at` column in the DB already uses timezone-aware ISO strings when populated by `financial_engine.py` (`datetime.now(timezone.utc).isoformat()`). Mixing naive and aware timestamps in the same column breaks any chronological sort or comparison that relies on string order (YYYY-MM-DDTHH:MM:SS vs YYYY-MM-DDTHH:MM:SS+00:00). On top of that, `cvm_downloader.write_to_db()` calls `datetime.utcnow()` for every batch, so all CVM-originated rows have naive timestamps while financial engine rows have aware ones.

**Fix:** Replace all occurrences with:
```python
from datetime import datetime, timezone
now = datetime.now(timezone.utc).isoformat()
```

---

### CR-05: `get_connection()` does not apply WAL mode or busy_timeout — concurrent write contention unmitigated

**File:** `Analista de Investimentos/12_PYTHON/src/ingestion/db.py:172-176`
**Issue:** `init_db()` correctly sets `PRAGMA journal_mode=WAL` and `PRAGMA busy_timeout=5000`. However, `get_connection()` — used by every other module to obtain connections for reading and writing — does **not** re-apply these PRAGMAs. In WAL mode, journal_mode is persistent at the file level, so journal_mode is not the concern; but `busy_timeout` is a **per-connection** setting. Any connection opened via `get_connection()` will have the default busy_timeout of 0 ms, meaning it will immediately raise `sqlite3.OperationalError: database is locked` when another writer holds the lock. The scheduler runs `b3_prices`, `cvm_ingest`, and `financial_engine` on overlapping time windows (19:00, 19:15, 20:00 on weekdays), making this a near-certain production failure.

**Fix:**
```python
def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")  # match init_db setting
    return conn
```

---

## Warnings

### WR-01: `_aggregate_ltm()` uses `row["value"] or 0.0` — legitimate zero values silently replaced

**File:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py:164`
**Issue:** `val = row["value"] or 0.0` converts any falsy DB value — including a genuine `0.0` — to `0.0`. For flow items like `capex` or `dividends_paid`, a real zero (company had no capex that quarter) is semantically different from NULL (capex not reported). The `or` idiom means a quarterly report with `VL_CONTA=0` contributes `0.0` but is added to `flow_seen`, masking the gap. The correct guard is `float(row["value"]) if row["value"] is not None else 0.0`.

**Fix:**
```python
val = float(row["value"]) if row["value"] is not None else 0.0
```

---

### WR-02: `_compute_multiples()` passes `shares` from `ltm.get("shares_outstanding")` but `ltm` never contains that key from `_aggregate_ltm()`

**File:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py:471` (bank path) and `503` (industrial path)
**Issue:** `_aggregate_ltm()` never inserts `"shares_outstanding"` into its returned dict — `SNAPSHOT_ITEMS` and `FLOW_ITEMS` do not include that key. The shares value is fetched via yfinance and stored in `financial_ltm`, but the `ltm` dict passed to `_compute_multiples()` (line 366) is the raw output of `_aggregate_ltm()`, not the DB row. So `ltm.get("shares_outstanding")` is always `None` in `_compute_multiples()`, meaning `market_cap_val` is always `None` and EV-based multiples are always NULL — silently, without a warning log.

**Fix:** Pass shares explicitly as a separate parameter, or augment the `ltm` dict before calling downstream functions:
```python
# In run_ticker(), after fetching shares:
ltm["shares_outstanding"] = shares  # make it available to multiples/DCF callers
```

---

### WR-03: `compute_wacc()` — bank path uses `gordon_assumptions` which may lack WACC fields

**File:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py:743-790`
**Issue:** When `cfg.is_bank_model` is True, `compute_wacc()` reads `a = cfg.gordon_assumptions`. The function then accesses `a.get("beta", 1.0)`, `a.get("erp", 0.055)`, `a.get("cost_of_debt", 0.115)`, `a.get("tax_rate", 0.27)`, `a.get("debt_to_capital", 0.25)`. These fields belong to the industrial DCF model; `gordon_assumptions` in `sectors.yaml` is defined for the Gordon Growth Model and typically only contains `coe`, `terminal_growth`, `payout_ratio`. All five fields silently default to hardcoded values that may be inconsistent with sector-specific settings. For `_compute_bank_model()`, the returned `wacc_full` (which is the full WACC, not just `ke`) is only used for metadata (selic_used, cds_used, used_fallback) so the numerical error is benign today, but the design is fragile and the logged `wacc_full` value is wrong for bank tickers.

**Fix:** Document that for bank tickers `compute_wacc()` should return only `(ke, selic, cds, fallback)` where `ke` is cost-of-equity, or gate on `is_bank_model` to return a dedicated bank ke computation instead of a full WACC.

---

### WR-04: DCF EV/EBITDA path: `_validate_dcf_inputs()` called AFTER `fair_value` is computed, not before

**File:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py:887-890`
**Issue:** In the `ev_ebitda_multiple` branch of `_compute_dcf_industrial()`, `_validate_dcf_inputs()` is called after `fair_value` is computed (line 887) and receives the computed `fair_value` as `price_target`. For the DCF FCFF path, the guard is correctly called first (line 895) and aborts on `INPUT_INVALIDO`. For the EV/EBITDA path, an `INPUT_INVALIDO` condition (e.g., `wacc <= 0.05`) still proceeds to compute and write `fair_value` — it just attaches a `confidence_flag`. This is inconsistent: a corrupt WACC produces a written fair_value with `INPUT_INVALIDO` flag rather than a NULL fair_value. Downstream readers of `financial_dcf` that filter on `confidence_flag IS NULL` will consume a suspect value.

**Fix:** Check `INPUT_INVALIDO` pre-conditions at the top of the ev_ebitda branch too, and write a NULL row on failure:
```python
pre_flag = _validate_dcf_inputs(ticker, wacc, terminal_growth, current_price, None)
if pre_flag == "INPUT_INVALIDO":
    _write_dcf_row(conn, ticker, computed_date, "ev_ebitda", None, None,
                   wacc, terminal_growth, selic_used, cds_used, used_fallback,
                   "INPUT_INVALIDO")
    return
```

---

### WR-05: `backfill_normalized_names()` calls private method `AccountMapper._map_row()` directly

**File:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py:277`
**Issue:** `backfill_normalized_names()` calls `mapper._map_row(...)` — a name-mangled private method. While `_map_row` uses a single underscore (not double), calling it externally violates the API contract and creates a hidden coupling. `AccountMapper` exposes `map_df()` and `to_dict()` as its public interface; `_map_row()` is an internal implementation detail. If `AccountMapper` is refactored (e.g., to add caching or validation in `_map_row`), `backfill_normalized_names` will silently bypass that logic.

**Fix:** Add a public `map_single(account_code, account_name)` method to `AccountMapper`, or expose `_map_row` as public (`map_row`). Use that instead.

---

### WR-06: `_compute_and_write_signals()` fetches at most 300 price rows — MA200 will always be None for sparse tickers

**File:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py:1095`
**Issue:** `LIMIT 300` means the price series has at most 300 trading days (about 14 months of daily data). However, `compute_signals()` requires 200 rows for MA200 (`if n >= 200`). With exactly 300 rows, both MA50 and MA200 can be computed. But for any ticker with fewer than 200 rows in `price_ohlcv` (new listings, recently added to watchlist), MA200 and crossover signals will be `None` — which is correct behavior — yet `momentum_score` silently uses `cross_score = 10` (neutral) rather than signaling that the score is incomplete. This is a data quality gap: the output looks like a real score but is partially fabricated.

**Fix:** Add a `signals_complete` boolean or confidence field to the returned dict and write it to `financial_signals`. Alternatively, emit a log warning when fewer than 200 rows are available so operators know the momentum score is degraded.

---

### WR-07: `job_news_ingest()` — unclosed connection on sync failure path

**File:** `Analista de Investimentos/12_PYTHON/src/scheduler.py:403-405`
**Issue:** Between `conn = get_connection()` (line 403) and `conn.close()` (line 405), the call to `sync_news_to_ingestion_db(conn)` is not inside a `try/finally` block. If `sync_news_to_ingestion_db()` raises, `conn` is never closed, leaking a SQLite connection. Other jobs in the scheduler run in the same process; a leaked connection holding a WAL write lock will cause the next `financial_engine` or `cvm_ingest` job to fail immediately with `database is locked`.

**Fix:**
```python
conn = get_connection()
try:
    inserted = sync_news_to_ingestion_db(conn)
finally:
    conn.close()
```

---

### WR-08: `_check_dfp_reconciliation()` subquery uses two separate ticker positional params — fragile pattern

**File:** `Analista de Investimentos/12_PYTHON/src/financial_engine.py:223-237`
**Issue:** The query passes `(ticker, ticker)` as two separate positional parameters for the outer and inner WHERE clauses. This is correct but fragile — if a future editor adds a parameter between them or restructures the query, the mismatch will produce silent wrong results (wrong company's DFP fetched). The mitigation comment (T-03-01-02) references the intent but the pattern is still error-prone. Using a CTE or a single-reference subquery would be safer.

**Fix:**
```sql
WITH latest_dfp AS (
    SELECT MAX(reference_date) AS max_date
    FROM cvm_statements
    WHERE ticker = ? AND period_type = 'DFP'
)
SELECT cs.value
FROM cvm_statements cs
JOIN latest_dfp ld ON cs.reference_date = ld.max_date
WHERE cs.ticker = ? AND cs.period_type = 'DFP'
  AND cs.normalized_name = 'net_revenue'
LIMIT 1
```
This makes the two `?` visually unambiguous.

---

### WR-09: `schedules.yaml` — `analyze` and `financial_engine` both fire at 20:00 — race condition

**File:** `Analista de Investimentos/12_PYTHON/config/schedules.yaml:22-23` and `47-48`
**Issue:** Both `analyze` (20:00) and `financial_engine` (20:00) have the same cron expression `"0 20 * * 1-5"`. APScheduler with `max_instances=1` and `coalesce=True` will run both jobs "at" 20:00 but they will serialize on the same thread. The concern is that `analyze` calls `run_metrics(ticker)` which reads from DB tables that `financial_engine` is simultaneously writing. `financial_engine` may write incomplete LTM/multiples rows (mid-batch) while `analyze` reads them, producing metrics computed from partially updated data.

**Fix:** Stagger `financial_engine` by at least 10 minutes before `analyze`:
```yaml
- job: financial_engine
  cron: "50 19 * * 1-5"   # 19:50 — before analyze at 20:00
```
Or make `analyze` explicitly wait for `financial_engine` completion (event-driven rather than cron-based).

---

## Info

### IN-01: `test_db_schema.py` — test name says "four tables" but asserts eight

**File:** `Analista de Investimentos/12_PYTHON/tests/test_db_schema.py:14-15`
**Issue:** `test_init_db_creates_all_four_tables` is named for the original schema (4 ingestion tables). The test body now correctly checks 8 tables (4 ingestion + 4 financial). The stale name will confuse future readers.

**Fix:** Rename to `test_init_db_creates_all_eight_tables`.

---

### IN-02: `test_db_schema.py` — `test_all_tables_have_text_pk` only checks 4 of 8 tables

**File:** `Analista de Investimentos/12_PYTHON/tests/test_db_schema.py:71-84`
**Issue:** The `tables` list covers only `["cvm_statements", "macro_series", "price_ohlcv", "news_articles"]` — the four financial tables (`financial_ltm`, `financial_multiples`, `financial_dcf`, `financial_signals`) are not checked. All four use `TEXT PRIMARY KEY` so they would pass, but the omission means a future schema change that accidentally introduces an `INTEGER` PK in a financial table would go undetected.

**Fix:** Extend the `tables` list to include all 8 tables.

---

### IN-03: `test_financial_engine.py:678` — monkeypatching `run_ticker.__module__` is a no-op

**File:** `Analista de Investimentos/12_PYTHON/tests/test_financial_engine.py:678`
**Issue:** `monkeypatch.setattr("src.financial_engine.run_ticker.__module__", "src.financial_engine")` sets a string attribute on the function object to its existing value. It is dead code that does nothing and adds confusion about test intent.

**Fix:** Remove line 678. The comment on line 677 ("Monkeypatch yfinance import used inside run_ticker") is misleading — the actual yfinance mock is done correctly on lines 683-685 via `sys.modules`.

---

### IN-04: `account_mapper.py` — `NAME_PATTERNS` `depreciation_amortization` regex maps to wrong canonical name

**File:** `Analista de Investimentos/12_PYTHON/src/normalization/account_mapper.py:59`
**Issue:** The regex `r"deprecia[çc][ãa]o|amortiza[çc][ãa]o|d&a"` maps to `"depreciation_amortization"`. However, `FLOW_ITEMS` in `financial_engine.py` (line 66) uses the key `"depreciation_amortization_cfo"` (not `"depreciation_amortization"`). A CVM row matched via the name regex (fallback path 3) will be stored under `"depreciation_amortization"` in `normalized_name`, which is not in `FLOW_ITEMS` and therefore silently ignored during LTM aggregation. The EBITDA derivation (`ebit + depreciation_amortization_cfo`) will produce `None` for any company where D&A was name-matched rather than code-matched. This only bites when `CODE_MAP` has no matching entry for the D&A account code — but it is a silent data loss.

**Fix:** Align the regex target name with `FLOW_ITEMS`:
```python
(re.compile(r"deprecia[çc][ãa]o|amortiza[çc][ãa]o|d&a", re.I), "depreciation_amortization_cfo"),
```
Or add `"depreciation_amortization"` to `FLOW_ITEMS` as an alias and handle both keys.

---

### IN-05: `scheduler.py` — `job_bcb_macro()` logs `result['failed']` directly (list, not int) in return string

**File:** `Analista de Investimentos/12_PYTHON/src/scheduler.py:369`
**Issue:** `return f"bcb_macro: inserted={result['inserted']} failed={result['failed']}"` — `result['failed']` is a `list[str]` (series names), not an integer count. The return string will contain the full list (e.g., `failed=['cds_brasil', 'ptax_usd']`) instead of a count. This is inconsistent with the other job return strings (e.g., `f"cvm_ingest: inserted={inserted} failed={len(failed)}"`) and may cause truncation in Telegram notifications (Telegram message limit is 4096 chars).

**Fix:**
```python
return f"bcb_macro: inserted={result['inserted']} failed={len(result['failed'])}"
```

---

_Reviewed: 2026-05-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
