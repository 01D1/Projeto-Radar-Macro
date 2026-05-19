# Stack Research — Investment Intelligence Platform

## Recommended Stack

### Core Runtime
- **Python 3.11+** — stable async support, pattern matching, performance improvements
- **uv** (package manager) — significantly faster than pip/poetry; or keep existing venv + pip if migration cost is high
- **python-dotenv** — `.env` config management (already implied by existing structure)
- **ruff** — already in use; keep for linting + formatting (replaces black + flake8 + isort)

### Financial Data Ingestion
| Library | Version | Purpose | Confidence |
|---|---|---|---|
| `yfinance` | ≥0.2.40 | B3 price series, corporate actions | High — already in use |
| `requests` + `httpx` | ≥0.27 | CVM/BCB HTTP calls, async-capable | High |
| `tenacity` | ≥8.3 | Retry logic with exponential backoff for all API calls | High — critical |
| `beautifulsoup4` | ≥4.12 | HTML parsing for news/CVM pages | Medium |
| `feedparser` | ≥6.0 | RSS feed ingestion (already used) | High |
| `pdfplumber` | ≥0.11 | PDF text extraction for CVM filings (IPE/DFP PDFs) | High |

### Data Processing
| Library | Version | Purpose | Confidence |
|---|---|---|---|
| `pandas` | ≥2.2 | Time series, financial data manipulation | High — already in use |
| `numpy` | ≥1.26 | DCF calculations, array operations | High |
| `pydantic` | ≥2.7 | Schema validation for all data models (replaces ad-hoc dicts) | High — critical |
| `pandera` | ≥0.20 | DataFrame schema validation at pipeline boundaries | Medium |

### LLM Integration
| Library | Version | Purpose | Confidence |
|---|---|---|---|
| `anthropic` | ≥0.28 | Claude API — already integrated | High |
| `jinja2` | ≥3.1 | Prompt template management (separates prompts from logic) | High |
| `instructor` | ≥1.4 | Structured outputs from Claude (Pydantic models from LLM responses) | High — critical for thesis generation |

**LLM patterns:**
- Use `instructor` + Pydantic to guarantee structured thesis output (no free-form parsing)
- Prompt caching already enabled — keep for all system prompts
- Use `claude-haiku-4-5` for classification/routing tasks, `claude-sonnet-4-6` for thesis generation
- Batch analysis requests per ticker to reduce API round trips

### Dashboard
| Library | Version | Purpose | Confidence |
|---|---|---|---|
| `streamlit` | ≥1.35 | Primary dashboard framework | High |
| `plotly` | ≥5.22 | Interactive charts (candlestick, time series, waterfall for DCF) | High |
| `streamlit-aggrid` | ≥0.3 | Institutional-quality data tables | Medium |

**Streamlit institutional patterns:**
- Multi-page app via `pages/` directory structure
- `st.cache_data` with TTL for financial data (avoid re-fetching on every interaction)
- Session state for watchlist persistence across pages
- Custom CSS for institutional look (dark theme, table formatting)

### Data Storage
| Library | Version | Purpose | Confidence |
|---|---|---|---|
| `sqlalchemy` | ≥2.0 | ORM abstraction over SQLite — same code works on Supabase (PostgreSQL) | High — critical for migration path |
| `alembic` | ≥1.13 | Schema migrations (version-controlled) | High |
| `supabase` | ≥2.0 | Cloud persistence (declared, not yet wired) | Medium |

**SQLite → Supabase migration path:**
- Use SQLAlchemy Core (not ORM) for financial data — easier to swap dialects
- Avoid SQLite-specific types (use TEXT for JSON, REAL for decimals)
- Store raw API responses as JSON blobs for reprocessing without re-fetching

### Report Generation
| Library | Version | Purpose | Confidence |
|---|---|---|---|
| `weasyprint` | ≥62 | HTML→PDF, CSS-styled institutional reports | High |
| `jinja2` | ≥3.1 | HTML report templates | High |

**Alternative:** `reportlab` (more complex, better for pixel-perfect layouts) — not recommended unless weasyprint proves insufficient.

### Configuration & Scheduling
| Library | Version | Purpose | Confidence |
|---|---|---|---|
| `python-dotenv` | ≥1.0 | .env loading | High |
| `pydantic-settings` | ≥2.3 | Typed settings from env vars (validates on startup) | High |
| `APScheduler` | ≥3.10 | Cron-style scheduling for pipeline runs | Medium |
| `structlog` | ≥24.1 | Structured JSON logging across all modules | High |

---

## What NOT to Use

| Library | Avoid Because |
|---|---|
| `langchain` | Heavy abstraction, anthropic SDK is sufficient; LangChain adds complexity without value here |
| `llama-index` | Same — overengineered for this use case |
| `FastAPI` | No API server needed in v1; Streamlit handles UI |
| `celery` | Redis/broker overhead; APScheduler sufficient for single-machine scheduling |
| `reportlab` | Steep learning curve; weasyprint + Jinja2 HTML templates are faster to maintain |
| `matplotlib` | Use plotly — interactive charts are standard in financial dashboards |
| `poetry` | uv is faster; if staying with pip+venv, don't add poetry overhead |

---

## Confidence Levels Summary
- **High confidence**: tenacity, pydantic, instructor, sqlalchemy+alembic, weasyprint, structlog
- **Medium confidence**: pandera (may be overkill given pydantic), APScheduler (vs simple cron), streamlit-aggrid
- **Low risk additions**: all above are actively maintained 2025/2026 libraries

---
*Researched: 2026-05-06*
