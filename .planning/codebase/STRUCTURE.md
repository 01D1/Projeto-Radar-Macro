# Codebase Structure

**Analysis Date:** 2026-05-06

## Directory Layout

```
12_PYTHON/                              # Root of the Python investment analysis system
├── src/                                # Primary production codebase
│   ├── main.py                         # CLI entry point (python -m src.main)
│   ├── pipeline.py                     # Legacy standalone pipeline runner
│   ├── scheduler.py                    # APScheduler daemon entry point
│   ├── ingestion/                      # Data acquisition layer
│   │   ├── cvm_downloader.py           # CVM ZIP download + extraction
│   │   └── b3_scraper.py               # B3 price history via yfinance → Parquet
│   ├── parsers/                        # Raw CSV → structured objects
│   │   ├── dfp_parser.py               # Industrial company DFP parser
│   │   └── bank_parser.py              # Bank DFP parser (uses BANK_REGISTRY)
│   ├── normalization/                  # Account code/name standardization
│   │   ├── account_mapper.py           # Industrial account mapping
│   │   └── bank_account_mapper.py      # Bank COSIF/IFRS account mapping
│   ├── validation/                     # Schema enforcement + consistency checks
│   │   ├── bank_schemas.py             # Pydantic v2 models for bank statements
│   │   ├── schemas.py                  # Industrial schemas
│   │   └── reconciler.py              # Cross-statement reconciliation
│   ├── processing/                     # Pipeline orchestration + read interface
│   │   ├── pipeline.py                 # ProcessingPipeline (raw → processed JSON)
│   │   └── storage.py                  # ProcessedStore (read data/processed/)
│   ├── analysis/                       # Financial analysis engines
│   │   ├── metrics_engine.py           # Ratio calculation (ROE, NIM, EBITDA, etc.)
│   │   ├── risk_engine.py              # Rule-based risk scoring
│   │   ├── insight_engine.py           # Deterministic insight generation
│   │   ├── detect_inconsistencies.py   # Balance-sheet validation
│   │   └── earnings_quality.py         # Earnings quality assessment
│   ├── valuation/                      # Company valuation models
│   │   ├── auto_dcf.py                 # Sector-aware valuation dispatcher
│   │   ├── valuation_dcf.py            # DCF FCFF implementation
│   │   ├── calculate_metrics.py        # Valuation metric helpers
│   │   └── sector_config.py            # SectorConfig — reads config/sectors.yaml
│   ├── content/                        # LLM-powered content generation
│   │   ├── llm_client.py               # Anthropic Claude wrapper (caching + retry)
│   │   ├── morning_call.py             # Daily market brief generator
│   │   ├── post_generator.py           # Ticker-specific analyst post
│   │   └── thesis_builder.py           # Full investment thesis generator
│   ├── delivery/                       # Output delivery
│   │   ├── obsidian_writer.py          # Write/update Markdown notes in vault
│   │   └── telegram_bot.py             # Telegram Bot API wrapper
│   ├── utils/                          # Cross-cutting utilities
│   │   ├── logger.py                   # Logging configuration + get_logger()
│   │   └── retry.py                    # Retry decorator for network calls
│   └── reporting/                      # (directory present, no .py files detected)
│
├── config/                             # Runtime configuration (YAML + Pydantic)
│   ├── settings.py                     # Pydantic-Settings: paths, API keys, env
│   ├── tickers.yaml                    # Active ticker registry {ticker, type, sector}
│   ├── cvm_codes.yaml                  # Ticker → CD_CVM mapping
│   ├── sectors.yaml                    # Sector methodologies + thresholds + DCF assumptions
│   └── schedules.yaml                  # APScheduler cron expressions per job
│
├── data/                               # Runtime data (not committed)
│   ├── raw/
│   │   ├── cvm/DFP/{year}/*.csv        # CVM ZIP extracts (all companies per year)
│   │   └── prices/{TICKER}.parquet     # B3 price history
│   ├── processed/{TICKER}/
│   │   └── dfp_{year}.json             # Parsed + validated financial statements
│   └── output/{TICKER}/
│       ├── metrics_{year}.json         # Computed financial ratios
│       ├── risk_report.json            # Risk assessment
│       ├── valuation.json              # DCF/Gordon/DDM scenarios
│       └── insights.json              # Rule-based insights
│
├── news_hunter/                        # Independent news crawling sub-system
│   ├── main.py                         # CLI entry point (argparse, run standalone)
│   ├── config.py                       # News Hunter configuration constants
│   ├── crawler.py                      # RSS/HTML fetcher
│   ├── scrapers.py                     # Source-specific scrapers
│   ├── classificador.py                # Keyword scoring classifier
│   ├── banco.py                        # SQLite persistence (banco.db)
│   ├── gerar_boletim.py                # Jinja2 bulletin renderer
│   ├── telegram_client.py              # Telegram sender (standalone)
│   ├── agendador.py                    # Independent APScheduler (07:30/12:00/18:00)
│   ├── market_agent.py                 # Market context agent
│   ├── calendario_economico.py         # Economic calendar integration
│   └── visualizar.py                   # Terminal bulletin viewer
│
├── pipeline banco completo/            # Older separate bank pipeline (legacy)
│   ├── scheduler.py                    # Legacy scheduler
│   ├── teste_pipeline.py               # Pipeline test runner
│   ├── streamlit_app.py                # Streamlit dashboard
│   ├── dump_cvm.py                     # CVM data dump utility
│   ├── config/
│   │   ├── settings.py                 # Legacy settings
│   │   ├── bancos.py                   # Bank registry
│   │   ├── mapeamento_contas.py        # Account mapping (bank-specific)
│   │   ├── mapeamento_contas_geral.py  # Account mapping (general)
│   │   ├── metodologias_setoriais.py   # Sector methodologies
│   │   └── empresa_loader.py           # Company loader
│   ├── modules/
│   │   ├── 01_coletor_cvm.py           # CVM collector
│   │   ├── 02_coletor_mercado.py       # Market data collector
│   │   ├── 03_coletor_macro.py         # Macro data collector
│   │   ├── 04_normalizador.py          # Data normalizer
│   │   ├── 05_valuation.py             # Valuation module
│   │   ├── 06_projecoes.py             # Projections module
│   │   ├── 07_escritor_excel.py        # Excel writer
│   │   ├── coletor_cvm.py              # CVM collector (refactored)
│   │   ├── coletor_mercado.py          # Market data collector (refactored)
│   │   ├── coletor_macro.py            # Macro data collector (refactored)
│   │   ├── normalizador.py             # Normalizer (refactored)
│   │   ├── valuation.py                # Valuation (refactored)
│   │   ├── database.py                 # Database module
│   │   ├── alerts.py                   # Alert system
│   │   ├── intelligence.py             # Intelligence engine
│   │   ├── qualitative_engine.py       # Qualitative analysis
│   │   ├── quality_gate.py             # Quality gate checks
│   │   ├── report_writer.py            # Report writer
│   │   ├── ri_crawler.py               # RI (Investor Relations) crawler
│   │   ├── parser_ri.py                # RI parser
│   │   ├── sector_operational_drivers.py  # Sector operational drivers
│   │   ├── excel_audit_sheet.py        # Excel audit sheet
│   │   ├── excel_theme.py              # Excel theme
│   │   ├── post_excel_quality_gate.py  # Post-Excel quality gate
│   │   ├── assumptions_auditor.py      # Assumptions auditor
│   │   └── data_completeness_auditor.py  # Data completeness auditor
│   ├── tools/
│   │   └── auditar_planilhas_valuation.py  # Valuation spreadsheet auditor
│   └── outputs/valuations/{TICKER}/   # Legacy valuation Excel outputs
│
├── notebooks/                          # Analysis exploration scripts
│   ├── 01_wege3_extracao_piloto.py     # WEGE3 extraction pilot
│   ├── 02_wege3_historico_completo.py  # WEGE3 full history
│   ├── 03_bancos_historico_completo.py # Banks full history
│   ├── build_comparativa_5_bancos.py   # 5-bank comparative analysis
│   └── build_banks_grandes_valuation.py # Large banks valuation
│
├── tests/                              # Test directory (empty/no .py files detected)
│
├── logs/                               # Runtime log files (not committed)
├── pyproject.toml                      # Python project config (ruff, dependencies)
├── requirements.txt                    # Pip dependencies
├── env                                 # Environment variables file (no dot — load via settings.py)
├── bootstrap.sh                        # Setup script
└── README.md                           # Project documentation
```

