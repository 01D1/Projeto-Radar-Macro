---
phase: 04-intelligence-layer
plan: 02
subsystem: intelligence-layer
tags: [instructor, anthropic, jinja2, pydantic, sqlite, hash-gate, daily-cap, tdd]

# Dependency graph
requires:
  - phase: 04-intelligence-layer
    plan: 01
    provides: InvestmentThesis schema, thesis_versions table, test stubs, thesis_prompt.j2 template

provides:
  - IntelligenceClient (instructor.from_provider + Mode.ANTHROPIC_TOOLS) importable from src.intelligence_layer
  - compute_input_hash(): SHA-256 gate with float rounding and sorted news_urls
  - _check_dcf_deviation(): ±10% tolerance cross-check against DCF fair value
  - _render_thesis_prompt() / _get_jinja_env() with StrictUndefined Jinja2 environment
  - _assemble_prompt_data(): 6-table DB read with fully parameterized queries
  - _next_version_num(), _compute_diff_summary(): thesis versioning helpers
  - _is_hash_match(), _is_daily_cap_reached(): cost-control gate helpers
  - run_ticker(): full 8-step flow — assemble→hash→hash_gate→daily_cap→render→generate→dcf_check→persist
  - thesis_versions table written correctly with INSERT OR REPLACE

affects:
  - 04-03 (compute_opportunity_signals can now call run_ticker and access thesis_versions)
  - 04-04 (run_all() implementation depends on working run_ticker)

# Tech tracking
tech-stack:
  added:
    - anthropic==0.102.0 (installed; was missing from environment despite pyproject.toml declaration)
  patterns:
    - instructor.from_provider("anthropic/claude-sonnet-4-6", mode=ANTHROPIC_TOOLS) — 1.15.1 API
    - run_ticker() 8-step flow: assemble→hash→gate1→gate2→render→generate→dcf_cross_check→persist
    - NoCloseConn test wrapper pattern: prevents closed-DB errors when run_ticker() calls conn.close()
    - _assemble_prompt_data monkeypatch: bypasses DB reads in gate tests

key-files:
  modified:
    - Analista de Investimentos/12_PYTHON/src/intelligence_layer.py
    - Analista de Investimentos/12_PYTHON/tests/test_intelligence_layer.py

key-decisions:
  - "instructor.from_provider() replaces from_anthropic() — removed in instructor>=1.0 refactor; from_provider('anthropic/claude-sonnet-4-6', mode=ANTHROPIC_TOOLS) is the correct 1.15.1 API"
  - "test_hash_gate_skips_on_match, test_daily_cap_after_two_runs require _assemble_prompt_data monkeypatch — gate tests must provide financial data so flow reaches hash/daily_cap check"
  - "NoCloseConn wrapper in test_thesis_versions_write — run_ticker() calls conn.close() in finally; test needs to query same conn after completion"
  - "anthropic package installed at runtime (0.102.0); pyproject.toml already declared >=0.39.0 but it was missing from the user-site environment"

requirements-completed: [INT-01, INT-02, INT-03, INT-04]

# Metrics
duration: 25min
completed: 2026-05-17
---

# Phase 4 Plan 2: Intelligence Layer Core Implementation

**IntelligenceClient (instructor.from_provider + ANTHROPIC_TOOLS), SHA-256 hash gate, 2/day cap, 6-table prompt assembly, DCF cross-check, and run_ticker() with thesis_versions persistence — INT-01/02/03/04 satisfied**

## Performance

- **Duration:** 25 min
- **Started:** 2026-05-17T16:29:00Z
- **Completed:** 2026-05-17T16:54:23Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- `IntelligenceClient` implemented using `instructor.from_provider("anthropic/claude-sonnet-4-6", mode=ANTHROPIC_TOOLS)` — schema-enforced thesis generation with max_retries=3 and temperature=0.1
- `compute_input_hash()` returns a stable SHA-256 hex digest (64 chars) with float rounding + sorted news_urls for order-independence (D-09)
- `_check_dcf_deviation()` flags >10% deviation between thesis.fair_value_brl and DCF fair value (D-03)
- `_assemble_prompt_data()` reads 6 tables (financial_ltm, financial_multiples, financial_dcf, financial_signals, macro_series, news_articles) with fully parameterized queries — no f-string SQL injection (T-04-05)
- `run_ticker()` 8-step flow: prompt assembly → hash computation → hash gate (D-10) → daily cap (D-11) → Jinja2 render → IntelligenceClient.generate_thesis() → DCF cross-check (D-03) → INSERT OR REPLACE into thesis_versions (D-12)
- 12 tests pass in test_intelligence_layer.py; 6 xfail reserved for Plan 04-03

## Task Commits

1. **RED — test(04-02): add failing tests** — `0f1379d`
2. **GREEN Task 1 — feat(04-02): IntelligenceClient, compute_input_hash, helpers** — `7433ee4`
3. **GREEN Task 2 — feat(04-02): run_ticker() implementation** — `bf1a14f`

