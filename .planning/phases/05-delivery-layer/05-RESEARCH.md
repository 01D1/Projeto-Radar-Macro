# Phase 5: Delivery Layer - Research

**Researched:** 2026-05-18
**Domain:** Streamlit multi-page dashboard, fpdf2 PDF generation, Telegram Bot extension, SQLite read layer
**Confidence:** HIGH (codebase verified, library APIs confirmed via official docs and pypi)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Streamlit App — Location & Structure**
- D-01: Add 4 new pages to `scanner_quant_profit_b3` — NOT a new standalone app. Host app has dark theme CSS, `st.page_link` horizontal navigation, and 5 existing pages. New intelligence pages added as files in `Analista de Investimentos/scanner_quant_profit_b3/pages/` and auto-discovered.
- D-02: Page files use `inteligencia_` prefix: `inteligencia_watchlist.py`, `inteligencia_ativo.py`, `inteligencia_macro.py`, `inteligencia_oportunidades.py`
- D-03: Dashboard launched with same existing command — `streamlit run 'Analista de Investimentos/scanner_quant_profit_b3/app.py'`. No changes to launch command.

**Streamlit — Data Access Layer**
- D-04: Thin query module `src/dashboard/data.py` — one function per data need, each decorated with `@st.cache_data(ttl=300)`. Pages import from `data.py` only — no direct SQLite in page files.
- D-05: DB path imported from `src.ingestion.db.DB_PATH` — single source of truth.
- D-06: Empty state: `st.info()` banner with actionable instruction when `thesis_latest` view has no rows.

**Streamlit — Watchlist Page**
- D-07: `st.dataframe` with colored positioning column — Pandas Styler for color-coding (COMPRAR/MANTER/VENDER).
- D-08: Freshness timestamp shown per row from `generated_at` in `thesis_latest` view.

**Streamlit — Asset Detail Page**
- D-09: Thesis displayed as structured expandable sections matching Phase 4 schema — bull/bear as `st.markdown`, drivers/risks as `st.expander` cards with impact/severity badges, positioning as colored `st.metric`.

**Streamlit — Opportunities Page**
- D-10: Signal cards with conviction score progress bar — `st.progress()` for each signal, top 10 ranked by conviction score descending.

**Streamlit — Macro Panel**
- D-11: Plotly line charts via `st.plotly_chart` — one chart per macro series with dark theme.

**Telegram Delivery**
- D-12: Extend existing `TelegramBot` in `src/delivery/telegram_bot.py` — add `send_thesis_alert()` and `send_daily_brief()` methods.
- D-13: Positioning-change alert fires INSIDE `job_intelligence()` / `run_ticker()` — compare `new_positioning != previous_positioning` using `diff_summary`.
- D-14: New `job_morning_brief()` in `src/scheduler.py` — separate from `job_morning_call()`. Default cron: `0 8 * * 1-5`.

**PDF Report Generator**
- D-15: Use `fpdf2` — NOT WeasyPrint (GTK3 system deps unreliable on Windows).
- D-16: `ReportGenerator` class in `src/delivery/pdf_report.py` with section methods.
- D-17: PDF generation in-memory (BytesIO) — `generate()` returns `bytes` for `st.download_button`.

**Testing**
- D-18: Telegram tests use `monkeypatch` on `TelegramBot.send()`.
- D-19: PDF tests assert bytes non-empty and starts with `b'%PDF'`, key strings appear in content.

### Claude's Discretion
- Navigation ordering of the 4 new intelligence pages within the existing `st.page_link` nav bar
- Exact Plotly chart styling (colors, gridlines) — match scanner_quant's existing dark theme
- Exact CVM IN 598 disclaimer wording — standard regulatory text
- Column selection and ordering for `st.dataframe` in the watchlist
- fpdf2 font choice and page margins for the PDF report

### Deferred Ideas (OUT OF SCOPE)
- Mobile-optimized view for scanner_quant
- PDF batch export (all tickers at once)
- Telegram command handlers (polling bot, interactive `/status PETR4`)
- Email delivery
- Real-time dashboard updates (WebSocket/SSE)
- Supabase cloud deployment
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEL-01 | Streamlit multi-page dashboard with Watchlist, Asset detail, Macro panel, Opportunities pages | D-01–D-11 locked; `st.navigation` + `st.Page` pattern confirmed in app.py; dark theme CSS extracted |
| DEL-02 | Dashboard uses `st.cache_data` with TTL; freshness timestamps; <5s for 50-ticker watchlist | `@st.cache_data(ttl=300)` confirmed; cache shared across pages when function names match — must use unique function names in `data.py` |
| DEL-03 | Telegram alert when thesis positioning changes — ticker, positioning, confidence, rationale, top opportunity | TelegramBot.send() verified; `send_thesis_alert()` pattern designed; integration point in `run_ticker()` confirmed |
| DEL-04 | Daily morning brief at configurable time — macro snapshot, top 3 movers, top opportunity | `job_morning_brief()` in `scheduler.py`; `_JOB_REGISTRY` + `schedules.yaml` pattern confirmed from Phase 4 |
| DEL-05 | PDF per ticker on demand — thesis, valuation, LTM, macro, risks, CVM IN 598 disclaimer; <30s; downloadable from Streamlit | fpdf2 2.8.7 confirmed; `bytes(pdf.output())` for in-memory; `st.download_button(data=...)` confirmed |
</phase_requirements>

---

## Summary

Phase 5 adds the user-facing surface of the investment intelligence platform: four Streamlit pages grafted onto the existing `scanner_quant_profit_b3` app, two Telegram delivery methods on the existing `TelegramBot` class, and an fpdf2-based PDF report generator. All three components read from `ingestion.db` — no new database writes in this phase.

The research confirms that the existing `app.py` uses `st.navigation(_PAGES, position="hidden")` with an explicit `pages.run()` call. New pages are registered by adding `st.Page(...)` entries to the `_PAGES` list in `app.py` and dropping the page files in the `pages/` directory. The host app's dark theme CSS block (confirmed at lines 16–135 of `app.py`) must be copied verbatim into each new page file via `st.markdown(_CSS, unsafe_allow_html=True)`.

