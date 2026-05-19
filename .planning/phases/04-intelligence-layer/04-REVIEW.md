---
phase: 04-intelligence-layer
reviewed: 2026-05-17T14:12:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - Analista de Investimentos/12_PYTHON/src/intelligence_layer.py
  - Analista de Investimentos/12_PYTHON/src/templates/thesis_prompt.j2
  - Analista de Investimentos/12_PYTHON/src/ingestion/db.py
  - Analista de Investimentos/12_PYTHON/src/scheduler.py
  - Analista de Investimentos/12_PYTHON/pyproject.toml
  - Analista de Investimentos/12_PYTHON/config/schedules.yaml
findings:
  critical: 4
  warning: 5
  info: 3
  total: 12
status: issues_found
---

# Phase 4: Intelligence Layer — Code Review Report

**Reviewed:** 2026-05-17T14:12:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

The Phase 4 intelligence layer is structurally sound: parameterized SQL throughout, no hardcoded credentials, `instructor` integration is correctly wired, and the hash gate + daily cap logic is functionally correct. However, four blockers were found: the `instructor.from_provider()` API signature is incorrect (the `api_key` kwarg is not accepted by that function, causing an `__init__` crash at first invocation); the `conviction_score >= 40` filter promised in the docstring is never actually applied (signals with score 1–39 are written to the DB); the macro query fetches `ORDER BY date DESC` globally across all three series without a `GROUP BY`, meaning it silently returns only the most-recent date's values and can miss older-but-valid series; and the `INSERT OR REPLACE` on `thesis_versions` uses a freshly-generated UUID as the PK while the UNIQUE constraint is on `(ticker, version_num)`, causing a silent duplicate insert on any race between two scheduler runs rather than an idempotent replace.

---

## Critical Issues

### CR-01: `instructor.from_provider()` does not accept `api_key` — crashes on first call

**File:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py:208-212`

**Issue:** `instructor.from_provider()` (introduced in instructor >=1.0) takes a provider string and optional client kwargs, but the `api_key` keyword argument is not part of its signature. The Anthropic SDK client is constructed internally by instructor using `ANTHROPIC_API_KEY` from the environment. Passing `api_key=` here raises `TypeError: from_provider() got an unexpected keyword argument 'api_key'` at `IntelligenceClient.__init__` time — i.e., every `run_ticker()` call crashes before any API request is made.

**Fix:** Remove the `api_key` kwarg from `from_provider()`. The key is already loaded via `python-dotenv` / `pydantic-settings` into `os.environ["ANTHROPIC_API_KEY"]`, which the Anthropic SDK picks up automatically:
```python
self._client = instructor.from_provider(
    "anthropic/claude-sonnet-4-6",
    mode=instructor.Mode.ANTHROPIC_TOOLS,
)
```
If explicit key injection is required (e.g., for testing), construct the Anthropic client separately and pass it to `instructor.from_anthropic()`:
```python
import anthropic
self._client = instructor.from_anthropic(
    anthropic.Anthropic(api_key=settings.anthropic_api_key),
    mode=instructor.Mode.ANTHROPIC_TOOLS,
)
```

---

### CR-02: `conviction_score >= 40` filter is documented but never enforced — low-quality signals written to DB

**File:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py:466-543`

**Issue:** The docstring for `compute_opportunity_signals()` states "Only signals with conviction_score >= 40 are included." The comment on line 541 repeats this: "D-17: filter >= 40 already applied above." Neither claim is true. The actual guards at lines 495, 515, and 530 check `score > 0`, not `score >= 40`. `_score_dcf_divergence` returns values in range 1–39 for divergences between 20%–100%, and `_score_momentum_crossover` returns values as low as 1. Signals with conviction 1–39 are appended to the list and written to `opportunity_signals` via `_write_opportunity_signals()`. This contradicts the D-17 decision and pollutes the signals table with low-conviction noise.

