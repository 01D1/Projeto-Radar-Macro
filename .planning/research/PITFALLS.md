# Pitfalls Research — Investment Intelligence Platform

## Critical Pitfalls (Must address before shipping)

These will break production or embarrass in front of clients if not addressed.

---

### P1 — LLM Hallucinated Numbers in Client Output
**Risk:** Claude generates a thesis that states "PETR4 trades at 8x EV/EBITDA" when the actual multiple is 12x. Client acts on wrong data.

**Warning signs:** AI thesis numbers don't match the financial data table shown alongside them.

**Prevention:**
- NEVER ask the LLM to calculate or retrieve numbers — pass all numbers as structured inputs
- The LLM's job is synthesis and narrative, not computation
- Every number in the AI thesis (fair value, multiples, revenue) must be injected from the Financial Engine output
- Add a post-generation validation step: cross-check thesis.fair_value_brl against computed DCF result (tolerance: ±5%)
- Include mandatory disclaimer: "Análise gerada por IA. Verificar dados antes de uso."

**Phase:** Address in Phase 4 (Intelligence Layer design) — build validation into the generation pipeline.

---

### P2 — CVM Data Format Changes Breaking Ingestion Silently
**Risk:** CVM changes XBRL account codes (happens periodically). Parser maps to wrong accounts. Financial statements appear correct but have wrong values. Downstream DCF produces garbage.

**Warning signs:** Revenue or EBITDA for a ticker suddenly changes dramatically between periods with no corresponding news.

**Prevention:**
- Store raw CVM XML alongside parsed data — enables reprocessing without re-downloading
- Add data quality assertions: revenue must be positive, EBITDA must be < revenue, net income can be negative
- Log and alert on account code mismatches (unknown codes) rather than silently dropping
- Maintain explicit account code mapping table (already partially exists in `config/mapeamento_contas_geral.py`) — version control it
- Run a "sanity check" step after each CVM ingestion: compare latest period to prior period, flag outliers >50% change

**Phase:** Address in Phase 2 (Reliable Ingestion).

---

### P3 — Hardcoded Credentials Committed to Git
**Risk:** Telegram tokens, Anthropic API keys in source code. If repo is ever shared or pushed to GitHub, credentials are exposed. Already present in `news_hunter/config.py` lines 60-61.

**Warning signs:** Already confirmed by codebase scan.

**Prevention:**
- Before first commit of application code: audit all Python files for hardcoded strings matching API key patterns
- Migrate all credentials to `.env` using `pydantic-settings` BaseSettings class
- Add `.env` to `.gitignore` immediately
- Add `detect-secrets` as a pre-commit hook to prevent future credential commits
- Rotate any tokens that were previously hardcoded before first push to any remote

**Phase:** Address in Phase 1 (Foundation) — this is a blocker for all subsequent work.

---

### P4 — LLM Cost Runaway
**Risk:** Intelligence layer regenerates thesis for all 50 tickers every time any data changes. At $0.10 per thesis × 50 tickers × 10 daily runs = $50/day. Quickly expensive.

**Warning signs:** Anthropic usage dashboard shows unexpected spike.

**Prevention:**
- Hash the inputs to each thesis (DCF result + multiples + top 3 news headlines + key signals)
- Only regenerate thesis when input hash changes — implement `thesis.input_hash` in schema
- Separate "data changed" events from "thesis needs refresh" logic
- Add a daily thesis refresh limit per ticker (max 2x/day regardless of input changes)
- Use `claude-haiku-4-5` for all classification tasks (news sentiment, event routing) — 10x cheaper than sonnet
- Monitor token usage per ticker in logs; alert if any single ticker exceeds daily threshold

**Phase:** Address in Phase 4 (Intelligence Layer).

---

### P5 — SQLite Corruption Under Concurrent Writes
**Risk:** Streamlit dashboard reads while APScheduler writes. SQLite in WAL mode handles this, but without WAL enabled, writes can corrupt the database.