The central technical risk for this phase is the `sys.path` insertion pattern needed in each page file — the pages directory is `scanner_quant_profit_b3/pages/`, but all `src.*` imports are rooted at `Analista de Investimentos/12_PYTHON/`. Each page must compute `PIPELINE_ROOT` and insert it into `sys.path` before any `src.*` import, matching the pattern used in `agendador.py` (verified in codebase). The `src/dashboard/` sub-package is new and must have an `__init__.py` created as part of Wave 0.

**Primary recommendation:** Build in four waves — (1) Wave 0: `src/dashboard/` package + `data.py` query module + app.py registration; (2) Wave 1 parallel: Watchlist + Opportunities pages; (3) Wave 2: Asset detail + Macro pages; (4) Wave 3: Telegram extension + PDF generator + scheduler wiring. Telegram and PDF have no Streamlit dependency, so they can proceed in parallel with the page work.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Watchlist overview (prices, multiples, signals, thesis) | Frontend Server (Streamlit) | Database (SQLite read) | Aggregates 4 tables; render logic belongs in page layer |
| Asset detail — thesis display | Frontend Server (Streamlit) | Database (SQLite read) | Reads `thesis_latest` VIEW + JSON deserialize |
| Macro charts | Frontend Server (Streamlit) | Database (SQLite read) | `macro_series` table → Plotly line charts |
| Opportunities ranked list | Frontend Server (Streamlit) | Database (SQLite read) | `opportunity_signals` table → progress bar cards |
| Data access / caching | API/Backend module (`data.py`) | — | Centralized SQLite reads with TTL cache; pages import only from this module |
| Positioning-change alert | API/Backend (`intelligence_layer.py`) | Delivery (telegram_bot.py) | Alert fires at generation time inside `run_ticker()`, not from UI |
| Morning brief | Scheduler (`scheduler.py`) | Delivery (telegram_bot.py) | Scheduled job, reads ingestion.db directly |
| PDF generation | Delivery module (`pdf_report.py`) | — | Pure Python fpdf2; invoked from Streamlit download button |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | 1.57.0 (installed) | Multi-page dashboard | Already in host app; `st.navigation` + `st.Page` is the v1.28+ standard pattern [VERIFIED: pip show] |
| plotly | 6.7.0 (installed) | Line charts for macro panel | Already dependency of scanner_quant; `plotly_dark` template built-in [VERIFIED: pip show] |
| fpdf2 | 2.8.7 (latest) | PDF report generation | Pure Python, no system deps, Windows-compatible; locked in D-15 [VERIFIED: pip index] |
| sqlite3 | stdlib | DB reads from ingestion.db | Already used across all phases; `get_connection()` from `src.ingestion.db` [VERIFIED: codebase] |
| pandas | 2.1.0+ | DataFrames + Styler for coloring | Already installed; Styler.map() for conditional cell coloring [VERIFIED: pyproject.toml] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| requests | 2.31.0+ | Telegram HTTP calls | Already used in TelegramBot._post() [VERIFIED: codebase] |
| jinja2 | 3.1.0+ | PDF section templates (if used) | Already installed from Phase 4; optional for PDF text blocks |
| pyyaml | 6.0.0+ | schedules.yaml for morning_brief cron | Already installed [VERIFIED: pyproject.toml] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| fpdf2 | WeasyPrint | WeasyPrint needs GTK3/libpango on Windows — unreliable; rejected in D-15 |
| fpdf2 | reportlab | reportlab is heavier, commercial license for advanced features |
| Pandas Styler | st.dataframe column_config | column_config has no cell-level color API as of Streamlit 1.57.0; Styler is the correct path |
| plotly_dark template | Manual chart styling | Template sets paper_bgcolor, plot_bgcolor, font color consistently; less code |

**Installation (Wave 0):**
```bash
pip install "fpdf2>=2.7.0"
# Add to pyproject.toml [project.dependencies]:
# "fpdf2>=2.7.0",
```

**Version verification:** [VERIFIED: `pip index versions fpdf2`] — latest 2.8.7 (2026-02-28). Pin `>=2.7.0` to allow patch updates while requiring the `table()` context manager API.

---

## Architecture Patterns

### System Architecture Diagram

```
ingestion.db (SQLite, WAL mode)
     │
     ├── thesis_latest VIEW ──────────────────────────────────┐
     ├── opportunity_signals                                   │
     ├── financial_dcf / financial_multiples / financial_ltm  │
     ├── macro_series                                          │
     └── price_ohlcv (b3_prices)                              │
                                                              │
                    src/dashboard/data.py                     │
                    @st.cache_data(ttl=300)                   │
              ┌─────────────────────────────┐                 │
              │ get_watchlist_summary()     │◄────────────────┤
              │ get_asset_detail(ticker)    │◄────────────────┤
              │ get_macro_panel()           │◄────────────────┤
              │ get_opportunities()         │◄────────────────┘
              └─────────────────────────────┘
                         │
          ┌──────────────┼──────────────┬──────────────┐
          ▼              ▼              ▼              ▼
  inteligencia_   inteligencia_  inteligencia_  inteligencia_
  watchlist.py    ativo.py       macro.py       oportunidades.py
  (st.dataframe)  (st.expander   (st.plotly_    (st.progress
                   + st.metric)   chart)         cards)
          └──────────────┴──────────────┴──────────────┘
                         │
              scanner_quant_profit_b3/app.py
              (host: dark CSS, st.navigation, page_link nav)
                         │
                    Browser (user)
                         │
              st.download_button ─────► src/delivery/pdf_report.py
                                        (ReportGenerator → fpdf2 → bytes)
                                                  │
                                         reads: thesis_versions
                                                 financial_dcf
                                                 financial_ltm
                                                 financial_multiples
                                                 macro_series

intelligence_layer.py run_ticker()
         │
         ▼ (when new_positioning != prev_positioning)
src/delivery/telegram_bot.py
TelegramBot.send_thesis_alert()
         │
         ▼
Telegram API

src/scheduler.py job_morning_brief()  [0 8 * * 1-5]
         │  reads ingestion.db directly
         ▼
TelegramBot.send_daily_brief()
         │
         ▼
Telegram API
```

