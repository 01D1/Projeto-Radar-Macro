# Phase 5: Delivery Layer - Pattern Map

**Mapped:** 2026-05-18
**Files analyzed:** 18 (new/modified)
**Analogs found:** 18 / 18

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `scanner_quant_profit_b3/pages/inteligencia_watchlist.py` | component (Streamlit page) | request-response / CRUD read | `scanner_quant_profit_b3/pages/agendador.py` | role-match (page structure, sys.path, CSS) |
| `scanner_quant_profit_b3/pages/inteligencia_ativo.py` | component (Streamlit page) | request-response / CRUD read | `scanner_quant_profit_b3/pages/agendador.py` | role-match |
| `scanner_quant_profit_b3/pages/inteligencia_macro.py` | component (Streamlit page) | request-response / CRUD read | `scanner_quant_profit_b3/pages/agendador.py` | role-match |
| `scanner_quant_profit_b3/pages/inteligencia_oportunidades.py` | component (Streamlit page) | request-response / CRUD read | `scanner_quant_profit_b3/pages/agendador.py` | role-match |
| `scanner_quant_profit_b3/_style.py` | utility (shared CSS constant) | — | `scanner_quant_profit_b3/app.py` lines 16–135 | exact (CSS extracted verbatim) |
| `scanner_quant_profit_b3/app.py` | config (app entry + nav) | — | `scanner_quant_profit_b3/app.py` (self) | exact (add entries to `_PAGES`) |
| `12_PYTHON/src/dashboard/__init__.py` | config (package init) | — | `12_PYTHON/src/delivery/__init__.py` (implied) | role-match (empty init) |
| `12_PYTHON/src/dashboard/data.py` | service (query layer) | CRUD read | `12_PYTHON/src/scheduler.py` `job_b3_prices()` / `job_bcb_macro()` | role-match (get_connection, try/finally, conn.close) |
| `12_PYTHON/src/delivery/pdf_report.py` | service (PDF generator) | transform / batch | No close analog — use RESEARCH.md fpdf2 patterns | no analog |
| `12_PYTHON/src/delivery/telegram_bot.py` | service (modify) | event-driven | `12_PYTHON/src/delivery/telegram_bot.py` (self) | exact (extend existing methods) |
| `12_PYTHON/src/intelligence_layer.py` | service (modify) | event-driven | `12_PYTHON/src/scheduler.py` `_check_and_alert_risks()` | role-match (post-write alert pattern) |
| `12_PYTHON/src/scheduler.py` | service (modify) | event-driven | `12_PYTHON/src/scheduler.py` `job_intelligence()` | exact (add new job following same pattern) |
| `12_PYTHON/config/schedules.yaml` | config (modify) | — | `12_PYTHON/config/schedules.yaml` (self) | exact (add entry) |
| `12_PYTHON/pyproject.toml` | config (modify) | — | `12_PYTHON/pyproject.toml` (self) | exact (add dependency) |
| `12_PYTHON/tests/test_delivery_telegram.py` | test | — | `12_PYTHON/tests/test_scheduler_intelligence.py` | exact (monkeypatch + assert pattern) |
| `12_PYTHON/tests/test_delivery_pdf.py` | test | — | `12_PYTHON/tests/test_scheduler_intelligence.py` | role-match |
| `12_PYTHON/tests/test_dashboard_data.py` | test | — | `12_PYTHON/tests/test_scheduler_intelligence.py` | role-match |
| `12_PYTHON/tests/test_scheduler_delivery.py` | test | — | `12_PYTHON/tests/test_scheduler_intelligence.py` | exact |

---

## Pattern Assignments

### `scanner_quant_profit_b3/pages/inteligencia_watchlist.py` (component, CRUD read)

**Analog:** `scanner_quant_profit_b3/pages/agendador.py` + `scanner_quant_profit_b3/pages/valuation_engine.py`

**sys.path bootstrap pattern** (`agendador.py` lines 14–16, `valuation_engine.py` lines 5–10):

```python
import sys
from pathlib import Path

# agendador.py uses single ROOT (scanner root only); valuation_engine.py uses the
# two-root pattern that intelligence pages MUST use (needs 12_PYTHON for src.*)
SCANNER_ROOT  = Path(__file__).resolve().parents[1]   # scanner_quant_profit_b3/
PIPELINE_ROOT = SCANNER_ROOT.parent / "12_PYTHON"     # Analista de Investimentos/12_PYTHON/

for _p in (str(PIPELINE_ROOT), str(SCANNER_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Safe to import after path bootstrap
from src.dashboard.data import get_watchlist_summary
```

**CSS injection pattern** (`agendador.py` lines 26–70, 130):

```python
# Each page has its own CSS block OR imports from _style.py (preferred)
# Option A (preferred): import shared constant
from _style import DARK_CSS
st.markdown(DARK_CSS, unsafe_allow_html=True)

# Option B (fallback per page): inline CSS block, exactly as in agendador.py:
_CSS = """
<style>
section.main > div { padding-top: 0.5rem; }
...
</style>
"""
# Called at top of main():
st.markdown(_CSS, unsafe_allow_html=True)
```

**Page entry point pattern** (`agendador.py` lines 129, 279–280):

```python
def main():
    st.markdown(_CSS, unsafe_allow_html=True)
    # ... page content ...

if __name__ == "__main__":
    main()
```

**Empty state pattern** (D-06):

```python
rows = get_watchlist_summary()
if not rows:
    st.info(
        "Nenhuma tese gerada ainda. Execute: "
        "python -m src.main daemon para iniciar o pipeline."
    )
    st.stop()
```