**Fix:** Apply the threshold at the filter point, not just in comments:
```python
# DCF_DIVERGENCE
score = _score_dcf_divergence(price, fair_value)
if score >= 40:
    ...

# MOMENTUM_CROSSOVER
score = _score_momentum_crossover(golden, death, momentum)
if score >= 40:
    ...

# IPE_EVENT — score is binary (0 or 30), so this will always be filtered out.
# Either lower the threshold for IPE or raise _score_ipe_event to return 40.
score = _score_ipe_event(ticker, conn)
if score >= 40:
    ...
```

Note the IPE_EVENT signal always returns 30, so it will *never* pass a `>= 40` filter. This is likely a secondary bug: `_score_ipe_event` should return 40 if the intent is for IPE events to emit signals.

---

### CR-03: Macro query returns wrong values — `ORDER BY date DESC` without `GROUP BY` gives at most one row per series only if all three series share the same max date

**File:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py:290-300`

**Issue:** The query is:
```sql
SELECT series_code, value FROM macro_series
WHERE series_code IN (11, 433, 29039)
ORDER BY date DESC
```
This returns ALL rows for the three series, ordered by date descending. The Python loop at lines 298–300 picks only the first occurrence of each `series_code`:
```python
for r in macro_rows:
    if r["series_code"] not in macro:
        macro[r["series_code"]] = r["value"]
```
The series with the most recent date will be populated first. However, if Selic (11) was last updated on 2026-05-15 but CDS (29039) was last updated on 2026-04-01, the CDS row at 2026-04-01 may appear after several Selic rows — meaning the loop works correctly **only by accident**, dependent on SQLite's row ordering for equal-date ties. More critically, `fetchall()` materialises all historical rows for all three series (potentially thousands of rows), and the de-duplication in Python is fragile. A correct fix uses a proper per-series latest value query.

**Fix:**
```python
macro_rows = conn.execute(
    """
    SELECT series_code, value
    FROM macro_series m
    WHERE series_code IN (11, 433, 29039)
      AND date = (
          SELECT MAX(date) FROM macro_series
          WHERE series_code = m.series_code
      )
    """,
).fetchall()
# Or equivalently with a CTE / GROUP BY JOIN pattern.
```
This guarantees the latest value per series regardless of relative update dates and avoids scanning the entire table.

---

### CR-04: `INSERT OR REPLACE` on `thesis_versions` with a fresh UUID PK creates duplicates instead of replacing

**File:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py:685-705`

**Issue:** `thesis_versions` has `id TEXT PRIMARY KEY` and `UNIQUE(ticker, version_num)`. The INSERT generates `id = str(uuid.uuid4())` — a new UUID every time. SQLite's `INSERT OR REPLACE` only replaces a row when the inserted data conflicts on an existing unique constraint. Because the UUID is always new, the PRIMARY KEY never conflicts. If a race condition (two concurrent `run_ticker()` calls for the same ticker) or a re-run with the same `version_num` occurs, the UNIQUE(ticker, version_num) constraint fires and SQLite deletes the old row then inserts the new one — **deleting the old thesis row's UUID**, which can break any foreign-key or application-level reference. In non-concurrent single-process use this is benign, but the intent (idempotent upsert) is undermined. The hash gate at step 3 guards the common case but does not prevent the race.

**Fix:** Use a deterministic ID derived from `(ticker, version_num)` so the PK is stable:
```python
import hashlib
thesis_id = hashlib.sha256(f"{ticker}:{version_num}".encode()).hexdigest()[:36]
# Or use a UNIQUE upsert with ON CONFLICT DO UPDATE:
conn.execute(
    """
    INSERT INTO thesis_versions
    (id, ticker, version_num, ...)
    VALUES (?, ?, ?, ...)
    ON CONFLICT(ticker, version_num) DO UPDATE SET
        generated_at=excluded.generated_at,
        input_hash=excluded.input_hash,
        ...
    """,
    (str(uuid.uuid4()), ticker, version_num, ...),
)
```

---

## Warnings

### WR-01: `tenacity` retry missing on `IntelligenceClient.generate_thesis()` — violates project hard rule

