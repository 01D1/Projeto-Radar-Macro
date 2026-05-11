---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: Phase 3 in progress — executing
last_updated: "2026-05-11"
planning_complete: "2026-05-11"
progress:
  total_phases: 5
  completed_phases: 2
  total_plans: 13
  completed_plans: 9
---

# Project State — Investment Intelligence Platform

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-06)

**Core value:** AI-powered investment decision engine — tells clients what to do and why, not just what's happening
**Current focus:** Phase 3 — Plan 01 complete, executing plans 02-05

---

## Active Phase

Phase 2: Reliable Data Ingestion — COMPLETE (2026-05-11)
Status: All 4 plans executed; 65/65 tests green; ING-01 through ING-07 satisfied

Phase 3: Financial Engine — IN PROGRESS (2026-05-11)
Status: Plans 01-02 complete; 77/77 tests green; FIN-01 partial, FIN-02 closed, BUG-01/GAP-02/D-01/D-06 closed
Current position: Plan 03 next (DCF engine)

---

## Decisions

- 2026-05-10 [01-01]: Venv recreated at OBSIDIAN root for Windows Python 3.10.11 (replacing stale macOS 3.9 artifact)
- 2026-05-10 [01-01]: pyproject.toml requires-python lowered to >=3.10 to match available Windows Python
- 2026-05-10 [01-01]: hatchling build config added with packages=[src, config, news_hunter]
- 2026-05-10 [01-01]: pyyaml added as explicit dependency (was implicit, missing from pyproject.toml)
- 2026-05-10 [01-01]: Both Task Scheduler tasks (ValuationBancario_Manha + Tarde) updated to vault path
- 2026-05-10 [01-02]: IsolatedSettings test pattern: subclass pydantic-settings BaseSettings with tmp_path env_file for env-file-dependent tests (env_ignore_empty=True incompatibility)
- 2026-05-10 [01-02]: patch('dotenv.load_dotenv') in test helpers when module under test loads .env at import time
- 2026-05-10 [01-02]: git rm --cached used to untrack env file before rename (file was previously committed)
- 2026-05-10 [01-02]: load_dotenv with explicit dotenv_path added to pipeline banco completo/config/settings.py (D-03 compliance)
- 2026-05-10 [02-01]: TEXT UUID PRIMARY KEY on all 4 ingestion tables (D-06: Supabase portability, no AUTOINCREMENT)
- 2026-05-10 [02-01]: INSERT OR IGNORE + UNIQUE INDEX for dedup (preserves ingested_at, cleaner than ON CONFLICT REPLACE)
- 2026-05-10 [02-01]: normalized_name=None in parse_and_store() — Phase 3 enrichment via ACCOUNT_MAP deferred
- 2026-05-10 [02-01]: extract_ipe_pdf_text() capped at 10 pages (T-02-03 mitigation)
- 2026-05-10 [02-01]: pandas-market-calendars pinned >=4.3.0, installed as 5.3.2
- 2026-05-11 [02-02]: BCB_SERIES dict contains exactly 5 series: selic_over(11), ipca_12m(433), ptax_usd(1), cds_brasil(29039), pib_nominal(4380)
- 2026-05-11 [02-02]: CDS Brasil series 29039 stored in decimal not basis points — raw / 10_000 at insert time
- 2026-05-11 [02-02]: adj_close = close column value after yfinance auto_adjust=True (no separate adj column)
- 2026-05-11 [02-02]: Gap rows inserted with NULL OHLCV prices (is_gap=1), never interpolated
- 2026-05-11 [02-02]: fetch_and_store() starts from MAX(date)+1day for existing tickers, DEFAULT_START only for new
- 2026-05-10 [02-03]: Cross-DB read pattern: open source connection, fetchall(), immediately close — no persistent handle to banco.db
- 2026-05-10 [02-03]: SELECT changes() per-row after INSERT OR IGNORE to count actual new inserts (not attempted rows)
- 2026-05-10 [02-03]: ticker_tags stores categoria as JSON list only when B3 regex matches; NULL otherwise (Phase 4 enrichment deferred)
- 2026-05-10 [02-03]: banco_db_path as explicit parameter (default BANCO_DB) enables clean test isolation with tmp_path
- 2026-05-11 [02-04]: bind_run_id("ingest") prefix used in all 4 new jobs — consistent run_id prefix for ingestion traceability
- 2026-05-11 [02-04]: b3_prices cron updated from 07:00 to 19:00 (post-B3-close) matching cvm_ingest window
- 2026-05-11 [02-04]: job_news_ingest uses subprocess.run list form — [sys.executable, main.py, --coletar], cwd=news_hunter, timeout=300
- 2026-05-11 [02-04]: Test pattern: sys.modules["config.settings"] for Pydantic Settings patch (not config.settings.settings)
- 2026-05-11 [02-04]: Test pattern: patch get_logger at source for D-15 log capture (jobs use internal _log not module-level log)
- 2026-05-11 [03-01]: EBITDA derivado como EBIT + D&A; ausência de linha DFC resulta em None (não 0) — evita falso positivo
- 2026-05-11 [03-01]: FCF=None quando cfo ou capex ausentes nos rows ITR (Pitfall 3) — "0 rows" distinto de "row com valor 0"
- 2026-05-11 [03-01]: is_bank=True força ebitda=None em _aggregate_ltm (Pitfall 2 — bancos não têm EBIT/EBITDA)
- 2026-05-11 [03-01]: test_db_schema.py atualizado para 8 tabelas; assertions alteradas para issubset em vez de igualdade exata
- 2026-05-11 [03-01]: AccountMapper._map_row chamado por row em parse_and_store() — _mapper = AccountMapper() instanciado uma vez antes do loop
- 2026-05-11 [03-02]: calculate_industrial_metrics() assinatura real requer ticker+year+params individuais (não dict) — adaptado no orchestrator sem alterar calculate_metrics.py (D-11)
- 2026-05-11 [03-02]: ev_revenue ausente de IndustrialMetrics — computado inline: (market_cap + net_debt) / net_revenue
- 2026-05-11 [03-02]: market_cap = price × shares_outstanding no orchestrator — nenhuma função de métricas o retorna diretamente
- 2026-05-11 [03-02]: compute_wacc() stub retorna fallback (0.12, 0.105, 0.015, True) em vez de NotImplementedError — mantém run_ticker() funcional antes do Plan 03-03

