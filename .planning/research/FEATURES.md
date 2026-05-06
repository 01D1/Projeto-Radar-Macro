# Features Research — Investment Intelligence Platform

**Domain:** AI-powered investment intelligence, Brazilian equities (B3/CVM/BCB)
**Researched:** 2026-05-06
**Confidence:** HIGH (terminal/platform features); HIGH (Brazilian regulatory specifics); MEDIUM (client delivery behavioral preferences)

---

## Table Stakes (Must Have)

Features users expect from any credible institutional investment platform. Absence causes immediate credibility loss or abandonment.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Historical price series with OHLCV | Every analysis starts here; no price data = no platform | Low | yfinance covers B3 — already integrated |
| Standard valuation multiples display | P/E, EV/EBITDA, P/BV, P/S — analysts verify these before reading any thesis | Low | Derived from CVM financials + price series |
| Income statement, balance sheet, cash flow display | Baseline data credibility check — analysts cross-reference | Medium | CVM DFP/ITR covers this — already ingested |
| Quarterly/annual financials with trend view | Analysts track trajectory, not snapshots | Medium | Requires normalizing CVM data across periods |
| LTM (last twelve months) financial aggregation | Standard institutional practice — sum of trailing four quarters | Medium | Derived from ITR data; needs rolling-window logic |
| Sector/peer comparison | No thesis exists in isolation; relative valuation is mandatory | Medium | Requires sector taxonomy and multi-ticker aggregation |
| Basic technical indicators | RSI, MACD, moving averages — even fundamental analysts use these as entry signals | Low | pandas-ta or ta-lib covers this |
| Macro context panel | Selic, IPCA, PTAX, CDS Brazil — no Brazilian equity thesis is written without macro | Low | BCB SGS already integrated |
| News feed per asset | Analysts need news context before reading any AI output | Low | RSS + CVM IPE already integrated |
| Search / ticker lookup | Fundamental navigation — without it the tool is unusable | Low | Streamlit sidebar or search widget |
| Watchlist management | Analysts track a defined universe; random browsing is not a workflow | Low | SQLite-backed list; simple CRUD |
| Data freshness indicators | Institutional users distrust stale data; timestamps are mandatory | Low | Add ingestion timestamps to all data models |
| Export to CSV/Excel | Every institutional analyst uses Excel downstream; blocking this creates friction | Low | pandas `.to_csv()` / `.to_excel()` |
| Error states and data-unavailable messaging | Silently empty screens destroy trust instantly | Low | "Data not available — last updated: X" messages |

**Rationale for table stakes classification:** Bloomberg Terminal, FactSet, and Refinitiv Eikon all treat these as baseline infrastructure. An analyst encountering a platform that lacks LTM aggregation, peer comparison, or macro context will immediately classify the tool as "toy-grade" regardless of AI capability.

---

## Differentiators (Competitive Advantage)

Features that separate this platform from Bloomberg/FactSet data terminals and from generic LLM chatbots applied to finance.

### Tier 1 — Core Differentiators (the reason this platform exists)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AI-generated investment thesis (bull case) | Replaces 2-4 hours of analyst synthesis; client-ready in seconds | High | Claude Sonnet as synthesis engine; requires Financial + News + Macro inputs |
| AI-generated investment thesis (bear case) | Balancing the bull case is what makes the thesis credible to institutional clients | High | Same engine, contrarian prompt framing |
| Key driver identification (top 3-5 factors) | Analysts need to explain "why" to clients; AI surfaces drivers from filings + news | High | Named entity + event extraction from CVM + news |
| Risk enumeration per asset | Idiosyncratic + macro + regulatory risks; required in any CVM-compliant research | High | Structured risk taxonomy from filings + news + macro |
| Fair value estimate with methodology disclosure | "R$ X.XX / DCF + multiples blend" — gives the AI output quantitative grounding | High | DCF engine + EV/EBITDA comp must feed into AI prompt |
| Suggested positioning (overweight/neutral/underweight) | The "so what" — what Bloomberg never gives; what clients actually ask for | High | Requires confidence scoring and risk-adjusted framing |
| Mispricing signal detection | "Stock trades 40% below DCF fair value amid sector selloff" — actionable | High | Requires price vs. fair value divergence logic |
| Event-driven alerts (earnings, dividends, fatos relevantes) | Timing is everything; AI thesis at event time is 10x more valuable | Medium | CVM IPE parsing + trigger logic already partially built |
| Thesis versioning / change log | "Thesis changed because Q3 EBITDA missed 12% vs consensus" — shows AI is tracking | High | Requires storing prior thesis versions + diff logic |