## Files Created/Modified

- `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py` — Full implementation: IntelligenceClient, compute_input_hash, _check_dcf_deviation, _render_thesis_prompt, _assemble_prompt_data, _next_version_num, _compute_diff_summary, _is_hash_match, _is_daily_cap_reached, run_ticker()
- `Analista de Investimentos/12_PYTHON/tests/test_intelligence_layer.py` — Removed xfail from 9 tests; updated monkeypatching for instructor 1.15.1 API; added _assemble_prompt_data mocks and NoCloseConn wrapper

## Decisions Made

- instructor.from_provider() replaces from_anthropic() — removed in instructor>=1.0 refactor; from_provider('anthropic/claude-sonnet-4-6', mode=ANTHROPIC_TOOLS) is the correct 1.15.1 API
- test_hash_gate_skips_on_match and test_daily_cap_after_two_runs require _assemble_prompt_data monkeypatch — the run_ticker flow assembles data BEFORE checking hash/daily_cap gates, so tests need financial data present
- NoCloseConn wrapper in test_thesis_versions_write — run_ticker() calls conn.close() in finally; test needs to query same conn after completion
- anthropic package installed at runtime (0.102.0); pyproject.toml already declared >=0.39.0 but it was missing from the user-site environment

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] instructor.from_anthropic() removed in 1.15.1 — use from_provider() instead**
- **Found during:** Task 1 GREEN phase — test_generate_thesis_returns_valid_schema failed with `AttributeError: module 'instructor' has no attribute 'from_anthropic'`
- **Issue:** instructor 1.15.1 API removed `from_anthropic()` at top-level; correct API is `instructor.from_provider("anthropic/claude-sonnet-4-6", mode=instructor.Mode.ANTHROPIC_TOOLS)`
- **Fix:** Updated `IntelligenceClient.__init__()` to use `instructor.from_provider()`; updated test monkeypatches from `instructor.from_anthropic` to `instructor.from_provider`
- **Files modified:** `src/intelligence_layer.py`, `tests/test_intelligence_layer.py`
- **Commit:** `7433ee4`

**2. [Rule 1 - Bug] Gate tests need _assemble_prompt_data mock — financial data required before hash gate**
- **Found during:** Task 2 — test_hash_gate_skips_on_match failed with skip_reason='no_financial_data' instead of 'hash_match'
- **Issue:** run_ticker() calls _assemble_prompt_data() BEFORE checking hash gate. Tests didn't insert financial_ltm data, so _assemble_prompt_data returned None early
- **Fix:** Added `monkeypatch.setattr("src.intelligence_layer._assemble_prompt_data", ...)` to test_hash_gate_skips_on_match and test_daily_cap_after_two_runs
- **Files modified:** `tests/test_intelligence_layer.py`
- **Commit:** `bf1a14f`

**3. [Rule 1 - Bug] run_ticker() closes conn in finally — test_thesis_versions_write needs NoCloseConn wrapper**
- **Found during:** Task 2 — test_thesis_versions_write failed with `sqlite3.ProgrammingError: Cannot operate on a closed database`
- **Issue:** run_ticker() calls `conn.close()` in its `finally` block. The test monkeypatches `get_connection` to return an in-memory conn, but that same conn is closed before the test can query it
- **Fix:** Added `_NoCloseConn` wrapper class that delegates all methods to the real conn but makes `close()` a no-op
- **Files modified:** `tests/test_intelligence_layer.py`
- **Commit:** `bf1a14f`

---

**Total deviations:** 3 auto-fixed (Rule 1 — bugs preventing test correctness)
**Impact on plan:** All deviations were test-layer fixes; the implementation logic itself was correct. No behavioral changes to production code except the instructor API call pattern.

## Known Stubs

| Stub | File | Line | Reason |
|------|------|------|--------|
| `run_all()` raises NotImplementedError | src/intelligence_layer.py | ~580 | Implemented in Plan 04-04 |
| `job_intelligence()` calls run_all() which raises | src/scheduler.py | ~427 | Active only after 04-04 |
| `compute_opportunity_signals()` | src/intelligence_layer.py | — | Implemented in Plan 04-03 |

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes beyond what the plan's threat model covers. `anthropic_api_key` is loaded inside `IntelligenceClient.__init__()` and never logged (T-04-07 mitigated).

## Self-Check

Files exist:
- [x] `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py` — FOUND (contains IntelligenceClient, compute_input_hash, run_ticker)
- [x] `Analista de Investimentos/12_PYTHON/tests/test_intelligence_layer.py` — FOUND (12 pass, 6 xfail)

Commits exist:
- [x] `0f1379d` — test(04-02) RED commit — FOUND
- [x] `7433ee4` — feat(04-02) Task 1 GREEN — FOUND
- [x] `bf1a14f` — feat(04-02) Task 2 GREEN — FOUND

## Self-Check: PASSED