**Watchlist table pattern** (D-07, from RESEARCH.md Pattern 5):

```python
import pandas as pd

POSITIONING_COLORS = {
    "COMPRAR": "background-color: #16a34a; color: white",
    "MANTER":  "background-color: #ca8a04; color: white",
    "VENDER":  "background-color: #dc2626; color: white",
}

def _color_positioning(val: str) -> str:
    return POSITIONING_COLORS.get(val, "")

df = pd.DataFrame(rows)
st.dataframe(
    df.style.map(_color_positioning, subset=["positioning"]),
    use_container_width=True,
    hide_index=True,
)
```

---

### `scanner_quant_profit_b3/pages/inteligencia_ativo.py` (component, CRUD read)

**Analog:** `scanner_quant_profit_b3/pages/agendador.py`

**Same sys.path bootstrap** as watchlist page (identical pattern).

**Ticker selector + asset detail pattern** (D-09):

```python
from src.dashboard.data import get_watchlist_summary, get_asset_detail

tickers = [r["ticker"] for r in get_watchlist_summary()]
ticker = st.selectbox("Ativo", tickers)
detail = get_asset_detail(ticker)

if detail is None:
    st.info(f"Sem tese gerada para {ticker}.")
    st.stop()

thesis = detail["thesis"]   # already json.loads'd in data.py — dict

# Positioning colored metric
col1, col2, col3 = st.columns(3)
col1.metric("Posicionamento", thesis["positioning"])
col2.metric("Fair Value", f"R$ {thesis['fair_value_brl']:,.2f}")
col3.metric("Upside", f"{detail['dcf']['upside_pct']:+.1f}%" if detail.get("dcf") else "—")

# Bull/Bear as markdown
st.markdown(f"**Caso Otimista**\n\n{thesis['bull_case']}")
st.markdown(f"**Caso Pessimista**\n\n{thesis['bear_case']}")

# Drivers as expanders (D-09 card pattern)
for d in thesis.get("drivers", []):
    with st.expander(f"{d['title']} — {d['impact']}"):
        st.write(d["description"])
```

**Expander dark theme** (CSS already in `app.py` lines 81–97 — inherited via global CSS):

```css
details summary {
    background: #111827 !important;
    border: 1px solid #1E2D42 !important;
    border-radius: 8px !important;
    color: #94A3B8 !important;
}
details > div {
    background: #0D1421 !important;
    border: 1px solid #1E2D42 !important;
}
```

---

### `scanner_quant_profit_b3/pages/inteligencia_macro.py` (component, CRUD read)

**Analog:** `scanner_quant_profit_b3/pages/agendador.py`

**Plotly dark chart pattern** (D-11, from RESEARCH.md Pattern 6):

```python
import plotly.graph_objects as go
from src.dashboard.data import get_macro_panel

macro = get_macro_panel()

for name, series in macro.items():
    dates  = [r["date"] for r in series]
    values = [r["value"] for r in series]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=values, mode="lines", name=name))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",    # transparent — blends with dark CSS
        plot_bgcolor="rgba(13,20,33,1)",  # #0D1421 matching app.py details background
        font=dict(color="#94A3B8"),
        margin=dict(l=10, r=10, t=30, b=10),
        height=280,
    )
    st.plotly_chart(fig, use_container_width=True)
```

---

### `scanner_quant_profit_b3/pages/inteligencia_oportunidades.py` (component, CRUD read)

**Analog:** `scanner_quant_profit_b3/pages/agendador.py`

**Signal card with progress bar pattern** (D-10):

```python
from src.dashboard.data import get_opportunities

opps = get_opportunities()
if not opps:
    st.info("Sem sinais de oportunidade gerados hoje.")
    st.stop()

for opp in opps:
    st.markdown(f"**{opp['ticker']}** — `{opp['signal_type']}`")
    st.caption(opp["description"])
    st.progress(opp["conviction_score"] / 100)
    st.markdown("---")
```

---

### `scanner_quant_profit_b3/_style.py` (utility, shared CSS constant)

**Analog:** `scanner_quant_profit_b3/app.py` lines 16–135

**Full CSS block to extract verbatim** (`app.py` lines 17–134):

