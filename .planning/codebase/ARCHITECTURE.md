<!-- refreshed: 2026-05-06 -->
# Architecture

**Analysis Date:** 2026-05-06

## System Overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLI Entry Point                               │
│              `src/main.py` — python -m src.main <command>               │
│              `src/scheduler.py` — daemon mode (APScheduler)             │
└──────────┬──────────────────┬──────────────────┬────────────────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌──────────────────┐ ┌───────────────────┐ ┌──────────────────────────────┐
│   Ingestion      │ │   Processing      │ │  Content / Delivery          │
│ `src/ingestion/` │ │ `src/processing/` │ │ `src/content/`               │
│  cvm_downloader  │ │  pipeline.py      │ │  morning_call.py             │
│  b3_scraper      │ │  storage.py       │ │  post_generator.py           │
└──────────┬───────┘ └────────┬──────────┘ │  thesis_builder.py           │
           │                  │            │  llm_client.py               │
           ▼                  ▼            └──────────────┬───────────────┘
┌──────────────────────────────────────────┐              │
│              Parsers                     │              ▼
│           `src/parsers/`                 │ ┌──────────────────────────────┐
│  dfp_parser.py   — industriais (CVM CSV) │ │       Delivery               │
│  bank_parser.py  — bancos (COSIF/IFRS)  │ │    `src/delivery/`           │
└──────────────────┬───────────────────────┘ │  obsidian_writer.py          │
                   │                         │  telegram_bot.py             │
                   ▼                         └──────────────────────────────┘
