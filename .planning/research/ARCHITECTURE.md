# Architecture Research — Investment Intelligence Platform

## Recommended Architecture Pattern

**Layered pipeline with event-triggered intelligence** — not microservices, not monolith.

Each layer is a clean Python module with defined inputs and outputs. Data flows downward (ingestion → processing → intelligence → delivery). Events (earnings, fatos relevantes) can trigger partial pipeline reruns starting at any layer. This is the right pattern because:
- Single-analyst tool: microservices add ops overhead with no benefit
- Financial data is batch-oriented (daily, quarterly) not real-time streaming
- Intelligence layer (LLM) is expensive — it should only run when data changes
- Streamlit dashboard reads from SQLite, not from live pipeline runs

---

## Component Map

```
┌─────────────────────────────────────────────────────────────────┐
│                     INGESTION LAYER                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────┐ ┌──────────┐  │
│  │  CVM Loader  │ │  BCB Loader  │ │  B3/YF   │ │   News   │  │
│  │ DFP/ITR/IPE  │ │ Selic/IPCA   │ │  Prices  │ │ RSS+IPE  │  │
│  └──────┬───────┘ └──────┬───────┘ └────┬─────┘ └────┬─────┘  │
└─────────│────────────────│──────────────│─────────────│─────────┘
          │                │              │             │
          ▼                ▼              ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER (SQLite)                       │
│  financial_statements | macro_series | prices | news_items       │
│  companies | tickers | valuations | signals | thesis_versions    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────┐
│  FINANCIAL   │  │   MARKET DATA    │  │   NEWS &     │
│   ENGINE     │  │     ENGINE       │  │  QUAL ENGINE │
│              │  │                  │  │              │
│ DCF valuation│  │ Price series     │  │ Event detect │
│ LTM aggregat │  │ Technical signals│  │ PDF parse    │
│ Multiples    │  │ Macro context    │  │ Event classify│
│ Projections  │  │ Macro signals    │  │ News summary │
└──────┬───────┘  └────────┬─────────┘  └──────┬───────┘
       │                   │                    │
       └───────────────────┼────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INTELLIGENCE LAYER                            │
│                                                                  │
│  Input: DCF result + multiples + macro + signals + news events   │
│  Process: Claude API (claude-sonnet-4-6) via instructor          │
│  Output: Structured InvestmentThesis Pydantic model              │
│                                                                  │
│  ┌────────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────┐ │
│  │ Bull thesis│ │  Bear thesis │ │ Key drivers │ │  Risks   │ │
│  │            │ │              │ │             │ │          │ │
│  │ Fair value │ │  Positioning │ │   Signals   │ │Confidence│ │
│  └────────────┘ └──────────────┘ └─────────────┘ └──────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────────┐  ┌──────────────┐
│  STREAMLIT   │  │    TELEGRAM      │  │   PDF REPORT │
│  DASHBOARD   │  │     ALERTS       │  │  GENERATOR   │
│              │  │                  │  │              │
│ Multi-page   │  │ Thesis summary   │  │ Jinja2+CSS   │
│ Watchlist    │  │ Event alerts     │  │ WeasyPrint   │
│ Charts+Tables│  │ Daily brief      │  │ Client-ready │
└──────────────┘  └──────────────────┘  └──────────────┘
```

---

## Data Flow (End-to-End)

### Daily Scheduled Run
```
06:00 → Ingestion: BCB macro update (Selic, IPCA, PTAX)
06:05 → Ingestion: B3 prices via yfinance (previous close)
06:10 → Ingestion: News RSS scrape (17+ sources)
06:15 → Ingestion: CVM IPE check (new events since last run)
06:20 → Financial Engine: recalculate multiples for watchlist
06:25 → Signal Engine: recalculate technical indicators
06:30 → Intelligence Layer: regenerate thesis for assets with changed inputs
06:45 → Delivery: Telegram morning brief (macro + top movers + top opportunity)
```