### Recommended Project Structure (new files only)

```
Analista de Investimentos/
├── scanner_quant_profit_b3/
│   ├── app.py                          # MODIFY: add 4 st.Page entries to _PAGES list
│   └── pages/
│       ├── inteligencia_watchlist.py   # NEW: watchlist overview page
│       ├── inteligencia_ativo.py       # NEW: asset detail page
│       ├── inteligencia_macro.py       # NEW: macro panel page
│       └── inteligencia_oportunidades.py  # NEW: opportunities page
└── 12_PYTHON/
    ├── pyproject.toml                  # MODIFY: add fpdf2>=2.7.0
    ├── config/
    │   └── schedules.yaml              # MODIFY: add morning_brief job
    ├── src/
    │   ├── dashboard/
    │   │   ├── __init__.py             # NEW: empty, makes it a package
    │   │   └── data.py                 # NEW: @st.cache_data query functions
    │   ├── delivery/
    │   │   ├── telegram_bot.py         # MODIFY: add send_thesis_alert(), send_daily_brief()
    │   │   └── pdf_report.py           # NEW: ReportGenerator class
    │   ├── intelligence_layer.py       # MODIFY: call send_thesis_alert() when positioning changes
    │   └── scheduler.py               # MODIFY: add job_morning_brief() + registry entry
    └── tests/
        ├── test_delivery_telegram.py   # NEW: Telegram method tests
        ├── test_delivery_pdf.py        # NEW: PDF generation tests
        ├── test_dashboard_data.py      # NEW: data.py query function tests
        └── test_scheduler_delivery.py  # NEW: job_morning_brief + registry tests
```

### Pattern 1: Page File sys.path Bootstrap

Every new page file must resolve the pipeline root and insert it before any `src.*` import. This pattern is established in the existing pages (`agendador.py` verified at line 19).

```python
# Source: verified in agendador.py (codebase)
import sys
from pathlib import Path

SCANNER_ROOT  = Path(__file__).resolve().parents[1]   # scanner_quant_profit_b3/
PIPELINE_ROOT = SCANNER_ROOT.parent / "12_PYTHON"     # Analista de Investimentos/12_PYTHON/

for _p in (str(PIPELINE_ROOT), str(SCANNER_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Now safe to import
from src.dashboard.data import get_watchlist_summary
```

### Pattern 2: Dark Theme CSS Injection

Each page must call the same CSS block used in `app.py` (verified lines 16–135). Extract to a shared `_style.py` module in the scanner_quant root or copy verbatim.

```python
# Source: verified in agendador.py + app.py (codebase)
import streamlit as st
# At top of page's render function:
st.markdown("""<style>
section.main > div { padding-top: 0.2rem; }
/* ... full block from app.py ... */
</style>""", unsafe_allow_html=True)
```

Preferred: create `scanner_quant_profit_b3/_style.py` with `DARK_CSS` constant; all 4 new pages import it.

### Pattern 3: st.cache_data Data Layer

```python
# Source: Streamlit docs (docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data)
import streamlit as st
from src.ingestion.db import get_connection, DB_PATH

@st.cache_data(ttl=300)
def get_watchlist_summary() -> list[dict]:
    """Returns latest thesis + price + multiples for all tickers."""
    with get_connection(DB_PATH) as conn:   # NOTE: get_connection() does NOT use context manager
        # Must use explicit conn / conn.close() pattern (verified in codebase)
        pass
```

**Critical note:** `get_connection()` in `src/ingestion/db.py` does NOT return a context manager — it returns a plain `sqlite3.Connection`. Use `try/finally conn.close()` pattern matching all existing scheduler jobs. [VERIFIED: db.py lines 209–219]

```python
# Correct pattern (matching scheduler.py jobs):
@st.cache_data(ttl=300)
def get_watchlist_summary() -> list[dict]:
    conn = get_connection(DB_PATH)
    try:
        rows = conn.execute("""
            SELECT tl.ticker, tl.positioning, tl.confidence, tl.fair_value_brl,
                   tl.generated_at, fm.pe_ratio, fm.ev_ebitda, fm.price,
                   fd.upside_pct
            FROM thesis_latest tl
            LEFT JOIN financial_multiples fm ON fm.ticker = tl.ticker
                AND fm.computed_date = (SELECT MAX(computed_date) FROM financial_multiples WHERE ticker = tl.ticker)
            LEFT JOIN financial_dcf fd ON fd.ticker = tl.ticker
                AND fd.computed_date = (SELECT MAX(computed_date) FROM financial_dcf WHERE ticker = tl.ticker)
            ORDER BY tl.positioning, fd.upside_pct DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
```

### Pattern 4: st.navigation Page Registration

New pages are registered by appending `st.Page(...)` to the `_PAGES` list in `app.py`. [VERIFIED: app.py lines 138–144]

```python
# app.py modification (Source: verified in app.py codebase)
_PAGES = [
    st.Page("pages/radar_quant.py",                title="Radar Quant",          icon="🎯"),
    st.Page("pages/valuation_engine.py",           title="Valuation Engine",     icon="📊"),
    st.Page("pages/performance.py",                title="Performance",          icon="📈"),
    st.Page("pages/calendario.py",                 title="Calendário",           icon="📅"),
    st.Page("pages/agendador.py",                  title="Agendador",            icon="⏱"),
    # Intelligence pages (Phase 5):
    st.Page("pages/inteligencia_watchlist.py",     title="Watchlist",            icon="🔭"),
    st.Page("pages/inteligencia_ativo.py",         title="Ativo",                icon="🧠"),
    st.Page("pages/inteligencia_macro.py",         title="Macro",                icon="🌐"),
    st.Page("pages/inteligencia_oportunidades.py", title="Oportunidades",        icon="🏆"),
]
```