┌──────────────────────────────────────────┐
│           Normalization + Validation      │
│   `src/normalization/`  `src/validation/` │
│  account_mapper.py   bank_account_mapper  │
│  schemas.py   bank_schemas.py (Pydantic)  │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Analysis + Valuation                           │
│           `src/analysis/`              `src/valuation/`          │
│  metrics_engine.py   risk_engine.py    auto_dcf.py               │
│  insight_engine.py   detect_inconsis.  valuation_dcf.py          │
│  earnings_quality.py                   sector_config.py          │
└──────────────────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Data Stores                                 │
│  data/raw/cvm/DFP/{year}/*.csv     — CVM ZIP extracts            │
│  data/raw/prices/{TICKER}.parquet  — B3 price history            │
│  data/processed/{TICKER}/dfp_{year}.json  — parsed statements    │
│  data/output/{TICKER}/metrics.json  risk_report.json  valuation  │
│  Obsidian Vault (03_COMPANIES/, 14_OUTPUTS/)  — Markdown notes   │
└──────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI | Argparse entry point; dispatches to all subsystems | `src/main.py` |
| Scheduler | APScheduler daemon; runs 9 jobs on cron schedule | `src/scheduler.py` |
| CVMDownloader | Downloads + extracts ZIP bundles from dados.cvm.gov.br | `src/ingestion/cvm_downloader.py` |
| B3Scraper | Fetches OHLCV prices via yfinance; saves Parquet | `src/ingestion/b3_scraper.py` |
| DFPParser | Filters CVM CSVs by CD_CVM; returns dict of DataFrames | `src/parsers/dfp_parser.py` |
| BankParser | Wraps DFPParser + BankAccountMapper → BankStatements | `src/parsers/bank_parser.py` |
| AccountMapper | Normalizes account names/codes to canonical fields | `src/normalization/account_mapper.py` |
| BankAccountMapper | Bank-specific COSIF/IFRS code → field mapping | `src/normalization/bank_account_mapper.py` |
| BankStatements | Pydantic v2 schema for bank financial statements | `src/validation/bank_schemas.py` |
| ProcessingPipeline | Orchestrates raw → parsed → validated → JSON | `src/processing/pipeline.py` |
| ProcessedStore | Read-only interface over data/processed/ JSONs | `src/processing/storage.py` |
| MetricsEngine | Computes financial ratios from processed data | `src/analysis/metrics_engine.py` |
| RiskEngine | Rule-based risk scoring using sector thresholds | `src/analysis/risk_engine.py` |
| InsightEngine | Deterministic insight generation from metrics | `src/analysis/insight_engine.py` |
| AutoDCF | Sector-aware valuation (Gordon/DDM/DCF/EV-EBITDA) | `src/valuation/auto_dcf.py` |
| SectorConfig | Loads config/sectors.yaml; maps ticker → methodology | `src/valuation/sector_config.py` |
| LLMClient | Anthropic Claude wrapper with caching + retry | `src/content/llm_client.py` |
| MorningCall | Daily market brief generated via Claude | `src/content/morning_call.py` |
| PostGenerator | Ticker-specific analyst post via Claude | `src/content/post_generator.py` |
| ThesisBuilder | Full investment thesis via Claude | `src/content/thesis_builder.py` |
| ObsidianWriter | Writes/updates Markdown notes in Obsidian vault | `src/delivery/obsidian_writer.py` |
| TelegramBot | Sends messages, alerts, files to Telegram channel | `src/delivery/telegram_bot.py` |
| Settings | Pydantic-Settings config with .env loading | `config/settings.py` |

## Pattern Overview

**Overall:** Layered ETL pipeline with deterministic analysis and LLM-powered content generation

**Key Characteristics:**
- Sector-driven polymorphism: `bank` vs `industrial` type routes to different parsers, mappers, schemas, and valuation methods throughout the entire stack
- Config-as-code: sector thresholds, valuation assumptions, ticker registry, and cron schedules all live in YAML files under `config/`; code reads them at runtime with no hardcoded values
- Idempotent stages with `force=False` guard: every stage checks for existing output before recomputing — safe to re-run partially failed pipelines
- Single-process, sequential execution: no worker threads or async I/O in the main pipeline; APScheduler jobs run one at a time (`max_instances=1`)

## Layers

**Ingestion:**
- Purpose: Acquire raw data from external sources (CVM, B3/yfinance)
- Location: `src/ingestion/`
- Contains: `cvm_downloader.py`, `b3_scraper.py`
- Depends on: `config/cvm_codes.yaml`, `config/settings.py`, `src/utils/retry.py`
- Used by: `src/processing/pipeline.py`, `src/scheduler.py` (via `job_cvm_check`, `job_b3_prices`)

**Parsers:**
- Purpose: Transform raw CVM CSVs into structured Python objects
- Location: `src/parsers/`
- Contains: `dfp_parser.py` (industrials), `bank_parser.py` (banks)
- Depends on: `src/normalization/`, `src/validation/bank_schemas.py`
- Used by: `src/processing/pipeline.py`, `src/pipeline.py`

**Normalization:**
- Purpose: Map heterogeneous CVM account codes/names to canonical field names
- Location: `src/normalization/`
- Contains: `account_mapper.py` (industrials), `bank_account_mapper.py` (banks)
- Depends on: `src/parsers/dfp_parser.py` (imports ACCOUNT_MAP constant)
- Used by: `src/parsers/bank_parser.py`, `src/parsers/dfp_parser.py`

**Validation:**
- Purpose: Pydantic v2 schema enforcement + balance-sheet consistency checks
- Location: `src/validation/`
- Contains: `bank_schemas.py`, `schemas.py`, `reconciler.py`
- Depends on: pydantic v2
- Used by: `src/parsers/bank_parser.py`, `src/processing/pipeline.py`

**Processing:**
- Purpose: Orchestrate raw → parsed → validated → persisted JSON; provide read interface
- Location: `src/processing/`
- Contains: `pipeline.py` (write), `storage.py` (read)
- Depends on: all parsers, normalization, validation layers
- Used by: `src/scheduler.py` (via `job_pipeline`), `src/main.py`

**Analysis:**
- Purpose: Compute financial metrics, risk scores, and rule-based insights from processed data
- Location: `src/analysis/`
- Contains: `metrics_engine.py`, `risk_engine.py`, `insight_engine.py`, `detect_inconsistencies.py`, `earnings_quality.py`
- Depends on: `src/processing/storage.py`, `src/valuation/sector_config.py`
- Used by: `src/scheduler.py` (via `job_analyze`), `src/main.py`

**Valuation:**
- Purpose: Sector-appropriate company valuation (Gordon Growth, DDM, DCF FCFF, EV/EBITDA)
- Location: `src/valuation/`
- Contains: `auto_dcf.py`, `valuation_dcf.py`, `calculate_metrics.py`, `sector_config.py`
- Depends on: `config/sectors.yaml`, `config/tickers.yaml`, `src/analysis/metrics_engine.py`
- Used by: `src/scheduler.py` (via `job_analyze`), `src/main.py`

**Content:**
- Purpose: Generate human-readable analysis via Claude API (morning call, posts, investment theses)
- Location: `src/content/`
- Contains: `llm_client.py`, `morning_call.py`, `post_generator.py`, `thesis_builder.py`
- Depends on: `src/analysis/`, `src/valuation/`, Anthropic SDK, Obsidian prompts at `11_PROMPTS/`
- Used by: `src/scheduler.py` (via `job_morning_call`, `job_content`), `src/main.py`

**Delivery:**
- Purpose: Push outputs to Obsidian vault and Telegram
- Location: `src/delivery/`
- Contains: `obsidian_writer.py`, `telegram_bot.py`
- Depends on: `config/settings.py`, requests (Telegram HTTP API)
- Used by: `src/content/`, `src/scheduler.py`

**Utilities:**
- Purpose: Cross-cutting concerns (logging, retry)
- Location: `src/utils/`
- Contains: `logger.py`, `retry.py`
- Depends on: nothing internal
- Used by: all layers

## Data Flow

### Primary Pipeline (full cycle per ticker/year)

1. **Download** — `CVMDownloader.download_dfp(year)` fetches ZIP from `https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/DFP/DADOS/`, extracts to `data/raw/cvm/DFP/{year}/*.csv` (`src/ingestion/cvm_downloader.py`)
2. **Price fetch** — `B3Scraper.fetch(ticker)` pulls OHLCV via yfinance, saves `data/raw/prices/{TICKER}.parquet` (`src/ingestion/b3_scraper.py`)
3. **Route** — `ProcessingPipeline._process_year()` checks `tickers.yaml` for `type=bank` vs `type=industrial` (`src/processing/pipeline.py`)
4. **Parse** — `BankParser.parse()` or `DFPParser.parse_company()` filters CSVs by `CD_CVM`, applies account mapping (`src/parsers/`)
5. **Validate** — `BankInconsistencyDetector.check()` verifies balance sheet integrity; `BankStatements` Pydantic model enforces schema (`src/validation/`)
6. **Persist** — Validated data saved as `data/processed/{TICKER}/dfp_{year}.json` (`src/processing/pipeline.py`)
7. **Metrics** — `MetricsEngine` loads processed JSON via `ProcessedStore`, computes ratios, saves `data/output/{TICKER}/metrics_{year}.json` (`src/analysis/metrics_engine.py`)
8. **Risk** — `RiskEngine.assess_risk()` applies sector thresholds from `config/sectors.yaml`, saves `data/output/{TICKER}/risk_report.json` (`src/analysis/risk_engine.py`)
9. **Valuation** — `AutoDCF.run_valuation()` selects method from `SectorConfig`, computes scenarios, saves `data/output/{TICKER}/valuation.json` (`src/valuation/auto_dcf.py`)
10. **Insights** — `InsightEngine.generate()` produces rule-based observations, saves `data/output/{TICKER}/insights.json` (`src/analysis/insight_engine.py`)
11. **Content** — `LLMClient` sends prompts + metrics to Claude API; output written to Obsidian vault via `ObsidianWriter` (`src/content/`, `src/delivery/obsidian_writer.py`)
12. **Notify** — `TelegramBot.send_*()` pushes summaries, alerts, and files to configured Telegram channel (`src/delivery/telegram_bot.py`)

### Scheduler Daily Cycle (weekdays, America/Sao_Paulo)

1. `06:00` → `job_news_fetcher` — collect overnight news (stub; `news_hunter/` is a separate system)
2. `06:30` → `job_morning_call` — generate + deliver morning call via Claude
3. `07:00` → `job_b3_prices` — update prices for all active tickers
4. `19:00` → `job_cvm_check` — check for new CVM filings
5. `19:30` → `job_pipeline` — process any new raw data
6. `20:00` → `job_analyze` — recalculate metrics + risk + valuation + insights
7. `20:30` → `job_content` — generate posts if new analysis exists today
8. `*/hour` → `job_health_check` — system health report to Telegram
9. `Sunday 10:00` → `job_weekly_review` — weekly portfolio summary

### News Hunter Flow (independent sub-system)

1. `news_hunter/crawler.py` + `news_hunter/scrapers.py` — fetch RSS/HTML from financial sources
2. `news_hunter/classificador.py` — score articles by keyword matching
3. `news_hunter/banco.py` — persist to SQLite (`banco.db`)
4. `news_hunter/gerar_boletim.py` — render Jinja2 template (`boletins/boletim_*.txt`)
5. `news_hunter/telegram_client.py` — send to Telegram at scheduled times
6. `news_hunter/agendador.py` — independent APScheduler at 07:30, 12:00, 18:00

**State Management:**
- Processed data persisted as JSON files under `data/processed/` and `data/output/`
- `force=False` guards prevent reprocessing: each stage checks output path existence before running
- Ticker registry and sector config loaded fresh from YAML on each invocation (sector_config uses `@lru_cache` to avoid repeated file reads within a single process run)

## Key Abstractions

**BankStatements / FinancialStatements:**
- Purpose: Typed containers for a single company/year's financial statements
- Examples: `src/validation/bank_schemas.py` (Pydantic v2 models: `BankStatements`, `BankIncomeStatement`, `BankBalanceSheet`, `BankAssets`, `BankLiabilities`, `BankCashFlow`)
- Pattern: Pydantic `BaseModel` with `model_dump()` for JSON serialization

**SectorConfig:**
- Purpose: Load sector-specific valuation methodology, DCF assumptions, and risk thresholds from `config/sectors.yaml`
- Examples: `src/valuation/sector_config.py`
- Pattern: Static factory `SectorConfig.for_ticker(ticker)` → resolves ticker type → looks up sectors dict

**PipelineConfig / ProcessingPipeline:**
- Purpose: Dataclass config + pipeline class pattern used consistently across `src/pipeline.py` and `src/processing/pipeline.py`
- Pattern: `Config` dataclass holds all parameters; `Pipeline` class receives config in `__init__`, exposes `run()` method

**BANK_REGISTRY:**
- Purpose: Central dictionary mapping ticker → `{cvm_code, name, bank_type, is_standard_bank}` for all supported banks
- Location: `src/parsers/bank_parser.py` (module-level `BANK_REGISTRY` dict)
- Pattern: Imported by `src/pipeline.py` to determine routing at class load time

## Entry Points

**Primary CLI:**
- Location: `src/main.py`
- Triggers: `python -m src.main <command>`
- Commands: `ingest`, `process`, `analyze`, `content`, `add-ticker`, `status`, `daemon`, `run-job`, `jobs`, `test`

**Daemon Scheduler:**
- Location: `src/scheduler.py` — `start_scheduler()` function, `IntelligenceScheduler` class
- Triggers: `python -m src.main daemon` or `from src.scheduler import start_scheduler; start_scheduler()`
- Responsibilities: Loads `config/schedules.yaml`, registers APScheduler cron jobs, sends Telegram startup notification

**Legacy Pipeline Runner (src-level):**
- Location: `src/pipeline.py` — `run_full_pipeline()`, `Pipeline` class
- Triggers: `python src/pipeline.py` (standalone script)
- Note: Older orchestrator; `src/processing/pipeline.py` is the current production path invoked by scheduler

**News Hunter:**
- Location: `news_hunter/main.py`
- Triggers: `python main.py --coletar-gerar-enviar` (run from within `news_hunter/` directory)
- Responsibilities: Crawl → classify → store → bulletin → Telegram; fully self-contained

**Legacy Bank Pipeline:**
- Location: `pipeline banco completo/teste_pipeline.py`, `pipeline banco completo/scheduler.py`
- Note: Separate, older pipeline for bank analysis with its own modules, config, and Excel output; superseded by `src/`

## Architectural Constraints

- **Threading:** Single-threaded per job; APScheduler `max_instances=1` prevents concurrent runs of the same job
- **Global state:** `settings` singleton instantiated at module load in `config/settings.py`; `_CVM_CODES` global cache in `src/ingestion/cvm_downloader.py`; `_BANK_REGISTRY` imported as class attribute in `src/pipeline.py` at class definition time
- **Path manipulation:** Several modules call `sys.path.insert(0, src_path)` before importing sibling packages (`src/processing/pipeline.py::_ensure_src_path`); this is a workaround for mixed import styles (some files use `from parsers.x import` without `src.` prefix)
- **Import duality:** `src/parsers/` modules use bare imports (`from normalization.bank_account_mapper import`) expecting `src/` on `sys.path`; `src/scheduler.py` and `src/main.py` use `from src.xxx import` — both styles coexist

## Anti-Patterns

### Mixed import style (bare vs. `src.`-prefixed)

**What happens:** `src/parsers/bank_parser.py` uses `from normalization.bank_account_mapper import ...` while `src/scheduler.py` uses `from src.content.morning_call import ...`. `_ensure_src_path()` is called in multiple files to patch `sys.path` at runtime.
**Why it's wrong:** Makes the package uninstallable as a proper Python package; breaks IDE navigation; causes `ImportError` if `src/` is not on `sys.path` at import time.
**Do this instead:** Standardize all internal imports to `from src.normalization.bank_account_mapper import ...` and add a proper `pyproject.toml` package entry point, or use relative imports (`from ..normalization.bank_account_mapper import ...`).

### Two pipeline orchestrators

**What happens:** Both `src/pipeline.py` (`Pipeline` class) and `src/processing/pipeline.py` (`ProcessingPipeline` class) orchestrate the same raw → parsed → persisted flow. The scheduler calls `src/processing/pipeline.py`; `src/pipeline.py` is a standalone script.
**Why it's wrong:** Logic duplication; unclear which is authoritative; risk of diverging behavior.
**Do this instead:** Retire `src/pipeline.py` or reduce it to a thin wrapper over `src/processing/pipeline.py`.

### Hardcoded CVM code in pipeline

**What happens:** `src/pipeline.py::_process_industrial` has `INDUSTRIAL_CVM = {"WEGE3": "005410"}` hardcoded instead of reading from `config/cvm_codes.yaml`.
**Why it's wrong:** Any new industrial ticker requires code change, not config change.
**Do this instead:** Call `get_cvm_code(ticker)` from `src/ingestion/cvm_downloader.py` (which reads `cvm_codes.yaml`) — as `src/processing/pipeline.py` already does correctly.

## Error Handling

**Strategy:** Log-and-continue with structured result objects; never silently discard failures

**Patterns:**
- Pipeline stages return dataclasses (`ExtractionResult`, `PeriodResult`, `ProcessingResult`) with `success: bool` and `error: str | None` fields — callers inspect results rather than catching exceptions
- `src/utils/retry.py` provides a `retry` decorator used by `CVMDownloader` and `B3Scraper` for transient network errors
- `TelegramBot` operates in silent mode (log-only) when token is not configured, so missing credentials never crash the pipeline
- `IntelligenceScheduler._run_job()` wraps every scheduled job in try/except, reports via Telegram, and continues to next job

## Cross-Cutting Concerns

**Logging:** `src/utils/logger.py` — `get_logger(__name__)` returns a configured logger; `configure_logging(logs_dir, level=)` called once at startup in `src/main.py`
**Validation:** Pydantic v2 (`BankStatements` and related models in `src/validation/bank_schemas.py`); balance-sheet consistency checked by `BankInconsistencyDetector` in `src/analysis/detect_inconsistencies.py`
**Configuration:** `config/settings.py` — `pydantic-settings` `BaseSettings` reads from `.env` or `env` file; YAML files (`tickers.yaml`, `cvm_codes.yaml`, `sectors.yaml`, `schedules.yaml`) loaded lazily

---

*Architecture analysis: 2026-05-06*