## Directory Purposes

**`src/`:**
- Purpose: All production code for the Intelligence System
- Contains: CLI, scheduler, 8 functional sub-packages
- Key files: `src/main.py` (CLI), `src/scheduler.py` (daemon), `src/pipeline.py` (legacy runner)

**`src/ingestion/`:**
- Purpose: External data acquisition only — no transformation
- Contains: CVM downloader, B3 price scraper
- Key files: `src/ingestion/cvm_downloader.py`, `src/ingestion/b3_scraper.py`

**`src/parsers/`:**
- Purpose: Convert raw CVM CSV rows into typed Python objects; routing differs by company type
- Contains: `dfp_parser.py` (industrials), `bank_parser.py` (banks + `BANK_REGISTRY`)
- Key files: `src/parsers/bank_parser.py` (contains the `BANK_REGISTRY` dict used throughout)

**`src/normalization/`:**
- Purpose: Canonical account name resolution — bridge between CVM codes and domain fields
- Contains: `account_mapper.py`, `bank_account_mapper.py`

**`src/validation/`:**
- Purpose: Pydantic v2 schema enforcement for parsed statements
- Contains: `bank_schemas.py` (primary — all bank Pydantic models live here)

**`src/processing/`:**
- Purpose: Orchestrate the full raw → processed pipeline; provide read-only access to outputs
- Contains: `pipeline.py` (write path), `storage.py` (read path via `ProcessedStore`)

