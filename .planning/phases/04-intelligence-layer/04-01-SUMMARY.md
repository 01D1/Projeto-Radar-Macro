---
phase: 04-intelligence-layer
plan: 01
subsystem: database
tags: [instructor, jinja2, pydantic, sqlite, intelligence-layer, schema]

# Dependency graph
requires:
  - phase: 03-financial-engine
    provides: financial_* tables (financial_ltm, financial_multiples, financial_dcf, financial_signals) that intelligence_layer.py reads for prompt data assembly
provides:
  - instructor>=1.0.0 and jinja2>=3.1.0 installed and declared in pyproject.toml
  - thesis_versions + opportunity_signals tables + thesis_latest VIEW in ingestion.db via init_db()
  - InvestmentThesis, Driver, Risk, OpportunitySignal, ThesisResult Pydantic models importable from src.intelligence_layer
  - Jinja2 prompt template stub at src/templates/thesis_prompt.j2 with all required variable slots
  - xfail-marked test stubs for INT-01..INT-06 in test_intelligence_layer.py + test_scheduler_intelligence.py
  - job_intelligence() stub registered in scheduler _JOB_REGISTRY under key "intelligence"
affects:
  - 04-02 (IntelligenceClient + run_ticker implementation — depends on InvestmentThesis schema and thesis_versions table)
  - 04-03 (opportunity_signals computation — depends on OpportunitySignal model and opportunity_signals table)
  - 04-04 (run_all + scheduler wiring — depends on ThesisResult + job_intelligence stub)