### CVM Quarterly Run (triggered on ITR/DFP availability)
```
CVM new filing detected →
  → Download + parse DFP/ITR XML →
  → Normalize to standard account schema →
  → Store in financial_statements table →
  → Trigger Financial Engine: recalculate LTM, DCF, multiples →
  → Trigger Intelligence Layer: regenerate thesis (inputs changed) →
  → Delivery: Telegram alert "PETR4 earnings updated — thesis refreshed"
```

### On-Demand (user-triggered via dashboard)
```
User selects ticker in Streamlit →
  → Check data freshness (all layers) →
  → If stale: trigger ingestion for that ticker →
  → Read from SQLite: financial data + signals + thesis →
  → Render dashboard page →
  → User clicks "Generate Report" →
  → PDF: Jinja2 template + WeasyPrint → downloads PDF
```

---

## LLM Integration Patterns

### Structured Output (Critical)
Use `instructor` library to enforce Pydantic schema on Claude output:
```python
class InvestmentThesis(BaseModel):
    ticker: str
    bull_case: str          # 2-3 sentences
    bear_case: str          # 2-3 sentences
    key_drivers: list[str]  # exactly 3-5 items
    risks: list[str]        # 3-5 items
    fair_value_brl: float
    methodology: str        # "DCF 60% + EV/EBITDA 40%"
    positioning: Literal["COMPRAR", "MANTER", "VENDER"]
    confidence: Literal["ALTA", "MEDIA", "BAIXA"]
    rationale: str          # positioning rationale, 1-2 sentences
    generated_at: datetime
```

This guarantees PDF report template can always render the thesis — no free-form parsing.

### Prompt Architecture
```
System prompt (cached): Platform role, output language (PT-BR), financial expertise context
User prompt: Structured context block containing:
  - Valuation block: DCF result, multiples vs. peers, fair value
  - Financial block: LTM revenue, EBITDA, net income, margins, YoY deltas
  - Macro block: Selic, IPCA, PTAX, CDS, relevant macro signals
  - Signals block: RSI, MACD, momentum, price vs. 52w high/low
  - Events block: Recent news summaries, earnings date, upcoming catalysts
  - Task: Generate InvestmentThesis for {ticker}
```

### Cost Control
- Cache system prompt (same for all tickers): saves ~80% of system prompt tokens
- Use `claude-haiku-4-5` for news classification and event routing (cheap, fast)
- Use `claude-sonnet-4-6` for thesis generation only (higher quality needed)
- Store generated thesis in SQLite — only regenerate when input data changes (hash-based invalidation)
- Estimated cost per thesis: ~$0.05-0.15 per ticker per day with sonnet; manageable at 20-50 ticker watchlist

---

## Storage Architecture

### Schema Design (SQLite-first, Supabase-compatible)

```sql
-- Core entities
companies (cvm_code, ticker, name, sector, governance_tier, created_at)
tickers (ticker, cvm_code, share_class, is_active, last_price, updated_at)

-- Financial data
financial_statements (id, cvm_code, period_type, period_end, account_code, 
                      account_name, value_brl, report_type, filing_date)
ltm_aggregates (cvm_code, calculated_at, revenue, ebitda, net_income, 
                fcf, net_debt, total_assets)

-- Market data
price_series (ticker, date, open, high, low, close, volume, adj_close)
macro_series (series_id, series_name, date, value, unit)

-- Computed
valuations (cvm_code, calculated_at, dcf_fair_value, pe_ratio, ev_ebitda, 
            price_to_book, upside_pct, methodology_json)
signals (ticker, calculated_at, rsi_14, macd_signal, ma_cross_50_200, 
         momentum_score, composite_score)

-- Intelligence
investment_thesis (id, ticker, bull_case, bear_case, key_drivers_json, 
                   risks_json, fair_value_brl, methodology, positioning, 
                   confidence, rationale, input_hash, generated_at)

-- News/Events
news_items (id, ticker, headline, source, published_at, url, 
            sentiment, ingested_at)
corporate_events (id, cvm_code, event_type, event_date, description, 
                  cvm_ipe_id, parsed_at)
```