**`src/analysis/`:**
- Purpose: All post-processing analytical computations
- Contains: metrics, risk, insights, inconsistency detection, earnings quality

**`src/valuation/`:**
- Purpose: Financial valuation using sector-appropriate methodologies
- Contains: `auto_dcf.py` (dispatcher), `sector_config.py` (YAML config reader)

**`src/content/`:**
- Purpose: LLM-powered content generation using Claude API
- Contains: `llm_client.py` (central API wrapper), three content generators
- Note: Prompts are read from the Obsidian vault at `11_PROMPTS/` — not from `src/`

**`src/delivery/`:**
- Purpose: Push outputs to Obsidian vault (Markdown) and Telegram
- Contains: `obsidian_writer.py`, `telegram_bot.py`

**`config/`:**
- Purpose: Runtime configuration for the entire `src/` system
- Contains: Python settings module + 4 YAML config files
- Key files: `config/settings.py` (Pydantic-Settings), `config/tickers.yaml` (ticker registry), `config/sectors.yaml` (valuation methodology + thresholds)

**`data/`:**
- Purpose: All runtime data (not committed to version control)
- Generated: Yes — created automatically by `settings.model_post_init`
- Committed: No

**`news_hunter/`:**
- Purpose: Independent financial news crawling + Telegram bulletin system
- Contains: Self-contained crawler, classifier, SQLite store, Jinja2 bulletin, scheduler
- Note: Does NOT import from `src/`; runs independently via `python news_hunter/main.py`

**`pipeline banco completo/`:**
- Purpose: Older, separate bank analysis pipeline with Excel output and Streamlit UI
- Contains: Legacy modules with numbered prefixes + refactored versions, Streamlit app
- Note: Superseded by `src/` for new development; retained for reference and Excel output capability

**`notebooks/`:**
- Purpose: Exploratory analysis scripts (not notebooks — plain `.py` files named as notebooks)
- Contains: Pilot extractions, historical rebuilds, bank comparatives

## Key File Locations

**Entry Points:**
- `src/main.py`: Primary CLI — all commands routed here
- `src/scheduler.py`: Daemon scheduler — `start_scheduler()` blocks indefinitely
- `news_hunter/main.py`: News Hunter CLI — standalone, run from `news_hunter/` directory

**Configuration:**
- `config/settings.py`: All path + API key settings (reads `env` file)
- `config/tickers.yaml`: Active ticker list with `type`, `sector`, `priority`, `active` fields
- `config/cvm_codes.yaml`: Ticker → 6-digit CVM code mapping (required for ingestion)
- `config/sectors.yaml`: Valuation methodology, DCF assumptions, risk thresholds per sector type
- `config/schedules.yaml`: Cron expressions for each scheduler job

