# Phase 4: Intelligence Layer - Research

**Researched:** 2026-05-12
**Domain:** Structured LLM synthesis with instructor + Pydantic v2, SQLite versioned storage, hash-gated API calls, Jinja2 templating, APScheduler integration
**Confidence:** HIGH (core stack verified against live PyPI registry and official docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Thesis Pydantic Schema**
- D-01: Structured sub-objects — `class Driver(BaseModel): title: str, description: str, impact: Literal['HIGH','MEDIUM','LOW']` and `class Risk(BaseModel): title: str, description: str, severity: Literal['HIGH','MEDIUM','LOW']`
- D-02: `InvestmentThesis` fields: `bull_case: str`, `bear_case: str`, `drivers: list[Driver]` (3-5), `risks: list[Risk]` (3-5), `fair_value_brl: float`, `methodology_disclosure: str`, `positioning: Literal['COMPRAR','MANTER','VENDER']`, `confidence: Literal['ALTA','MEDIA','BAIXA']`, `rationale: str`, `summary_one_line: str`
- D-03: `fair_value_brl` injected from DCF — never LLM-generated; post-generation cross-check ±10% tolerance; flag `dcf_deviation_flag = True` but still store

**instructor Wiring**
- D-04: New `IntelligenceClient` in `src/intelligence_layer.py` — `LLMClient` stays unchanged
- D-05: Hard-fail on instructor validation failure — raise `IngestionError`, never store partial thesis
- D-06: `instructor.from_anthropic()` with `mode=instructor.Mode.ANTHROPIC_TOOLS`

**Prompt Template**
- D-07: Jinja2 template in `src/templates/thesis_prompt.j2`
- D-08: Full snapshot injection — LTM, multiples, DCF, macro, signals, last 3 news, ticker metadata, explicit fair_value instruction in Portuguese

**Hash-Based Gate**
- D-09: SHA-256 of (fair_value_brl + upside_pct + top-5 multiples + selic + cds + momentum_score + top-3 news URLs), serialized as stable JSON
- D-10: Gate: query `MAX(generated_at)` for ticker where `input_hash = current_hash` — if found, skip
- D-11: 2-per-day cap — count rows in `thesis_versions` where `ticker = X AND DATE(generated_at) = today`; if >= 2, skip

**Thesis Versioning**
- D-12: `thesis_versions` table schema (TEXT UUID PK, ticker, version_num, generated_at, input_hash, positioning, confidence, fair_value_brl, dcf_deviation_flag, thesis_json, diff_summary; UNIQUE(ticker, version_num))
- D-13: `version_num` auto-incremented per ticker; `diff_summary` = field-by-field human-readable diff
- D-14: `thesis_latest` VIEW — `SELECT * FROM thesis_versions WHERE (ticker, version_num) IN (SELECT ticker, MAX(version_num) FROM thesis_versions GROUP BY ticker)`

**Opportunity Signals**
- D-15: `compute_opportunity_signals(ticker)` in `intelligence_layer.py`, called after thesis generation
- D-16: `OpportunitySignal` schema: ticker, signal_type (DCF_DIVERGENCE/MOMENTUM_CROSSOVER/IPE_EVENT), description, conviction_score (0-100), generated_at
- D-17: Conviction score weighted sum: DCF_DIVERGENCE up to 40pts, MOMENTUM_CROSSOVER up to 30pts, IPE_EVENT 30pts binary; emit only if score >= 40
- D-18: Top-3 signals stored in `opportunity_signals` table, keyed (ticker, computed_date, signal_type), INSERT OR REPLACE

**Scheduler Integration**
- D-19: `job_intelligence()` in `scheduler.py` with `bind_run_id("intelligence")`; cron `0 21 * * 1-5`
- D-20: Public API `run_ticker(ticker) -> ThesisResult` + `run_all() -> list[ThesisResult]`; `ThesisResult` wraps thesis + signals + metadata

### Claude's Discretion
(None explicitly — all implementation details locked in CONTEXT.md)

### Deferred Ideas (OUT OF SCOPE)
- Multi-scenario thesis (bull/base/bear DCF comparison)
- Peer comparison section in thesis
- LLM-enriched insights via `insight_engine.py`
- Thesis quality scoring / feedback loop
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INT-01 | AI investment thesis via Claude/instructor with enforced Pydantic schema; output in Portuguese | D-06 + instructor API verified; schema locked in D-01/D-02 |
| INT-02 | All numbers injected from Financial Engine; post-gen cross-check ±10% | D-03; read path from financial_dcf verified in db.py |
| INT-03 | Input hash per thesis; regenerate only on change; max 2/day per ticker | D-09/D-10/D-11; hashlib.sha256 + json.dumps pattern confirmed |
| INT-04 | Thesis stored in DB with version history; each version records input hash, timestamp, diff | D-12/D-13/D-14; SQLite DDL pattern confirmed against db.py |
| INT-05 | Opportunity signals: price vs DCF divergence, momentum shift, IPE event | D-15/D-16/D-17; reads from existing financial_* tables |
| INT-06 | Signals ranked across watchlist by conviction score; top 3 as structured output | D-18; INSERT OR REPLACE pattern matches existing code |
</phase_requirements>

---

## Summary

Phase 4 adds a pure synthesis layer on top of the completed Financial Engine (Phase 3). The new `src/intelligence_layer.py` module reads from six existing tables (`financial_ltm`, `financial_multiples`, `financial_dcf`, `financial_signals`, `macro_series`, `news_articles`), calls Claude via `instructor.from_anthropic()` with a Pydantic-enforced `InvestmentThesis` schema, applies a two-tier gate (hash deduplication + 2/day cap), stores versioned thesis history, and computes three types of opportunity signals.

The key engineering challenge is the `instructor` integration. The library version on PyPI is **1.15.1** [VERIFIED: pip index] and is NOT yet installed in the project venv [VERIFIED: pip show returned empty]. The project currently has `anthropic==0.100.0` [VERIFIED: pip show] and `pydantic==2.13.4` [VERIFIED: pip show] — both compatible with instructor 1.x. The `instructor.from_anthropic()` function defaults to `mode=instructor.Mode.ANTHROPIC_TOOLS`, which matches D-06 exactly. When instructor exhausts all retries, it raises `InstructorRetryException` — the plan must catch this and re-raise as `IngestionError` per D-05.

The second challenge is extending `db.py` safely. The established pattern is: append new DDL blocks to `_CREATE_SQL`, add both new tables and the `thesis_latest` VIEW in the same `executescript()` call, and extend `test_db_schema.py` assertions from "exactly 8 tables" to ">= 10 tables". The VIEW must be created after both tables — SQLite's `CREATE VIEW IF NOT EXISTS` is idempotent like `CREATE TABLE IF NOT EXISTS`.

**Primary recommendation:** One new module (`src/intelligence_layer.py`) + one new template (`src/templates/thesis_prompt.j2`) + two new DB tables + one DB view + one new scheduler job + one pyproject.toml dependency. All other files are touched minimally (db.py DDL append, scheduler.py registry, schedules.yaml cron entry, pyproject.toml dependency).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Thesis generation (LLM call) | Intelligence Layer (`intelligence_layer.py`) | — | Single module owns all Claude API interaction for structured thesis |
| Data assembly for prompt | Intelligence Layer | DB (read) | Reads six tables; assembles dict before rendering template |
| Prompt rendering | Intelligence Layer | Filesystem (`src/templates/`) | Jinja2 renders template with injected values |
| Hash computation and gate | Intelligence Layer | DB (read) | Stateless computation; gate checks `thesis_versions` table |
| Thesis persistence | Intelligence Layer | DB (write) | Writes to `thesis_versions`; VIEW is DB-only |
| Signal computation | Intelligence Layer | DB (read) | Pure computation from financial_* tables |
| Signal persistence | Intelligence Layer | DB (write) | Writes to `opportunity_signals` |
| Scheduling | Scheduler (`scheduler.py`) | — | `job_intelligence()` added to `_JOB_REGISTRY` |
| Schema definition | DB (`db.py`) | — | DDL appended to `_CREATE_SQL`; VIEW created in same script |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| instructor | 1.15.1 | Structured LLM output via Pydantic | Official solution for tool-use validation with Anthropic; auto-retry on schema violation |
| anthropic | 0.100.0 (installed) | Claude API client | Already installed; instructor wraps it |
| pydantic | 2.13.4 (installed) | Schema definition and validation | Already installed; instructor 1.x requires Pydantic v2 |
| jinja2 | not installed — must add | Prompt template rendering | Standard Python templating; separates prompt data from prompt structure |
| hashlib | stdlib | SHA-256 input hashing | No external dependency; stdlib reliability |
| json | stdlib | Stable serialization for hash input | `sort_keys=True` guarantees deterministic output |

[VERIFIED: pip index versions instructor — latest is 1.15.1]
[VERIFIED: pip show anthropic — 0.100.0 installed]
[VERIFIED: pip show pydantic — 2.13.4 installed]
[VERIFIED: pip list — jinja2 NOT installed; instructor NOT installed]

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | 9.1.4 (installed) | Retry decorator | Network-level retries on Anthropic API (rate limit / 529); separate from instructor's validation retries |
| loguru | 0.7.0+ (installed) | Structured logging | Already the project logger — use `bind_run_id("intelligence")` |
| uuid | stdlib | UUID primary keys | TEXT UUIDs match existing schema pattern |
| datetime | stdlib | ISO date strings, UTC timestamps | Matches existing ingested_at pattern |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| instructor ANTHROPIC_TOOLS | instructor ANTHROPIC_JSON | TOOLS mode uses native tool-call API with validation retry loop; JSON mode requires manual extraction and loses auto-retry — D-06 locks TOOLS |
| jinja2 | f-string prompt | Jinja2 is version-controllable, testable, iterable without code changes — D-07 locks jinja2 |
| instructor max_retries | tenacity on top of instructor | Instructor's built-in retry loop feeds validation errors back to the LLM (better than blind network retry); tenacity still useful for 429/529 |

**Installation:**
```bash
pip install "instructor>=1.15.1" "jinja2>=3.1.0"
```

**pyproject.toml additions:**
```toml
"instructor>=1.0.0",    # structured LLM output (latest: 1.15.1)
"jinja2>=3.1.0",        # prompt template rendering
```

---

## Architecture Patterns

### System Architecture Diagram

```
tickers.yaml (watchlist)
        |
        v
run_all() ---> [per ticker] run_ticker(ticker)
                                   |
                         +---------+----------+
                         |                    |
                    GATE CHECK           [if no cached hash]
                    (hash + 2/day)              |
                         |                     v
                    [skip if hit]    _assemble_prompt_data(ticker, conn)
                                     reads: financial_ltm
                                             financial_multiples
                                             financial_dcf
                                             financial_signals
                                             macro_series
                                             news_articles
                                             |
                                    Jinja2.render(thesis_prompt.j2, data)
                                             |
                                    IntelligenceClient.generate_thesis()
                                    instructor.from_anthropic()
                                    mode=ANTHROPIC_TOOLS
                                             |
                                    [validation loop, max_retries=3]
                                             |
                                    InvestmentThesis (Pydantic)
                                             |
                                 +-----------+-----------+
                                 |                       |
                          DCF cross-check         compute_opportunity_signals()
                          ±10% tolerance           DCF_DIVERGENCE
                          set dcf_deviation_flag   MOMENTUM_CROSSOVER
                                 |                 IPE_EVENT
                                 v                       |
                          thesis_versions           opportunity_signals
                          (INSERT OR REPLACE)       (INSERT OR REPLACE)
                                 |
                          thesis_latest VIEW
                          (Phase 5 reads here)
```

### Recommended Project Structure
```
src/
├── intelligence_layer.py      # new — entire Phase 4 logic
├── templates/                 # new directory
│   └── thesis_prompt.j2       # new — Jinja2 prompt template
├── ingestion/
│   └── db.py                  # modified — append thesis_versions + opportunity_signals + view
├── scheduler.py               # modified — add job_intelligence() and _JOB_REGISTRY entry
config/
└── schedules.yaml             # modified — add intelligence cron entry
```

### Pattern 1: instructor.from_anthropic() — Structured Generation

**What:** Wraps an `anthropic.Anthropic()` client so that `messages.create()` accepts `response_model` and validates the response against a Pydantic schema, retrying up to `max_retries` times when validation fails.

**When to use:** Any time Claude must return structured, schema-validated output.

**Exact signatures** [VERIFIED: github.com/instructor-ai/instructor /providers/anthropic/client.py]:

```python
# from_anthropic() parameters:
instructor.from_anthropic(
    client: anthropic.Anthropic,   # required — the raw Anthropic client
    mode: instructor.Mode = instructor.Mode.ANTHROPIC_TOOLS,  # default
    beta: bool = False,            # True → uses client.beta.messages.create
    **kwargs,                      # passed to Instructor constructor
) -> instructor.Instructor

# Valid modes for Anthropic:
# instructor.Mode.ANTHROPIC_TOOLS        ← use this (D-06)
# instructor.Mode.ANTHROPIC_JSON
# instructor.Mode.ANTHROPIC_REASONING_TOOLS
# instructor.Mode.ANTHROPIC_PARALLEL_TOOLS
```

**create() call signature** [VERIFIED: github.com/instructor-ai/instructor /core/client.py]:

```python
instructor_client.messages.create(
    # Standard Anthropic parameters
    model="claude-sonnet-4-6",
    max_tokens=4096,
    system="...",                          # optional system prompt
    messages=[{"role": "user", "content": "..."}],
    # Instructor-specific parameters
    response_model=InvestmentThesis,       # the Pydantic model to validate against
    max_retries=3,                         # default=3; retries on validation failure
    # Optional Anthropic parameters
    temperature=0.3,
)
# Returns: InvestmentThesis instance (not a raw anthropic response)
```

**Key behavioral detail:** When validation fails, instructor feeds the Pydantic validation error back to the LLM in the next retry message ("Here's what was wrong: ..."). This is different from a blind network retry. After `max_retries` exhausted, raises `instructor.exceptions.InstructorRetryException`.

**Full IntelligenceClient pattern** (from CONTEXT.md specifics, confirmed compatible):

```python
# Source: CONTEXT.md D-04 + verified instructor API
import instructor
import anthropic
from src.utils.errors import IngestionError

class IntelligenceClient:
    def __init__(self):
        from config.settings import settings
        self._raw = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._client = instructor.from_anthropic(
            self._raw,
            mode=instructor.Mode.ANTHROPIC_TOOLS,
        )

    def generate_thesis(
        self,
        ticker: str,
        prompt: str,
        system: str,
    ) -> "InvestmentThesis":
        try:
            return self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                response_model=InvestmentThesis,
                max_retries=3,
            )
        except Exception as exc:
            # Catches InstructorRetryException + any anthropic API errors
            raise IngestionError("generate_thesis", exc) from exc
```

### Pattern 2: Jinja2 Template Loading

**What:** Load a `.j2` template from the filesystem, render with a data dict, return rendered string.

**When to use:** The thesis prompt (D-07/D-08).

```python
# Source: jinja2.palletsprojects.com/en/3.1.x/api
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pathlib import Path

_TEMPLATE_DIR = Path(__file__).parent / "templates"

def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        undefined=StrictUndefined,   # raises on missing variable — catches bugs early
        autoescape=False,            # prompt is plain text, not HTML
    )

def render_thesis_prompt(data: dict) -> str:
    env = _get_jinja_env()
    template = env.get_template("thesis_prompt.j2")
    return template.render(**data)
```

**Float formatting in Jinja2** [VERIFIED: jinja2.palletsprojects.com/en/3.1.x]:

```jinja2
{# Two decimal places — use format filter #}
{{ fair_value_brl | round(2) }}           {# 42.55 → 42.55 (still float) #}
{{ "R$ %.2f" | format(fair_value_brl) }}  {# "R$ 42.55" — printf style #}
{{ "{:.2f}".format(fair_value_brl) }}     {# "42.55" — Python str.format #}

{# Percentage #}
{{ "%.1f%%" | format(upside_pct * 100) }} {# "+13.6%" #}
```

**Gotcha:** `|round(2)` returns a float, not a string — always wrap in format filter for display. Use `StrictUndefined` so missing template variables fail loudly rather than silently rendering as empty string.

### Pattern 3: SHA-256 Hash for Gate

**What:** Stable hash of financial inputs to detect when thesis needs regeneration.

**When to use:** D-09 — before every thesis generation attempt.

```python
# Source: Python stdlib hashlib docs + CONTEXT.md D-09 specifics
import hashlib, json

def compute_input_hash(
    fair_value_brl: float | None,
    upside_pct: float | None,
    multiples: dict,          # pe_ratio, ev_ebitda, pb_ratio, dividend_yield, ev_revenue
    selic: float | None,
    cds: float | None,
    momentum_score: int | None,
    news_urls: list[str],     # top-3 sorted
) -> str:
    hash_dict = {
        "fair_value_brl": round(fair_value_brl, 2) if fair_value_brl is not None else None,
        "upside_pct": round(upside_pct, 4) if upside_pct is not None else None,
        "pe_ratio": round(multiples.get("pe_ratio") or 0.0, 2),
        "ev_ebitda": round(multiples.get("ev_ebitda") or 0.0, 2),
        "pb_ratio": round(multiples.get("pb_ratio") or 0.0, 2),
        "dividend_yield": round(multiples.get("dividend_yield") or 0.0, 4),
        "ev_revenue": round(multiples.get("ev_revenue") or 0.0, 2),
        "selic": round(selic, 4) if selic is not None else None,
        "cds": round(cds, 4) if cds is not None else None,
        "momentum_score": momentum_score,
        "news_urls": sorted(news_urls)[:3],  # sorted for stability
    }
    payload = json.dumps(hash_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()
```

**Why round before hashing:** Float arithmetic can produce `42.550000000001` vs `42.55` from different code paths. Rounding to a fixed precision (2dp for BRL values, 4dp for rates) eliminates spurious hash mismatches. [ASSUMED — standard practice, not in official docs]

### Pattern 4: Extending db.py Safely

**What:** Append new DDL to `_CREATE_SQL` in `db.py` and call `executescript()` — same pattern used in Phases 2 and 3.

**When to use:** Adding `thesis_versions`, `opportunity_signals`, and `thesis_latest` VIEW.

**Key insight about CREATE VIEW in SQLite:**

```sql
-- SQLite supports CREATE VIEW IF NOT EXISTS — same idempotency as CREATE TABLE IF NOT EXISTS
-- VERIFIED: SQLite documentation — executescript() processes each statement sequentially
CREATE VIEW IF NOT EXISTS thesis_latest AS
SELECT * FROM thesis_versions
WHERE (ticker, version_num) IN (
    SELECT ticker, MAX(version_num)
    FROM thesis_versions
    GROUP BY ticker
);
```

**Critical ordering rule:** The VIEW must come AFTER both tables in `_CREATE_SQL` because `executescript()` runs statements in order. SQLite will error if a VIEW references a table not yet created in the same script — but `CREATE VIEW IF NOT EXISTS` on an already-created view is a no-op, so subsequent `init_db()` calls are safe.

**db.py extension approach:**

```python
# In db.py — append to existing _CREATE_SQL string
_CREATE_SQL = """
... (existing 8 tables) ...

CREATE TABLE IF NOT EXISTS thesis_versions (
    id                TEXT PRIMARY KEY,
    ticker            TEXT NOT NULL,
    version_num       INTEGER NOT NULL,
    generated_at      TEXT NOT NULL,
    input_hash        TEXT NOT NULL,
    positioning       TEXT NOT NULL,
    confidence        TEXT NOT NULL,
    fair_value_brl    REAL NOT NULL,
    dcf_deviation_flag INTEGER DEFAULT 0,
    thesis_json       TEXT NOT NULL,
    diff_summary      TEXT,
    UNIQUE(ticker, version_num)
);
CREATE INDEX IF NOT EXISTS idx_thesis_ticker ON thesis_versions(ticker);
CREATE INDEX IF NOT EXISTS idx_thesis_hash ON thesis_versions(ticker, input_hash);

CREATE TABLE IF NOT EXISTS opportunity_signals (
    id               TEXT PRIMARY KEY,
    ticker           TEXT NOT NULL,
    computed_date    TEXT NOT NULL,
    signal_type      TEXT NOT NULL,
    description      TEXT NOT NULL,
    conviction_score INTEGER NOT NULL,
    ingested_at      TEXT NOT NULL,
    UNIQUE(ticker, computed_date, signal_type)
);
CREATE INDEX IF NOT EXISTS idx_signals_ticker ON opportunity_signals(ticker);

CREATE VIEW IF NOT EXISTS thesis_latest AS
SELECT * FROM thesis_versions
WHERE (ticker, version_num) IN (
    SELECT ticker, MAX(version_num)
    FROM thesis_versions
    GROUP BY ticker
);
"""
```

**Test impact:** `test_db_schema.py` currently asserts `count == 8` in `test_init_db_is_idempotent`. This must change to `>= 10` (2 new tables; VIEW appears in `sqlite_master` with `type='view'` not `type='table'`). The `test_all_tables_have_text_pk` test iterates a hard-coded table list — must be extended with the two new tables.

### Pattern 5: Scheduler Job Registration

**What:** Add `job_intelligence()` to `_JOB_REGISTRY` and append cron entry to `schedules.yaml`.

**When to use:** D-19 wiring.

```python
# In scheduler.py — append to _JOB_REGISTRY dict
def job_intelligence() -> str:
    """Gera teses estruturadas + sinais de oportunidade para todos os tickers — INT-01..06."""
    from src.intelligence_layer import run_all
    from src.utils.logger import bind_run_id, get_logger as _get
    from datetime import datetime, timezone

    _log = _get(__name__)
    with bind_run_id("intelligence") as run_id:
        _log.info(f"[intelligence] iniciado — run_id={run_id}")
        t0 = time.time()
        results = run_all()
        ok = sum(1 for r in results if not r.skipped and r.thesis is not None)
        skipped = sum(1 for r in results if r.skipped)
        fail = len(results) - ok - skipped
        duration_ms = int((time.time() - t0) * 1000)
        # D-15 pattern: structured summary log
        _log.info(
            "[intelligence] summary",
            source="intelligence",
            records_inserted=ok,
            records_updated=0,
            duration_ms=duration_ms,
            status="ok" if fail == 0 else "partial",
            last_ingested_at=datetime.now(timezone.utc).isoformat(),
            skipped_tickers=skipped,
            failed_tickers=fail,
        )
        return f"intelligence: ok={ok} skipped={skipped} failed={fail}"

_JOB_REGISTRY: dict[str, Callable] = {
    # ... existing entries ...
    "intelligence": job_intelligence,   # INT-01..06
}
```

```yaml
# In schedules.yaml — append
- job: intelligence
  cron: "0 21 * * 1-5"      # seg-sex 21:00 — após financial_engine (19:50) e analyze (20:00)
  description: Gerar teses estruturadas e sinais de oportunidade
```

### Pattern 6: ThesisResult Dataclass

**What:** Return type from `run_ticker()` — wraps thesis + signals + skip metadata.

```python
# Source: CONTEXT.md D-20 + Phase 3 FinancialResult pattern
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ThesisResult:
    ticker: str
    skipped: bool = False
    skip_reason: Optional[str] = None   # "hash_match", "daily_cap", "no_financial_data"
    thesis: Optional[InvestmentThesis] = None
    signals: list[OpportunitySignal] = field(default_factory=list)
    version_num: Optional[int] = None
    dcf_deviation_flag: bool = False
    error: Optional[str] = None
```

### Anti-Patterns to Avoid

- **Calling `run_ticker()` from `financial_engine.py`:** Phase 4 reads from DB tables, not from the Financial Engine's public API. Calling `run_ticker()` would trigger re-computation (slow, wasteful). Always read from `financial_*` tables directly via `get_connection()`.
- **f-string SQL with ticker:** Every SQL statement must use parameterized queries `(ticker,)` — never `f"WHERE ticker = '{ticker}'"`. Applies to all six read tables and two write tables.
- **Storing `instructor` client as module-level singleton:** `anthropic.Anthropic()` reads `api_key` at construction time. Keep `IntelligenceClient` as a per-job instantiation to avoid stale settings.
- **Trusting LLM for `fair_value_brl`:** The prompt instructs Claude to echo the injected value. The post-generation cross-check (D-03) must run regardless — always compare `thesis.fair_value_brl` against `dcf.fair_value_brl`.
- **Using `json.loads()` on thesis_json without error handling:** `thesis_json` is a TEXT column. Always wrap in try/except when reading for diff computation.
- **Omitting `CREATE VIEW IF NOT EXISTS` — just using `CREATE VIEW`:** `executescript()` called by `init_db()` is idempotent. Using bare `CREATE VIEW` will raise on the second call.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output validation | Custom JSON parser + regex | `instructor` + Pydantic | instructor handles tool-call parsing, JSON extraction, re-ask retry loop, and exception wrapping — 300+ lines of state machine |
| Prompt template with variables | f-string with if/else | `jinja2.Environment` + `.j2` file | Jinja2 handles None values, filters, conditionals, whitespace control; f-strings fail on None |
| Schema validation with retries | Manual try/except + retry | instructor `max_retries` | Validation errors are fed back to LLM in context — not just blind retries |
| SQLite row deduplication | Custom MERGE logic | `INSERT OR REPLACE` + `UNIQUE` index | Already established pattern in all financial_* tables |

**Key insight:** `instructor` eliminates the hardest part of LLM integration — handling malformed responses. Without it, you'd need to parse Claude's tool-call XML/JSON, validate field types, handle partial responses, and implement the re-ask loop manually.

---

## Runtime State Inventory

> NOT a rename/refactor phase — no existing names are changing. This section is included for completeness.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | No existing thesis data — `thesis_versions` and `opportunity_signals` tables don't exist yet | None — tables created by `init_db()` |
| Live service config | No external service config affected | None |
| OS-registered state | No OS-level names changing | None |
| Secrets/env vars | `ANTHROPIC_API_KEY` already in `.env` — no new secrets needed | None |
| Build artifacts | instructor and jinja2 not installed — must `pip install` | Run `pip install "instructor>=1.15.1" "jinja2>=3.1.0"` and add to pyproject.toml |

---

## Common Pitfalls

### Pitfall 1: instructor vs anthropic message format for system prompt
**What goes wrong:** Passing `system` as a single string vs as a list of `{"type": "text", "text": "..."}` objects. With `instructor.from_anthropic()`, the system parameter follows the raw Anthropic SDK convention — a plain string is acceptable.
**Why it happens:** `LLMClient` uses the list format with `cache_control` (prompt caching). `IntelligenceClient` is simpler — no caching for thesis generation (each call has a different prompt anyway).
**How to avoid:** Pass `system` as a plain string to `self._client.messages.create()`. Do NOT add `cache_control` — the prompt is unique per ticker per day, so caching offers no benefit.
**Warning signs:** `anthropic.BadRequestError` with "Invalid system prompt format".

### Pitfall 2: InstructorRetryException vs anthropic API errors
**What goes wrong:** Catching only `InstructorRetryException` and missing raw `anthropic.RateLimitError` (429) or `anthropic.InternalServerError` (529).
**Why it happens:** instructor's retry loop handles schema validation failures, but network/rate errors at the HTTP level may not be caught by instructor's retry mechanism (depends on version).
**How to avoid:** Wrap the entire `generate_thesis()` call in a broad `except Exception` that converts to `IngestionError` (per D-05). Add outer retry using the existing `retry` decorator from `src/utils/retry.py` for 429/529 with exponential backoff.
**Warning signs:** `IntelligenceClient.generate_thesis()` raises with `anthropic.RateLimitError` uncaught.

### Pitfall 3: SQLite VIEW and test assertion breakage
**What goes wrong:** `test_db_schema.py::test_init_db_is_idempotent` asserts `count == 8` (table count). After Phase 4, there are 10 tables. The VIEW is separate — it appears in `sqlite_master` with `type='view'`.
**Why it happens:** Tests were written with a hard-coded "8 tables" assertion.
**How to avoid:** Change assertion to `count >= 10` (or exact 10). Separately test that `thesis_latest` appears in `sqlite_master WHERE type='view'`.
**Warning signs:** Existing test suite fails on `test_init_db_is_idempotent` after db.py is modified.

### Pitfall 4: `diff_summary` on first thesis version (no prior version)
**What goes wrong:** `_compute_diff_summary(old_thesis, new_thesis)` crashes when `old_thesis` is `None` (first thesis for a ticker).
**Why it happens:** `MAX(version_num)` returns `None` when no prior rows exist for the ticker.
**How to avoid:** Guard with `if prior_thesis_json is None: return None` — `diff_summary` column is nullable per D-12.
**Warning signs:** `TypeError: 'NoneType' object is not subscriptable` in `_compute_diff_summary`.

### Pitfall 5: Jinja2 StrictUndefined on None financial values
**What goes wrong:** Template renders `fair_value_brl` and it is `None` (DCF returned `confidence_flag='INPUT_INVALIDO'`). With `StrictUndefined`, a missing variable raises. With `None` variable, Jinja2 renders `"None"` as a string.
**Why it happens:** `financial_dcf.fair_value_brl` can be NULL in the database (invalid DCF inputs).
**How to avoid:** Guard in `_assemble_prompt_data()`: if `fair_value_brl is None`, skip thesis generation for this ticker and return `ThesisResult(ticker=ticker, skipped=True, skip_reason="no_dcf_value")`. Document this in template with a comment: `{# fair_value_brl is guaranteed non-None here — None case skips generation #}`.
**Warning signs:** Thesis contains "None" as a string for fair value.

### Pitfall 6: `INSERT OR REPLACE` version_num gap in thesis_versions
**What goes wrong:** `INSERT OR REPLACE INTO thesis_versions ... UNIQUE(ticker, version_num)` — if two concurrent runs compute `version_num = MAX + 1 = 3` simultaneously, one silently replaces the other.
**Why it happens:** SQLite is single-writer but job functions call `MAX(version_num)` and `INSERT` in separate statements — a race window exists if `run_all()` is ever called concurrently.
**How to avoid:** Since `max_instances=1` and `coalesce=True` are set in APScheduler (confirmed in `scheduler.py`), concurrent runs cannot happen in the scheduled path. For defensive safety, add `busy_timeout=5000` (already set in `get_connection()`) — SQLite will queue rather than fail.
**Warning signs:** `UNIQUE constraint failed: thesis_versions.ticker, thesis_versions.version_num`.

### Pitfall 7: IPE event query for conviction scoring — correct table filter
**What goes wrong:** Querying `cvm_statements WHERE period_type = 'IPE'` with `normalized_name IS NOT NULL` filter excludes IPE rows (IPE events have account_code/account_name but no normalized_name in the current schema).
**Why it happens:** IPE rows have `normalized_name = NULL` — the backfill function in `financial_engine.py` only processes rows with non-null `account_code`.
**How to avoid:** Query for IPE events using `period_type = 'IPE'` WITHOUT the `normalized_name IS NOT NULL` filter. Check `reference_date >= DATE('now', '-30 days')`.

```sql
SELECT COUNT(*) FROM cvm_statements
WHERE ticker = ? AND period_type = 'IPE'
  AND reference_date >= DATE('now', '-30 days')
```

**Warning signs:** IPE_EVENT signal never fires even for tickers with recent CVM events.

### Pitfall 8: temperature with ANTHROPIC_TOOLS mode
**What goes wrong:** Setting `temperature=0` may cause issues with tool-use mode in some Anthropic SDK versions.
**Why it happens:** Anthropic's tool-use endpoint has different behavior for temperature=0 vs very small positive values.
**How to avoid:** Use `temperature=0.1` (or omit entirely — default is fine). Thesis generation benefits from slight creativity anyway (temperature=0 makes positioning deterministic but bull/bear case dull).
**Warning signs:** Thesis bull_case and bear_case are identical across tickers.

---

## Code Examples

### DB Read — Assembling Prompt Data
```python
# Source: Pattern from financial_engine.py _get_current_price() + db.py get_connection()
def _fetch_financial_data(ticker: str, conn: sqlite3.Connection) -> dict | None:
    """Returns all data needed for thesis prompt, or None if critical data missing."""
    # LTM — latest row for ticker
    ltm = conn.execute(
        "SELECT * FROM financial_ltm WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    if ltm is None:
        return None

    multiples = conn.execute(
        "SELECT * FROM financial_multiples WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()

    dcf = conn.execute(
        "SELECT * FROM financial_dcf WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()

    signals = conn.execute(
        "SELECT * FROM financial_signals WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
        (ticker,),
    ).fetchone()

    # Macro — latest Selic (11) and IPCA_12m (433)
    macro_rows = conn.execute(
        """
        SELECT series_code, value FROM macro_series
        WHERE series_code IN (11, 433, 29039)
        ORDER BY date DESC
        """,
    ).fetchall()
    macro: dict[int, float] = {}
    for r in macro_rows:
        if r["series_code"] not in macro:
            macro[r["series_code"]] = r["value"]

    # Last 3 news for ticker
    news = conn.execute(
        """
        SELECT title, published_at, url FROM news_articles
        WHERE ticker_tags LIKE ?
        ORDER BY published_at DESC LIMIT 3
        """,
        (f"%{ticker}%",),
    ).fetchall()

    return {
        "ltm": dict(ltm) if ltm else {},
        "multiples": dict(multiples) if multiples else {},
        "dcf": dict(dcf) if dcf else {},
        "signals": dict(signals) if signals else {},
        "macro": macro,
        "news": [dict(n) for n in news],
    }
```

### DCF Deviation Cross-Check
```python
# Source: CONTEXT.md D-03
def _check_dcf_deviation(
    thesis: InvestmentThesis,
    dcf_fair_value: float,
) -> bool:
    """Returns True if thesis.fair_value_brl deviates >10% from computed DCF."""
    if dcf_fair_value <= 0:
        return False
    deviation = abs(thesis.fair_value_brl - dcf_fair_value) / dcf_fair_value
    return deviation > 0.10
```

### Version Number Auto-Increment
```python
# Source: CONTEXT.md D-13 + db.py INSERT OR REPLACE pattern
def _next_version_num(ticker: str, conn: sqlite3.Connection) -> int:
    row = conn.execute(
        "SELECT MAX(version_num) FROM thesis_versions WHERE ticker = ?",
        (ticker,),
    ).fetchone()
    current_max = row[0]  # None if no rows
    return (current_max or 0) + 1
```

### Conviction Score for DCF_DIVERGENCE
```python
# Source: CONTEXT.md D-17
def _score_dcf_divergence(price: float, fair_value: float) -> int:
    """0-40 proportional to divergence magnitude; 0 if divergence <= 20%."""
    if fair_value <= 0 or price <= 0:
        return 0
    divergence = abs(fair_value - price) / price
    if divergence <= 0.20:
        return 0
    # Scale: 20% divergence = 0 pts; 100%+ divergence = 40 pts (capped)
    score = int(min((divergence - 0.20) / 0.80 * 40, 40))
    return score
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `instructor.from_openai()` only | `instructor.from_anthropic()` with ANTHROPIC_TOOLS mode | instructor >=0.6.x | Native Anthropic tool-call support without workarounds |
| `instructor.Mode.ANTHROPIC_JSON` | `instructor.Mode.ANTHROPIC_TOOLS` (default) | instructor >=1.0.0 | Tool mode uses native API; JSON mode is legacy for Anthropic |
| `instructor.patch(client)` | `instructor.from_anthropic(client)` | instructor >=1.0.0 | `patch()` is backward-compat wrapper; `from_anthropic()` is canonical |
| `max_retries` on client constructor | `max_retries` on each `create()` call | instructor >=1.0.0 | Per-call retry control is more flexible |
| Pydantic v1 models | Pydantic v2 `BaseModel` | instructor >=1.0.0 | instructor 1.x requires Pydantic v2 — project already on 2.13.4 |

**Deprecated/outdated:**
- `instructor.patch()`: Works (backward compat) but `from_anthropic()` is the current canonical pattern [CITED: github.com/instructor-ai/instructor /instructor/patch.py]
- `instructor.Mode.ANTHROPIC_PARALLEL_TOOLS`: Deprecated — use `Iterable[Union[...]]` pattern instead [CITED: python.useinstructor.com/integrations/anthropic/]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Rounding floats to 2dp before hashing prevents precision drift | Pattern 3 (Hash) | Hash mismatches → unnecessary API calls (cost, not correctness) |
| A2 | `ticker_tags LIKE '%PETR4%'` is the correct filter for news_articles | Code Examples (read) | Wrong news injected into thesis prompt |
| A3 | temperature=0.1 is safe for ANTHROPIC_TOOLS mode | Pitfall 8 | Could affect output diversity but not correctness |
| A4 | IPE rows have normalized_name=NULL in all cases | Pitfall 7 | IPE_EVENT signal query would need adjustment |

**All core claims (instructor API, versions, db.py patterns) are VERIFIED or CITED.**

---

## Open Questions

1. **news_articles ticker_tags format**
   - What we know: `ticker_tags` stores a JSON list when B3 regex matches (from STATE.md [02-03])
   - What's unclear: Is `LIKE '%TICKER%'` safe, or should we use `json_each()` / Python-side filtering?
   - Recommendation: Use `LIKE '%TICKER%'` for speed (acceptable for top-3 news lookup); add a comment noting the limitation. If false positives become an issue (e.g., PETR3 matching PETR4 queries), switch to `json_each()`.

2. **`thesis_prompt.j2` system vs user message split**
   - What we know: `LLMClient` puts the analyst persona in `system` and data in `user`. `IntelligenceClient.generate_thesis()` accepts both `system` and `prompt` parameters.
   - What's unclear: Whether the Jinja2 template renders the full combined prompt, or whether there are separate system/user templates.
   - Recommendation: Use separate strings — `system` = static analyst persona (short, same for all calls); `prompt` = Jinja2-rendered data snapshot. This matches the existing LLMClient pattern.

3. **`financial_dcf.confidence_flag` handling for thesis generation**
   - What we know: `confidence_flag` can be `'FORA DO INTERVALO CONFIAVEL'`, `'INPUT_INVALIDO'`, `'ERRO_CALCULO'`, `'SEM_LUCRO'`, or `None`.
   - What's unclear: Should thesis generation proceed when confidence_flag is non-null? The CONTEXT.md D-03 only specifies the ±10% cross-check, not a skip rule for existing confidence flags.
   - Recommendation: Proceed with thesis generation even when confidence_flag is set, but inject the flag into the prompt so Claude can reflect it in the `methodology_disclosure` field and confidence rating.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| anthropic | LLM calls | Yes | 0.100.0 | — |
| pydantic | Schema validation | Yes | 2.13.4 | — |
| instructor | Structured output | No | — (latest: 1.15.1) | None — must install |
| jinja2 | Prompt templating | No | — (latest: 3.1.4) | None — must install |
| tenacity | Retry | Yes | 9.1.4 | — |
| loguru | Logging | Yes | 0.7.3 | — |
| Python | Runtime | Yes | 3.10.11 | — |
| ingestion.db | Data source | Yes | Live DB with Phase 3 tables | — |

[VERIFIED: pip show for all "Yes" entries; pip list for "No" entries]

**Missing dependencies with no fallback:**
- `instructor>=1.15.1` — must install before any implementation task
- `jinja2>=3.1.0` — must install before implementing template rendering

**Wave 0 task:** `pip install "instructor>=1.15.1" "jinja2>=3.1.0"` and add both to `pyproject.toml` dependencies.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x (already installed) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]`, `pythonpath = ["."]` |
| Quick run command | `python -m pytest tests/test_intelligence_layer.py -x -q` |
| Full suite command | `python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INT-01 | IntelligenceClient.generate_thesis() returns InvestmentThesis with all required fields | unit (mock anthropic) | `pytest tests/test_intelligence_layer.py::test_generate_thesis_returns_valid_schema -x` | No — Wave 0 |
| INT-01 | InvestmentThesis Pydantic schema validates correct structure (Driver, Risk nested models) | unit (no LLM) | `pytest tests/test_intelligence_layer.py::test_investment_thesis_schema -x` | No — Wave 0 |
| INT-02 | fair_value_brl cross-check logs WARNING and sets dcf_deviation_flag when deviation >10% | unit | `pytest tests/test_intelligence_layer.py::test_dcf_deviation_flag -x` | No — Wave 0 |
| INT-03 | Hash gate skips generation when same hash exists in thesis_versions | unit (in-memory SQLite) | `pytest tests/test_intelligence_layer.py::test_hash_gate_skips_on_match -x` | No — Wave 0 |
| INT-03 | 2/day cap skips generation after 2 thesis rows for same ticker today | unit (in-memory SQLite) | `pytest tests/test_intelligence_layer.py::test_daily_cap_after_two_runs -x` | No — Wave 0 |
| INT-04 | thesis_versions row is written with correct version_num, input_hash, positioning | unit (in-memory SQLite) | `pytest tests/test_intelligence_layer.py::test_thesis_versions_write -x` | No — Wave 0 |
| INT-04 | thesis_latest VIEW returns only the MAX(version_num) row per ticker | unit (in-memory SQLite) | `pytest tests/test_db_schema.py::test_thesis_latest_view -x` | No — Wave 0 |
| INT-05 | DCF_DIVERGENCE signal emitted when price vs DCF divergence >20% | unit (no LLM) | `pytest tests/test_intelligence_layer.py::test_dcf_divergence_signal -x` | No — Wave 0 |
| INT-05 | MOMENTUM_CROSSOVER signal emitted when golden_cross=1 and momentum_score>=60 | unit (no LLM) | `pytest tests/test_intelligence_layer.py::test_momentum_crossover_signal -x` | No — Wave 0 |
| INT-05 | IPE_EVENT signal emitted when IPE event in last 30 days | unit (in-memory SQLite) | `pytest tests/test_intelligence_layer.py::test_ipe_event_signal -x` | No — Wave 0 |
| INT-05 | Signals with conviction_score < 40 are filtered out | unit (no LLM) | `pytest tests/test_intelligence_layer.py::test_signal_conviction_threshold -x` | No — Wave 0 |
| INT-06 | opportunity_signals table receives top-3 signals via INSERT OR REPLACE | unit (in-memory SQLite) | `pytest tests/test_intelligence_layer.py::test_opportunity_signals_write -x` | No — Wave 0 |
| All | job_intelligence() registered in _JOB_REGISTRY and calls run_all() | unit (mock run_all) | `pytest tests/test_scheduler_intelligence.py::test_job_intelligence_registered -x` | No — Wave 0 |
| All | init_db() creates thesis_versions, opportunity_signals tables and thesis_latest view | unit | `pytest tests/test_db_schema.py::test_phase4_schema -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_intelligence_layer.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q` (all 93+ tests green)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_intelligence_layer.py` — covers INT-01 through INT-06 (new file)
- [ ] `tests/test_scheduler_intelligence.py` — covers D-19 scheduler wiring (new file, or append to test_scheduler_ingestion.py)
- [ ] Update `tests/test_db_schema.py` — add `test_thesis_latest_view`, update `test_init_db_is_idempotent` count assertion from `== 8` to `>= 10`
- [ ] Dependencies install: `pip install "instructor>=1.15.1" "jinja2>=3.1.0"`
- [ ] `src/templates/` directory creation

**Test strategy for mocking LLM:** Use `unittest.mock.patch("instructor.from_anthropic")` to return a mock that yields a pre-built `InvestmentThesis` instance. This avoids real API calls in tests. The `IntelligenceClient` is designed with a lazy `_client` property to make patching straightforward.

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | API key via .env / pydantic-settings (already in place) |
| V3 Session Management | No | No HTTP sessions |
| V4 Access Control | No | Single-user local tool |
| V5 Input Validation | Yes | Pydantic schema enforces all field types/constraints; parameterized SQL for all queries |
| V6 Cryptography | No (not applicable) | SHA-256 for hash gating — not for security, for deduplication |

### Known Threat Patterns for Intelligence Layer

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via ticker symbol | Tampering | All SQL uses `(ticker,)` positional params — never f-string interpolation (established T-03 pattern) |
| LLM prompt injection via news headlines | Tampering | News article titles injected as data, not instructions; system prompt provides role framing; Pydantic schema enforces output structure regardless |
| API key exposure in logs | Info Disclosure | `settings.anthropic_api_key` is never logged; loguru format does not capture settings object |
| Cost runaway from API calls | Elevation of Privilege | Hash gate (D-09/D-10) + 2/day cap (D-11) — two independent controls; instructor max_retries=3 caps per-call attempts |
| LLM hallucinated fair_value_brl | Tampering | DCF cross-check (D-03) detects deviation >10% and sets `dcf_deviation_flag`; fair value injected in prompt with explicit Portuguese instruction |
| Partial/empty thesis stored | Integrity | D-05: hard-fail → IngestionError on validation failure; instructor never returns partial model |
| Thesis JSON stored unsanitized | Integrity | `thesis_json = thesis.model_dump_json()` via Pydantic — always valid JSON by construction |

**Critical threat — LLM cost runaway:** The two-tier gate (hash match → skip; daily cap → skip) prevents runaway costs even if the scheduler fires unexpectedly. For a 20-ticker watchlist, maximum daily API calls = 20 × 2 = 40 calls. At claude-sonnet-4-6 pricing (~$3/MTok input, ~$15/MTok output) and ~3000 token prompts + ~500 token outputs, maximum daily cost ≈ 40 × (3000×$3/1M + 500×$15/1M) ≈ 40 × ($0.009 + $0.0075) ≈ $0.66/day. [ASSUMED based on Anthropic public pricing]

---

## Sources

### Primary (HIGH confidence)
- PyPI registry — `pip index versions instructor` — latest version 1.15.1 confirmed
- `pip show anthropic pydantic tenacity loguru` — installed versions in project venv
- `pip list` — confirmed jinja2 and instructor NOT installed
- `db.py` (read directly) — DDL pattern, `_CREATE_SQL`, `init_db()`, `get_connection()`
- `financial_engine.py` (read directly) — public API, INSERT OR REPLACE pattern, parameterized SQL
- `scheduler.py` (read directly) — `_JOB_REGISTRY`, `job_financial_engine()` pattern, D-15 summary log
- `llm_client.py` (read directly) — retry pattern, lazy import, settings access
- `schedules.yaml` (read directly) — cron format confirmed
- `04-CONTEXT.md` (read directly) — all locked decisions

### Secondary (MEDIUM confidence)
- github.com/instructor-ai/instructor /providers/anthropic/client.py — `from_anthropic()` signature with mode parameter and defaults [WebFetch]
- github.com/instructor-ai/instructor /core/client.py — `create()` signature with max_retries, response_model [WebFetch]
- python.useinstructor.com/concepts/retrying/ — InstructorRetryException details [WebFetch]
- python.useinstructor.com/integrations/anthropic/ — mode options, ANTHROPIC_TOOLS vs JSON [WebFetch]
- jinja2.palletsprojects.com/en/3.1.x — Environment, FileSystemLoader, float filter syntax [WebFetch]

### Tertiary (LOW confidence)
- A1: Float rounding before hashing — standard practice but not officially documented [ASSUMED]
- A2: `ticker_tags LIKE '%TICKER%'` pattern — inferred from STATE.md [02-03] description [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard stack (instructor API, Pydantic, Jinja2): HIGH — verified via live pip registry and official source
- DB extension pattern: HIGH — read directly from db.py, exact DDL syntax confirmed
- Scheduler wiring: HIGH — read directly from scheduler.py, exact registry pattern confirmed
- Hash computation: HIGH — stdlib hashlib, confirmed approach from CONTEXT.md D-09
- instructor retry behavior: MEDIUM — sourced from official docs + GitHub source (not a local pip show)
- Jinja2 float formatting: MEDIUM — from official Jinja2 docs, confirmed filters
- Security threat model: MEDIUM — derived from established patterns (T-03 SQL injection) + ASSUMED for cost estimate

**Research date:** 2026-05-12
**Valid until:** 2026-06-12 (instructor releases frequently; re-verify if >30 days pass before implementation)