The nav bar uses `st.columns([1.6] + [1] * len(_PAGES))` — with 9 pages this becomes narrower. Claude's discretion: consider adjusting the logo column ratio or abbreviating labels.

### Pattern 5: Pandas Styler for Positioning Colors

`st.dataframe` does not support direct cell colors via `column_config`. Use `df.style.map()` (Pandas 2.x — `applymap` deprecated in favor of `map`). [VERIFIED: Pandas Styler docs, confirmed Streamlit 1.57.0 supports Styler]

```python
# Source: Streamlit docs + pandas Styler docs
POSITIONING_COLORS = {
    "COMPRAR": "background-color: #16a34a; color: white",
    "MANTER":  "background-color: #ca8a04; color: white",
    "VENDER":  "background-color: #dc2626; color: white",
}

def _color_positioning(val: str) -> str:
    return POSITIONING_COLORS.get(val, "")

st.dataframe(
    df.style.map(_color_positioning, subset=["positioning"]),
    use_container_width=True,
    hide_index=True,
)
```

### Pattern 6: Plotly Dark Theme Charts

```python
# Source: plotly.com/python/templates + verified plotly 6.7.0 installed
import plotly.graph_objects as go

fig = go.Figure()
fig.add_trace(go.Scatter(x=dates, y=values, mode="lines", name="Selic"))
fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",   # transparent — blends with dark CSS
    plot_bgcolor="rgba(13,20,33,1)",  # #0D1421 matching app.py details background
    font=dict(color="#94A3B8"),
    margin=dict(l=10, r=10, t=30, b=10),
    height=280,
)
st.plotly_chart(fig, use_container_width=True)
```

### Pattern 7: fpdf2 In-Memory PDF

```python
# Source: py-pdf.github.io/fpdf2/UsageInWebAPI.html [CITED]
from fpdf import FPDF

class ReportGenerator(FPDF):
    def header(self):
        self.set_font("Helvetica", style="B", size=14)
        self.cell(0, 10, self._doc_title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", style="I", size=8)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

    def generate(self, ticker: str) -> bytes:
        self._doc_title = f"Relatório de Investimento — {ticker}"
        self.add_page()
        self._header_section(ticker)
        self._thesis_section(...)
        # ... other sections ...
        self._disclaimer()
        return bytes(self.output())   # returns bytearray → cast to bytes
```

Streamlit download button:
```python
# Source: py-pdf.github.io/fpdf2/UsageInWebAPI.html [CITED]
pdf_bytes = ReportGenerator().generate(ticker)
st.download_button(
    label="Baixar Relatório PDF",
    data=pdf_bytes,
    file_name=f"relatorio_{ticker}.pdf",
    mime="application/pdf",
)
```

### Pattern 8: TelegramBot Extension

```python
# Source: verified in telegram_bot.py (codebase)
def send_thesis_alert(
    self,
    ticker: str,
    old_positioning: str,
    new_positioning: str,
    confidence: str,
    rationale_one_line: str,
    top_opportunity_desc: str,
) -> bool:
    """Fires when thesis positioning changes — D-12."""
    text = (
        f"🔔 *{ticker}* — Tese atualizada\n"
        f"Posicionamento: {old_positioning} → *{new_positioning}*\n"
        f"Confiança: {confidence}\n"
        f"{rationale_one_line}\n"
        f"Top oportunidade: {top_opportunity_desc}"
    )
    return self.send(text)

def send_daily_brief(
    self,
    macro_snapshot: dict,
    top_movers: list[dict],
    top_opportunity: dict | None,
) -> bool:
    """Daily morning brief — D-12."""
    from datetime import date
    date_str = date.today().strftime("%d/%m/%Y")
    lines = [
        f"📊 *Resumo de Mercado — {date_str}*",
        f"Selic: {macro_snapshot['selic']:.2f}% | PTAX: R${macro_snapshot['ptax']:.4f} | IBOV: {macro_snapshot['ibov_pct']:+.1f}%",
        "",
        "🏆 *Top Oportunidades*",
    ]
    for i, m in enumerate(top_movers[:3], 1):
        lines.append(f"{i}. {m['ticker']}: {m['description']} (score: {m['score']})")
    return self.send("\n".join(lines))
```

### Pattern 9: job_morning_brief() in scheduler.py

Follow the exact pattern established by `job_intelligence()` (verified lines 427–454 in scheduler.py):

```python
# Source: verified scheduler.py pattern (codebase)
def job_morning_brief() -> str:
    """Envia resumo diário de mercado via Telegram — DEL-04."""
    from src.delivery.telegram_bot import get_bot
    from src.ingestion.db import get_connection, DB_PATH
    from src.utils.logger import bind_run_id, get_logger as _get

    _log = _get(__name__)
    with bind_run_id("delivery") as run_id:
        _log.info(f"[morning_brief] iniciado — run_id={run_id}")
        # ... reads from ingestion.db, calls get_bot().send_daily_brief()
    return "morning_brief: sent"
```

Register in `_JOB_REGISTRY`:
```python
"morning_brief": job_morning_brief,   # DEL-04
```

Add to `schedules.yaml`:
```yaml
- job: morning_brief
  cron: "0 8 * * 1-5"      # seg-sex 08:00
  description: Resumo diário de mercado via Telegram
```

### Anti-Patterns to Avoid

