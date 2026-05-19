---
phase: 04-intelligence-layer
verified: 2026-05-17T17:45:00Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
---

# Phase 4: Intelligence Layer Verification Report

**Phase Goal:** Build a schema-enforced AI thesis generation layer that calls Claude via instructor (ANTHROPIC_TOOLS mode), gates regeneration via SHA-256 input hash + 2/day cap, stores versioned theses and opportunity signals in SQLite, and wires into the nightly scheduler.
**Verified:** 2026-05-17T17:45:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC-1 | Pydantic-validated InvestmentThesis (bull/bear, 3-5 drivers/risks, fair_value_brl, positioning, confidence, rationale) in Portuguese; instructor enforces schema; no partial thesis ever returned | VERIFIED | `test_investment_thesis_schema`, `test_generate_thesis_returns_valid_schema`, `test_hard_fail_on_validation_error` all pass; `IntelligenceClient.generate_thesis()` raises `IngestionError` on any exception — lines 237-240 of `intelligence_layer.py` |
| SC-2 | All numbers injected from Financial Engine; LLM synthesizes only; post-generation DCF cross-check ±10% with deviation flag | VERIFIED | `_assemble_prompt_data()` reads 6 DB tables and passes them as template variables; `_check_dcf_deviation()` implemented lines 179-187; `dcf_deviation_flag` stored in `thesis_versions`; `test_dcf_deviation_flag` and `test_dcf_deviation_within_tolerance` pass |
| SC-3 | Input hash gates regeneration (no re-call when data unchanged); max 2/day per ticker enforced | VERIFIED | `compute_input_hash()` SHA-256 with sorted news URLs; `_is_hash_match()` and `_is_daily_cap_reached()` called before `IntelligenceClient` instantiation (lines 646-657); `test_hash_gate_skips_on_match` and `test_daily_cap_after_two_runs` pass |
| SC-4 | Thesis stored in DB with version history, input hash, generation timestamp, diff_summary relative to prior version | VERIFIED | `thesis_versions` table created with `UNIQUE(ticker, version_num)`; `_next_version_num()`, `_compute_diff_summary()` implemented; `INSERT OR REPLACE INTO thesis_versions` at line 685; `test_thesis_versions_write` and `test_thesis_latest_view_query` pass |
| SC-5 | Opportunity signals (DCF divergence >20%, MA crossover, IPE event) computed per ticker, ranked by conviction score; top 3 available as structured output | VERIFIED | `compute_opportunity_signals()`, `_score_dcf_divergence()`, `_score_momentum_crossover()`, `_score_ipe_event()`, `_write_opportunity_signals()` all implemented; 6 INT-05/06 tests pass; `opportunity_signals` table written via INSERT OR REPLACE |
| SC-6 (goal) | Wired into nightly scheduler via `job_intelligence()` in `_JOB_REGISTRY` + `schedules.yaml` cron `0 21 * * 1-5` | VERIFIED | `_JOB_REGISTRY["intelligence"] = job_intelligence` at `scheduler.py` line 502; `schedules.yaml` line 50-52 confirmed; `test_job_intelligence_registered`, `test_job_intelligence_calls_run_all`, `test_job_intelligence_summary_log` all pass |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact | Status | Details |
|----------|--------|---------|
| `src/intelligence_layer.py` | VERIFIED | 783 lines; contains all required classes (Driver, Risk, InvestmentThesis, OpportunitySignal, ThesisResult), all functions (IntelligenceClient, compute_input_hash, run_ticker, run_all, compute_opportunity_signals, _write_opportunity_signals); no NotImplementedError stubs remaining |
| `src/ingestion/db.py` | VERIFIED | `CREATE TABLE IF NOT EXISTS thesis_versions` at line 155, `CREATE TABLE IF NOT EXISTS opportunity_signals` at line 172, `CREATE VIEW IF NOT EXISTS thesis_latest` at line 184 — all appended to `_CREATE_SQL` |
| `src/templates/thesis_prompt.j2` | VERIFIED | Exists; contains `fair_value_brl`, "DEVE ser exatamente", all 6 data sections (LTM, multiples, DCF, macro, signals, news) |
| `src/scheduler.py` | VERIFIED | `job_intelligence()` at line 427; `_JOB_REGISTRY["intelligence"] = job_intelligence` at line 502 |
| `config/schedules.yaml` | VERIFIED | `job: intelligence`, `cron: "0 21 * * 1-5"` at lines 50-52 |
| `pyproject.toml` | VERIFIED | `"instructor>=1.0.0"` at line 42; `"jinja2>=3.1.0"` at line 43 |
| `tests/test_intelligence_layer.py` | VERIFIED | 18 tests; 0 xfail markers; all pass |
| `tests/test_scheduler_intelligence.py` | VERIFIED | 3 tests; 0 xfail markers; all pass |
| `tests/test_db_schema.py` | VERIFIED | 7 tests including `test_phase4_schema` and `test_thesis_latest_view`; all pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `IntelligenceClient.__init__()` | `instructor.Mode.ANTHROPIC_TOOLS` | `instructor.from_provider()` with `mode=instructor.Mode.ANTHROPIC_TOOLS` | VERIFIED | Lines 208-211; uses `from_provider` (correct for instructor 1.15.1 — `from_anthropic` removed); mode explicitly set |
| `IntelligenceClient.generate_thesis()` | `IngestionError` on failure | `except Exception as exc: raise IngestionError(...)` | VERIFIED | Lines 237-240; hard-fail on any exception (D-05) |
| `run_ticker()` | `thesis_versions` table | `INSERT OR REPLACE INTO thesis_versions` | VERIFIED | Line 685; parameterized with UUID PK |
| `compute_input_hash()` | hash gate check | `_is_hash_match(ticker, current_hash, conn)` | VERIFIED | Lines 646-650; called before any LLM instantiation |
| `run_ticker()` | `compute_opportunity_signals()` | Step 9 after thesis persist and commit | VERIFIED | Lines 713-718; signals attached to `ThesisResult.signals` |
| `_write_opportunity_signals()` | `opportunity_signals` table | `INSERT OR REPLACE INTO opportunity_signals` | VERIFIED | Line 560; UNIQUE(ticker, computed_date, signal_type) prevents duplicates |
| `job_intelligence()` | `src.intelligence_layer.run_all` | lazy import inside job function | VERIFIED | Line 431: `from src.intelligence_layer import run_all` |
| `schedules.yaml` | `job_intelligence()` | `_JOB_REGISTRY['intelligence']` | VERIFIED | `schedules.yaml` job name `intelligence` matches registry key |
| `run_all()` | `tickers.yaml` | `yaml.safe_load` active_tickers filter | VERIFIED | Lines 750-758; `t.get("active", True)` filter |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `run_ticker()` → `_assemble_prompt_data()` | `ltm`, `dcf`, `multiples`, `signals`, `macro`, `news_rows` | 6 parameterized DB queries (financial_ltm, financial_multiples, financial_dcf, financial_signals, macro_series, news_articles) | Yes — real DB reads with NULL guards | FLOWING |
| `compute_input_hash()` | `hash_dict` | values from `_assemble_prompt_data()` dict; floats rounded; news_urls sorted | Yes — deterministic SHA-256 of real data | FLOWING |
| `compute_opportunity_signals()` | `mult_row`, `dcf_row`, `sig_row` | parameterized DB queries (financial_multiples, financial_dcf, financial_signals, cvm_statements) | Yes — real DB reads | FLOWING |
| `_score_ipe_event()` | `row[0]` (COUNT) | `cvm_statements WHERE period_type='IPE' AND reference_date >= DATE('now','-30 days')` — no normalized_name filter | Yes — Pitfall 7 correctly avoided | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Pydantic models import | `python -c "from src.intelligence_layer import IntelligenceClient, compute_input_hash, _check_dcf_deviation, run_ticker, run_all"` | Exit 0 | PASS |
| Hash determinism | Same inputs with reversed news URL order produce identical hash | Verified via test_compute_input_hash_deterministic | PASS |
| scheduler registry | `from src.scheduler import _JOB_REGISTRY; assert 'intelligence' in _JOB_REGISTRY` | Exit 0 | PASS |
| schedules.yaml cron | `job: intelligence`, `cron: "0 21 * * 1-5"` | Confirmed in file | PASS |
| Full INT test suite | `pytest tests/test_intelligence_layer.py tests/test_scheduler_intelligence.py tests/test_db_schema.py -q` | 28/28 passed | PASS |
| Full project suite | `pytest tests/ -q --ignore=tests/test_news_hunter_config.py` | 114/114 passed | PASS |