```python
"""Shared dark theme CSS for scanner_quant_profit_b3 pages."""

DARK_CSS: str = """
<style>
section.main > div { padding-top: 0.2rem; }
[data-testid="stDecoration"] { display: none; }
[data-testid="collapsedControl"] { display: none; }

/* ── page_link nav ── */
[data-testid="stPageLink"] a {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    background: transparent !important;
    border: 1px solid #1E2D42 !important;
    border-radius: 8px !important;
    color: #64748B !important;
    font-weight: 700 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.3px !important;
    padding: 6px 10px !important;
    text-decoration: none !important;
    transition: all 0.15s ease !important;
    width: 100% !important;
}
[data-testid="stPageLink"] a:hover {
    background: #1E2D42 !important;
    color: #93C5FD !important;
    border-color: #2563EB !important;
}
[data-testid="stPageLink"][aria-current="page"] a,
[data-testid="stPageLink"] a[aria-current="page"] {
    background: #0D1F38 !important;
    color: #93C5FD !important;
    border-color: #2563EB !important;
}

/* ── Widgets globais dark ── */
div[data-baseweb="select"] > div {
    background-color: #111827 !important;
    border-color: #1E2D42 !important;
    color: #E2E8F0 !important;
}
div[data-baseweb="input"] > div {
    background-color: #111827 !important;
    border-color: #1E2D42 !important;
}
input { color: #E2E8F0 !important; }
.stTextInput input, .stNumberInput input {
    background: #111827 !important;
    border-color: #1E2D42 !important;
    color: #E2E8F0 !important;
}
.stDateInput input {
    background: #111827 !important;
    border-color: #1E2D42 !important;
    color: #E2E8F0 !important;
}

/* ── Expanders ── */
details summary {
    background: #111827 !important;
    border: 1px solid #1E2D42 !important;
    border-radius: 8px !important;
    color: #94A3B8 !important;
    font-size: 0.82rem !important;
    font-weight: 700 !important;
    padding: 8px 14px !important;
}
details[open] summary { border-radius: 8px 8px 0 0 !important; }
details > div {
    background: #0D1421 !important;
    border: 1px solid #1E2D42 !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
    padding: 12px 14px !important;
}

/* ── Métricas ── */
[data-testid="stMetric"] {
    background: #111827;
    border: 1px solid #1E2D42;
    border-radius: 10px;
    padding: 12px 14px;
}
[data-testid="stMetricLabel"] { color: #475569 !important; font-size: 0.68rem !important; }
[data-testid="stMetricValue"] { color: #F1F5F9 !important; font-size: 1.3rem !important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #0A0E1A; }
::-webkit-scrollbar-thumb { background: #1E2D42; border-radius: 3px; }
</style>
"""
```

---

### `scanner_quant_profit_b3/app.py` (modify: add 4 st.Page entries)

**Analog:** `scanner_quant_profit_b3/app.py` (self) lines 138–167

**Existing navigation pattern** (`app.py` lines 138–167):

```python
_PAGES = [
    st.Page("pages/radar_quant.py",      title="Radar Quant",      icon="🎯"),
    st.Page("pages/valuation_engine.py", title="Valuation Engine", icon="📊"),
    st.Page("pages/performance.py",      title="Performance",      icon="📈"),
    st.Page("pages/calendario.py",       title="Calendário",       icon="📅"),
    st.Page("pages/agendador.py",        title="Agendador",        icon="⏱"),
]

pages = st.navigation(_PAGES, position="hidden")

c_logo, *c_navs = st.columns([1.6] + [1] * len(_PAGES))
```

**Modification: append to `_PAGES` before `st.navigation()` call** (line 147):

```python
_PAGES = [
    # ... existing 5 entries unchanged ...
    # Intelligence pages (Phase 5 — D-01, D-02):
    st.Page("pages/inteligencia_watchlist.py",     title="Watchlist",    icon="🔭"),
    st.Page("pages/inteligencia_ativo.py",         title="Ativo",        icon="🧠"),
    st.Page("pages/inteligencia_macro.py",         title="Macro",        icon="🌐"),
    st.Page("pages/inteligencia_oportunidades.py", title="Opções",       icon="🏆"),
]
# NOTE: column ratio becomes [1.6] + [1] * 9 — test for nav overflow on screen.
# If overflow: reduce logo ratio to 1.0 or shorten page labels further.
```

---

### `12_PYTHON/src/dashboard/__init__.py` (new package init)

**Pattern:** Empty file — matches `src/delivery/__init__.py` convention. No content needed.

---

### `12_PYTHON/src/dashboard/data.py` (service, CRUD read)

**Analog:** `12_PYTHON/src/scheduler.py` `job_b3_prices()` and `job_bcb_macro()` (lines 66–113 and 338–369)

**Module header pattern** (matches `intelligence_layer.py` header convention):

```python
"""
data.py
-------
Dashboard query layer for Phase 5 Delivery.

Fluxo: ingestion.db → cached query functions → Streamlit pages
Uso:
    from src.dashboard.data import get_watchlist_summary, get_asset_detail
"""
from __future__ import annotations

import json
import streamlit as st
from src.ingestion.db import get_connection, DB_PATH
```

**get_connection + try/finally pattern** (`scheduler.py` lines 79–97, `db.py` lines 209–219):

```python
# CRITICAL: get_connection() returns plain sqlite3.Connection — NOT a context manager.
# Always use try/finally conn.close() — never `with get_connection() as conn:`
# Source: db.py lines 209–219 (verified: no __enter__/__exit__)

@st.cache_data(ttl=300)
def get_watchlist_summary() -> list[dict]:
    conn = get_connection(DB_PATH)
    try:
        rows = conn.execute("""
            SELECT
                tl.ticker, tl.positioning, tl.confidence, tl.fair_value_brl,
                tl.generated_at, fm.price, fm.pe_ratio, fm.ev_ebitda, fd.upside_pct
            FROM thesis_latest tl
            LEFT JOIN financial_multiples fm
                ON fm.ticker = tl.ticker
               AND fm.computed_date = (
                   SELECT MAX(computed_date) FROM financial_multiples WHERE ticker = tl.ticker
               )
            LEFT JOIN financial_dcf fd
                ON fd.ticker = tl.ticker
               AND fd.computed_date = (
                   SELECT MAX(computed_date) FROM financial_dcf WHERE ticker = tl.ticker
               )
            ORDER BY fd.upside_pct DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()   # WR-06: always close even on exception
```

**thesis_json deserialization pattern** (Pitfall 5 from RESEARCH.md):