**Warning signs:** SQLite "database is locked" errors in logs.

**Prevention:**
- Enable WAL mode on database initialization: `PRAGMA journal_mode=WAL`
- Use SQLAlchemy connection pool with `check_same_thread=False` for Streamlit
- Design pipeline to write in batches at end of ingestion run (not row-by-row during scraping)
- Keep a daily SQLite backup before pipeline run: `shutil.copy(db_path, f"{db_path}.bak.{date}")`

**Phase:** Address in Phase 1 (schema design) and Phase 5 (Streamlit integration).

---

## High Risk (Address in early phases)

---

### P6 — yfinance API Breaking Changes / Rate Limiting
**Risk:** Yahoo Finance is an unofficial API. yfinance breaks 2-3x per year when Yahoo changes their API. The existing pipeline has no retry or fallback.

**Warning signs:** `yfinance` raises exceptions or returns empty DataFrames silently.

**Prevention:**
- Wrap all yfinance calls with `tenacity` retry (exponential backoff, 3 retries)
- Store last-known-good price in SQLite — serve stale data with timestamp rather than crashing
- Add `try/except` around all yfinance calls; log failures and continue (don't crash the pipeline)
- Pin yfinance version in requirements; test upgrades before deploying
- Consider `investpy` as fallback (though also unofficial) or B3 MarketData API as paid alternative

**Phase:** Address in Phase 2 (Reliable Ingestion).

---

### P7 — DCF Model Errors (Circular References, Terminal Value Explosion)
**Risk:** DCF models have well-known failure modes: WACC miscalculation, terminal growth rate > WACC (makes terminal value negative or infinite), circular reference in WACC (equity value → beta → WACC → equity value).

**Warning signs:** Fair value output is negative, infinite, or >10x current price.

**Prevention:**
- Validate DCF inputs before running: assert terminal_growth < WACC, assert WACC > 0.05
- Add output bounds check: if fair_value > 5x current price OR < 0.1x current price, flag as "FORA DO INTERVALO CONFIÁVEL" rather than displaying
- Use pre-tax WACC for simplicity in v1 (avoid circular reference)
- Document DCF methodology assumptions explicitly (what discount rate source, what terminal growth assumption)
- Cross-validate DCF with EV/EBITDA multiple — they should agree within 30-40% for mature companies

**Phase:** Address in Phase 3 (Financial Engine).

---

### P8 — Duplicate Codebase Creating Split-Brain Updates
**Risk:** Three copies of code exist (`Analista de Investimentos/12_PYTHON/`, `Meu segundo Cerébro/12_PYTHON/`, `_ARQUIVO_Analista_vs_code/12_PYTHON/`). A bug fix in one copy isn't applied to others. A regression in one affects results differently than another.

**Warning signs:** Already confirmed — running scripts from different directories produces different outputs.

**Prevention:**
- In Phase 1: delete or archive `_ARQUIVO_Analista_vs_code/` and `Meu segundo Cerébro/12_PYTHON/`
- Keep one canonical source: `Analista de Investimentos/12_PYTHON/src/`
- Ensure all scheduler scripts and notebooks import from the canonical location only
- Use relative imports within the package; avoid `sys.path` manipulation

**Phase:** Address in Phase 1 (Foundation) — do this first.

---

### P9 — Obsidian Vault Polluted with Generated Content
**Risk:** `obsidian_writer.py` writes analysis files into the vault. Generated files interleave with hand-written notes. Obsidian's search and graph view becomes polluted. Accidental deletion of generated files causes "missing" data perception.

**Warning signs:** Obsidian graph shows hundreds of auto-generated nodes; search returns noise.

**Prevention:**
- Confine generated outputs to a specific vault folder (e.g., `Analista de Investimentos/13_AI_REPORTS/`)
- Add a frontmatter tag to all generated files: `tags: [ai-generated, do-not-edit]`
- Never write to folders that contain hand-written notes
- Consider whether Streamlit dashboard replaces the Obsidian output need entirely (it probably does for v1)

**Phase:** Address in Phase 5 (Delivery Layer design).

---

## Medium Risk (Address before scale)

---

### P10 — Brazilian Holiday Calendar in Date Arithmetic
**Risk:** Calculating "trading days between earnings and current date" or "YoY comparison" using calendar days instead of business days produces wrong results. Brazil has many national holidays not in standard libraries.

**Prevention:**
- Use `pandas_market_calendars` with the `BMFBOVESPA` calendar for all B3 trading day calculations
- Alternatively use `bizdays` package with Brazilian calendar
- Never use `pd.bdate_range` (US business days only)

**Phase:** Address in Phase 3 (Financial Engine).

---

### P11 — Streamlit Performance with Large DataFrames
**Risk:** Loading 5 years × 50 tickers of OHLCV data into Streamlit on every page render. Streamlit reruns the entire script on any user interaction. With unoptimized data loading this becomes unusably slow.

**Prevention:**
- Use `@st.cache_data(ttl=3600)` on all data-loading functions
- Limit displayed data to relevant date range (default: 2 years); let user expand
- Use `st.dataframe` with `use_container_width=True` for lazy rendering
- Never load all tickers at once — load on demand based on selected watchlist item

**Phase:** Address in Phase 5 (Dashboard implementation).

---

### P12 — Prompt Drift Making Thesis Inconsistent
**Risk:** Prompt is edited to improve output for one ticker but degrades quality for others. Without versioning or regression testing, prompt quality silently deteriorates.

**Prevention:**
- Store prompts as Jinja2 templates in `src/intelligence/prompts/` directory (not inline strings)
- Version prompts with semantic versioning in the template header
- Maintain a small set of 5-10 "golden" reference tickers with known-good thesis outputs
- Before deploying prompt changes, regenerate these reference tickers and manually review

**Phase:** Address in Phase 4 (Intelligence Layer).

---

### P13 — CVM Account Code Mapping Divergence for Banks
**Risk:** Banks use COSIF accounting (Banco Central) instead of IFRS. CVM filings for Itaú, Bradesco, BB have completely different account structures. Mapping table designed for industrial companies produces wrong results for financials.

**Warning signs:** Bank EBITDA calculations are nonsensical (banks don't have "operating profit" in the industrial sense).

**Prevention:**
- Detect bank/financial institution sector (CVM sector code) and route to a separate mapping table
- For banks: use Net Interest Income (NIM) instead of EBITDA; use ROE instead of ROIC
- Maintain two DCF model variants: industrial (FCF-based) and bank (dividend discount / excess capital)
- The existing `pipeline banco completo/` codebase has this logic — extract and canonicalize it

**Phase:** Address in Phase 3 (Financial Engine) — model bifurcation at sector detection.

---

## Phase Mapping Summary

| Pitfall | Severity | Address in Phase |
|---------|----------|-----------------|
| P3 — Hardcoded credentials | CRITICAL | Phase 1 |
| P8 — Duplicate codebase | CRITICAL | Phase 1 |
| P5 — SQLite WAL mode | HIGH | Phase 1 |
| P6 — yfinance fragility | HIGH | Phase 2 |
| P2 — CVM format changes | HIGH | Phase 2 |
| P7 — DCF model errors | HIGH | Phase 3 |
| P13 — Bank accounting divergence | HIGH | Phase 3 |
| P1 — LLM hallucinated numbers | CRITICAL | Phase 4 |
| P4 — LLM cost runaway | HIGH | Phase 4 |
| P12 — Prompt drift | MEDIUM | Phase 4 |
| P9 — Obsidian pollution | MEDIUM | Phase 5 |
| P11 — Streamlit performance | MEDIUM | Phase 5 |
| P10 — Holiday calendar | LOW | Phase 3 |

---
*Researched: 2026-05-06*