---

## Phase History

| Phase | Completed | Plans | Notes |
|-------|-----------|-------|-------|
| 01-foundation-and-cleanup | 2026-05-10 | 3/3 | 15/15 tests green; FOUND-01/02/03/04 closed |
| 02-reliable-data-ingestion | 2026-05-11 | 4/4 | 65/65 tests green; ING-01 through ING-07 closed |

---

## Performance Metrics

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 01-foundation-and-cleanup | 01 | 45min | 2 | 9 |
| 01-foundation-and-cleanup | 02 | 60min | 2 | 9 |
| 02-reliable-data-ingestion | 01 | 8min | 2 | 6 |
| 02-reliable-data-ingestion | 02 | 7min | 2 | 4 |
| 02-reliable-data-ingestion | 03 | 3min | 1 | 2 |
| 02-reliable-data-ingestion | 04 | 8min | 2 | 3 |
| 03-financial-engine | 01 | 8min | 2 | 7 |
| 03-financial-engine | 02 | 12min | 2 | 2 |

---

## Notes

- 2026-05-06: Phase 1 context gathered via /gsd-discuss-phase 1. Resume file: .planning/phases/01-foundation-and-cleanup/01-CONTEXT.md
- 2026-05-10: Plan 01-01 completed. Windows venv recreated, 5 test stub files created, pipeline.py cleaned, DEPRECATED.md added, schtasks updated.
- 2026-05-10: Plan 01-02 completed. Live Telegram token removed, env renamed to .env with gitignore protection, startup guards wired in config/settings.py + src/main.py + news_hunter/main.py, pipeline banco completo wired to .env. FOUND-02 requirement satisfied. 5/5 credential tests green.
- 2026-05-10: Plan 01-03 executed. FOUND-03 (errors.py + retry jitter + IngestionError), FOUND-04 (bind_run_id), CR-04 (startup guard moved inside app()) — all closed. 15/15 tests green.
- 2026-05-10: Phase 2 planned. 4 plans in 3 waves. Research confirmed CDS Brasil at BCB SGS series 29039; pdfplumber installed for IPE PDFs; pandas-market-calendars missing (Wave 0 task in Plan 02-01). ING-01 through ING-07 covered.
- 2026-05-10: Plan 02-01 completed. ingestion.db schema (4 tables, TEXT UUIDs), CVM DFP/ITR/IPE pipeline, 19/19 tests green. ING-01/02/03 satisfied.
- 2026-05-11: Plan 02-02 completed. BCB SGS ingestion (bcb.py, 5 series, CDS bp conversion), B3Scraper extended (write_to_db, detect_and_insert_gaps, fetch_and_store), 15/15 tests green. ING-04/05 satisfied.
- 2026-05-10: Plan 02-03 completed. news_sync.py cross-DB bridge (banco.db → news_articles), INSERT OR IGNORE URL dedup, B3 ticker regex tagging, 9/9 tests green. ING-06 satisfied.
- 2026-05-11: Plan 02-04 completed. 4 ingestion jobs wired into scheduler (_JOB_REGISTRY), schedules.yaml updated with 4 cron entries, 65/65 tests green. ING-07 satisfied. Phase 2 complete.
- 2026-05-11: Phase 3 context gathered via /gsd-discuss-phase 3. Resume file: .planning/phases/03-financial-engine/03-CONTEXT.md
- 2026-05-11: Plan 03-01 completed. BUG-01 (encoding), GAP-02 (import), D-01 (schema), D-06 (AccountMapper wire-up), FIN-01 partial (LTM). 74/74 tests green.
- 2026-05-11: Plan 03-02 completed. FIN-02 (multiples computation) — _get_current_price(), _compute_multiples() implementados, run_ticker() wired, 3 FIN-02 tests. 77/77 tests green.
  Last session: 2026-05-11T18:42:00Z