```python
@st.cache_data(ttl=300)
def get_asset_detail(ticker: str) -> dict | None:
    conn = get_connection(DB_PATH)
    try:
        thesis_row = conn.execute(
            "SELECT * FROM thesis_latest WHERE ticker = ?", (ticker,)
        ).fetchone()
        if not thesis_row:
            return None
        result = dict(thesis_row)
        # MANDATORY: deserialize thesis_json before returning — it is stored as TEXT
        result["thesis"] = json.loads(result["thesis_json"])
        result["dcf"] = dict(conn.execute(
            "SELECT * FROM financial_dcf WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
            (ticker,)
        ).fetchone() or {})
        result["ltm"] = dict(conn.execute(
            "SELECT * FROM financial_ltm WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
            (ticker,)
        ).fetchone() or {})
        result["multiples"] = dict(conn.execute(
            "SELECT * FROM financial_multiples WHERE ticker = ? ORDER BY computed_date DESC LIMIT 1",
            (ticker,)
        ).fetchone() or {})
        return result
    finally:
        conn.close()

@st.cache_data(ttl=300)
def get_macro_panel() -> dict[str, list[dict]]:
    SERIES = {"selic": 11, "ipca_12m": 433, "ptax": 1, "cds_brasil": 29039, "pib_nominal": 4380}
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

@st.cache_data(ttl=300)
def get_opportunities() -> list[dict]:
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

**Module-level logger** (matches all `src/` modules):

```python
from src.utils.logger import get_logger
log = get_logger(__name__)   # always `log`, never `logger`
```

---

### `12_PYTHON/src/delivery/telegram_bot.py` (modify: add 2 methods)

**Analog:** `12_PYTHON/src/delivery/telegram_bot.py` (self) — extend `TelegramBot` class

**Existing method signature pattern** (`telegram_bot.py` lines 126–142, `send_risk_alert`):

```python
def send_risk_alert(
    self,
    ticker: str,
    severity: str,
    risks: list[str],
) -> bool:
    """Envia alerta de risco para um ticker."""
    icons = {"low": "ℹ️", "medium": "⚠️", "high": "🔴", "critical": "🚨"}
    icon = icons.get(severity, "⚠️")
    lines = [
        f"{icon} *Alerta de Risco — {ticker}*",
        f"Severidade: `{severity.upper()}`",
        "",
    ]
    for r in risks[:5]:
        lines.append(f"• {r}")
    return self.send("\n".join(lines))
```

**New methods to add** (after `send_weekly_review`, before `_post`):

```python
def send_thesis_alert(
    self,
    ticker: str,
    old_positioning: str,
    new_positioning: str,
    confidence: str,
    rationale_one_line: str,
    top_opportunity_desc: str,
) -> bool:
    """Envia alerta quando tese muda de posicionamento — DEL-03 / D-12."""
    text = (
        f"🔔 *{ticker}* — Tese atualizada\n"
        f"Posicionamento: {old_positioning} → *{new_positioning}*\n"
        f"Confiança: {confidence}\n"
        f"{rationale_one_line}\n"
        f"Top oportunidade: {top_opportunity_desc}"
    )
    return self.send(text)   # self.send() handles truncation at 4096 chars

def send_daily_brief(
    self,
    macro_snapshot: dict,
    top_movers: list[dict],
    top_opportunity: dict | None,
) -> bool:
    """Envia resumo diário de mercado — DEL-04 / D-12."""
    from datetime import date
    date_str = date.today().strftime("%d/%m/%Y")
    lines = [
        f"📊 *Resumo de Mercado — {date_str}*",
        f"Selic: {macro_snapshot['selic']:.2f}% | "
        f"PTAX: R${macro_snapshot['ptax']:.4f} | "
        f"IBOV: {macro_snapshot.get('ibov_pct', 0.0):+.1f}%",
        "",
        "🏆 *Top Oportunidades*",
    ]
    for i, m in enumerate(top_movers[:3], 1):
        lines.append(f"{i}. {m['ticker']}: {m['description']} (score: {m['score']})")
    return self.send("\n".join(lines))
```

**Truncation guard** (`telegram_bot.py` line 32, line 73–74):

```python
_MAX_MESSAGE_LENGTH = 4096   # hard Telegram limit — self.send() already truncates
# Keep thesis_alert < 400 chars: use summary_one_line (Phase 4 D-02), not full rationale
```

---

### `12_PYTHON/src/intelligence_layer.py` (modify: add positioning-change alert trigger)

**Analog:** `12_PYTHON/src/scheduler.py` `_check_and_alert_risks()` lines 559–581

**Alert injection point in `run_ticker()`** (after line 705 `conn.commit()`, before step 9 signals):

```python
# ── 8b. Positioning-change Telegram alert (D-13) ─────────────────────────
# Reads prev positioning from diff_summary or re-parses prior_json
# prior_json already fetched at line 676 — compare with new thesis
_prev_positioning: str | None = None
if prior_json:
    try:
        _prev_positioning = json.loads(prior_json).get("positioning")
    except (json.JSONDecodeError, TypeError):
        pass