### Tier 2 — Strong Differentiators (enhance credibility and stickiness)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Earnings transcript parsing + AI summary | Visible Alpha / AlphaSense core feature; surfaces management tone and guidance deltas | High | Requires PDF parser for CVM earnings calls; Portuguese NLP |
| Momentum + fundamental signal combination | Pure quant (momentum) + pure fundamental (DCF) disagree often; combined signal is more robust | High | Quant module feeding into thesis prompt |
| Macro-driven trade identification | "Selic cut cycle = banks compress NIM = sell banks, buy exporters" — systematic macro rotation | High | Requires macro → sector → stock transmission model |
| Scenario analysis (base/bull/bear with probabilities) | Clients ask "what if Selic stays at 13% for 2 years" — quantified scenarios | High | Monte Carlo or sensitivity table; complex |
| Sector rotation heatmap | Visual representation of relative attractiveness across IBOVESPA sectors | Medium | Derived from peer comparison + macro signals |
| Client-ready PDF report generation | One-click institutional report; letterhead-ready format | Medium | WeasyPrint or ReportLab; structured from thesis output |
| Telegram alerts with thesis summary | Clients receive "PETR4 thesis updated: bull conviction raised" with key points | Low | Already integrated; needs thesis → message formatting |

### Tier 3 — Emerging Differentiators (build after core is stable)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Management credibility tracking | "CEO has guided correctly 6/8 quarters" — AI from CVM disclosures | Very High | Long-horizon NLP + structured memory |
| Sentiment scoring on earnings calls | Tone change from "confident" to "cautious" is predictive; AlphaSense charges extra for this | Very High | Requires speech-to-text if calls are audio; Portuguese models |
| Regulatory risk scoring | CVM enforcement actions, CADE antitrust activity, ANATEL/ANS/ANEEL interventions | High | Event-driven from regulatory RSS/open data |
| Insider trading / ownership change alerts | CVM Form 358 / Formulário de Referência changes — legally public, rarely tracked systematically | Medium | CVM IPE parser extension |

---

## Anti-Features (Do NOT Build in v1)

Features that appear valuable but impose disproportionate complexity, regulatory risk, or scope creep relative to v1 value.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Real-time order execution / trading | Requires CVM broker licensing (CTVM/DTVM), regulatory compliance, client fund custody — entirely different business | Stay firmly "read-only decision support"; add legal disclaimer in UI |
| Multi-user authentication and RBAC | v1 is single-analyst; auth adds weeks of infra work with zero thesis-quality benefit | Design DB schema to be multi-tenant-ready, but ship single-user |
| Bloomberg API integration | $20K+/year terminal cost; data already covered by CVM + Yahoo Finance + BCB | Yahoo Finance + CVM covers 95% of needed data; document gap explicitly |
| Real-time streaming prices (websocket) | B3 requires BovespaTech DMA licensing for true real-time; polling at 5-15 min cadence sufficient for investment analysis (not trading) | yfinance polling cadence is adequate for non-HFT use cases |
| Natural language query interface ("chat with your portfolio") | Sounds appealing; actually requires retrieval-augmented generation infrastructure, embedding DB, query routing — 3x engineering scope | Structured thesis generation is more reliable and client-presentable |
| Options / derivatives analytics | Requires pricing models (Black-Scholes, binomial), vol surface construction — separate domain entirely | Scope to equities only; note derivatives as future milestone |
| ESG scoring engine | Data sourcing for ESG in Brazil is fragmented (no single authoritative source); building your own = enormous ongoing maintenance | Reference ISE B3 index membership as a proxy; do not build scoring |
| Backtesting engine for signals | Requires point-in-time data (survivorship bias avoidance), statistical rigor, compliance disclaimers — 2-4 month standalone project | Note as Phase 4+ milestone; do not let it delay AI thesis launch |
| Fixed income analytics | Brazil's fixed income (Tesouro Direto, CRIs, CRAs, debentures) requires different valuation models, different data sources (ANBIMA), different regulatory context | Stay B3 equities in v1; fixed income is a separate product expansion |
| Social sentiment / Twitter scraping | Noisy, legally ambiguous (data resale), requires continuous infrastructure; institutional clients distrust retail sentiment as signal | RSS from qualified financial sources is sufficient for news signal |
| Automated client report emailing | Email infrastructure, unsubscribe compliance, bounces — not worth it when Telegram already works | Telegram + Obsidian vault covers delivery; PDF is manual share |
| Mobile app | Institutional analysts work on desktop; mobile-first adds React Native / Flutter complexity | Streamlit is responsive enough for tablet; defer native mobile |

