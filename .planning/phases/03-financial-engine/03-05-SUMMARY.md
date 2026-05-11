---
phase: 03-financial-engine
plan: 05
subsystem: financial-engine
tags: [pandas, rsi, macd, moving-averages, technical-signals, apscheduler, scheduler, sqlite]

# Dependency graph
requires:
  - phase: 03-financial-engine/03-01
    provides: financial_engine.py estrutura base, run_ticker(), price_ohlcv table com is_gap
  - phase: 03-financial-engine/03-02
    provides: _compute_multiples(), financial_multiples table
  - phase: 03-financial-engine/03-03
    provides: compute_wacc(), _compute_dcf_industrial(), financial_dcf table
  - phase: 03-financial-engine/03-04
    provides: _compute_bank_model(), _write_dcf_row(), DDM wiring
provides:
  - compute_signals() — RSI-14 (Wilder's EWM com=13), MACD (12/26/9), MA50/200, golden/death cross, composite momentum score
  - _compute_and_write_signals() — price series fetch (is_gap=0), signal computation, financial_signals INSERT OR REPLACE
  - job_financial_engine() — scheduler job com bind_run_id, run_all(), D-15 summary log
  - financial_engine registrado em _JOB_REGISTRY e schedules.yaml (cron 0 20 * * 1-5)
  - 7 novos testes: 5 FIN-06 (test_financial_signals.py) + 2 D-12 (test_financial_engine.py)
affects:
  - phase-04-intelligence-layer (consome financial_signals para recomendações de posicionamento)
  - phase-05-delivery (thesis context inclui momentum_score, rsi_14, golden_cross)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "RSI-14 via Wilder's smoothing: EWM com=13, gain/loss.replace(0, nan) para evitar divisão por zero"
    - "MACD 12/26/9: ewm(span=12/26/9, adjust=False) — identidade macd_hist = macd_line - macd_signal"
    - "Crossover guard: verificar len >= 2 antes de iloc[-2] para evitar IndexError"
    - "Momentum score incremental: rsi_score(30) + macd_score(30) + ma200_score(20) + cross_score(10/20) — sempre múltiplo de 10"
    - "Gap row exclusion: WHERE is_gap = 0 AND adj_close IS NOT NULL em todos os queries de sinais"

key-files:
  created:
    - Analista de Investimentos/12_PYTHON/tests/test_financial_signals.py
  modified:
    - Analista de Investimentos/12_PYTHON/src/financial_engine.py
    - Analista de Investimentos/12_PYTHON/src/scheduler.py
    - Analista de Investimentos/12_PYTHON/config/schedules.yaml
    - Analista de Investimentos/12_PYTHON/tests/test_financial_engine.py

key-decisions:
  - "compute_signals() aceita pd.Series com índice de strings de data e valores float — indexação string é suficiente para pandas EWM/rolling"
  - "ma_50=None quando n<50, ma_200=None quando n<200 — nunca crash em série curta"
  - "cross_score=10 (neutro) quando MA200 não disponível — preserva validez do momentum_score como múltiplo de 10"
  - "job_financial_engine() importa run_all e bind_run_id dentro da função (lazy import) — segue padrão de todos os jobs existentes"
  - "Cron 0 20 * * 1-5 para financial_engine — executa após cvm_ingest (19:15) e b3_prices (19:00) garantindo dados frescos"

patterns-established:
  - "Signal computation: pure pandas (sem ta-lib), EWM adjust=False para consistência com Wilder's definition"
  - "Null signals guard: _write_null_signals() escreve linha com golden_cross=0, death_cross=0, outros campos NULL — nunca deixa ticker sem linha em financial_signals"
  - "D-15 summary log em job_financial_engine: source, records_inserted (=tickers_ok), duration_ms, status, failed_tickers"

requirements-completed: [FIN-06]

# Metrics
duration: 20min
completed: 2026-05-11
---

# Phase 3 Plan 05: Financial Engine — Technical Signals + Scheduler Wiring Summary

**RSI-14 (Wilder's EWM), MACD (12/26/9), MA50/200 com crossover e momentum score composto (0-100) implementados via pandas puro; pipeline completo FIN-01..06 encerrado com job_financial_engine() agendado diariamente às 20:00 seg-sex**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-05-11T18:40:00Z
- **Completed:** 2026-05-11T18:57:55Z
- **Tasks:** 2
- **Files modified:** 4 (modificados) + 1 (criado)

## Accomplishments

- compute_signals() implementado com RSI-14 (Wilder's smoothing via EWM com=13), MACD (12/26/9 EWM), MA50/200 (rolling mean), detecção de golden/death cross e score composto sempre múltiplo de 10
- _compute_and_write_signals() conectado ao run_ticker() — todos os tickers recebem linha em financial_signals após cada execução diária; gap rows (is_gap=1) excluídos via SQL
- job_financial_engine() registrado em _JOB_REGISTRY e schedules.yaml com cron 0 20 * * 1-5 — fecha requisito D-03 (automated daily execution) e D-12 (public job API)
- Suite completa: 93/93 testes green (86 pré-existentes + 5 FIN-06 + 2 D-12)

## Task Commits

Cada tarefa foi commitada atomicamente no submódulo `Analista de Investimentos`:

1. **Task 1: Implement compute_signals() and wire into run_ticker()** - `226c03e` (feat)
2. **Task 2: Scheduler wiring — job_financial_engine(), schedules.yaml, registry, job tests** - `1a730f4` (feat)

## Files Created/Modified

- `Analista de Investimentos/12_PYTHON/src/financial_engine.py` — compute_signals(), _compute_and_write_signals(), _write_null_signals() adicionados; _compute_and_write_signals() conectado ao run_ticker()
- `Analista de Investimentos/12_PYTHON/src/scheduler.py` — job_financial_engine() adicionado após job_news_ingest(); "financial_engine" adicionado ao _JOB_REGISTRY
- `Analista de Investimentos/12_PYTHON/config/schedules.yaml` — entrada financial_engine com cron "0 20 * * 1-5" adicionada
- `Analista de Investimentos/12_PYTHON/tests/test_financial_engine.py` — test_job_registered() e test_job_summary_log() adicionados (D-12)
- `Analista de Investimentos/12_PYTHON/tests/test_financial_signals.py` — criado com 5 testes FIN-06 (RSI range, MACD identity, MA crossover, momentum score, gap exclusion)

## Decisions Made

- compute_signals() aceita pd.Series com índice de strings de data — indexação string é suficiente para EWM/rolling, sem necessidade de pd.DatetimeIndex
- ma_50=None quando n<50, ma_200=None quando n<200; cross_score=10 (neutro) quando MA200 não disponível — preserva invariante momentum_score % 10 == 0 em qualquer tamanho de série
- job_financial_engine() usa lazy imports dentro da função (from src.financial_engine import run_all) — padrão consistente com todos os outros jobs do scheduler
- Cron 20:00 escolhido para rodar após b3_prices (19:00) e cvm_ingest (19:15) — garantia de dados frescos

## Deviations from Plan

None — plano executado exatamente como especificado. Todos os contratos de interface, padrões de teste e critérios de aceitação foram seguidos sem desvios.

## Issues Encountered

None — commits feitos diretamente no submódulo `Analista de Investimentos` (git submodule), conforme padrão estabelecido nos planos anteriores da Phase 3.

## User Setup Required

None — implementação puramente interna. Nenhuma variável de ambiente ou configuração externa necessária.

## Next Phase Readiness

- Phase 3 completa: FIN-01..06 todos encerrados, 93/93 testes green
- financial_signals table populada diariamente às 20:00 com RSI-14, MACD, momentum_score
- Phase 4 (Intelligence Layer) pode consumir financial_signals para recomendações de posicionamento (rsi_14, momentum_score, golden_cross, death_cross)
- Pipeline completo: price_ohlcv → financial_signals → Phase 4 thesis context

---
*Phase: 03-financial-engine*
*Completed: 2026-05-11*
