# Phase 5: Delivery Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-18
**Phase:** 5-Delivery Layer
**Areas discussed:** Streamlit app structure, Telegram alert architecture, PDF generation library, Dashboard data access layer, Macro panel charts, PDF download in Streamlit, Dashboard launch, Testing strategy for delivery

---

## Streamlit App Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Add pages to scanner_quant_profit_b3 | Reuse dark theme, nav, existing patterns | ✓ |
| New standalone app under src/dashboard/ | Separate app, isolated | |
| New app importing scanner_quant design system | Isolated with design consistency | |

**User's choice:** Add pages to scanner_quant_profit_b3
**Notes:** User clarified the Streamlit app is in `scanner_quant_profit_b3/`, not `pipeline banco completo/`. App has dark theme CSS, `st.page_link` horizontal nav, and 5 existing pages.

---

## Pages Layout

| Option | Description | Selected |
|--------|-------------|----------|
| Separate section — 4 new pages alongside existing 5 | `inteligencia_` prefix, 9 total pages | ✓ |
| Merge/replace existing pages where overlap | Smaller nav, requires refactoring | |
| You decide | Claude picks grouping | |

**User's choice:** Separate section with `inteligencia_` prefix

---

## Caching Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| @st.cache_data(ttl=300) per query function | 5-minute TTL | ✓ |
| @st.cache_data(ttl=900) | 15-minute TTL | |
| You decide | Claude picks | |

**User's choice:** @st.cache_data(ttl=300)

---

## Thesis Display (Asset Detail)

| Option | Description | Selected |
|--------|-------------|----------|
| Structured sections — expandable cards per Driver/Risk | Matches Phase 4 D-01 design | ✓ |
| Single prose block | Simpler, less scannable | |
| You decide | Claude picks | |

**User's choice:** Expandable cards per Driver/Risk

---

## Watchlist Layout

| Option | Description | Selected |
|--------|-------------|----------|
| st.dataframe with colored positioning column | Sortable, fast render | ✓ |
| Card grid — one card per ticker | More visual, slower | |
| You decide | Claude picks | |

**User's choice:** st.dataframe with colored positioning column

---

## Opportunities Page

| Option | Description | Selected |
|--------|-------------|----------|
| Signal cards with conviction score bar | Top 10 ranked | ✓ |
| Simple sorted table | Consistent with watchlist | |
| You decide | Claude picks | |

**User's choice:** Signal cards with conviction score progress bar

---

## Telegram Client

| Option | Description | Selected |
|--------|-------------|----------|
| Extend existing TelegramBot in src/delivery/telegram_bot.py | No new deps, already wired | ✓ |
| Use python-telegram-bot SDK | More featureful, more complex | |
| You decide | Claude picks | |

**User's choice:** Extend existing TelegramBot

---

## Alert Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Inside job_intelligence() after each thesis write | Immediate, uses diff_summary | ✓ |
| Separate job_telegram_alerts() | Batch scan after intelligence run | |
| You decide | Claude picks | |

**User's choice:** Inside job_intelligence() — compare positioning after write

---

## Daily Brief Schedule

| Option | Description | Selected |
|--------|-------------|----------|
| New job_morning_brief() at configurable time, default 08:00 | Separate from morning_call | ✓ |
| Extend existing job_morning_call() | Simpler, conflates output types | |
| You decide | Claude picks | |

**User's choice:** New job_morning_brief() at 08:00 Mon–Fri

---

## PDF Generation Library

| Option | Description | Selected |
|--------|-------------|----------|
| WeasyPrint | HTML+CSS → PDF, best quality, Windows deps | |
| fpdf2 | Pure Python, no system deps | ✓ |
| xhtml2pdf | HTML → PDF, lighter deps | |

**User's choice:** fpdf2 — avoid GTK3/libpango system dependencies on Windows

---

## PDF Template

| Option | Description | Selected |
|--------|-------------|----------|
| FPDF2 class with method per section | Testable, consistent layout | ✓ |
| Jinja2 → fpdf2 text rendering | Template files but adds parse step | |
| You decide | Claude picks | |

**User's choice:** ReportGenerator class with _header(), _thesis_section(), etc.

---

## PDF Location

| Option | Description | Selected |
|--------|-------------|----------|
| src/delivery/pdf_report.py | Fits delivery layer | ✓ |
| src/reports/pdf_report.py | New reports module | |

**User's choice:** src/delivery/pdf_report.py

---

## Dashboard Data Access

| Option | Description | Selected |
|--------|-------------|----------|
| Thin query module src/dashboard/data.py | Testable, caching centralized | ✓ |
| Direct sqlite3 + pandas in each page | Simple, duplicates DB logic | |
| You decide | Claude picks | |

**User's choice:** src/dashboard/data.py with one function per data need

---

## DB Path Resolution

| Option | Description | Selected |
|--------|-------------|----------|
| Import DB_PATH from src.ingestion.db | Single source of truth | ✓ |
| Configure via .env DASHBOARD_DB_PATH | Flexible but complex | |

**User's choice:** Import DB_PATH from src.ingestion.db

---

## Empty State

| Option | Description | Selected |
|--------|-------------|----------|
| st.info() with actionable instruction | Friendly, actionable | ✓ |
| Empty tables/charts | Could confuse users | |
| You decide | Claude picks | |

**User's choice:** st.info() banner: "Nenhuma tese gerada ainda. Execute: python -m src.main daemon para iniciar o pipeline."

---

## Macro Panel Charts

| Option | Description | Selected |
|--------|-------------|----------|
| Plotly line charts via st.plotly_chart | Consistent with scanner_quant | ✓ |
| st.line_chart native | Simpler, less customizable | |
| You decide | Claude picks | |

**User's choice:** Plotly line charts

---

## PDF Download

| Option | Description | Selected |
|--------|-------------|----------|
| In-memory BytesIO → st.download_button | No temp files | ✓ |
| Temp file generate/serve/clean | More overhead | |
| You decide | Claude picks | |

**User's choice:** In-memory BytesIO

---

## Dashboard Launch

| Option | Description | Selected |
|--------|-------------|----------|
| Same command, pages auto-discovered | No changes needed | ✓ |
| Add dashboard command to src/main.py CLI | Integrated CLI but adds coupling | |
| You decide | Claude picks | |

**User's choice:** Same streamlit run command, new pages auto-discovered

---

## Testing Strategy for Delivery

| Option | Description | Selected |
|--------|-------------|----------|
| Patch TelegramBot.send() and assert payload content | Mock-based, asserts content | ✓ |
| Silent mode integration test | Verifies no exception, no content check | |
| You decide | Claude picks | |

**User's choice:** monkeypatch TelegramBot.send() and assert message content

---

## Claude's Discretion

- Navigation ordering of 4 new intelligence pages within `st.page_link` nav
- Exact Plotly chart styling — match scanner_quant dark theme
- CVM IN 598 disclaimer exact wording
- Column selection and ordering for watchlist `st.dataframe`
- fpdf2 font choice and page margins

## Deferred Ideas

- Mobile-optimized view for scanner_quant
- PDF batch export (all tickers at once)
- Telegram command handlers (interactive bot)
- Email delivery
- Real-time dashboard updates (WebSocket/SSE)
- Supabase cloud deployment