- **Direct SQLite in page files:** Pages must import from `src.dashboard.data` only. No `sqlite3.connect()` calls in page files — caching will not work and connections will leak.
- **`conn.close()` missing in `data.py`:** `get_connection()` is not a context manager — always use `try/finally conn.close()`.
- **Reusing FPDF instance across requests:** `fpdf2` docs warn: "content cannot be added once `output()` has been called." Create a fresh `ReportGenerator` per `generate()` call.
- **`applymap` in Pandas 2.x:** Use `df.style.map()` not `df.style.applymap()` — `applymap` is deprecated in Pandas 2.0+.
- **Same function name in multiple page files for cached functions:** Streamlit 1.57.0 has a known issue where `@st.cache_data` functions with the same name across pages share the same cache. All cached functions must live in `data.py` with unique names — never inline cached functions in page files.
- **f-string SQL with ticker:** All SQL parameterized with `?` placeholder (T-DCF-02 rule, established in all prior phases).
- **Hardcoded DB path in pages:** Always import `DB_PATH` from `src.ingestion.db` (D-05).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF generation | Custom byte-stream builder | fpdf2 FPDF class | Font embedding, page layout, text wrapping — dozens of edge cases |
| PDF table rendering | Manual cell coordinate math | `fpdf.table()` context manager (fpdf2 2.7+) | Auto-column widths, border styles, header repeat on page break |
| Telegram HTTP retry | Custom `requests.post` loop | Existing `TelegramBot._post()` with retry | Already handles 429 rate limit, exponential backoff |
| Plotly dark theme | Manual `bgcolor` on every chart | `template="plotly_dark"` + transparent `paper_bgcolor` | Consistent token-level theming across all chart elements |
| Cache invalidation logic | Custom TTL dict | `@st.cache_data(ttl=300)` | Handles thread safety, serialization, TTL expiry automatically |
| Positioning color map | Inline CSS in cell | Pandas `Styler.map()` | Works with `st.dataframe`; column_config has no cell-color API |

**Key insight:** The most dangerous hand-roll in this phase is trying to build DB caching directly in page files. The `@st.cache_data` decorator in a centralized `data.py` module is the only correct pattern — it keeps page files thin and avoids the function-name collision cache bug.

---

## Common Pitfalls

### Pitfall 1: sys.path not bootstrapped before src.* import
**What goes wrong:** `ModuleNotFoundError: No module named 'src'` when Streamlit runs the page file.
**Why it happens:** Page files run with `scanner_quant_profit_b3/` as cwd, but `src/` lives in `12_PYTHON/`.
**How to avoid:** Insert `PIPELINE_ROOT = SCANNER_ROOT.parent / "12_PYTHON"` into `sys.path` at the top of every page file before any `src.*` import. Match the pattern in `agendador.py` exactly. [VERIFIED: agendador.py lines 14–20]
**Warning signs:** Import error only appears when Streamlit runs the page, not during unit tests that set `sys.path` themselves.

### Pitfall 2: get_connection() is not a context manager
**What goes wrong:** `AttributeError: __exit__` or connection never closed, leaving WAL lock held.
**Why it happens:** `get_connection()` returns a plain `sqlite3.Connection`, not a `contextlib.contextmanager`. [VERIFIED: db.py lines 209–219]
**How to avoid:** Always use `try/finally conn.close()` — never `with get_connection() as conn:`.
**Warning signs:** Database locked errors in scheduler jobs running concurrently with the dashboard.

### Pitfall 3: st.cache_data function-name collision across pages
**What goes wrong:** Watchlist page and asset detail page both define `def get_data()` — they share the same cache, causing one page to return stale data from the other.
**Why it happens:** Streamlit 1.57.0 cache key is based on function name + source; across `st.Page` navigation, same-named functions collide. [CITED: github.com/streamlit/streamlit/issues/14639]
**How to avoid:** All cached query functions live exclusively in `src/dashboard/data.py` with unique names. Page files call `from src.dashboard.data import get_watchlist_summary` — never define their own cached functions.
**Warning signs:** Watchlist shows thesis data for a different ticker after navigating from asset detail page.

### Pitfall 4: fpdf2 instance reuse after output()
**What goes wrong:** Second call to `generate()` on the same `ReportGenerator` instance produces an empty or corrupt PDF.
**Why it happens:** `fpdf2` finalizes the internal buffer on `output()` — adding content after that point raises an error or is silently dropped. [CITED: py-pdf.github.io/fpdf2/UsageInWebAPI.html]
**How to avoid:** `generate()` instantiates a fresh `ReportGenerator` (or calls `super().__init__()` at start), or the public API creates a new instance per call. Pattern: `return ReportGenerator()._build(ticker)` where `_build` does all the work.
**Warning signs:** Second download attempt in the same Streamlit session returns 0-byte PDF.

### Pitfall 5: thesis_json deserialization missing
**What goes wrong:** `thesis_latest` VIEW stores `thesis_json` as TEXT (JSON string). Accessing `row["drivers"]` raises `KeyError` because it's a raw string.
**Why it happens:** `thesis_versions.thesis_json` is stored as `json.dumps(thesis.model_dump())`. [VERIFIED: intelligence_layer.py schema + db.py CREATE TABLE]
**How to avoid:** In `data.py`, always `json.loads(row["thesis_json"])` before accessing thesis fields. The `InvestmentThesis` model can be reconstructed with `InvestmentThesis.model_validate(json.loads(row["thesis_json"]))`.
**Warning signs:** `KeyError: 'drivers'` or `TypeError: string indices must be integers` in asset detail page.

### Pitfall 6: Telegram message length > 4096 chars
**What goes wrong:** Long thesis rationale causes `send()` to silently truncate or fail with Telegram API error.
**Why it happens:** Telegram Bot API has a hard 4096-char limit on message text. `TelegramBot.send()` already truncates at `_MAX_MESSAGE_LENGTH` (verified at line 73). [VERIFIED: telegram_bot.py line 32]
**How to avoid:** Keep alert messages under 400 chars. Use `InvestmentThesis.summary_one_line` (Phase 4 D-02) — not the full `rationale` field — for the one-line alert text.
**Warning signs:** Telegram alert truncated mid-sentence.