---

## Feature Dependencies

Features are ordered by dependency — upstream features must be stable before downstream features are safe to build.

```
Layer 0 — Data Infrastructure (no dependencies)
├── CVM financial statements ingestion (DFP/ITR/IPE)       [existing]
├── BCB macro series ingestion (Selic, IPCA, PIB, CDS)     [existing]
├── B3 price series ingestion (Yahoo Finance)               [existing]
├── News aggregation (RSS + CVM IPE events)                 [existing]
└── SQLite persistence with ingestion timestamps            [existing, needs .env cleanup]

Layer 1 — Financial Engine (depends on Layer 0)
├── LTM financial aggregation (rolling 4-quarter ITR)
├── Standard valuation multiples (P/E, EV/EBITDA, P/BV)
├── Peer/sector comparison data model
└── DCF fair value model (WACC, terminal growth, projections)

Layer 2 — Signal Layer (depends on Layer 1)
├── Technical indicators (RSI, MACD, MA crossovers)
├── Price vs. fair value divergence (mispricing signal)
├── Momentum scoring
└── Macro-to-sector transmission signals

Layer 3 — Intelligence Layer (depends on Layers 1 + 2)
├── AI thesis generation [bull case]                        ← CORE DIFFERENTIATOR
│   └── Inputs: DCF, multiples, peer comp, macro, news, signals
├── AI thesis generation [bear case]
├── Key driver identification
├── Risk enumeration
├── Fair value + methodology disclosure
└── Suggested positioning

Layer 4 — Delivery Layer (depends on Layer 3)
├── Streamlit dashboard (watchlist, valuation, signals, macro, news, thesis)
├── Telegram alerts (thesis summary + key points)
├── PDF report generation
└── Obsidian vault output                                   [existing]

Layer 5 — Advanced Features (depends on Layer 4 stability)
├── Thesis versioning + change log
├── Event-driven thesis refresh (earnings, fato relevante)
├── Scenario analysis (base/bull/bear with probabilities)
└── Sector rotation heatmap
```

**Critical dependency:** The AI thesis (Layer 3) is only as credible as the Financial Engine (Layer 1). Building the intelligence layer before fair value and LTM aggregation are solid will produce hallucinated or misleading thesis outputs. Layer 1 must be stable before Layer 3 is exposed to clients.

**Second critical dependency:** PDF report generation depends on thesis being structurally consistent (same sections, same formatting) across assets. Free-form AI output cannot feed a PDF template. Thesis structure must be schema-enforced before PDF is built.

---

## Brazilian Market Specifics

Features and constraints unique to CVM/B3/BCB that have no equivalent in US-market platforms and that differentiate this platform from generic AI finance tools.

### CVM Filing System (Comissão de Valores Mobiliários)