**File:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py:226-240`

**Issue:** `CLAUDE.md` hard rule #3 states: "`tenacity` retry on every external API call (CVM, BCB, yfinance, Anthropic, Telegram)." `generate_thesis()` has no `tenacity` retry decorator. Transient `anthropic.RateLimitError` or `anthropic.APIConnectionError` will be immediately caught and re-raised as `IngestionError`, silently skipping a ticker for the run. `instructor`'s own `max_retries=3` only retries Pydantic validation failures, not network/rate-limit errors.

**Fix:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import anthropic

@retry(
    retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(3),
    reraise=True,
)
def generate_thesis(self, ticker: str, prompt: str, system: str) -> InvestmentThesis:
    ...
```

---

### WR-02: `_is_daily_cap_reached()` uses `DATE(generated_at)` but `generated_at` is stored as a UTC ISO string — timezone boundary bug

**File:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py:590-597`

**Issue:** `generated_at` is set via `datetime.now(timezone.utc).isoformat()` (line 684), producing a string like `"2026-05-17T22:05:00+00:00"`. The cap check at line 594 uses:
```python
"SELECT COUNT(*) FROM thesis_versions WHERE ticker = ? AND DATE(generated_at) = ?"
(ticker, today)
```
where `today = date.today().isoformat()` uses **local wall-clock time**. On a machine in UTC-3 (Brasília), `date.today()` returns `2026-05-17` but a thesis generated at 23:00 local is stored as `2026-05-18T02:00:00+00:00`. `DATE("2026-05-18T02:00:00+00:00")` in SQLite returns `"2026-05-18"`, so the cap query for `today="2026-05-17"` returns 0 and the thesis is generated again — bypassing the daily cap across the midnight boundary.

**Fix:** Store `generated_at` as local date string or normalise both sides to UTC:
```python
today_utc = datetime.now(timezone.utc).date().isoformat()
row = conn.execute(
    "SELECT COUNT(*) FROM thesis_versions WHERE ticker = ? AND DATE(generated_at) = ?",
    (ticker, today_utc),
).fetchone()
```
And align `date.today()` in `_write_opportunity_signals()` (line 557) similarly.

---

### WR-03: `IntelligenceClient` is instantiated inside the hot path of `run_ticker()` on every call

**File:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py:661`

**Issue:** `client = IntelligenceClient()` is called at line 661 inside `run_ticker()`, which is called in a loop by `run_all()`. Each instantiation reads `settings`, imports `instructor`, and constructs an Anthropic client with a new HTTP connection pool. For N tickers this creates N separate clients. This is unnecessary overhead and makes it harder to inject a test double.

**Fix:** Accept an optional `client: IntelligenceClient | None = None` parameter in `run_ticker()`, defaulting to a module-level singleton:
```python
_intelligence_client: IntelligenceClient | None = None

def _get_client() -> IntelligenceClient:
    global _intelligence_client
    if _intelligence_client is None:
        _intelligence_client = IntelligenceClient()
    return _intelligence_client
```

---

### WR-04: `_assemble_prompt_data()` swallows all exceptions from `SectorConfig.for_ticker()` silently

**File:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py:313-319`

**Issue:**
```python
try:
    cfg = SectorConfig.for_ticker(ticker)
    ...
except Exception:
    sector = "Desconhecido"
    is_bank_model = False
```
A bare `except Exception` with no logging means any bug in `SectorConfig` (import error, data corruption, wrong ticker format) is silently masked. Crucially, `is_bank_model` defaults to `False` — so a bank ticker (ITUB4, BBDC4) that fails sector lookup will be routed through the DCF/FCFF model path, producing a structurally wrong thesis without any warning. The Jinja2 template at line 23 uses `is_bank_model` to select the model label, and the system prompt does not compensate.

**Fix:**
```python
except Exception as exc:
    log.warning(f"[{ticker}] SectorConfig.for_ticker falhou: {exc} — usando defaults")
    sector = "Desconhecido"
    is_bank_model = False
