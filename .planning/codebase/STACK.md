# Technology Stack

**Analysis Date:** 2026-05-06

## Languages

**Primary:**
- Python 3.11+ - All application code across all modules

**Secondary:**
- YAML - Configuration files (`config/tickers.yaml`, `config/cvm_codes.yaml`, `config/sectors.yaml`, `config/schedules.yaml`, `pipeline banco completo/config/empresas.yaml`)
- Markdown / Jinja2 - Report templates (`news_hunter/templates/boletim_mercado.j2`)
- Bash - Utility scripts (`bootstrap.sh`, `pipeline banco completo/atualizar.bat`)

## Runtime

**Environment:**
- Python 3.11 (minimum, declared in `pyproject.toml` `requires-python = ">=3.11"`)
- Virtual environment: `.venv/` at `Analista de Investimentos/12_PYTHON/.venv/`
- Ruff cache: `.ruff_cache/` at vault root (version 0.15.12)

**Package Manager:**
- pip with `requirements.txt` (root system) and `pyproject.toml` (primary)
- Lockfile: Not present — only version range constraints

## Frameworks

**Core:**
- Pydantic v2 (`>=2.5.0`) - Data validation, settings management
- Pydantic-Settings (`>=2.2.0`) - Environment-driven configuration via `config/settings.py`
- APScheduler (`>=3.10.0`) - Job scheduling daemon (`src/scheduler.py`)

**Web / HTTP:**
- Requests (`>=2.31.0`) - Primary HTTP client throughout all modules
- HTTPX (`>=0.27.0`) - Async HTTP (declared in `pyproject.toml`)
- Feedparser (`>=6.0.0`) - RSS feed parsing in `news_hunter/crawler.py`
- Cloudscraper (`>=1.2.71`) - Cloudflare bypass for scraping in `news_hunter/scrapers.py`
- BeautifulSoup4 (`>=4.12.0`) + lxml (`>=5.1.0`) - HTML parsing

**Data Processing:**
- Pandas (`>=2.1.0`) - DataFrames throughout all pipeline modules
- NumPy (`>=1.26.0`) - Numerical computation in valuation and analysis
- PyArrow (`>=14.0.0`) - Parquet file read/write for price series storage
- DuckDB (`>=0.9.0/0.10.0`) - Analytical queries (declared in both `pyproject.toml` and `requirements.txt`)

**Document Parsing:**
- PDFPlumber (`>=0.10.0`) - PDF extraction from CVM documents
- PyMuPDF (`>=1.24.0`) - PDF parsing (pipeline banco completo)
- OpenPyXL (`>=3.1.0`) - Excel read/write for valuation templates
- python-docx (`>=1.1.0`) - Word document parsing
- Jinja2 (`>=3.1.0`) - Template rendering for news bulletins

**AI / LLM:**
- Anthropic SDK (`>=0.39.0`/`>=0.40.0`) - Claude API client, used in `src/content/llm_client.py`
  - Model for content generation: `claude-sonnet-4-6` (configurable via `claude_model_content`)
  - Model for classification: `claude-haiku-4-5-20251001` (configurable via `claude_model_classify`)
  - Features used: prompt caching (`cache_control: ephemeral`), exponential backoff

**Dashboard / Visualization:**
- Streamlit (`>=1.34.0`) - Dashboard UI at `pipeline banco completo/streamlit_app.py`
- Plotly (`>=5.20.0`) - Charts (optional dependency in `pyproject.toml`)

**Delivery:**
- python-telegram-bot (`>=21.0.0`) - Telegram bot SDK (declared in `pyproject.toml`)
- Requests-based Telegram client also used directly in `news_hunter/telegram_client.py`

**Testing:**
- pytest (`>=7.4.0`/`>=8.0.0`) - Test runner; testpaths = `tests/`
- pytest-cov (`>=4.1.0`/`>=5.0.0`) - Coverage reports

**Build:**
- Hatchling - Build backend declared in `pyproject.toml`

## Key Dependencies

**Critical:**
- `anthropic>=0.39.0` - AI analysis and content generation; entire content layer depends on it (`src/content/llm_client.py`)
- `yfinance>=0.2.40` - Market price data from Yahoo Finance; used in both `src/ingestion/b3_scraper.py` and `pipeline banco completo/modules/coletor_mercado.py`
- `pydantic-settings>=2.2.0` - Central configuration management via `config/settings.py`; all modules depend on `settings` singleton
- `pandas>=2.1.0` + `pyarrow>=14.0.0` - Data layer for all financial series stored as Parquet
- `supabase>=2.0.0` - Cloud storage/database declared in `pyproject.toml`

**Infrastructure:**
- `loguru>=0.7.0` - Structured logging throughout `src/` (via `src/utils/logger.py`)
- `python-dotenv>=1.0.0` - `.env` / `env` file loading
- `apscheduler>=3.10.0` - Daemon scheduling in `src/scheduler.py` (runs daily pipeline at defined hours)
- `pdfplumber>=0.10.0` + `pymupdf>=1.24.0` - Document ingestion from CVM
- `openpyxl>=3.1.0` - Excel valuation template generation

**Quality:**
- `ruff>=0.1.0` - Linter/formatter (target `py311`, line-length 100)
- `black>=23.0.0` - Formatter (also declared in `requirements.txt`)

## Configuration

**Environment:**
- Settings loaded from `env` file (no dot prefix) or `.env` via `pydantic-settings`
- Config class: `config/settings.py` → `Settings(BaseSettings)` singleton `settings`
- Key env vars required:
  - `ANTHROPIC_API_KEY` - Anthropic Claude API
  - `SUPABASE_URL` + `SUPABASE_KEY` - Supabase cloud database
  - `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` - Telegram delivery
- Optional overrides: `ENV`, `CLAUDE_MODEL_CONTENT`, `CLAUDE_MODEL_CLASSIFY`, `CVM_BASE_URL`

**Build:**
- `pyproject.toml` at `Analista de Investimentos/12_PYTHON/pyproject.toml` - primary project definition
- `pyproject.toml` also defines `[tool.ruff]` and `[tool.pytest.ini_options]`
- Entry point: `intelligence = "src.main:app"` (CLI)

**YAML Config Files:**
- `config/tickers.yaml` - Active tickers with `active: true/false` flags
- `config/cvm_codes.yaml` - Ticker → CVM code mapping
- `config/sectors.yaml` - Sector classification
- `config/schedules.yaml` - APScheduler job definitions
- `pipeline banco completo/config/empresas.yaml` - Per-company assumptions and RI URLs

## Platform Requirements

**Development:**
- Python 3.11+ with pip
- Virtual environment at `Analista de Investimentos/12_PYTHON/.venv/`
- Windows (path conventions in `.bat` files); also runs on Unix via `bootstrap.sh`
- Obsidian vault at parent directory (`vault_path = ROOT.parent`)

**Production:**
- Local machine execution (no container or cloud hosting detected)
- Daemon mode via `python -m src.main daemon` (APScheduler)
- Streamlit dashboard via `streamlit run pipeline\ banco\ completo/streamlit_app.py`
- Scheduled jobs run during Brazilian market hours (07:00–20:30 BRT)

---

*Stack analysis: 2026-05-06*