| Feature / Consideration | Detail | Implementation Note |
|------------------------|--------|---------------------|
| DFP (Demonstrações Financeiras Padronizadas) | Annual audited financials — full income statement, balance sheet, cash flow in XBRL-like structured format | Already ingested; normalize to common schema across all tickers |
| ITR (Informações Trimestrais) | Quarterly unaudited financials — same structure as DFP | Already ingested; use for LTM rolling aggregation |
| IPE (Informações Periódicas e Eventuais) | Corporate events: dividends, fatos relevantes (material facts), earnings releases, director appointments | Partially ingested; IPE is the trigger for event-driven thesis refresh |
| Fato Relevante parsing | CVM-mandated disclosure of material information — M&A, guidance changes, regulatory actions | Critical for event detection; PDF parsing required for full text |
| Formulário de Referência | Annual disclosure including risk factors, business description, related-party transactions, executive compensation | Rich source for AI risk enumeration; complex to parse but high value |
| IFRS vs. BR GAAP awareness | Post-2010 CVM mandated IFRS adoption; some companies report both; financial comparisons must flag the standard | Hardcode IFRS as default; flag BR GAAP outliers |
| Non-recurring item detection | Brazilian companies frequently reclassify items; raw EBITDA from CVM often includes non-recurring | AI must be instructed to flag "adjusted vs. reported" distinction |
| CVM enforcement actions (PAS) | Punitive Administrative Process disclosures — material for governance risk | Future milestone; CVM publishes these publicly |

### B3 Data Specifics

| Feature / Consideration | Detail | Implementation Note |
|------------------------|--------|---------------------|
| Ticker convention | B3 uses 4-letter + number suffix: PETR3 (ON), PETR4 (PN), PETR11 (BDR unit) — different share classes have different voting rights and liquidity | yfinance appends ".SA"; must handle suffix logic in ticker normalization |
| ON vs. PN share classes | Ordinária (ON) = voting; Preferencial (PN) = dividend preference; same company, different prices | Valuation must aggregate both classes for market cap; voting premium is an analytical consideration |
| BDR (Brazilian Depositary Receipts) | Foreign companies listed on B3 (e.g., AAPL34) — different regulatory treatment, no CVM DFP | Explicitly exclude from v1 or flag as "CVM data unavailable" |
| IBOVESPA index composition | The benchmark; analysts frame all thesis relative to IBOV weight and contribution | Pull composition from B3 public data; flag index weight in UI |
| Sector classification | B3 uses its own sector taxonomy (different from GICS) — Novo Mercado governance tiers are layered on top | Map B3 sector codes in the peer comparison module |
| Novo Mercado / Nível 2 / Básico | Governance tiers that affect institutional investor appetite; Novo Mercado = highest standards | Surface governance tier prominently in thesis header |
| Circuit breakers and trading halts | B3 has automatic circuit breakers (10%/15%/20% intraday moves) — data gaps on halt days | Handle yfinance gaps gracefully; do not interpolate |
| Dividend tax treatment | JCP (Juros sobre Capital Próprio) is a Brazilian dividend-equivalent with different tax treatment | Flag JCP vs. dividends in financial display; affects yield calculations |

### BCB Macro Integration

| Feature / Consideration | Detail | Implementation Note |
|------------------------|--------|---------------------|
| Selic rate and transmission | Selic = benchmark rate; higher Selic = higher discount rates = lower equity valuations (especially growth) | Selic feeds directly into DCF WACC; display Selic curve in macro panel |
| IPCA inflation context | Real vs. nominal return distinction is critical; inflation erodes margins | Integrate into earnings analysis: "IPCA-adjusted revenue growth" |
| PTAX (USD/BRL) | Commodity exporters (VALE, PETR) have USD-denominated revenues — PTAX is a primary driver | Surface PTAX prominently for commodity/exporter tickers |
| CDS Brazil (sovereign risk) | Country risk premium that feeds into WACC for Brazilian equities (EMBI+) | Use as systematic risk component in DCF CAPM |
| PIB (GDP) growth | Macro context for cyclical sectors (retail, construction, financials) | Include in macro panel; use for sector-level macro sensitivity |
| FOCUS Market Report | BCB weekly survey of market expectations for Selic, IPCA, PIB, PTAX — consensus forecasts | High value for scenario analysis; BCB API available; add in Layer 5 |
| Copom meeting calendar | BCB rate decisions are the single most important event for equity valuations | Hard-code Copom meeting dates as events in the platform calendar |