# Tech tracking
tech-stack:
  added:
    - instructor==1.15.1 (structured LLM output via instructor.from_anthropic())
    - jinja2==3.1.6 (already installed; added to pyproject.toml)
  patterns:
    - Pydantic v2 BaseModel with Literal types for constrained fields (positioning, confidence, impact, severity)
    - xfail test stubs pattern: mark tests with xfail(reason="... — Plan 04-XX") to red-gate until implementation
    - Jinja2 template separation: prompts live in src/templates/*.j2, not in Python code
    - ThesisResult dataclass wraps thesis + metadata + skip info (skipped/skip_reason/version_num)
    - CREATE VIEW IF NOT EXISTS after both CREATE TABLE blocks for idempotent executescript()

key-files:
  created:
    - Analista de Investimentos/12_PYTHON/src/intelligence_layer.py
    - Analista de Investimentos/12_PYTHON/src/templates/thesis_prompt.j2
    - Analista de Investimentos/12_PYTHON/tests/test_intelligence_layer.py
    - Analista de Investimentos/12_PYTHON/tests/test_scheduler_intelligence.py
  modified:
    - Analista de Investimentos/12_PYTHON/pyproject.toml
    - Analista de Investimentos/12_PYTHON/src/ingestion/db.py
    - Analista de Investimentos/12_PYTHON/src/scheduler.py
    - Analista de Investimentos/12_PYTHON/tests/test_db_schema.py

key-decisions:
  - "instructor 1.15.1 installed from PyPI; pyproject.toml declares instructor>=1.0.0 (minimum bound, not pinned)"
  - "ThesisResult uses dataclass (not Pydantic) to wrap thesis + skip metadata — consistent with FinancialResult pattern in financial_engine.py (D-20)"
  - "job_intelligence() stub added to scheduler.py immediately (Rule 2 deviation) so test_job_intelligence_registered passes as a live test in Wave 0"
  - "CREATE VIEW IF NOT EXISTS thesis_latest placed after both table DDL blocks in _CREATE_SQL to ensure executescript() ordering is safe (T-04-01)"
  - "Jinja2 template uses Portuguese language throughout; fair_value_brl injection point explicitly commented to prevent LLM hallucination (P-01)"

patterns-established:
  - "InvestmentThesis schema: bull_case/bear_case/drivers(3-5)/risks(3-5)/fair_value_brl/methodology_disclosure/positioning/confidence/rationale/summary_one_line"
  - "All Pydantic field types use Literal[...] for constrained string values — Pydantic v2 rejects invalid values at construction time"
  - "Test stubs: xfail(reason='not yet implemented — Plan 04-XX') marks tests that will go red as stubs are replaced by real implementations"
  - "Scheduler job_intelligence() follows the same D-15 structured summary log pattern as all other scheduler jobs"

requirements-completed: [INT-01, INT-04]

# Metrics
duration: 10min
completed: 2026-05-17
---

# Phase 4 Plan 1: Intelligence Layer Foundation — Schema + Models + Stubs

**instructor 1.15.1 + jinja2 installed; thesis_versions/opportunity_signals tables and thesis_latest VIEW added to ingestion.db; InvestmentThesis/Driver/Risk/OpportunitySignal/ThesisResult Pydantic models + 21 test stubs ready for Plans 04-02..04-04**

## Performance

- **Duration:** 10 min
- **Started:** 2026-05-17T16:29:32Z
- **Completed:** 2026-05-17T16:39:37Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- `instructor>=1.15.1` and `jinja2>=3.1.0` installed and declared in pyproject.toml
- Phase 4 DB schema extended: `thesis_versions` (11 cols, UNIQUE ticker+version_num), `opportunity_signals` (7 cols, UNIQUE ticker+date+type), and `thesis_latest` VIEW (MAX(version_num) per ticker) — all idempotent via IF NOT EXISTS
- Pydantic v2 schema enforced: Driver/Risk models with Literal impact/severity; InvestmentThesis with min_length=3/max_length=5 on drivers/risks; ThesisResult dataclass wrapping thesis + skip metadata
- 21 test stubs collected cleanly: 18 in test_intelligence_layer.py (INT-01..INT-06) + 3 in test_scheduler_intelligence.py (1 live + 2 xfail); all 7 test_db_schema.py tests pass

## Task Commits

1. **Task 1: Install dependencies, pyproject.toml, db.py DDL, thesis_prompt.j2** - `7e1eb60` (feat)
2. **Task 2: Pydantic models, intelligence_layer.py stub, test stubs** - `e54b707` (feat)

## Files Created/Modified

- `Analista de Investimentos/12_PYTHON/pyproject.toml` — Added instructor>=1.0.0 and jinja2>=3.1.0 after anthropic>=0.39.0
- `Analista de Investimentos/12_PYTHON/src/ingestion/db.py` — Appended thesis_versions + opportunity_signals DDL + thesis_latest VIEW to _CREATE_SQL
- `Analista de Investimentos/12_PYTHON/src/templates/thesis_prompt.j2` — Jinja2 prompt template with all required variable slots (ticker, sector, financials, multiples, DCF, macro, signals, news)
- `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py` — Driver, Risk, InvestmentThesis, OpportunitySignal Pydantic models + ThesisResult dataclass + run_ticker/run_all stubs
- `Analista de Investimentos/12_PYTHON/src/scheduler.py` — Added job_intelligence() stub + registered under "intelligence" key in _JOB_REGISTRY
- `Analista de Investimentos/12_PYTHON/tests/test_db_schema.py` — Updated count>=10, added thesis_versions/opportunity_signals to pk test, added test_phase4_schema + test_thesis_latest_view
- `Analista de Investimentos/12_PYTHON/tests/test_intelligence_layer.py` — 18 test stubs for INT-01..INT-06 (3 live schema tests + 15 xfail)
- `Analista de Investimentos/12_PYTHON/tests/test_scheduler_intelligence.py` — 3 tests for job_intelligence (1 live + 2 xfail)

## Decisions Made

- instructor 1.15.1 installed from PyPI; pyproject.toml declares instructor>=1.0.0 (minimum bound, not pinned) — consistent with project convention
- ThesisResult uses `@dataclass` (not Pydantic) to wrap thesis + skip metadata — matches FinancialResult pattern in financial_engine.py (D-20)
- `job_intelligence()` stub added to scheduler.py immediately (deviation Rule 2) so `test_job_intelligence_registered` passes as a live test in Wave 0
- Jinja2 template uses Portuguese throughout; fair_value_brl has explicit comment preventing LLM hallucination (P-01 mitigation)
- `CREATE VIEW IF NOT EXISTS` placed after both table blocks in _CREATE_SQL to guarantee executescript() ordering (T-04-01)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added job_intelligence() stub to scheduler + registered in _JOB_REGISTRY**
- **Found during:** Task 2 (test stubs creation)
- **Issue:** `test_job_intelligence_registered` in test_scheduler_intelligence.py is NOT marked xfail — it must pass in Wave 0. The plan's Task 2 only listed scheduler job registration as a future plan (04-04), but the test requires "intelligence" to be in `_JOB_REGISTRY` immediately.
- **Fix:** Added `job_intelligence()` stub function to scheduler.py with D-15 structured summary log pattern, and registered it under key "intelligence" in `_JOB_REGISTRY`. The stub calls `run_all()` which raises `NotImplementedError` until Plan 04-04 — but the job is registered and importable.
- **Files modified:** `src/scheduler.py`
- **Verification:** `test_job_intelligence_registered` passes; `test_job_intelligence_calls_run_all` and `test_job_intelligence_summary_log` remain xfail as planned
- **Committed in:** `e54b707` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 — missing critical functionality for test correctness)
**Impact on plan:** Minimal scope addition. The job_intelligence() stub is a placeholder that the plan already intended to implement in Plan 04-04. Adding it in Wave 0 only adds the function signature and registry entry — zero behavioral change until 04-04 removes the NotImplementedError.

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `run_ticker()` raises NotImplementedError | src/intelligence_layer.py | ~110 | Implemented in Plan 04-02 |
| `run_all()` raises NotImplementedError | src/intelligence_layer.py | ~118 | Implemented in Plan 04-04 |
| `job_intelligence()` calls run_all() which raises | src/scheduler.py | ~427 | Active only after 04-04 |

These stubs are intentional Wave 0 foundations. Plans 04-02 through 04-04 will replace them with real implementations.

## Issues Encountered

**Pre-existing working-tree issue (out of scope):** `news_hunter/config.py` has been modified in the working tree with a hardcoded Telegram token, causing `test_token_loaded_from_env` to fail. This is unrelated to Plan 04-01 changes — the committed version of news_hunter/config.py is correct. Documented in `deferred-items.md`.

## User Setup Required

None — no external service configuration required for this plan. Plan 04-02 will require ANTHROPIC_API_KEY to be present in .env.

## Next Phase Readiness

- Plan 04-02 can start immediately: InvestmentThesis schema importable, thesis_versions table exists, test stubs ready to go red when IntelligenceClient is implemented
- Plan 04-03 can proceed after 04-02: OpportunitySignal model importable, opportunity_signals table exists
- Plan 04-04 can proceed after 04-02 and 04-03: job_intelligence stub already registered, only needs run_all() implementation

---
*Phase: 04-intelligence-layer*
*Completed: 2026-05-17*
