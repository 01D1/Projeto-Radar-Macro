# Phase 5: Delivery Layer - Context

**Gathered:** 2026-05-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Build four intelligence pages inside the existing `scanner_quant_profit_b3` Streamlit app, a Telegram delivery layer (positioning-change alerts + daily morning brief), and a PDF report generator — all reading from `ingestion.db` and delivering outputs in Portuguese with CVM IN 598 disclaimer. No new app is created; pages are added to the existing multi-page dashboard.

</domain>

<decisions>
## Implementation Decisions

### Streamlit App — Location & Structure
- **D-01:** **Add 4 new pages to `scanner_quant_profit_b3` — NOT a new standalone app.** The host app already has dark theme CSS, `st.page_link` horizontal navigation, and 5 existing pages. New intelligence pages are added as files in `Analista de Investimentos/scanner_quant_profit_b3/pages/` and auto-discovered by Streamlit.
- **D-02:** **Page files use `inteligencia_` prefix to group as a separate section:**
  - `inteligencia_watchlist.py` — Watchlist overview (all tickers: price, multiples, signals, positioning)
  - `inteligencia_ativo.py` — Asset detail (per-ticker: thesis, valuation, financials, macro, news)
  - `inteligencia_macro.py` — Macro panel (Selic, IPCA, PTAX, CDS, PIB charts)
  - `inteligencia_oportunidades.py` — Opportunities (ranked signals with conviction scores)
- **D-03:** **Dashboard launched with same existing command** — `streamlit run 'Analista de Investimentos/scanner_quant_profit_b3/app.py'`. New pages auto-discovered. No changes to launch command.

### Streamlit — Data Access Layer
- **D-04:** **Thin query module `src/dashboard/data.py`** — one function per data need: `get_watchlist_summary()`, `get_asset_detail(ticker)`, `get_macro_panel()`, `get_opportunities()`. Each decorated with `@st.cache_data(ttl=300)`. Pages import from `data.py` only — no direct SQLite in page files.
- **D-05:** **DB path imported from `src.ingestion.db.DB_PATH`** — single source of truth. Dashboard and scheduler always use the same database file.
- **D-06:** **Empty state: `st.info()` banner with actionable instruction** when `thesis_latest` view has no rows: `"Nenhuma tese gerada ainda. Execute: python -m src.main daemon para iniciar o pipeline."`

### Streamlit — Watchlist Page
- **D-07:** **`st.dataframe` with colored positioning column** — single interactive table with all tickers. Positioning (COMPRAR/MANTER/VENDER) color-coded via `st.dataframe` column config. Sortable by conviction score or upside %.
- **D-08:** **Freshness timestamp shown per row** from `generated_at` in `thesis_latest` view. Additional freshness for price data from `b3_prices.date`.

### Streamlit — Asset Detail Page
- **D-09:** **Thesis displayed as structured expandable sections matching Phase 4 schema:**
  - Bull/bear case as prose `st.markdown` blocks
  - Drivers rendered as `st.expander` cards: title as header, description as body, impact (HIGH/MEDIUM/LOW) as colored badge
  - Risks rendered as `st.expander` cards: title as header, description as body, severity as colored badge
  - Positioning (COMPRAR/MANTER/VENDER) as a colored `st.metric`
  - Fair value and upside % side by side in `st.metric` columns

### Streamlit — Opportunities Page
- **D-10:** **Signal cards with conviction score progress bar** — each opportunity displayed as a card showing: ticker, signal_type badge (DCF_DIVERGENCE / MOMENTUM_CROSSOVER / IPE_EVENT), one-sentence description, and a horizontal `st.progress()` bar for conviction score (0–100). Top 10 signals ranked by conviction score descending.

### Streamlit — Macro Panel
- **D-11:** **Plotly line charts via `st.plotly_chart`** — one chart per macro series (Selic, IPCA_12m, PTAX, CDS_brasil, PIB_nominal) with date on x-axis, value on y-axis. Reuses scanner_quant's existing Plotly dependency. Dark theme consistent with host app.

### Telegram Delivery
- **D-12:** **Extend existing `TelegramBot` in `src/delivery/telegram_bot.py`** — add two new methods:
  - `send_thesis_alert(ticker, old_positioning, new_positioning, confidence, rationale_one_line, top_opportunity_desc)` — for positioning-change alerts
  - `send_daily_brief(macro_snapshot, top_movers, top_opportunity)` — for morning brief
- **D-13:** **Positioning-change alert fires INSIDE `job_intelligence()` / `run_ticker()`** — after a new thesis version is written to `thesis_versions`, compare `new_positioning != previous_positioning` using the `diff_summary` already computed in Phase 4. If changed, immediately call `bot.send_thesis_alert()`. Uses `InvestmentThesis.summary_one_line` field (Phase 4 D-02) for the one-line rationale.
- **D-14:** **New `job_morning_brief()` in `src/scheduler.py`** — separate from existing `job_morning_call()`. Reads directly from `ingestion.db`:
  - Macro snapshot: latest `macro_series` rows (Selic, IBOV % change from `b3_prices`, PTAX)
  - Top 3 movers: tickers with largest `upside_pct` change from `financial_dcf` today
  - Top opportunity: highest `conviction_score` from today's `opportunity_signals`
  - Default cron: `15 8 * * 1-5` (08:15 Mon–Fri — staggered from `bcb_macro` at `0 8`; configurable via `schedules.yaml`)