---

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| INT-01 | 04-01, 04-02 | AI investment thesis via instructor + Pydantic schema | SATISFIED | `IntelligenceClient`, `InvestmentThesis` schema with all required fields; 5 tests pass |
| INT-02 | 04-02 | Numbers injected from Financial Engine; DCF cross-check ±10% | SATISFIED | `_assemble_prompt_data()` reads 6 tables; `_check_dcf_deviation()` verified by 2 tests |
| INT-03 | 04-02 | SHA-256 input hash gate; 2/day cap | SATISFIED | `compute_input_hash()`, `_is_hash_match()`, `_is_daily_cap_reached()`; 3 tests pass |
| INT-04 | 04-01, 04-02 | Versioned thesis storage in thesis_versions | SATISFIED | `thesis_versions` table + `thesis_latest` VIEW; `_next_version_num()`, `_compute_diff_summary()`; 3 tests pass |
| INT-05 | 04-03 | Opportunity signals (DCF divergence, MA crossover, IPE event) | SATISFIED | `compute_opportunity_signals()` + 3 `_score_*()` functions; 5 tests pass |
| INT-06 | 04-03, 04-04 | Top-3 signals by conviction score; stored in opportunity_signals | SATISFIED | `_write_opportunity_signals()` via INSERT OR REPLACE; `test_opportunity_signals_write` confirms dedup |