_maybe_send_thesis_alert(
    ticker=ticker,
    new_positioning=thesis.positioning,
    prev_positioning=_prev_positioning,
    confidence=thesis.confidence,
    summary_one_line=thesis.summary_one_line,  # Phase 4 D-02 field
    conn=conn,
)
```

**Helper function pattern** (mirrors `_check_and_alert_risks()` isolation approach):

```python
def _maybe_send_thesis_alert(
    ticker: str,
    new_positioning: str,
    prev_positioning: str | None,
    confidence: str,
    summary_one_line: str,
    conn: sqlite3.Connection,
) -> None:
    """Fires Telegram alert when positioning changes. D-13.
    Never raises — alert failure must not block thesis storage.
    """
    if prev_positioning is None or new_positioning == prev_positioning:
        return
    opp_row = conn.execute(
        "SELECT description FROM opportunity_signals WHERE ticker = ? "
        "ORDER BY conviction_score DESC LIMIT 1",
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
        # Never re-raise — alert failure must not block thesis storage
```

---

### `12_PYTHON/src/scheduler.py` (modify: add `job_morning_brief()`)

**Analog:** `12_PYTHON/src/scheduler.py` `job_intelligence()` lines 427–454

**New job function pattern** (copy structure of `job_intelligence()` exactly):

```python
def job_morning_brief() -> str:
    """Envia resumo diário de mercado via Telegram — DEL-04 / D-14."""
    from src.delivery.telegram_bot import get_bot
    from src.ingestion.db import get_connection, DB_PATH
    from src.utils.logger import bind_run_id, get_logger as _get
    import time

    _log = _get(__name__)
    with bind_run_id("delivery") as run_id:
        _log.info(f"[morning_brief] iniciado — run_id={run_id}")
        t0 = time.time()
        conn = get_connection(DB_PATH)
        try:
            # Read macro snapshot (latest Selic + PTAX)
            macro_snapshot = {}
            selic_row = conn.execute(
                "SELECT value FROM macro_series WHERE series_code = 11 ORDER BY date DESC LIMIT 1"
            ).fetchone()
            macro_snapshot["selic"] = selic_row["value"] if selic_row else 0.0
            ptax_row = conn.execute(
                "SELECT value FROM macro_series WHERE series_code = 1 ORDER BY date DESC LIMIT 1"
            ).fetchone()
            macro_snapshot["ptax"] = ptax_row["value"] if ptax_row else 0.0
            # IBOV % change via b3_prices (IBOV ticker if tracked, else 0.0)
            macro_snapshot["ibov_pct"] = 0.0  # fallback — may not be in watchlist

            # Top 3 movers by upside_pct change
            top_rows = conn.execute("""
                SELECT ticker, upside_pct FROM financial_dcf
                WHERE computed_date = (SELECT MAX(computed_date) FROM financial_dcf)
                ORDER BY upside_pct DESC LIMIT 3
            """).fetchall()
            top_movers = [
                {"ticker": r["ticker"], "description": f"upside {r['upside_pct']:+.1f}%",
                 "score": "-"}
                for r in top_rows
            ]

            # Top opportunity
            opp_row = conn.execute(
                "SELECT * FROM opportunity_signals WHERE computed_date = "
                "(SELECT MAX(computed_date) FROM opportunity_signals) "
                "ORDER BY conviction_score DESC LIMIT 1"
            ).fetchone()
            top_opportunity = dict(opp_row) if opp_row else None
        finally:
            conn.close()  # WR-06: always close connection even on exception

        duration_ms = int((time.time() - t0) * 1000)
        _log.info(
            "[morning_brief] summary",
            source="morning_brief",
            records_inserted=0,
            records_updated=0,
            duration_ms=duration_ms,
            status="ok",
        )
        get_bot().send_daily_brief(macro_snapshot, top_movers, top_opportunity)
        return "morning_brief: sent"
```

**Registry entry** (`scheduler.py` lines 488–503 pattern):

```python
_JOB_REGISTRY: dict[str, Callable] = {
    # ... existing entries ...
    "morning_brief": job_morning_brief,   # DEL-04
}
```

---

### `12_PYTHON/config/schedules.yaml` (modify: add morning_brief cron)

**Analog:** `schedules.yaml` (self) — existing `bcb_macro` entry at 08:00 is a conflict.

**Note:** `bcb_macro` already uses `0 8 * * 1-5`. Morning brief should run at `0 8 * * 1-5` too — order in YAML determines registration order; APScheduler runs both. No conflict in execution, but brief should fire after bcb_macro completes. Consider `15 8 * * 1-5` to stagger:

```yaml
  - job: morning_brief
    cron: "15 8 * * 1-5"     # seg–sex 08:15 — após bcb_macro (08:00)
    description: Resumo diário de mercado via Telegram
```

---

### `12_PYTHON/pyproject.toml` (modify: add fpdf2 dependency)

**Analog:** `pyproject.toml` (self) lines 11–54

**Pattern for adding to `[project.dependencies]`** (after line 50 `pyyaml`):

```toml
[project.dependencies]
    # ... existing entries ...
    # Delivery — PDF reports (Phase 5 D-15)
    "fpdf2>=2.7.0",
```

**Note:** `python-telegram-bot>=21.0.0` is already listed (line 47) but `TelegramBot` uses raw `requests` (not `python-telegram-bot` SDK). No change needed to Telegram dependency.

---

### `12_PYTHON/tests/test_delivery_telegram.py` (new tests)

**Analog:** `12_PYTHON/tests/test_scheduler_intelligence.py` (full file — exact pattern)

**Module header pattern** (`test_scheduler_intelligence.py` lines 1–18):

```python
"""
test_delivery_telegram.py
--------------------------
Phase 5 — Telegram delivery tests covering DEL-03, DEL-04.

Covers:
  - send_thesis_alert() sends message with ticker, old/new positioning, rationale
  - Alert fires only when positioning changes
  - Alert failure does not raise (does not block thesis storage)
  - send_daily_brief() sends message with Selic, PTAX, top 3 movers
"""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest
```

**monkeypatch on `send()` pattern** (D-18, mirrors `test_scheduler_intelligence.py` lines 28–53):

```python
def test_send_thesis_alert_format(monkeypatch):
    """DEL-03: send_thesis_alert() sends text containing ticker and new positioning."""
    sent_texts = []

    def mock_send(self, text, **kwargs):
        sent_texts.append(text)
        return True

    monkeypatch.setattr("src.delivery.telegram_bot.TelegramBot.send", mock_send)

    from src.delivery.telegram_bot import TelegramBot
    bot = TelegramBot(token="fake", chat_id="123")
    result = bot.send_thesis_alert(
        ticker="PETR4",
        old_positioning="MANTER",
        new_positioning="COMPRAR",
        confidence="ALTA",
        rationale_one_line="DCF sugere forte desconto ao preço atual.",
        top_opportunity_desc="DCF_DIVERGENCE — upside 35%",
    )

    assert result is True
    assert len(sent_texts) == 1
    assert "PETR4" in sent_texts[0]
    assert "COMPRAR" in sent_texts[0]
    assert "MANTER" in sent_texts[0]
```

**Alert-only-on-change pattern** (D-18):

```python
def test_alert_failure_does_not_raise(monkeypatch):
    """DEL-03: _maybe_send_thesis_alert() never raises even if bot.send() fails."""
    monkeypatch.setattr(
        "src.delivery.telegram_bot.TelegramBot.send",
        lambda self, *a, **k: (_ for _ in ()).throw(RuntimeError("network error")),
    )
    from src.intelligence_layer import _maybe_send_thesis_alert
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE opportunity_signals (ticker TEXT, description TEXT, conviction_score INT, computed_date TEXT)")
    # Must not raise
    _maybe_send_thesis_alert("PETR4", "COMPRAR", "MANTER", "ALTA", "one line", conn)
    conn.close()
```

---

### `12_PYTHON/tests/test_delivery_pdf.py` (new tests)

**Analog:** `12_PYTHON/tests/test_scheduler_intelligence.py` (structure only)

**PDF bytes assertion pattern** (D-19):

```python
"""
test_delivery_pdf.py
--------------------
Phase 5 — PDF generation tests covering DEL-05.

Covers:
  - generate() returns non-empty bytes starting with b'%PDF'
  - PDF contains ticker name and CVM IN 598 disclaimer text
  - generate() completes under 30s
"""
from __future__ import annotations
import time
import pytest

def test_generate_returns_pdf_bytes():
    """DEL-05: ReportGenerator.generate() returns bytes starting with b'%PDF'."""
    from src.delivery.pdf_report import ReportGenerator
    rg = ReportGenerator()
    # Use minimal fixture dict — PDF must not require live DB
    pdf_bytes = rg.generate_from_fixture("PETR4")   # or generate() with mocked DB
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes[:4] == b"%PDF"

def test_pdf_contains_required_strings():
    """DEL-05: PDF contains ticker and CVM IN 598 disclaimer."""
    import io
    from src.delivery.pdf_report import ReportGenerator
    pdf_bytes = ReportGenerator().generate_from_fixture("PETR4")
    # fpdf2 text is embedded as streams; basic string search works for Latin chars
    pdf_text = pdf_bytes.decode("latin-1", errors="replace")
    assert "PETR4" in pdf_text
    assert "CVM" in pdf_text   # CVM IN 598 disclaimer always present

def test_generate_under_30s():
    """DEL-05: PDF generation completes under 30 seconds."""
    from src.delivery.pdf_report import ReportGenerator
    t0 = time.time()
    ReportGenerator().generate_from_fixture("PETR4")
    assert time.time() - t0 < 30
```

---

### `12_PYTHON/tests/test_dashboard_data.py` (new tests)

**Analog:** `12_PYTHON/tests/test_intelligence_layer.py` (in-memory SQLite fixture pattern, lines 34–116)

**In-memory DB fixture pattern** (matches `test_intelligence_layer.py` `make_db()` approach):

```python
"""
test_dashboard_data.py
-----------------------
Phase 5 — Dashboard data layer tests covering DEL-01, DEL-02.
"""
from __future__ import annotations
import json
import sqlite3
import pytest

@pytest.fixture
def mem_db(monkeypatch, tmp_path):
    """In-memory ingestion.db with minimal schema and test data."""
    import src.dashboard.data as data_module
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS thesis_versions (
            id TEXT PRIMARY KEY, ticker TEXT NOT NULL, version_num INTEGER,
            generated_at TEXT, input_hash TEXT, positioning TEXT, confidence TEXT,
            fair_value_brl REAL, dcf_deviation_flag INTEGER, thesis_json TEXT, diff_summary TEXT
        );
        CREATE VIEW IF NOT EXISTS thesis_latest AS
            SELECT * FROM thesis_versions WHERE version_num = (
                SELECT MAX(version_num) FROM thesis_versions tv2 WHERE tv2.ticker = thesis_versions.ticker
            );
        CREATE TABLE IF NOT EXISTS opportunity_signals (
            id TEXT PRIMARY KEY, ticker TEXT, signal_type TEXT,
            description TEXT, conviction_score INTEGER, computed_date TEXT
        );
        CREATE TABLE IF NOT EXISTS macro_series (
            id TEXT PRIMARY KEY, series_code INTEGER, series_name TEXT,
            date TEXT, value REAL, ingested_at TEXT
        );
        CREATE TABLE IF NOT EXISTS financial_dcf (
            id TEXT PRIMARY KEY, ticker TEXT, computed_date TEXT,
            fair_value_brl REAL, upside_pct REAL
        );
        CREATE TABLE IF NOT EXISTS financial_multiples (
            id TEXT PRIMARY KEY, ticker TEXT, computed_date TEXT,
            price REAL, pe_ratio REAL, ev_ebitda REAL
        );
    """)
    # Seed test data
    thesis_json = json.dumps({"bull_case": "test", "bear_case": "test",
                               "drivers": [], "risks": [], "positioning": "COMPRAR",
                               "confidence": "ALTA", "fair_value_brl": 40.0,
                               "rationale": "r", "summary_one_line": "s",
                               "methodology_disclosure": "DCF"})
    conn.execute(
        "INSERT INTO thesis_versions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        ("id1","PETR4",1,"2026-05-18","hash1","COMPRAR","ALTA",40.0,0,thesis_json,None)
    )
    conn.execute(
        "INSERT INTO opportunity_signals VALUES (?,?,?,?,?,?)",
        ("sig1","PETR4","DCF_DIVERGENCE","Teste",85,"2026-05-18")
    )
    conn.execute(
        "INSERT INTO macro_series VALUES (?,?,?,?,?,?)",
        ("m1",11,"Selic","2026-05-18",14.75,"2026-05-18")
    )
    conn.commit()
    conn.close()
    # Patch DB_PATH in data module
    monkeypatch.setattr("src.dashboard.data.DB_PATH", db_path)
    monkeypatch.setattr("src.ingestion.db.DB_PATH", db_path)
    return db_path

def test_get_watchlist_summary(mem_db):
    """DEL-01: get_watchlist_summary() returns list of dicts from thesis_latest."""
    from src.dashboard.data import get_watchlist_summary
    get_watchlist_summary.clear()   # clear Streamlit cache between tests
    rows = get_watchlist_summary()
    assert isinstance(rows, list)
    assert rows[0]["ticker"] == "PETR4"

def test_cache_decorators_present():
    """DEL-02: @st.cache_data decorator present on all 4 data.py functions."""
    import src.dashboard.data as m
    for fn_name in ("get_watchlist_summary", "get_asset_detail",
                    "get_macro_panel", "get_opportunities"):
        fn = getattr(m, fn_name)
        # st.cache_data wraps function — check __wrapped__ or cache-specific attr
        assert hasattr(fn, "__wrapped__") or hasattr(fn, "clear"), (
            f"{fn_name} missing @st.cache_data decorator"
        )
```

---

### `12_PYTHON/tests/test_scheduler_delivery.py` (new tests)

**Analog:** `12_PYTHON/tests/test_scheduler_intelligence.py` (exact pattern)

**Registry + cron entry pattern** (copy of `test_scheduler_intelligence.py` lines 19–25 and structure):

```python
"""
test_scheduler_delivery.py
---------------------------
Phase 5 — Scheduler delivery tests covering DEL-04.

Covers:
  - job_morning_brief registered in _JOB_REGISTRY under key 'morning_brief'
  - morning_brief cron entry exists in schedules.yaml
  - job_morning_brief() calls send_daily_brief() and returns 'morning_brief: sent'
"""
from __future__ import annotations
from contextlib import contextmanager
from unittest.mock import MagicMock
import pytest


def test_morning_brief_registered():
    """DEL-04: job_morning_brief is registered in _JOB_REGISTRY."""
    from src.scheduler import _JOB_REGISTRY
    assert "morning_brief" in _JOB_REGISTRY, (
        f"'morning_brief' not in _JOB_REGISTRY. Keys: {list(_JOB_REGISTRY.keys())}"
    )


def test_morning_brief_cron_in_yaml():
    """DEL-04: morning_brief cron entry exists in schedules.yaml."""
    import yaml
    from pathlib import Path
    path = Path(__file__).parent.parent / "config" / "schedules.yaml"
    data = yaml.safe_load(path.read_text())
    jobs = [e["job"] for e in data.get("schedules", [])]
    assert "morning_brief" in jobs, f"'morning_brief' not in schedules.yaml. Found: {jobs}"


def test_morning_brief_calls_send_daily_brief(monkeypatch):
    """DEL-04: job_morning_brief() calls get_bot().send_daily_brief()."""
    called = []
    mock_bot = MagicMock()
    mock_bot.send_daily_brief = lambda *a, **k: called.append(1) or True

    @contextmanager
    def mock_bind(prefix):
        yield f"{prefix}-test"

    monkeypatch.setattr("src.delivery.telegram_bot.get_bot", lambda: mock_bot)
    monkeypatch.setattr("src.utils.logger.bind_run_id", mock_bind)

    # Patch get_connection to return in-memory DB
    import sqlite3
    mock_conn = sqlite3.connect(":memory:")
    mock_conn.row_factory = sqlite3.Row
    mock_conn.executescript("""
        CREATE TABLE macro_series (id TEXT, series_code INT, series_name TEXT,
                                   date TEXT, value REAL, ingested_at TEXT);
        CREATE TABLE financial_dcf (id TEXT, ticker TEXT, computed_date TEXT,
                                    fair_value_brl REAL, upside_pct REAL);
        CREATE TABLE opportunity_signals (id TEXT, ticker TEXT, signal_type TEXT,
                                          description TEXT, conviction_score INT,
                                          computed_date TEXT);
    """)
    monkeypatch.setattr("src.ingestion.db.get_connection", lambda *a, **k: mock_conn)

    from src.scheduler import job_morning_brief
    result = job_morning_brief()
    assert "morning_brief" in result
    assert len(called) == 1
```

---

## Shared Patterns

### Pattern A: Module-Level Logger

**Source:** `12_PYTHON/src/delivery/telegram_bot.py` line 30, `12_PYTHON/src/intelligence_layer.py` line 42
**Apply to:** All new `src/` Python modules (`data.py`, `pdf_report.py`)

```python
from src.utils.logger import get_logger
log = get_logger(__name__)   # always `log`, never `logger`
```

### Pattern B: get_connection try/finally

**Source:** `12_PYTHON/src/scheduler.py` lines 79–97 (`job_b3_prices`)
**Apply to:** `src/dashboard/data.py` all 4 query functions, `scheduler.py` `job_morning_brief()`

```python
conn = get_connection(DB_PATH)
try:
    # ... query work ...
finally:
    conn.close()  # WR-06: always close connection even on exception
```

**CRITICAL:** Never use `with get_connection() as conn:` — `get_connection()` is NOT a context manager (`db.py` lines 209–219).

### Pattern C: Parameterized SQL (no f-strings with ticker)

**Source:** `12_PYTHON/src/scheduler.py` lines 301–310, throughout intelligence_layer.py
**Apply to:** All `data.py` queries, `scheduler.py` `job_morning_brief()`

```python
# CORRECT — T-DCF-02 rule
conn.execute("SELECT * FROM table WHERE ticker = ?", (ticker,))
# WRONG — never do this
conn.execute(f"SELECT * FROM table WHERE ticker = '{ticker}'")
```

### Pattern D: sys.path Bootstrap for Streamlit Pages

**Source:** `scanner_quant_profit_b3/pages/valuation_engine.py` lines 5–10
**Apply to:** All 4 new `inteligencia_*.py` pages

```python
import sys
from pathlib import Path

SCANNER_ROOT  = Path(__file__).resolve().parents[1]   # scanner_quant_profit_b3/
PIPELINE_ROOT = SCANNER_ROOT.parent / "12_PYTHON"     # Analista de Investimentos/12_PYTHON/

for _p in (str(PIPELINE_ROOT), str(SCANNER_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
```

### Pattern E: bind_run_id in Scheduler Jobs

**Source:** `12_PYTHON/src/scheduler.py` `job_intelligence()` lines 435–437
**Apply to:** `job_morning_brief()`

```python
with bind_run_id("delivery") as run_id:
    _log.info(f"[morning_brief] iniciado — run_id={run_id}")
```

### Pattern F: D-15 Structured Summary Log

**Source:** `12_PYTHON/src/scheduler.py` `job_b3_prices()` lines 101–112
**Apply to:** `job_morning_brief()` — emit at end with `source="morning_brief"`

```python
_log.info(
    "[morning_brief] summary",
    source="morning_brief",
    records_inserted=0,
    records_updated=0,
    duration_ms=duration_ms,
    status="ok",
    last_ingested_at=datetime.now(timezone.utc).isoformat(),
)
```

### Pattern G: Alert Never Raises

**Source:** `12_PYTHON/src/scheduler.py` `_check_and_alert_risks()` lines 559–581 (bare `except: pass`)
**Apply to:** `_maybe_send_thesis_alert()` in `intelligence_layer.py`

```python
try:
    get_bot().send_thesis_alert(...)
except Exception as exc:
    log.warning(f"[{ticker}] Telegram alert failed: {exc}")
    # Never re-raise — alert failure must not block thesis storage
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `12_PYTHON/src/delivery/pdf_report.py` | service | transform | No PDF generation code exists anywhere in the codebase. Use RESEARCH.md Pattern 7 (fpdf2 FPDF subclass) and the fpdf2 table() context manager API. |

**Guidance for `pdf_report.py`:** Follow RESEARCH.md Pattern 7 exactly. Key points:
- Subclass `FPDF` for `header()` / `footer()` overrides
- `generate()` must instantiate a fresh `ReportGenerator()` (or call `super().__init__()`) before each call — never reuse after `output()`
- Return `bytes(self.output())` — NOT `self.output(dest='S')` (old fpdf API)
- `_disclaimer()` must always be the last section added before `output()`
- CVM IN 598 disclaimer: standard text — "Este relatório foi elaborado exclusivamente para fins informativos e não constitui oferta, solicitação, recomendação de compra ou venda de valores mobiliários. Elaborado em conformidade com a Instrução CVM nº 598."

---

## Metadata

**Analog search scope:** `scanner_quant_profit_b3/pages/`, `12_PYTHON/src/`, `12_PYTHON/tests/`, `12_PYTHON/config/`
**Files scanned:** 12 source files read in full
**Pattern extraction date:** 2026-05-18

**Key warnings for planner:**
1. `get_connection()` at `db.py:209` is NOT a context manager — all callers must use `try/finally conn.close()`. This is the #1 pitfall.
2. `@st.cache_data` function names must be unique across ALL pages — keep all cached functions in `data.py` exclusively. Never define cached functions inline in page files.
3. The `_PAGES` nav expansion from 5 to 9 entries changes the column ratio line `app.py:149` — test for overflow.
4. `thesis_json` in `thesis_versions` is raw JSON TEXT — always call `json.loads()` before accessing `.drivers`, `.risks` etc. in `data.py:get_asset_detail()`.
5. `fpdf2` is NOT installed — Wave 0 must `pip install fpdf2>=2.7.0` and add to `pyproject.toml` before any `pdf_report.py` implementation.
6. `bcb_macro` already uses cron `0 8 * * 1-5` — stagger `morning_brief` to `15 8 * * 1-5` to avoid simultaneous DB reads.