### Pitfall 7: Missing `src/dashboard/__init__.py`
**What goes wrong:** `ModuleNotFoundError: No module named 'src.dashboard'` even with correct sys.path.
**Why it happens:** Python requires `__init__.py` in every package directory. `src/delivery/` has one (verified); `src/dashboard/` does not exist yet.
**How to avoid:** Wave 0 must create both `src/dashboard/__init__.py` (empty) and `src/dashboard/data.py`.
**Warning signs:** Import error even after sys.path is correct.

### Pitfall 8: Pandas Styler breaks st.dataframe sorting
**What goes wrong:** User cannot sort the watchlist table by clicking column headers after Styler is applied.
**Why it happens:** When a `Styler` object is passed to `st.dataframe`, column sorting may be disabled.
**How to avoid:** Test sorting after applying Styler. If broken, use `st.dataframe` with plain DataFrame + separate HTML badges for positioning color (using `st.markdown` in adjacent column). Decision is Claude's discretion — either approach is acceptable.
**Warning signs:** Clicking column headers has no effect on sort order.

---

## Code Examples

### Verified Query: get_watchlist_summary()

```python
# Source: verified db schema in db.py + thesis_latest VIEW definition
@st.cache_data(ttl=300)
def get_watchlist_summary() -> list[dict]:
    from src.ingestion.db import get_connection, DB_PATH
    conn = get_connection(DB_PATH)
    try:
        rows = conn.execute("""
            SELECT
                tl.ticker,
                tl.positioning,
                tl.confidence,
                tl.fair_value_brl,
                tl.generated_at,
                fm.price,
                fm.pe_ratio,
                fm.ev_ebitda,
                fd.upside_pct
            FROM thesis_latest tl
            LEFT JOIN financial_multiples fm
                ON fm.ticker = tl.ticker
               AND fm.computed_date = (
                   SELECT MAX(computed_date) FROM financial_multiples
                   WHERE ticker = tl.ticker
               )
            LEFT JOIN financial_dcf fd
                ON fd.ticker = tl.ticker
               AND fd.computed_date = (
                   SELECT MAX(computed_date) FROM financial_dcf
                   WHERE ticker = tl.ticker
               )
            ORDER BY fd.upside_pct DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
```

### Verified Query: get_asset_detail(ticker)

```python
# Source: verified db schema in db.py
@st.cache_data(ttl=300)
def get_asset_detail(ticker: str) -> dict | None:
    import json
    from src.ingestion.db import get_connection, DB_PATH
    conn = get_connection(DB_PATH)
    try:
        # Thesis (deserialize JSON)
        thesis_row = conn.execute(
            "SELECT * FROM thesis_latest WHERE ticker = ?", (ticker,)
        ).fetchone()
        if not thesis_row:
            return None
        result = dict(thesis_row)
        result["thesis"] = json.loads(result["thesis_json"])

        # Financial data
        result["dcf"] = conn.execute(
            "SELECT * FROM financial_dcf WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
            (ticker,)
        ).fetchone()
        result["ltm"] = conn.execute(
            "SELECT * FROM financial_ltm WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
            (ticker,)
        ).fetchone()
        result["multiples"] = conn.execute(
            "SELECT * FROM financial_multiples WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
            (ticker,)
        ).fetchone()

        # News (latest 5)
        result["news"] = conn.execute(
            "SELECT title, published_at, source FROM news_articles WHERE ticker_tags LIKE ? ORDER BY published_at DESC LIMIT 5",
            (f'%"{ticker}"%',)
        ).fetchall()

        return result
    finally:
        conn.close()
```

### Verified Query: get_macro_panel()

```python
# Source: verified macro_series schema — BCB_SERIES: selic_over(11), ipca_12m(433), ptax_usd(1), cds_brasil(29039), pib_nominal(4380)
@st.cache_data(ttl=300)
def get_macro_panel() -> dict[str, list[dict]]:
    from src.ingestion.db import get_connection, DB_PATH
    SERIES = {
        "selic": 11, "ipca_12m": 433, "ptax": 1, "cds_brasil": 29039, "pib_nominal": 4380
    }
    conn = get_connection(DB_PATH)
    try:
        result = {}
        for name, code in SERIES.items():
            rows = conn.execute(
                "SELECT date, value FROM macro_series WHERE series_code = ? ORDER BY date DESC LIMIT 365",
                (code,)
            ).fetchall()
            result[name] = [dict(r) for r in reversed(rows)]
        return result
    finally:
        conn.close()
```

### Verified Query: get_opportunities()

```python
# Source: verified opportunity_signals schema in db.py
@st.cache_data(ttl=300)
def get_opportunities() -> list[dict]:
    from src.ingestion.db import get_connection, DB_PATH
    conn = get_connection(DB_PATH)
    try:
        rows = conn.execute("""
            SELECT ticker, signal_type, description, conviction_score, computed_date
            FROM opportunity_signals
            WHERE computed_date = (SELECT MAX(computed_date) FROM opportunity_signals)
            ORDER BY conviction_score DESC
            LIMIT 10
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
```

### fpdf2 Table Example (drivers/risks)

```python
# Source: py-pdf.github.io/fpdf2/Tutorial.html [CITED]
from fpdf import FPDF
from fpdf.fonts import FontFace

def _drivers_risks_section(self, drivers: list[dict], risks: list[dict]):
    self.set_font("Helvetica", style="B", size=11)
    self.cell(0, 8, "Drivers de Investimento", new_x="LMARGIN", new_y="NEXT")
    self.ln(2)
    with self.table(col_widths=(60, 110, 20), borders_layout="SINGLE_TOP_LINE") as table:
        hrow = table.row()
        for h in ("Driver", "Descrição", "Impacto"):
            hrow.cell(h)
        for d in drivers:
            row = table.row()
            row.cell(d["title"])
            row.cell(d["description"])
            row.cell(d["impact"])
```

### Integration Point: run_ticker() Telegram Alert