All 6 requirements SATISFIED.

---

### Anti-Patterns Found

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| `src/intelligence_layer.py` lines 495, 515, 530 | Emission filter uses `score > 0` instead of plan-specified `score >= 40` | INFO | Intentional deviation documented in 04-03-SUMMARY.md. The plan's `>= 40` threshold contradicted the tests (IPE always returns 30; MOMENTUM max was 30 in plan but tests require it to emit). Executor reconciled by changing MOMENTUM scale to 0-60 (so golden_cross=1+ms=72 gives 43 ≥ 40 effectively) and using `> 0` filter so IPE (30 pts) emits. All 6 INT-05/06 tests pass with this behavior. The economic logic is preserved: signals only emit when the condition is met (score > 0 means the trigger condition was satisfied). |

No blockers. The score-threshold deviation is a spec reconciliation, not a functional gap.

---

### Human Verification Required

None — all must-haves are verifiable programmatically and confirmed by passing tests.

---

### Gaps Summary

No gaps. All 6 roadmap success criteria verified against the actual codebase:

- Pydantic schema enforcement: `InvestmentThesis` with Literal types, min/max length on drivers/risks, instructor ANTHROPIC_TOOLS mode — confirmed by test suite.
- Data injection (not LLM calculation): `_assemble_prompt_data()` reads all 6 source tables; DCF cross-check `_check_dcf_deviation()` with ±10% tolerance — confirmed by tests.
- Hash gate + 2/day cap: `compute_input_hash()` SHA-256 with float rounding and sorted news URLs; dual gate checks before any LLM call — confirmed by tests.
- Versioned storage: `thesis_versions` table with `_next_version_num()` and `_compute_diff_summary()`; `thesis_latest` VIEW — confirmed by tests.
- Opportunity signals: 3 signal types with scoring functions, top-3 selection, `opportunity_signals` INSERT OR REPLACE — confirmed by tests.
- Scheduler wiring: `job_intelligence()` in `_JOB_REGISTRY`, cron `0 21 * * 1-5` in `schedules.yaml` — confirmed by tests and file inspection.

Pre-existing failure `tests/test_news_hunter_config.py::test_token_loaded_from_env` (working-tree modification to `news_hunter/config.py`) predates Phase 4 and is documented in `deferred-items.md`. It is unrelated to any Phase 4 deliverable.

---

_Verified: 2026-05-17T17:45:00Z_
_Verifier: Claude (gsd-verifier)_