```
Consider also raising if the ticker is in a known-banks list so the error is not silently ignored in production.

---

### WR-05: `run_ticker()` catches `Exception` broadly and returns a `ThesisResult(error=...)` — `IngestionError` path is redundant and confusing

**File:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py:729-734`

**Issue:** The exception handler structure is:
```python
except IngestionError:
    raise          # line 730-731
except Exception as exc:
    log.warning(...)
    return ThesisResult(ticker=ticker, error=str(exc))
```
The docstring says D-05 means hard-fail on `IngestionError` — yet `run_all()` catches `IngestionError` and appends an error result anyway (lines 768-771). The re-raise in `run_ticker()` and the catch in `run_all()` are consistent, but the broad `except Exception` below means any non-`IngestionError` exception (e.g., `sqlite3.OperationalError` mid-write after the thesis was already generated but before `conn.commit()`) returns a soft error result while the thesis row may be partially written. The `conn.close()` in `finally` does not roll back an uncommitted transaction.

**Fix:** Add an explicit rollback in the broad exception handler to ensure atomicity:
```python
except Exception as exc:
    try:
        conn.rollback()
    except Exception:
        pass
    log.warning(f"[{ticker}] run_ticker falhou: {exc}")
    return ThesisResult(ticker=ticker, error=str(exc))
```

---

## Info

### IN-01: Docstring and module header disagree on `instructor` API used

**File:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py:7` and `194`

**Issue:** The module docstring (line 7) states "via `instructor.from_anthropic()` (ANTHROPIC_TOOLS mode)" and the class docstring (line 194) repeats "Wraps `instructor.from_anthropic()`". The actual code uses `instructor.from_provider()`. Stale documentation causes confusion when debugging.

**Fix:** Update both docstrings to reference `instructor.from_provider()`.

---

### IN-02: `ev_revenue` is hardcoded to `None` in `run_ticker()` but is available in the DB

**File:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py:632`

**Issue:**
```python
"ev_revenue": None,  # not in _assemble_prompt_data — will default to 0.0 in compute_input_hash
```
`financial_multiples` has an `ev_revenue` column (confirmed in `db.py:117`) and `_assemble_prompt_data()` fetches the full multiples row. Hardcoding `None` here means `ev_revenue` is excluded from the input hash even when it changes, causing the hash gate to miss updates to this multiple. This is a silent hash incompleteness, not a crash.

**Fix:** Add `ev_revenue` to `_assemble_prompt_data()`'s return dict and propagate it to `multiples_dict` in `run_ticker()`:
```python
# in _assemble_prompt_data return dict:
"ev_revenue": multiples["ev_revenue"] if multiples else None,

# in run_ticker multiples_dict:
"ev_revenue": data.get("ev_revenue"),
```

---

### IN-03: `schedules.yaml` — `b3_prices` scheduled at 19:00, `cvm_ingest` at 19:15, `financial_engine` at 19:50, but `pipeline` (19:30) and `analyze` (20:00) are legacy jobs that duplicate financial_engine work

**File:** `Analista de Investimentos/12_PYTHON/config/schedules.yaml:17-22` and `47-48`

**Issue:** The schedule runs both `pipeline` (19:30) and `analyze` (20:00) — legacy jobs from the pre-Phase-4 architecture — alongside the new `financial_engine` (19:50) and `intelligence` (21:00). Based on `scheduler.py`, `job_analyze()` calls `run_metrics`, `assess_risk`, `run_valuation`, and `InsightEngine.generate()` — overlapping with what `financial_engine` computes. The `pipeline` job (19:30) runs before `financial_engine` (19:50), so it processes stale data. This is a scheduling debt that may cause redundant API calls or overwrite `financial_engine` outputs.

**Fix:** Audit whether `pipeline` and `analyze` jobs are still needed post-Phase-4. If `financial_engine` supersedes them, disable them in `schedules.yaml` to avoid redundant work and potential output collisions.

---

_Reviewed: 2026-05-17T14:12:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