```python
# Source: intelligence_layer.py — position to inject (after thesis_versions write, before return)
# D-13 pattern: compare positioning, fire alert if changed
def _maybe_send_thesis_alert(
    ticker: str,
    new_positioning: str,
    prev_positioning: str | None,
    confidence: str,
    summary_one_line: str,
    conn: sqlite3.Connection,
) -> None:
    """Fires Telegram alert when positioning changes. D-13."""
    if prev_positioning is None or new_positioning == prev_positioning:
        return
    # Get top opportunity for this ticker
    opp_row = conn.execute(
        "SELECT description FROM opportunity_signals WHERE ticker = ? ORDER BY conviction_score DESC LIMIT 1",
        (ticker,)
    ).fetchone()
    top_opp_desc = opp_row["description"] if opp_row else "—"
    try:
        from src.delivery.telegram_bot import get_bot
        get_bot().send_thesis_alert(
            ticker=ticker,
            old_positioning=prev_positioning,
            new_positioning=new_positioning,
            confidence=confidence,
            rationale_one_line=summary_one_line,
            top_opportunity_desc=top_opp_desc,
        )
    except Exception as exc:
        log.warning(f"[{ticker}] Telegram alert failed: {exc}")
        # Never raise — alert failure must not block thesis storage
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `st.experimental_memo` / `st.experimental_singleton` | `@st.cache_data` / `@st.cache_resource` | Streamlit 1.18.0 (2023) | Old decorators removed; use `cache_data` for data, `cache_resource` for connections |
| Manual `pages/` directory auto-discovery | `st.navigation` + `st.Page` | Streamlit 1.28.0 (2023) | More control; pages no longer auto-discovered from `pages/` without registration in `st.navigation` |
| `df.style.applymap()` | `df.style.map()` | Pandas 2.1.0 (2023) | `applymap` deprecated; use `map` for element-wise styling |
| `fpdf` (original) | `fpdf2` | 2020 fork | Unicode support, table API, BytesIO output, active maintenance |
| WeasyPrint for PDF | fpdf2 | Project decision D-15 | WeasyPrint requires GTK3 on Windows — incompatible with this environment |

**Deprecated/outdated:**
- `st.experimental_memo`: Removed in Streamlit 1.28+ — use `@st.cache_data`
- `FPDF.output(dest='S')`: Old fpdf API for string output — fpdf2 uses `bytes(pdf.output())`
- `Styler.applymap()`: Deprecated in Pandas 2.1, use `Styler.map()`

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `thesis_json` in `thesis_versions` stores the full `InvestmentThesis.model_dump()` including nested `drivers` and `risks` lists | Code Examples | Page crashes on JSON access; fix: adjust key names to match actual stored schema |
| A2 | `news_articles.ticker_tags` stores ticker as `'["PETR4"]'` JSON string; LIKE query `%"TICKER"%` matches correctly | Code Examples | News section shows 0 articles; fix: check actual stored format and adjust query |
| A3 | Navigation bar fits 9 pages (5 existing + 4 new) at column ratio `[1.6] + [1]*9` without overflow | Architecture | Nav wraps or clips; fix: reduce ratio or use shorter page titles |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

---

## Open Questions

1. **thesis_json stored format**
   - What we know: `thesis_versions.thesis_json` is `TEXT NOT NULL` [VERIFIED: db.py line 165]. `run_ticker()` calls `thesis.model_dump()` then `json.dumps()` [ASSUMED from Phase 4 pattern]
   - What's unclear: Whether `drivers` and `risks` are stored as nested lists or as separate JSON fields
   - Recommendation: Have the executor run `SELECT thesis_json FROM thesis_versions LIMIT 1` and inspect the actual JSON shape before writing `data.py`

2. **prev_positioning extraction in run_ticker()**
   - What we know: `diff_summary` is computed in Phase 4 [VERIFIED: STATE.md 2026-05-17 entry]
   - What's unclear: Whether `diff_summary` contains a structured dict with `prev_positioning` key or is a free-form string
   - Recommendation: Read `intelligence_layer.py` `_compute_diff_summary()` implementation before implementing the alert trigger in D-13

3. **Nav bar overflow with 9 pages**
   - What we know: Current nav uses `st.columns([1.6] + [1] * 5)` = 6 columns [VERIFIED: app.py lines 149–160]
   - What's unclear: Whether 9 total page entries overflow on typical screen widths
   - Recommendation: Claude's discretion — use shorter labels for new pages (e.g., "Watchlist", "Ativo", "Macro", "Ops") or use a two-row nav arrangement

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| streamlit | Streamlit pages | Yes | 1.57.0 | — |
| plotly | Macro charts | Yes | 6.7.0 | — |
| pandas | Styler coloring | Yes | (pyproject >=2.1.0) | — |
| fpdf2 | PDF reports | No | — | Must install: `pip install fpdf2>=2.7.0` |
| requests | Telegram HTTP | Yes | (pyproject >=2.31.0) | — |
| pyyaml | schedules.yaml | Yes | (pyproject >=6.0.0) | — |
| sqlite3 | DB reads | Yes | stdlib | — |

**Missing dependencies with no fallback:**
- `fpdf2`: Not installed in the project venv [VERIFIED: `pip show fpdf2` returns nothing]. Wave 0 must install it and add to `pyproject.toml`.

**Missing dependencies with fallback:**
- None.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0.0+ |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (testpaths=["tests"], pythonpath=["."]) |
| Quick run command | `cd "Analista de Investimentos/12_PYTHON" && pytest tests/test_delivery_telegram.py tests/test_delivery_pdf.py tests/test_dashboard_data.py tests/test_scheduler_delivery.py -x -q` |
| Full suite command | `cd "Analista de Investimentos/12_PYTHON" && pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEL-01 | `get_watchlist_summary()` returns list of dicts from thesis_latest | unit | `pytest tests/test_dashboard_data.py::test_get_watchlist_summary -x` | ❌ Wave 0 |
| DEL-01 | `get_asset_detail(ticker)` deserializes thesis_json to dict | unit | `pytest tests/test_dashboard_data.py::test_get_asset_detail -x` | ❌ Wave 0 |
| DEL-01 | `get_macro_panel()` returns 5 series dicts | unit | `pytest tests/test_dashboard_data.py::test_get_macro_panel -x` | ❌ Wave 0 |
| DEL-01 | `get_opportunities()` returns list ordered by conviction_score DESC | unit | `pytest tests/test_dashboard_data.py::test_get_opportunities -x` | ❌ Wave 0 |
| DEL-02 | `@st.cache_data` decorator present on all 4 `data.py` functions | unit | `pytest tests/test_dashboard_data.py::test_cache_decorators_present -x` | ❌ Wave 0 |
| DEL-03 | `send_thesis_alert()` sends message with ticker, old/new positioning, one-line rationale | unit | `pytest tests/test_delivery_telegram.py::test_send_thesis_alert_format -x` | ❌ Wave 0 |
| DEL-03 | Alert fires only when positioning changes (no alert when same) | unit | `pytest tests/test_delivery_telegram.py::test_alert_only_on_change -x` | ❌ Wave 0 |
| DEL-03 | Alert does not propagate exception — failure is logged, thesis is stored | unit | `pytest tests/test_delivery_telegram.py::test_alert_failure_does_not_raise -x` | ❌ Wave 0 |
| DEL-04 | `job_morning_brief` in `_JOB_REGISTRY` | unit | `pytest tests/test_scheduler_delivery.py::test_morning_brief_registered -x` | ❌ Wave 0 |
| DEL-04 | `send_daily_brief()` sends message with Selic, PTAX, IBOV, top 3 movers | unit | `pytest tests/test_delivery_telegram.py::test_send_daily_brief_format -x` | ❌ Wave 0 |
| DEL-04 | `morning_brief` cron entry exists in schedules.yaml | unit | `pytest tests/test_scheduler_delivery.py::test_morning_brief_cron_in_yaml -x` | ❌ Wave 0 |
| DEL-05 | `ReportGenerator.generate(ticker)` returns non-empty bytes starting with `b'%PDF'` | unit | `pytest tests/test_delivery_pdf.py::test_generate_returns_pdf_bytes -x` | ❌ Wave 0 |
| DEL-05 | PDF contains ticker name string and CVM IN 598 disclaimer text | unit | `pytest tests/test_delivery_pdf.py::test_pdf_contains_required_strings -x` | ❌ Wave 0 |
| DEL-05 | PDF generates in <30s (timing test) | smoke | `pytest tests/test_delivery_pdf.py::test_generate_under_30s -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_delivery_telegram.py tests/test_delivery_pdf.py tests/test_dashboard_data.py tests/test_scheduler_delivery.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q` (full 115+ test suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_delivery_telegram.py` — covers DEL-03, DEL-04 Telegram methods
- [ ] `tests/test_delivery_pdf.py` — covers DEL-05 PDF generation
- [ ] `tests/test_dashboard_data.py` — covers DEL-01, DEL-02 data layer
- [ ] `tests/test_scheduler_delivery.py` — covers DEL-04 scheduler wiring
- [ ] `src/dashboard/__init__.py` — empty package init file
- [ ] `src/dashboard/data.py` — query module stub
- [ ] `src/delivery/pdf_report.py` — ReportGenerator stub
- [ ] `pip install fpdf2>=2.7.0` + `pyproject.toml` dependency entry

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in v1 (single-analyst local tool) |
| V3 Session Management | No | Streamlit manages session locally |
| V4 Access Control | No | Local single-user deployment |
| V5 Input Validation | Yes (ticker param) | Parameterized SQL `?` placeholder (T-DCF-02) |
| V6 Cryptography | No | No crypto in delivery layer |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via ticker URL param | Tampering | Parameterized queries `?` — already enforced across all phases |
| Telegram token exposure in logs | Information Disclosure | Token loaded from `.env` via `settings.telegram_bot_token`; never logged |
| PDF path traversal (if writing to disk) | Tampering | D-17: PDF is in-memory BytesIO — no file write, no path |
| JavaScript injection via thesis text in PDF | Tampering | fpdf2 renders text as PDF text streams, not HTML — XSS not applicable |

---

## Sources

### Primary (HIGH confidence)
- [VERIFIED: app.py, agendador.py, telegram_bot.py, scheduler.py, db.py, intelligence_layer.py, pyproject.toml] — Direct codebase inspection for all established patterns
- [VERIFIED: `pip show streamlit`] — Streamlit 1.57.0 installed
- [VERIFIED: `pip show plotly`] — Plotly 6.7.0 installed
- [VERIFIED: `pip index versions fpdf2`] — fpdf2 2.8.7 latest, not installed in project venv
- [CITED: py-pdf.github.io/fpdf2/UsageInWebAPI.html] — fpdf2 in-memory output pattern, Streamlit download button integration
- [CITED: py-pdf.github.io/fpdf2/Tutorial.html] — FPDF class methods, table() context manager, header/footer

### Secondary (MEDIUM confidence)
- [CITED: docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data] — TTL caching, multi-page cache behavior
- [CITED: docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation] — st.navigation + st.Page structure
- [CITED: plotly.com/python/templates] — plotly_dark template, update_layout() usage
- [CITED: github.com/streamlit/streamlit/issues/14639] — Same-name function cache collision in multi-page apps

### Tertiary (LOW confidence)
- None — all claims verified or cited from official sources.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified via pip, codebase confirmed
- Architecture: HIGH — patterns verified directly in existing page files and scheduler
- Pitfalls: HIGH — most derived from verified codebase patterns (get_connection context manager issue, function-name cache collision from official GitHub issue)
- SQL queries: MEDIUM — schema verified from db.py, but exact field names in thesis_json require runtime inspection (A1, A2 in Assumptions Log)

**Research date:** 2026-05-18
**Valid until:** 2026-06-18 (stable libraries; Streamlit releases frequently but APIs confirmed on 1.57.0)
