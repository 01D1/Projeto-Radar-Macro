---
phase: 03
slug: financial-engine
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-11
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ticker parameter → SQL query | ticker string from tickers.yaml used in cvm_statements and price_ohlcv queries |
| raw CVM account_code/account_name → normalized_name | Input from CVM CSV; external data, not user-controlled but untrusted |
| ticker → price_ohlcv query | ticker string used in parameterized SELECT |
| price_ohlcv adj_close → ratio computation | Raw float from DB; could be anomalous but not attacker-controlled |
| macro_series values → WACC computation | Selic and CDS values from DB; if corrupted could produce bad WACC |
| WACC + terminal_growth → run_dcf() | Critical pre-validation boundary — T-DCF-01 |
| ticker string → financial_dcf SQL | Parameterized INSERT — must never be f-string |
| SectorConfig.is_bank_model → routing decision | Wrong routing could apply DCF to banks — produces nonsense output |
| ke (cost of equity) → run_ddm() | If ke <= terminal_growth: DDM produces negative equity |
| ticker → price_ohlcv signals query | Parameterized SELECT; same boundary as Plan 01 |
| price_ohlcv adj_close → pandas computation | Float values from DB; NaN propagation risk on gap rows |
| ticker → financial_signals INSERT | Parameterized; same boundary as all prior plans |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Status | Evidence |
|-----------|----------|-----------|-------------|--------|----------|
| T-03-01-01 | Tampering | `_aggregate_ltm()` SQL ticker param | mitigate | CLOSED | `financial_engine.py:127` — `(ticker,)` positional param; `financial_engine.py:151` — `(ticker, *ref_dates)` positional; no f-string ticker in SQL |
| T-03-01-02 | Tampering | `_check_dfp_reconciliation()` double ticker | mitigate | CLOSED | `financial_engine.py:238-246` — CTE `WITH latest_dfp AS (...)` applied (WR-08 from REVIEW-FIX); two positional `?` params, purpose visually unambiguous |
| T-03-01-03 | Info Disclosure | `account_mapper.py` import path | **accept** | CLOSED | See Accepted Risks Log — no security boundary crossed; import resolution fix only |
| T-03-01-04 | DoS | division by zero in divergence | mitigate | CLOSED | `financial_engine.py:257` — `max(abs(dfp_revenue), 1.0)` as denominator; zero-division impossible |
| T-03-01-05 | Tampering | `backfill_normalized_names()` UPDATE | mitigate | CLOSED | `financial_engine.py:297-299` — `UPDATE cvm_statements SET normalized_name = ? WHERE id = ?` with `(norm, row["id"])` positional params |
| T-03-02-01 | Tampering | `_get_current_price()` SQL | mitigate | CLOSED | `financial_engine.py:455` — `WHERE ticker = ? AND is_gap = 0 AND adj_close IS NOT NULL`; `financial_engine.py:459` — `(ticker,)` positional |
| T-03-02-02 | Tampering | `_compute_multiples()` INSERT | mitigate | CLOSED | `financial_engine.py:556-576` — `INSERT OR REPLACE INTO financial_multiples` with all positional params; ticker never in SQL string |
| T-03-02-03 | Tampering | zero-division in ratio computation | mitigate | CLOSED | `financial_engine.py:485,513,520` — `current_price is not None` and `shares > 0` guards before division; None price propagates as None to metric functions which return None ratios |
| T-03-02-04 | Info Disclosure | `is_gap=0` filter missing | mitigate | CLOSED | `financial_engine.py:455` — `is_gap = 0 AND adj_close IS NOT NULL` present in `_get_current_price()` SELECT |
| T-DCF-01 | Tampering | DCF terminal value division `(wacc-g)` | mitigate | CLOSED | `financial_engine.py:895,934` — `_validate_dcf_inputs()` called BEFORE `run_dcf()` in both ev_ebitda and dcf_fcff paths; `financial_engine.py:849` — `if terminal_growth >= wacc: return "INPUT_INVALIDO"`; early return with NULL fair_value |
| T-DCF-02 | Tampering | SQL in `_write_dcf_row()` | mitigate | CLOSED | `financial_engine.py:607-614` — `INSERT OR REPLACE INTO financial_dcf` with `(str(uuid.uuid4()), ticker, ...)` positional params; ticker never embedded in SQL string |
| T-DCF-03 | Info Disclosure | WACC fallback hardcoded | mitigate | CLOSED | `financial_engine.py:805` — fallback reads `a.get("risk_free", 0.105)` where `a = cfg.dcf_assumptions` loaded from sectors.yaml; `0.105` Python literal is last-resort guard only |
| T-03-03-04 | Tampering | WACC from stale macro | mitigate | CLOSED | `financial_engine.py:793-798` — `_is_stale_date(selic_date) or _is_stale_date(cds_date)` freshness check; stale → fallback to sectors.yaml with WARNING log |
| T-03-03-05 | Tampering | EV/EBITDA div-by-zero shares=0 | mitigate | CLOSED | `financial_engine.py:910-911` — `if ebitda is not None and net_debt is not None and shares and shares > 0:` guard before division |
| T-03-04-01 | Tampering | Bank/industrial routing | mitigate | CLOSED | `financial_engine.py:386-391` — `if cfg.is_bank_model:` is the sole routing gate in `run_ticker()`; `_compute_dcf_industrial()` never called for banks |
| T-03-04-02 | Tampering | DDM div-by-zero `ke <= g` | mitigate | CLOSED | `financial_engine.py:676` — `if base_net_income > 0 and ke > terminal_growth and ke > 0.05:` guard before `run_ddm()`; violation sets `confidence_flag="INPUT_INVALIDO"`, `fair_value=None` |
| T-03-04-03 | Tampering | SQL in `_write_dcf_row()` DDM path | mitigate | CLOSED | Same function as T-DCF-02 (`financial_engine.py:589-614`); DDM path calls `_write_dcf_row()` at `financial_engine.py:730`; shared parameterized INSERT |
| T-03-04-04 | Info Disclosure | COSIF via IFRS AccountMapper | mitigate | CLOSED | `financial_engine.py` `backfill_normalized_names()` now routes bank tickers to `BankAccountMapper._map_code()/_map_name()` via `_bank_cache` keyed on `SectorConfig.for_ticker(t).is_bank_model`. `cvm_downloader.py` `parse_and_store()` checks `SectorConfig.for_ticker(ticker).is_bank_model` before instantiating mapper; bank tickers use `BankAccountMapper`, non-bank tickers use `AccountMapper`. Fix applied 2026-05-11; 93 tests green. |
| T-03-05-01 | Tampering | `is_gap=0` absent from signals query | mitigate | CLOSED | `financial_engine.py:1132` — `WHERE ticker = ? AND is_gap = 0 AND adj_close IS NOT NULL` in `_compute_and_write_signals()` SELECT |
| T-03-05-02 | Tampering | SQL injection in `_compute_and_write_signals` | mitigate | CLOSED | `financial_engine.py:1136` — `(ticker,)` positional param in signals SELECT; INSERT uses positional params via `_write_null_signals()` and direct parameterized `conn.execute` |
| T-03-05-03 | DoS | RSI division by zero | mitigate | CLOSED | `financial_engine.py:1039` — `loss.replace(0, float("nan"))` before RSI computation; produces NaN RSI rather than ZeroDivisionError |
| T-03-05-04 | DoS | IndexError prices < 2 rows | mitigate | CLOSED | `financial_engine.py:1139-1144` — `if len(rows) < 2:` guard with `_write_null_signals(); return` before any crossover computation using `iloc[-2]` |
| T-03-05-05 | Tampering | `job_financial_engine()` without bind_run_id | mitigate | CLOSED | `scheduler.py:436` — `with bind_run_id("financial") as run_id:` inside `job_financial_engine()` |

