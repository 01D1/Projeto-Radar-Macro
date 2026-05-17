---
phase: 4
slug: intelligence-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-12
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (installed) |
| **Config file** | `Analista de Investimentos/12_PYTHON/pyproject.toml` — `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/test_intelligence_layer.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_intelligence_layer.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green (all 93+ prior tests + new INT tests)
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 0 | INT-01 | — | deps installed, pyproject.toml updated | integration | `pip show instructor jinja2` | ✅ (manual) | ⬜ pending |
| 04-01-02 | 01 | 0 | INT-01 | — | DB schema has thesis_versions + opportunity_signals + thesis_latest view | unit | `pytest tests/test_db_schema.py::test_phase4_schema -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 0 | INT-01 | — | InvestmentThesis Pydantic schema validates correct structure | unit | `pytest tests/test_intelligence_layer.py::test_investment_thesis_schema -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | INT-01 | T-04-01 | IntelligenceClient.generate_thesis() returns InvestmentThesis; never returns partial | unit (mock) | `pytest tests/test_intelligence_layer.py::test_generate_thesis_returns_valid_schema -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 1 | INT-01 | T-04-01 | IngestionError raised on instructor validation exhaustion; no partial thesis stored | unit (mock) | `pytest tests/test_intelligence_layer.py::test_hard_fail_on_validation_error -x` | ❌ W0 | ⬜ pending |
| 04-02-01 | 02 | 1 | INT-02 | T-04-02 | dcf_deviation_flag=True logged when thesis.fair_value_brl deviates >10% from DCF | unit | `pytest tests/test_intelligence_layer.py::test_dcf_deviation_flag -x` | ❌ W0 | ⬜ pending |
| 04-02-02 | 02 | 1 | INT-03 | — | Hash gate skips generation when same input_hash found in thesis_versions | unit (in-memory SQLite) | `pytest tests/test_intelligence_layer.py::test_hash_gate_skips_on_match -x` | ❌ W0 | ⬜ pending |
| 04-02-03 | 02 | 1 | INT-03 | — | 2/day cap skips generation after 2 thesis rows for same ticker today | unit (in-memory SQLite) | `pytest tests/test_intelligence_layer.py::test_daily_cap_after_two_runs -x` | ❌ W0 | ⬜ pending |
| 04-03-01 | 02 | 1 | INT-04 | — | thesis_versions row written with correct version_num, input_hash, positioning, thesis_json | unit (in-memory SQLite) | `pytest tests/test_intelligence_layer.py::test_thesis_versions_write -x` | ❌ W0 | ⬜ pending |
| 04-03-02 | 02 | 1 | INT-04 | — | thesis_latest VIEW returns only MAX(version_num) row per ticker | unit (in-memory SQLite) | `pytest tests/test_db_schema.py::test_thesis_latest_view -x` | ❌ W0 | ⬜ pending |
| 04-04-01 | 03 | 2 | INT-05 | — | DCF_DIVERGENCE signal emitted when price vs DCF divergence >20% | unit | `pytest tests/test_intelligence_layer.py::test_dcf_divergence_signal -x` | ❌ W0 | ⬜ pending |
| 04-04-02 | 03 | 2 | INT-05 | — | MOMENTUM_CROSSOVER signal emitted when golden_cross=1 and momentum_score>=60 | unit | `pytest tests/test_intelligence_layer.py::test_momentum_crossover_signal -x` | ❌ W0 | ⬜ pending |
| 04-04-03 | 03 | 2 | INT-05 | — | IPE_EVENT signal emitted when IPE event in last 30 days (no normalized_name filter) | unit (in-memory SQLite) | `pytest tests/test_intelligence_layer.py::test_ipe_event_signal -x` | ❌ W0 | ⬜ pending |
| 04-04-04 | 03 | 2 | INT-05 | — | Signals with conviction_score < 40 filtered out | unit | `pytest tests/test_intelligence_layer.py::test_signal_conviction_threshold -x` | ❌ W0 | ⬜ pending |
| 04-05-01 | 03 | 2 | INT-06 | — | opportunity_signals table receives top-3 signals via INSERT OR REPLACE | unit (in-memory SQLite) | `pytest tests/test_intelligence_layer.py::test_opportunity_signals_write -x` | ❌ W0 | ⬜ pending |
| 04-06-01 | 04 | 3 | INT-01..06 | — | job_intelligence() in _JOB_REGISTRY; cron 0 21 * * 1-5 in schedules.yaml | unit (mock) | `pytest tests/test_scheduler_intelligence.py::test_job_intelligence_registered -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `Analista de Investimentos/12_PYTHON/tests/test_intelligence_layer.py` — stub all INT-01..06 tests (new file)
- [ ] `Analista de Investimentos/12_PYTHON/tests/test_scheduler_intelligence.py` — stub job_intelligence registration test (new file or append to test_scheduler_ingestion.py)
- [ ] Update `Analista de Investimentos/12_PYTHON/tests/test_db_schema.py` — add `test_phase4_schema` and `test_thesis_latest_view`; update `test_init_db_is_idempotent` count assertion from `== 8` to `>= 10`
- [ ] Install dependencies: `pip install "instructor>=1.15.1" "jinja2>=3.1.0"`
- [ ] Add to `pyproject.toml` dependencies: `"instructor>=1.0.0"`, `"jinja2>=3.1.0"`
- [ ] Create `Analista de Investimentos/12_PYTHON/src/templates/` directory

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Thesis generated in Portuguese with valid investment language | INT-01 | LLM output quality cannot be automated | Run `python -c "from src.intelligence_layer import run_ticker; print(run_ticker('PETR4'))"` and inspect bull_case/bear_case language |
| fair_value_brl in thesis matches DCF output within ±10% | INT-02 | End-to-end requires live DB with Phase 3 data | After live run, query `SELECT fair_value_brl FROM thesis_latest WHERE ticker='PETR4'` and compare to `financial_dcf` |
| Opportunity signals describe real market conditions meaningfully | INT-05 | Signal descriptions require domain judgment | Review top-3 signals for a ticker with known IPE event; verify description is coherent |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