### Regulatory and Compliance Framing

| Consideration | Detail | Implementation Note |
|--------------|--------|---------------------|
| CVM Instrução 598 (research analysts) | Regulates conflitos de interesse in investment research; requires disclosure of analyst relationships | Platform output must include boilerplate disclaimer: "This is AI-generated analysis, not investment advice under CVM IN 598" |
| Client presentation format | Institutional clients (fundos, family offices, asset managers) expect ABNT-formatted documents or structured investment memos | PDF template should follow standard investment memo structure: Thesis Summary → Valuation → Risks → Recommendation |
| Portuguese language output | All client-facing content must be in Portuguese; English is acceptable for internal/technical layers | AI prompts must explicitly request Portuguese output; financial terminology follows Brazilian convention (e.g., "patrimônio líquido" not "equity") |
| LGPD compliance | Lei Geral de Proteção de Dados — if any client data (watchlists, preferences) is stored, basic LGPD compliance required | v1 single-user local; LGPD becomes relevant when cloud/multi-user is added |

---

## MVP Feature Prioritization

Based on the dependency graph and the platform's core value proposition ("Bloomberg tells you what; this tells you what to do and why"):

**Must ship in v1 (Phase 1-3):**
1. Financial Engine: LTM aggregation, valuation multiples, DCF fair value — credibility foundation
2. AI Investment Thesis: bull/bear, drivers, risks, fair value, positioning — core differentiator
3. Macro context panel (Selic, IPCA, PTAX, CDS) — non-negotiable for Brazilian equities
4. News + event feed per asset — provides AI thesis context and trigger for refreshes
5. Telegram delivery of thesis summary — already built; just needs thesis → message formatting
6. Streamlit dashboard (single-page): watchlist, valuation, macro, thesis display

**Ship in v2 (Phase 4-5):**
7. PDF report generation — depends on thesis having stable, schema-enforced structure
8. Event-driven thesis refresh (earnings, fato relevante trigger)
9. Peer/sector comparison with relative valuation
10. Mispricing signal detection (price vs. DCF divergence)
11. Thesis versioning with change tracking

**Defer to v3+:**
12. Scenario analysis with probabilities
13. Sector rotation heatmap
14. FOCUS forecast integration
15. Management credibility tracking
16. Backtesting engine

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| Bloomberg/FactSet/Refinitiv table stakes | HIGH | Well-documented industry standard through 2025; extensively published analyst workflow literature |
| AlphaSense/Visible Alpha differentiators | HIGH | Both platforms have detailed public feature documentation; AI-native research features are well-documented |
| CVM filing types and structure | HIGH | CVM data portal is publicly documented; DFP/ITR/IPE taxonomy is stable and authoritative |
| B3 ticker conventions and share classes | HIGH | B3 publicly documents this; yfinance behavior for .SA suffix is well-known |
| BCB macro data and transmission | HIGH | BCB API documentation is public and stable |
| LLM investment report credibility criteria | HIGH | Active research area; institutional standards are publicly discussed in CFA Institute and IOSCO publications through 2025 |
| Client delivery format preferences | MEDIUM | Behavioral preference data less precise; Telegram + PDF recommendation based on known institutional patterns in Brazilian market, not direct survey data |
| Brazilian regulatory framing (CVM IN 598) | HIGH | CVM instruções normativas are publicly available; disclaimer requirement is straightforward |

---

*Researched: 2026-05-06*
*Sources: Training knowledge (Bloomberg/FactSet/Refinitiv feature sets, AlphaSense/Visible Alpha, CVM/B3/BCB documentation, CFA Institute standards) — web search unavailable in this environment; web verification not possible for this session.*
