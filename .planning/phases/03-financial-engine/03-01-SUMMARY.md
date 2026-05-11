---
phase: 03-financial-engine
plan: 01
subsystem: database
tags: [sqlite, financial-engine, ltm, account-mapper, sector-config, python]

requires:
  - phase: 02-reliable-data-ingestion
    provides: ingestion.db com cvm_statements, macro_series, price_ohlcv, news_articles

provides:
  - financial_ltm, financial_multiples, financial_dcf, financial_signals tables in ingestion.db
  - src/financial_engine.py com run_ticker(), run_all(), _aggregate_ltm(), backfill_normalized_names()
  - AccountMapper wired em cvm_downloader.parse_and_store() — normalized_name preenchido no write
  - BUG-01 fechado: sector_config.py encoding=utf-8 (sem UnicodeDecodeError no Windows)
  - GAP-02 fechado: account_mapper.py import path corrigido para src.parsers.dfp_parser

affects: [03-02-multiples, 03-03-dcf, 03-04-bank-model, 03-05-signals, 04-intelligence-layer]

tech-stack:
  added: []
  patterns:
    - "_aggregate_ltm(): DISTINCT reference_date LIMIT 4 para trailing 4 ITR quarters"
    - "FLOW_ITEMS somados; SNAPSHOT_ITEMS: latest reference_date vence"
    - "EBITDA = EBIT + D&A; FCF = CFO - abs(capex); None quando inputs ausentes"
    - "Parameterized queries everywhere — nunca f-string com ticker (T-03-01-01)"
    - "ltm_reconciliation_warning=1 quando |LTM-DFP revenue| > 5% (D-07)"
    - "INSERT OR REPLACE keyed by (ticker, computed_date) — one row per day (D-04)"

key-files:
  created:
    - Analista de Investimentos/12_PYTHON/src/financial_engine.py
    - Analista de Investimentos/12_PYTHON/tests/test_financial_db_schema.py
    - Analista de Investimentos/12_PYTHON/tests/test_financial_engine.py
  modified:
    - Analista de Investimentos/12_PYTHON/src/valuation/sector_config.py
    - Analista de Investimentos/12_PYTHON/src/normalization/account_mapper.py
    - Analista de Investimentos/12_PYTHON/src/ingestion/db.py
    - Analista de Investimentos/12_PYTHON/src/ingestion/cvm_downloader.py
    - Analista de Investimentos/12_PYTHON/tests/test_db_schema.py

key-decisions:
  - "EBITDA derivado como EBIT + D&A — ausência de linha DFC resulta em None, não 0"
  - "FCF=None quando cfo ou capex ausentes nos rows ITR (Pitfall 3 evitado)"
  - "is_bank=True força ebitda=None em _aggregate_ltm (Pitfall 2 evitado)"
  - "backfill_normalized_names usa parameterized UPDATE (T-03-01-05)"
  - "test_db_schema.py atualizado para 8 tabelas (4 ingestion + 4 financial)"
  - "AccountMapper._map_row chamado em parse_and_store() por row (não em batch)"

patterns-established:
  - "Pattern LTM: DISTINCT ref_dates LIMIT 4 → IN placeholders → sum flow / latest snapshot"
  - "Pattern Reconciliation: max(abs(dfp_revenue), 1.0) como denominador (T-03-01-04)"
  - "Pattern Stubs: raise NotImplementedError com comentario 'Implemented in Plan 03-0X'"

requirements-completed: [FIN-01]

duration: 8min
completed: 2026-05-11
---

# Phase 3 Plan 01: Financial Engine Foundation Summary

**LTM aggregation engine com 4-quarter ITR rolling sum, AccountMapper wired em cvm_downloader, 4 financial_* tables no ingestion.db, e encoding/import bugs fechados — 74/74 testes green**

## Performance

- **Duration:** 8 min
- **Started:** 2026-05-11T18:14:44Z
- **Completed:** 2026-05-11T18:22:43Z
- **Tasks:** 2
- **Files modified:** 7 (5 modificados + 3 criados)

## Accomplishments

- BUG-01 fechado: sector_config.py agora lê sectors.yaml e tickers.yaml com encoding='utf-8' — sem UnicodeDecodeError no Windows
- GAP-02 fechado: account_mapper.py corrigido para `from src.parsers.dfp_parser import` — importa sem erro do project root
- D-01 fechado: init_db() agora cria as 4 tabelas financial_* com UNIQUE indexes
- D-06 fechado: cvm_downloader.parse_and_store() popula normalized_name via AccountMapper._map_row no momento do write
- FIN-01 (parcial): _aggregate_ltm() soma 4 ITR quarters, deriva EBITDA/FCF/net_debt, dispara ltm_reconciliation_warning quando divergência LTM-DFP > 5%
- 74/74 testes green (65 anteriores + 3 schema + 6 engine)

## Task Commits