### PDF Report Generator
- **D-15:** **Use `fpdf2` — NOT WeasyPrint.** WeasyPrint requires GTK3/libpango/libcairo system libraries that are unreliable on Windows. fpdf2 is pure Python with no system deps.
- **D-16:** **`ReportGenerator` class in `src/delivery/pdf_report.py`** with one method per section:
  - `_header(ticker, generated_at)` — title, ticker, date
  - `_thesis_section(thesis)` — bull/bear, positioning, confidence
  - `_drivers_risks_section(drivers, risks)` — tables with title/description/impact
  - `_valuation_section(dcf, multiples)` — fair value, upside %, P/E, EV/EBITDA, etc.
  - `_financials_section(ltm)` — LTM revenue, EBITDA, net income, FCF, net debt
  - `_macro_section(macro)` — Selic, IPCA, CDS, PTAX
  - `_disclaimer()` — CVM IN 598 text (hardcoded, always appended last)
  - Public API: `generate(ticker) -> bytes` — returns in-memory BytesIO bytes for `st.download_button`
- **D-17:** **PDF generation is in-memory (BytesIO)** — `generate()` returns `bytes`. Streamlit calls `st.download_button(data=pdf_bytes, file_name=f"relatorio_{ticker}.pdf")`. No temp files.

### Testing
- **D-18:** **Telegram tests use `monkeypatch` on `TelegramBot.send()`** — patch send() to a no-op and assert that the captured text contains the expected ticker, positioning label, and formatting strings. Same pattern as existing scheduler tests.
- **D-19:** **PDF tests generate a report for a fixture ticker** — assert bytes is non-empty and starts with `b'%PDF'` header. Section-level tests assert that key strings (ticker name, CVM IN 598 disclaimer) appear in the PDF text content.

### Claude's Discretion
- Navigation ordering of the 4 new intelligence pages within the existing `st.page_link` nav bar
- Exact Plotly chart styling (colors, gridlines) — match scanner_quant's existing dark theme
- Exact CVM IN 598 disclaimer wording — standard regulatory text
- Column selection and ordering for `st.dataframe` in the watchlist
- fpdf2 font choice and page margins for the PDF report

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §DEL-01 through DEL-05 — acceptance criteria for this phase
- `.planning/ROADMAP.md` §Phase 5 — goal, 4 planned deliverables, success criteria
- `.planning/PROJECT.md` — constraints (Python-only, reuse existing logic, SQLite→Supabase-compatible, no overengineering)

### Prior Phase Context (decisions that carry forward)
- `.planning/phases/04-intelligence-layer/04-CONTEXT.md` — D-01/D-02 (Driver/Risk schema designed for card rendering), D-02 (`summary_one_line` field for Telegram), D-14 (`thesis_latest` VIEW), D-16/D-18 (`opportunity_signals` schema and top-3 pattern)
- `.planning/phases/02-reliable-data-ingestion/02-CONTEXT.md` — ingestion.db schema rules (TEXT UUID PK, ISO date strings)

### Existing Streamlit App (host for new pages)
- `Analista de Investimentos/scanner_quant_profit_b3/app.py` — host app: dark theme CSS, `st.page_link` nav pattern, `st.set_page_config` — MUST match this structure for new pages
- `Analista de Investimentos/scanner_quant_profit_b3/pages/radar_quant.py` — reference page implementation: how pages import data, use the dark theme, and render charts
- `Analista de Investimentos/scanner_quant_profit_b3/pages/valuation_engine.py` — reference for financial data display patterns

### Intelligence Data Sources (Phase 5 reads these)
- `Analista de Investimentos/12_PYTHON/src/ingestion/db.py` — `DB_PATH`, `get_connection()` — use this for all dashboard reads
- `Analista de Investimentos/12_PYTHON/src/intelligence_layer.py` — `run_ticker()`, `ThesisResult`, `InvestmentThesis`, `OpportunitySignal` Pydantic schemas
- `Analista de Investimentos/12_PYTHON/data/ingestion.db` — tables: `thesis_versions`, `thesis_latest` (VIEW), `opportunity_signals`, `financial_ltm`, `financial_multiples`, `financial_dcf`, `financial_signals`, `macro_series`, `b3_prices`, `news_articles`

### Telegram Delivery
- `Analista de Investimentos/12_PYTHON/src/delivery/telegram_bot.py` — `TelegramBot` class to extend (add `send_thesis_alert()`, `send_daily_brief()`)

