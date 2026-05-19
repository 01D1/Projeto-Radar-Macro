---
phase: 05-delivery-layer
fixed_at: 2026-05-18T19:45:00Z
review_path: .planning/phases/05-delivery-layer/05-REVIEW.md
iteration: 1
findings_in_scope: 12
fixed: 12
skipped: 0
status: all_fixed
---

# Phase 05: Code Review Fix Report

**Fixed at:** 2026-05-18T19:45:00Z
**Source review:** .planning/phases/05-delivery-layer/05-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 12 (5 Critical + 7 Warning)
- Fixed: 12
- Skipped: 0

## Fixed Issues

### CR-01: Telegram token exposed in exception log

**Files modified:** `Analista de Investimentos/12_PYTHON/src/delivery/telegram_bot.py`
**Commit:** 7a6c303
**Applied fix:** Replaced `str(exc)` in warning log with `type(exc).__name__` so that the full exception message (which can embed the token-containing URL for `requests.ConnectionError`) is never written to logs.

---

### CR-02: XSS via unescaped LLM content in inteligencia_ativo.py

**Files modified:** `Analista de Investimentos/scanner_quant_profit_b3/pages/inteligencia_ativo.py`
**Commit:** ddda5fb
**Applied fix:** Changed `st.markdown(thesis.get("bull_case"))` and `st.markdown(thesis.get("bear_case"))` to `st.write(...)`. `st.write()` renders as plain text without HTML interpretation, eliminating the injection surface.

---

### CR-03: Double main() execution on all four Streamlit pages

**Files modified:** `inteligencia_ativo.py`, `inteligencia_watchlist.py`, `inteligencia_macro.py`, `inteligencia_oportunidades.py`
**Commit:** ddda5fb
**Applied fix:** Removed the bare unconditional `main()` call at the end of each file, keeping only the `if __name__ == "__main__": main()` guard. Streamlit's `st.navigation` runner already executes module-level code; the bare call was doubling every DB query and chart render.

---

### CR-04: Conviction-score >= 40 filter missing in compute_opportunity_signals()

**Files modified:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py`
**Commit:** 487f7db (filter added), 80a0438 (IPE score raised + tests updated)
**Applied fix:** Added `signals = [s for s in signals if s.conviction_score >= 40]` after the sort. Also raised `_score_ipe_event()` return value from 30 to 40 so IPE events can pass the threshold (as REVIEW.md suggested). Updated two test mocks that asserted `conviction_score == 30` to expect `40`. Fixed three test `get_connection` lambdas that accepted zero args to accept `*a, **k` (follow-on from WR-02).
**Note:** Requires human verification — the >= 40 threshold is now enforced but the DCF_DIVERGENCE scoring formula still only produces exactly 40 at 100%+ divergence (see IN-02). The filter is logically correct per the docstring spec.

---

### CR-05: dividend_yield displayed as 0.0% instead of 4.8% in PDF

**Files modified:** `Analista de Investimentos/12_PYTHON/src/delivery/pdf_report.py`
**Commit:** e1c8028
**Applied fix:** Added `_fmt_yield()` helper that multiplies the decimal fraction by 100 before formatting (`f"{float(v) * 100:.2f}%"`). Replaced the `_fmt_pct()` call for "Dividend Yield" with `_fmt_yield()`. The fixture value `0.048` now renders as `4.80%` instead of `+0.0%`.

---

### WR-01: current_price=0.0 silently suppressed

**Files modified:** `Analista de Investimentos/12_PYTHON/src/delivery/telegram_bot.py`
**Commit:** 7a6c303
**Applied fix:** Changed `if current_price:` to `if current_price is not None:` in `send_valuation_update()`. A price of `0.0` is now rendered rather than silently omitted.

---

### WR-02: get_connection() called without DB_PATH in run_ticker()

**Files modified:** `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py`
**Commit:** 487f7db
**Applied fix:** Added `DB_PATH` to the `from src.ingestion.db import` statement and changed `conn = get_connection()` to `conn = get_connection(DB_PATH)` in `run_ticker()`, matching the pattern used by all other callers in the codebase.

---

### WR-03: Non-429 4xx errors exhaust all retry iterations unnecessarily

**Files modified:** `Analista de Investimentos/12_PYTHON/src/delivery/telegram_bot.py`
**Commit:** 7a6c303
**Applied fix:** Added early `return False` for 4xx responses (excluding 429) before the 429 rate-limit handler. Retrying a `400 Bad Request` is pointless and wasting retry budget.

---

### WR-04: get_macro_panel() called while conn is open — nested connections

**Files modified:** `Analista de Investimentos/12_PYTHON/src/dashboard/data.py`
**Commit:** 0e09879
**Applied fix:** Moved the `macro = get_macro_panel()` call to before `conn = get_connection(DB_PATH)` in `get_asset_detail()`. The macro result is then assigned inside the try block as `result["macro"] = macro`. This eliminates nested open SQLite connections.

---

### WR-05: app.py duplicates full CSS block from _style.py

**Files modified:** `Analista de Investimentos/scanner_quant_profit_b3/app.py`
**Commit:** 013fc7f
**Applied fix:** Removed the 118-line inline CSS block and replaced it with `from _style import DARK_CSS` + `st.markdown(DARK_CSS, unsafe_allow_html=True)`. Added `sys.path` insertion for the scanner root to ensure the relative import works correctly. The IN-03 character divergence issue is also resolved as a side effect.

---

### WR-06: test_get_opportunities passes vacuously when fixture returns empty

**Files modified:** `Analista de Investimentos/12_PYTHON/tests/test_dashboard_data.py`
**Commit:** 1b07a33
**Applied fix:** Replaced the `if opps:` guard with `assert len(opps) >= 1, "fixture should produce at least one opportunity signal"` followed by unconditional structural assertions. The test now fails loudly if the fixture produces no results.

---

### WR-07: No test for send_morning_call_summary() frontmatter stripping

**Files modified:** `Analista de Investimentos/12_PYTHON/tests/test_delivery_telegram.py`
**Commit:** ba8f556
**Applied fix:** Added `test_morning_call_strip_frontmatter()` covering three cases: (1) file with standard YAML frontmatter — verified stripped from output, (2) file without frontmatter — verified full content forwarded, (3) file with `---` inside body content — verified frontmatter stripped and body preserved. All three cases pass.

---

## Test Results

**Final run:** 130 passed, 1 failed (pre-existing)

The 1 failure (`test_news_hunter_config::test_token_loaded_from_env`) is pre-existing and unrelated to any fix in this session — it tests a hardcoded credential issue in `news_hunter/config.py` that predates Phase 5.

All 130 tests relevant to Phase 5 delivery layer fixes pass.

---

_Fixed: 2026-05-18T19:45:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
