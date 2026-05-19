---
phase: 5
slug: delivery-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-18
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.0.0+ |
| **Config file** | `Analista de Investimentos/12_PYTHON/pyproject.toml` — `[tool.pytest.ini_options]` (testpaths=["tests"], pythonpath=["."]) |
| **Quick run command** | `cd "Analista de Investimentos/12_PYTHON" && pytest tests/test_delivery_telegram.py tests/test_delivery_pdf.py tests/test_dashboard_data.py tests/test_scheduler_delivery.py -x -q` |
| **Full suite command** | `cd "Analista de Investimentos/12_PYTHON" && pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds (new test files only); ~60–90 seconds (full suite with 115+ existing tests) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_delivery_telegram.py tests/test_delivery_pdf.py tests/test_dashboard_data.py tests/test_scheduler_delivery.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q` (full suite)
- **Before `/gsd-verify-work`:** Full suite must be green (all 115+ prior + new delivery tests)
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 0 | DEL-01 | T-DCF-02 | Parameterized SQL `?` placeholder — no f-string ticker | unit | `pytest tests/test_dashboard_data.py::test_get_watchlist_summary -x` | ❌ Wave 0 | ⬜ pending |
| 05-01-02 | 01 | 0 | DEL-01 | — | N/A | unit | `pytest tests/test_dashboard_data.py::test_get_asset_detail -x` | ❌ Wave 0 | ⬜ pending |
| 05-01-03 | 01 | 0 | DEL-01 | — | N/A | unit | `pytest tests/test_dashboard_data.py::test_get_macro_panel -x` | ❌ Wave 0 | ⬜ pending |
| 05-01-04 | 01 | 0 | DEL-01 | — | N/A | unit | `pytest tests/test_dashboard_data.py::test_get_opportunities -x` | ❌ Wave 0 | ⬜ pending |
| 05-01-05 | 01 | 0 | DEL-02 | — | N/A | unit | `pytest tests/test_dashboard_data.py::test_cache_decorators_present -x` | ❌ Wave 0 | ⬜ pending |
| 05-02-01 | 02 | 1 | DEL-03 | — | Alert failure does not propagate — thesis stored regardless | unit | `pytest tests/test_delivery_telegram.py::test_send_thesis_alert_format -x` | ❌ Wave 0 | ⬜ pending |
| 05-02-02 | 02 | 1 | DEL-03 | — | Alert only fires on positioning change | unit | `pytest tests/test_delivery_telegram.py::test_alert_only_on_change -x` | ❌ Wave 0 | ⬜ pending |
| 05-02-03 | 02 | 1 | DEL-03 | — | Exception swallowed — no raise | unit | `pytest tests/test_delivery_telegram.py::test_alert_failure_does_not_raise -x` | ❌ Wave 0 | ⬜ pending |
| 05-02-04 | 02 | 1 | DEL-04 | — | Telegram token from env — never hardcoded | unit | `pytest tests/test_delivery_telegram.py::test_send_daily_brief_format -x` | ❌ Wave 0 | ⬜ pending |
| 05-03-01 | 03 | 1 | DEL-04 | — | N/A | unit | `pytest tests/test_scheduler_delivery.py::test_morning_brief_registered -x` | ❌ Wave 0 | ⬜ pending |
| 05-03-02 | 03 | 1 | DEL-04 | — | N/A | unit | `pytest tests/test_scheduler_delivery.py::test_morning_brief_cron_in_yaml -x` | ❌ Wave 0 | ⬜ pending |
| 05-04-01 | 04 | 2 | DEL-05 | — | PDF in-memory only — no file write, no path traversal | unit | `pytest tests/test_delivery_pdf.py::test_generate_returns_pdf_bytes -x` | ❌ Wave 0 | ⬜ pending |
| 05-04-02 | 04 | 2 | DEL-05 | — | CVM IN 598 disclaimer always present | unit | `pytest tests/test_delivery_pdf.py::test_pdf_contains_required_strings -x` | ❌ Wave 0 | ⬜ pending |
| 05-04-03 | 04 | 2 | DEL-05 | — | N/A | smoke | `pytest tests/test_delivery_pdf.py::test_generate_under_30s -x` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_delivery_telegram.py` — stubs for DEL-03, DEL-04 Telegram methods (`send_thesis_alert`, `send_daily_brief`)
- [ ] `tests/test_delivery_pdf.py` — stubs for DEL-05 PDF generation (`ReportGenerator.generate()`)
- [ ] `tests/test_dashboard_data.py` — stubs for DEL-01, DEL-02 data layer (all 4 query functions + cache decorator check)
- [ ] `tests/test_scheduler_delivery.py` — stubs for DEL-04 scheduler wiring (`job_morning_brief` registration + cron entry)
- [ ] `src/dashboard/__init__.py` — empty package init file (Pitfall 7)
- [ ] `src/dashboard/data.py` — query module stub (4 functions decorated with `@st.cache_data(ttl=300)`)
- [ ] `src/delivery/pdf_report.py` — `ReportGenerator` class stub
- [ ] `pip install "fpdf2>=2.7.0"` + add `"fpdf2>=2.7.0"` to `pyproject.toml [project.dependencies]`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Streamlit pages render correctly in browser | DEL-01, DEL-02 | Streamlit page layout and CSS injection cannot be unit-tested; requires live browser | Run `streamlit run 'Analista de Investimentos/scanner_quant_profit_b3/app.py'`; navigate to each of the 4 intelligence pages; verify dark theme, data loads, empty state banner appears if no thesis data |
| Nav bar fits 9 pages on 1280px screen | A3 (Research open question) | Screen width behavior is visual; no automated test | Resize browser window to 1280px; verify all 9 nav buttons visible without horizontal scroll |
| PDF visual quality (layout, fonts, section breaks) | DEL-05 | PDF rendering is visual; only bytes-level tests are automated | Click "Baixar Relatório PDF" in Asset Detail page; open the downloaded PDF; verify all 8 sections present, CVM disclaimer on last section, Helvetica font, page numbers in footer |
| Telegram messages received on phone | DEL-03, DEL-04 | Requires live Telegram API + configured bot token | Trigger a thesis positioning change in test run; verify alert received in Telegram chat within 30 seconds |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
