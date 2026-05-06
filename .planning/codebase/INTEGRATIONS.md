# External Integrations
<!-- last_mapped: 2026-05-06 -->

## Summary

| Integration | Type | Usage | Auth |
|---|---|---|---|
| Anthropic Claude API | LLM | Content generation, analysis | `ANTHROPIC_API_KEY` env var |
| Telegram Bot API | Messaging | News delivery, alerts | `TELEGRAM_TOKEN` env var |
| CVM (dados.cvm.gov.br) | Public Data | Financial statements (DFP/ITR/IPE) | None (public) |
| BCB PTAX (olinda.bcb.gov.br) | Public Data | Exchange rates | None (public) |
| BCB SGS (api.bcb.gov.br) | Public Data | Macroeconomic series | None (public) |
| Yahoo Finance (yfinance) | Market Data | B3 stock price series | None (public) |
| Supabase | Database | Cloud storage (declared, not wired) | `SUPABASE_URL`, `SUPABASE_KEY` |
| SQLite | Database | Local data persistence | None (file-based) |
| RSS Feeds | News | Financial news aggregation | None (public) |
| Obsidian vault | Local FS | Analysis output delivery | None (local) |

---

## Anthropic Claude API

- **Files:** `Analista de Investimentos/12_PYTHON/src/content/llm_client.py`
- **Models used:** `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`
- **Features:** Prompt caching enabled
- **Auth:** `ANTHROPIC_API_KEY` environment variable

---

## Telegram Bot API

Two independent Telegram clients exist:

- **`src/delivery/telegram_bot.py`** — main pipeline delivery
- **`news_hunter/telegram_client.py`** — news hunter delivery

- **Auth:** `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` — read from env vars (defaults visible in `news_hunter/config.py` lines 60–61, should be overridden via env)

---

## CVM — Comissão de Valores Mobiliários

- **URL:** `dados.cvm.gov.br`
- **Data:** DFP (annual), ITR (quarterly), IPE (events) — downloaded as ZIP files
- **Files:**
  - `Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py`
  - `Analista de Investimentos/12_PYTHON/pipeline banco completo/modules/01_coletor_cvm.py`
- **Auth:** None (public open data)

---

## BCB PTAX — Exchange Rates

- **URL:** `olinda.bcb.gov.br`
- **Data:** USD/BRL exchange rates
- **Files:** `Analista de Investimentos/12_PYTHON/news_hunter/scrapers.py` (inferred)
- **Auth:** None (public)

---

## BCB SGS — Macroeconomic Series

- **URL:** `api.bcb.gov.br`
- **Data:** Selic rate, IPCA inflation, GDP (PIB), CDS spreads
- **Files:** `Analista de Investimentos/12_PYTHON/pipeline banco completo/modules/03_coletor_macro.py`
- **Auth:** None (public)

---

## Yahoo Finance (yfinance)

- **Library:** `yfinance` Python package
- **Data:** B3 stock price series
- **Files:**
  - `Analista de Investimentos/12_PYTHON/src/ingestion/b3_scraper.py`
  - `Analista de Investimentos/12_PYTHON/pipeline banco completo/modules/02_coletor_mercado.py`
- **Auth:** None (public)

---

## Supabase

- **Status:** Declared in `pyproject.toml` (`supabase>=2.0.0`), not yet fully wired in source code
- **Intended use:** Cloud database storage
- **Auth:** `SUPABASE_URL`, `SUPABASE_KEY` environment variables (anticipated)

---

## SQLite (Local Databases)

Two local SQLite databases:

- `Analista de Investimentos/12_PYTHON/news_hunter/banco.db` — news/articles storage
- `Analista de Investimentos/12_PYTHON/pipeline banco completo/data/valuation.db` — valuation results

---

## RSS Feeds

- **Config:** `Analista de Investimentos/12_PYTHON/news_hunter/fontes.txt`
- **Sources:** 17+ feeds including InfoMoney, Brazil Journal, CNBC, MarketWatch, Yahoo Finance, and others
- **Usage:** Financial news aggregation for the news hunter module

---

## Obsidian Vault (Local Filesystem)

- **File:** `Analista de Investimentos/12_PYTHON/src/delivery/obsidian_writer.py`
- **Usage:** Writes analysis output (reports, notes) directly into the Obsidian vault directory structure
- **Auth:** None (local filesystem write)

---

*Last mapped: 2026-05-06*