1. **Task 1: Fix encoding, import e schema** - `bd10703` (fix)
2. **Task 2: LTM engine, AccountMapper wire-up, tests** - `e5cf275` (feat)

## Files Created/Modified

- `src/financial_engine.py` — Novo orchestrador: FinancialResult, run_ticker(), run_all(), _aggregate_ltm(), _check_dfp_reconciliation(), backfill_normalized_names(), stubs para Plans 02-05
- `src/valuation/sector_config.py` — encoding='utf-8' nas duas chamadas open() (BUG-01)
- `src/normalization/account_mapper.py` — import path corrigido para src.parsers.dfp_parser (GAP-02)
- `src/ingestion/db.py` — DDL das 4 tabelas financial_* appendado ao _CREATE_SQL (D-01)
- `src/ingestion/cvm_downloader.py` — AccountMapper importado e chamado em parse_and_store() (D-06)
- `tests/test_financial_db_schema.py` — 3 testes de schema (D-01, D-02, D-04)
- `tests/test_financial_engine.py` — 6 testes FIN-01 (LTM sum, reconciliation, bank EBITDA, backfill, AccountMapper)
- `tests/test_db_schema.py` — Contagem de tabelas atualizada de 4 para 8

## Decisions Made

- EBITDA derivado como EBIT + D&A; se nenhum row DFC encontrado, ebitda=None (não 0) — evita falso positivo em tickers sem DFC trimestral
- FCF=None quando cfo ou capex não têm rows — "0 rows" distinto de "row com valor 0"
- is_bank=True força ebitda=None em _aggregate_ltm (Pitfall 2 do RESEARCH.md)
- test_db_schema.py atualizado para refletir 8 tabelas — necessário para não quebrar suite existente

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Testes existentes test_db_schema.py quebrariam com 8 tabelas**
- **Found during:** Task 1 (extensão do db.py)
- **Issue:** test_init_db_creates_all_four_tables e test_init_db_is_idempotent verificavam exatamente 4 tabelas; após adicionar 4 financial_* tables, count seria 8 e assertion `tables == {"cvm_statements", ...}` falharia
- **Fix:** Atualizado test_db_schema.py: `issubset` em vez de `==` para tabelas, e count de 4 para 8
- **Files modified:** tests/test_db_schema.py
- **Verification:** `python -m pytest tests/test_db_schema.py -q` — 5 passed
- **Committed in:** bd10703 (Task 1)

**2. [Rule 1 - Bug] test_normalized_name_backfill falhava com UNIQUE constraint**
- **Found during:** Task 2 (criação dos testes)
- **Issue:** Inserir 3 rows com mesmo account_code '3.01' e reference_date '2024-09-30' viola o UNIQUE INDEX em (ticker, period_type, year, account_code, reference_date)
- **Fix:** Usar account_codes diferentes por row: '3.01', '3.02', '3.03'
- **Files modified:** tests/test_financial_engine.py
- **Verification:** `python -m pytest tests/test_financial_engine.py -q` — 6 passed
- **Committed in:** e5cf275 (Task 2)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - Bug)
**Impact on plan:** Ambos auto-fixes necessários para correção dos testes. Sem scope creep.

## Issues Encountered

Nenhum bloqueio encontrado. Todos os módulos importaram corretamente após as correções de BUG-01 e GAP-02.

## Known Stubs

Os seguintes stubs existem em `src/financial_engine.py` e serão implementados nos planos subsequentes:

| Stub | Arquivo | Linha | Plano |
|------|---------|-------|-------|
| `compute_wacc()` | financial_engine.py | ~290 | Plan 03-03 |
| `_compute_multiples()` | financial_engine.py | ~295 | Plan 03-02 |
| `_compute_dcf()` | financial_engine.py | ~300 | Plans 03-03/04 |
| `compute_signals()` | financial_engine.py | ~305 | Plan 03-05 |

Os stubs usam `raise NotImplementedError` — não retornam dados ao usuário e não afetam o objetivo deste plano (FIN-01 LTM aggregation).

## Threat Flags

Nenhuma nova superfície de ataque além das documentadas no threat_model do PLAN.md.
Todas as mitigações T-03-01-01 a T-03-01-05 implementadas conforme especificado.

## Next Phase Readiness

- **Plan 03-02 (Multiples):** Pode começar — financial_ltm existe, run_ticker() está disponível, calculate_industrial_metrics() e calculate_bank_metrics() são pure-compute
- **Plan 03-03 (DCF):** Pode começar após 03-02 — compute_wacc() stub pronto para implementação, macro_series tem Selic e CDS disponíveis
- **Bloqueio potencial:** ingestion.db ainda não tem dados reais (DB vazio) — testes usam in-memory DB. Dados reais requerem execução do pipeline de ingestão (Phase 2 jobs)

## Self-Check: PASSED

---
*Phase: 03-financial-engine*
*Completed: 2026-05-11*