### Scheduler
- `Analista de Investimentos/12_PYTHON/src/scheduler.py` — add `job_morning_brief()` to `_JOB_REGISTRY`
- `Analista de Investimentos/12_PYTHON/config/schedules.yaml` — add `morning_brief` cron entry (**revised to `15 8 * * 1-5`** — `0 8 * * 1-5` is occupied by `bcb_macro`; stagger to avoid collision)

### Configuration
- `Analista de Investimentos/12_PYTHON/pyproject.toml` — add `fpdf2>=2.7.0` to dependencies
- `Analista de Investimentos/12_PYTHON/config/tickers.yaml` — watchlist tickers (active flag)

### Utilities
- `Analista de Investimentos/12_PYTHON/src/utils/logger.py` — `bind_run_id("delivery")`, `get_logger()`
- `Analista de Investimentos/12_PYTHON/src/utils/retry.py` — `@retry` decorator for Telegram API calls

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scanner_quant_profit_b3/app.py` — complete dark theme CSS block. Copy verbatim into each new page's `st.markdown()` call or extract to a shared `_style.py` module imported by all pages.
- `src/delivery/telegram_bot.py` — `TelegramBot` class with `send()`, retry, silent mode. Extend with 2 new methods; do not modify existing methods.
- `src/ingestion/db.py` — `get_connection()` returns a plain `sqlite3.Connection` (NOT a context manager — use `try/finally conn.close()`), plus `DB_PATH` constant. Use for all dashboard DB reads.
- `src/scheduler.py` — `_JOB_REGISTRY` dict + `bind_run_id()` pattern. Add `job_morning_brief()` following the same pattern as `job_intelligence()`.

### Established Patterns
- Streamlit pages in scanner_quant use `st.page_link` for navigation, not `st.sidebar`. New pages must follow this pattern.
- All `src/` jobs use `bind_run_id("service_name")` at the top of the job function (Phase 1 convention).
- All SQL parameterized — never f-string with ticker (T-DCF-02).
- Module docstrings follow the `metrics_engine.py` header pattern with Fluxo/Uso sections.
- Module-level logger: `log = get_logger(__name__)` (never `logger`).

### Integration Points
- `ingestion.db` `thesis_latest` VIEW → `src/dashboard/data.py` `get_watchlist_summary()` and `get_asset_detail(ticker)`
- `ingestion.db` `opportunity_signals` → `src/dashboard/data.py` `get_opportunities()`
- `ingestion.db` `macro_series` → `src/dashboard/data.py` `get_macro_panel()` and `job_morning_brief()`
- `run_ticker()` in `intelligence_layer.py` → extend to call `bot.send_thesis_alert()` when positioning changes
- `scanner_quant_profit_b3/pages/` → drop 4 new `inteligencia_*.py` files here

</code_context>

<specifics>
## Specific Ideas

- **Positioning color coding** in `st.dataframe`: COMPRAR → green (`#16a34a`), MANTER → yellow (`#ca8a04`), VENDER → red (`#dc2626`) — consistent with scanner_quant's color palette.
- **Telegram alert message format** (Portuguese):
  ```
  🔔 *{ticker}* — Tese atualizada
  Posicionamento: {old} → *{new}*
  Confiança: {confidence}
  {summary_one_line}
  Top oportunidade: {top_opportunity_desc}
  ```
- **Daily brief message format**:
  ```
  📊 *Resumo de Mercado — {date}*
  Selic: {selic:.2f}% | PTAX: R${ptax:.4f} | IBOV: {ibov_pct:+.1f}%
  
  🏆 *Top Oportunidades*
  1. {ticker1}: {description1} (score: {score1})
  2. {ticker2}: {description2}
  3. {ticker3}: {description3}
  ```
- **PDF section order**: Header → Thesis summary (positioning/confidence/rationale) → Bull/Bear → Drivers → Risks → Valuation (DCF + multiples table) → LTM financials → Macro context → CVM IN 598 disclaimer
- **CVM IN 598 disclaimer** is mandatory on every PDF report (DEL-05) — add as the last page/section, always present regardless of ticker type.
- **`src/dashboard/` is a new sub-package** — create `src/dashboard/__init__.py` (empty) and `src/dashboard/data.py`. Follow existing `src/` package conventions.

</specifics>

<deferred>
## Deferred Ideas

- **Mobile-optimized view for scanner_quant** — responsive layout for tablet/phone. Out of Phase 5 scope; scanner_quant handles this separately.
- **PDF batch export** — generate reports for all tickers at once. Phase 5 is on-demand per ticker only.
- **Telegram command handlers** (polling bot) — interactive `/status PETR4` commands. Phase 5 is one-way push only. `python-telegram-bot` SDK enables this for a future phase.
- **Email delivery** — send PDF reports via email. Out of v1 scope.
- **Real-time dashboard updates** — WebSocket/SSE push when new thesis is generated. Phase 5 uses TTL-based cache only.
- **Supabase cloud deployment** — dashboard running on hosted infrastructure. Designed for via `DB_PATH` import pattern; deferred to post-v1 migration.

</deferred>

---

*Phase: 5-Delivery Layer*
*Context gathered: 2026-05-18*