### SQLite → Supabase Migration Strategy
- Use SQLAlchemy Core (dialect-neutral SQL) — same codebase targets both
- Avoid SQLite-specific types: use TEXT for JSON columns, REAL for decimals, INTEGER for timestamps
- Store JSON as TEXT columns (not SQLite JSON type) — PostgreSQL TEXT also handles this
- When ready to migrate: `pg_dump`-equivalent → Supabase `psql` import + switch connection string

---

## Suggested Build Order

Dependencies flow strictly downward. Each phase must be stable before the next begins.

```
Phase 1 — Foundation (no dependencies)
  ├── Consolidate codebase to single src/ (archive duplicates)
  ├── .env configuration layer (python-dotenv + pydantic-settings)
  ├── Unified SQLAlchemy schema (all tables, migrations via alembic)
  ├── Retry wrapper around all external API calls (tenacity)
  └── Structlog logging across all modules

Phase 2 — Reliable Ingestion (depends on Phase 1)
  ├── CVM ingestion: unified DFP/ITR/IPE downloader + XML parser
  ├── BCB ingestion: unified macro series (Selic, IPCA, PTAX, CDS, PIB)
  ├── B3/yfinance: price series with corporate action adjustment
  ├── News: RSS + CVM IPE event ingestion
  └── Ingestion scheduler (APScheduler or cron)

Phase 3 — Financial Engine (depends on Phase 2)
  ├── LTM aggregation (rolling 4-quarter ITR + annual DFP reconcile)
  ├── Standard multiples (P/E, EV/EBITDA, P/BV, dividend yield)
  ├── DCF model (WACC from Selic+CDS, FCF projection, terminal value)
  ├── Peer/sector comparison (multi-ticker multiples table)
  └── Technical signals (RSI, MACD, MA crossover via pandas-ta)

Phase 4 — Intelligence Layer (depends on Phase 3) ← CORE DIFFERENTIATOR
  ├── Pydantic InvestmentThesis schema
  ├── instructor + Claude API integration
  ├── Prompt templates (Jinja2, one per analysis type)
  ├── Input hash-based thesis invalidation (only regenerate when data changes)
  └── Thesis storage and versioning

Phase 5 — Delivery Layer (depends on Phase 4)
  ├── Streamlit dashboard (watchlist → valuation → signals → thesis)
  ├── Telegram: thesis summary + event alerts + morning brief
  └── PDF report: Jinja2 HTML → WeasyPrint → institutional format

Phase 6 — Advanced Features (depends on Phase 5 stability)
  ├── Event-driven thesis refresh (CVM IPE trigger)
  ├── Opportunity detection (mispricing, momentum + fundamental combo)
  ├── Scenario analysis (sensitivity tables)
  └── Supabase cloud migration
```

---

## Key Architectural Decisions

| Decision | Rationale | Constraint Created |
|---|---|---|
| SQLAlchemy Core over raw SQLite | Supabase migration without rewrite | Can't use SQLite-specific features |
| instructor over raw Claude API | Guaranteed structured thesis output | Adds instructor dependency |
| Jinja2 for prompts and PDF templates | Separates content from logic; easy to iterate prompts without code changes | Prompt changes don't require code deploys |
| Input hash-based thesis invalidation | LLM cost control; only call API when data actually changes | Need to maintain hash computation per thesis |
| APScheduler over cron | Cross-platform scheduling (Windows/Linux); visible in Python code | Slightly more complex than cron |
| Single SQLite file (local) | Simple, zero-ops, fast | Concurrency limited to one writer; acceptable for single-user |

---
*Researched: 2026-05-06*