---

## Accepted Risks Log

### T-03-01-03 — Information Disclosure: account_mapper.py import path

| Field | Value |
|-------|-------|
| Threat ID | T-03-01-03 |
| Category | Information Disclosure |
| Component | `account_mapper.py` — ACCOUNT_MAP import path |
| Disposition | accept |
| Risk Level | Low |
| Accepted By | Phase 03 executor (gsd-execute) |
| Accepted Date | 2026-05-11 |
| Rationale | Import path changed from `parsers.` to `src.parsers.` — no security boundary crossed. This is an import resolution fix (Python module path correction) only. The account mapping data itself (ACCOUNT_MAP dict) is a static lookup table with no user-supplied input. No credentials, PII, or sensitive computation is exposed. |
| Residual Risk | None — the fix was applied. Risk entry documents that the pre-fix state was an import error, not a security vulnerability. |

---

## Threat Flags from SUMMARY.md

| Plan | Flag | Mapping | Classification |
|------|------|---------|----------------|
| 03-01 | "Nenhuma nova superfície de ataque além das documentadas no threat_model do PLAN.md." | All flags map to T-03-01-01..05 | Informational |
| 03-02 | "Nenhuma nova superfície de ataque além das documentadas no threat_model do PLAN.md." | All flags map to T-03-02-01..04 | Informational |
| 03-03 | "Nenhuma nova superfície de ataque além das documentadas no threat_model do PLAN.md." | All flags map to T-DCF-01..T-03-03-05 | Informational |
| 03-04 | "Nenhuma nova superficie de ataque alem das documentadas no threat_model do PLAN.md." | All flags map to T-03-04-01..04 | Informational |
| 03-05 | No new surface — plan executed exactly as specified with no deviations. | All flags map to T-03-05-01..05 | Informational |

No unregistered threat flags detected across all five plan summaries.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | ASVS Level | Run By |
|------------|--------------|--------|------|------------|--------|
| 2026-05-11 | 23 | 22 | 1 | 1 | gsd-secure-phase (claude-sonnet-4-6) |
| 2026-05-11 | 23 | 23 | 0 | 1 | gsd-secure-phase — T-03-04-04 fix applied + 93 tests verified |

---

## Sign-Off

- [x] Threat register extracted from all five PLAN.md `<threat_model>` blocks (23 threats)
- [x] All `mitigate` threats grepped against implementation files
- [x] `accept` disposition documented in Accepted Risks Log (T-03-01-03)
- [x] REVIEW-FIX.md changes verified (WR-08 CTE upgrade applied — T-03-01-02 CLOSED)
- [x] T-03-04-03 and T-DCF-02 confirmed as same function `_write_dcf_row()` — both CLOSED
- [x] Threat flags from all five SUMMARY.md files reviewed — no unregistered flags
- [x] T-03-04-04 CLOSED — COSIF routing implemented in `backfill_normalized_names()` and `cvm_downloader.parse_and_store()`; 93 tests green
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-11