**Core Logic:**
- `src/processing/pipeline.py`: Main production pipeline (raw → processed → validated → JSON)
- `src/parsers/bank_parser.py`: Bank parsing + `BANK_REGISTRY` (central bank directory)
- `src/valuation/auto_dcf.py`: Valuation entry point for all sector types
- `src/valuation/sector_config.py`: `SectorConfig.for_ticker()` — maps any ticker to its config

**Data Interfaces:**
- `src/processing/storage.py`: `ProcessedStore` — read `data/processed/{TICKER}/dfp_{year}.json`
- `src/ingestion/cvm_downloader.py`: `get_cvm_code(ticker)` — resolve CVM code from YAML

## Naming Conventions

**Files:**
- `snake_case.py` throughout — e.g., `cvm_downloader.py`, `bank_account_mapper.py`
- Legacy `pipeline banco completo/modules/` uses numbered prefixes: `01_coletor_cvm.py`
- Config: `snake_case.yaml`

**Classes:**
- PascalCase: `CVMDownloader`, `B3Scraper`, `BankParser`, `DFPParser`, `ProcessingPipeline`, `MetricsEngine`, `SectorConfig`, `TelegramBot`, `ObsidianWriter`
- Dataclasses for result objects: `PipelineConfig`, `ExtractionResult`, `PeriodResult`, `ProcessingResult`, `ScenarioResult`, `Risk`

**Functions:**
- Top-level convenience functions use verb prefixes: `run_full_pipeline()`, `run_metrics()`, `run_valuation()`, `assess_risk()`, `process_ticker()`, `ingest_ticker()`
- Scheduler jobs: `job_<name>()` — e.g., `job_b3_prices()`, `job_morning_call()`

**Data files:**
- Processed: `dfp_{year}.json` (per ticker/year)
- Output: `metrics_{year}.json`, `risk_report.json`, `valuation.json`, `insights.json`
- Prices: `{TICKER}.parquet`

## Where to Add New Code

**New ticker:**
1. Add entry to `config/tickers.yaml` (ticker, type, sector, active, priority)
2. Add CVM code to `config/cvm_codes.yaml`
3. If new sector type, add methodology block to `config/sectors.yaml`
4. Run: `python -m src.main add-ticker TICKER --type TYPE --cvm-code XXXXXX`

**New ingestion source:**
- Implementation: `src/ingestion/{source_name}.py`
- Register as job: add function to `src/scheduler.py` `_JOB_REGISTRY`
- Schedule: add entry to `config/schedules.yaml`

**New analysis metric:**
- Implementation: `src/analysis/metrics_engine.py` (add to existing `MetricsEngine` class)
- If new risk rule: `src/analysis/risk_engine.py` + update thresholds in `config/sectors.yaml`

**New valuation method:**
- Implementation: `src/valuation/valuation_dcf.py` or new file in `src/valuation/`
- Register method name in `src/valuation/auto_dcf.py` dispatch logic
- Add methodology config to `config/sectors.yaml`

**New content format:**
- Implementation: `src/content/{format_name}.py`
- Add prompt template to Obsidian vault at `11_PROMPTS/PROMPT_{NAME}.md`
- Add LLM call via `src/content/llm_client.py`
- Schedule if recurring: add job to `src/scheduler.py` and `config/schedules.yaml`

**New delivery channel:**
- Implementation: `src/delivery/{channel}.py`
- Follow `TelegramBot` pattern: silent fallback when credentials not configured

**Utilities:**
- Shared helpers: `src/utils/` (logger, retry — keep minimal and generic)

## Special Directories

**`data/`:**
- Purpose: All runtime data (raw CVM ZIPs, prices, processed JSON, output reports)
- Generated: Yes — auto-created by `Settings.model_post_init` on first run
- Committed: No

**`logs/`:**
- Purpose: Application log files
- Generated: Yes — auto-created by `Settings.model_post_init`
- Committed: No

**`pipeline banco completo/outputs/`:**
- Purpose: Legacy Excel valuation outputs per ticker
- Generated: Yes — by legacy pipeline modules
- Committed: No (large binary files)

**`.ruff_cache/`:**
- Purpose: Ruff linter cache
- Generated: Yes — by ruff
- Committed: No

**`news_hunter/boletins/`:**
- Purpose: Generated bulletin text files
- Generated: Yes — by `news_hunter/gerar_boletim.py`
- Committed: No

---

*Structure analysis: 2026-05-06*
