---
phase: 1
slug: foundation-and-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-06
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` — `[tool.pytest.ini_options] testpaths = ["tests"]` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v --cov=src` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v --cov=src`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| consolidation | 01 | 1 | FOUND-01 | — | Only `src.` imports work; duplicate directories not importable | smoke | `pytest tests/test_consolidation.py -x` | ❌ W0 | ⬜ pending |
| credentials-settings | 02 | 1 | FOUND-02 | T-env-gitignore | Settings raises SystemExit on missing prod key | unit | `pytest tests/test_settings.py::test_startup_guard -x` | ❌ W0 | ⬜ pending |
| credentials-news_hunter | 02 | 1 | FOUND-02 | T-hardcoded-token | No literal token in news_hunter/config.py | unit | `pytest tests/test_news_hunter_config.py::test_no_hardcoded_token -x` | ❌ W0 | ⬜ pending |
| retry-backoff | 03 | 2 | FOUND-03 | — | Exponential backoff with jitter applied on each retry | unit | `pytest tests/test_retry.py::test_backoff_jitter -x` | ❌ W0 | ⬜ pending |
| retry-error | 03 | 2 | FOUND-03 | — | Final retry exhaustion raises IngestionError | unit | `pytest tests/test_retry.py::test_ingestion_error -x` | ❌ W0 | ⬜ pending |
| logging-retention | 03 | 2 | FOUND-04 | — | Log files rotate daily with 7-day retention | unit | `pytest tests/test_logger.py::test_retention -x` | ❌ W0 | ⬜ pending |
| logging-run-id | 03 | 2 | FOUND-04 | — | bind_run_id() injects run_id into all log records in scope | unit | `pytest tests/test_logger.py::test_run_id_binding -x` | ❌ W0 | ⬜ pending |
| logging-no-stdlib | 03 | 2 | FOUND-04 | — | No stdlib `import logging` in src/ (except legacy) | static | `grep -r "^import logging" "Analista de Investimentos/12_PYTHON/src/" --include="*.py"` exits 1 | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Working `.venv` at OBSIDIAN root — delete macOS artifact, create with Windows Python 3.10: `python -m venv .venv && .venv\Scripts\pip install -e "Analista de Investimentos/12_PYTHON/[dev]"`
- [ ] `pip install pytest pytest-cov` into new venv
- [ ] `tests/__init__.py` — empty marker file
- [ ] `tests/test_consolidation.py` — stubs for FOUND-01 import path assertions
- [ ] `tests/test_settings.py` — stubs for FOUND-02 startup guard (test_startup_guard)
- [ ] `tests/test_news_hunter_config.py` — stubs for FOUND-02 no-hardcoded-token
- [ ] `tests/test_retry.py` — stubs for FOUND-03 backoff jitter + IngestionError
- [ ] `tests/test_logger.py` — stubs for FOUND-04 retention + run_id binding

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Windows Task Scheduler task points to vault path | FOUND-01 (D-02) | Windows OS state, not testable via pytest | Run `schtasks /Query /FO LIST` and verify task path matches `C:\Users\55819\OneDrive - EPEJUD\DIEGO\OBSIDIAN\Analista de Investimentos\12_PYTHON\pipeline banco completo\scheduler.py` |
| `env` file not staged by git | FOUND-02 | Git index state | Run `git check-ignore -v env` and verify a match is returned |
| `pipeline banco completo/` DEPRECATED.md is present | FOUND-01 (D-01) | File existence | `ls "Analista de Investimentos/12_PYTHON/pipeline banco completo/DEPRECATED.md"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
