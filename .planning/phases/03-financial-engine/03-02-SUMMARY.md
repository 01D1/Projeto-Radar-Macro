---
phase: 03-financial-engine
plan: 02
subsystem: financial-engine
tags: [sqlite, financial-multiples, calculate-metrics, sector-routing, python, fin-02]

requires:
  - phase: 03-financial-engine
    plan: 01
    provides: financial_ltm table, run_ticker(), SectorConfig, financial_* schema

provides:
  - _get_current_price() — parameterized price fetch from price_ohlcv (is_gap=0)
  - _compute_multiples() — industrial/bank routing, writes financial_multiples row
  - run_ticker() wired to call _compute_multiples() after financial_ltm write
  - FIN-02 satisfied by 3 passing tests (industrial, missing price, bank ev_ebitda=NULL)

affects: [03-03-dcf, 03-04-bank-model, 04-intelligence-layer]

tech-stack:
  added: []
  patterns:
    - "_get_current_price(): SELECT adj_close WHERE is_gap=0 AND adj_close IS NOT NULL ORDER BY date DESC LIMIT 1"
    - "_compute_multiples(): SectorConfig.is_bank_model gates calculate_bank_metrics() vs calculate_industrial_metrics()"
    - "ev_ebitda_val = None para bancos — FIN-05 guard aplicado em Plan 02"
    - "ev_revenue computado manualmente como (market_cap + net_debt) / net_revenue — campo ausente em IndustrialMetrics"
    - "market_cap = price × shares_outstanding — calculado no orchestrator pois calculate_industrial_metrics() e calculate_bank_metrics() não retornam market_cap diretamente"
    - "compute_wacc() stub retorna (0.12, 0.105, 0.015, True) para manter run_ticker() compilável até Plan 03-03"

key-files:
  modified:
    - Analista de Investimentos/12_PYTHON/src/financial_engine.py
    - Analista de Investimentos/12_PYTHON/tests/test_financial_engine.py

key-decisions:
  - "calculate_industrial_metrics() assinatura real difere do PLAN.md — aceita ticker, year e parâmetros individuais (não dict); adaptado sem alterar calculate_metrics.py (D-11)"
  - "calculate_bank_metrics() igualmente requer ticker e year — market_cap computado manualmente no orchestrator"
  - "ev_revenue ausente de IndustrialMetrics — computado inline como (market_cap + net_debt) / net_revenue"
  - "compute_wacc() stub retorna fallback fixo (0.12, 0.105, 0.015, True) em vez de NotImplementedError — mantém run_ticker() funcional para testes antes do Plan 03-03"

patterns-established:
  - "Pattern price fetch: parameterized SELECT is_gap=0 + adj_close IS NOT NULL — dupla guard contra gap rows e NULL adj_close"
  - "Pattern bank guard: ev_ebitda_val = None atribuído explicitamente antes do INSERT — nunca propagado de calculate_bank_metrics()"
  - "Pattern metric dispatch: cfg.is_bank_model como único gate — sem múltiplos isinstance() ou string comparison"

requirements-completed: [FIN-02]

duration: 12min
completed: 2026-05-11
---

# Phase 3 Plan 02: Multiples Computation Summary

**_get_current_price() + _compute_multiples() implementados em financial_engine.py com roteamento industrial/banco, is_gap=0 guard, e 77/77 testes green**

## Performance

- **Duration:** 12 min
- **Started:** 2026-05-11T18:30:00Z
- **Completed:** 2026-05-11T18:42:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- FIN-02 implementado: `_get_current_price()` busca adj_close mais recente com is_gap=0 filter
- `_compute_multiples()` roteia para `calculate_industrial_metrics()` (industrial) ou `calculate_bank_metrics()` (banco)
- Bancos: ev_ebitda=NULL explícito (FIN-05 guard), sem ev_revenue
- Industriais: P/E, EV/EBITDA, P/BV, dividend_yield via calculate_industrial_metrics(); ev_revenue calculado inline
- run_ticker() estendido para chamar _compute_multiples() após o write do financial_ltm
- compute_wacc() stub substituído por fallback funcional (sem NotImplementedError) — plano 03-03 implementará versão real
- 3 testes FIN-02 adicionados e passando: industrial, missing price (sem crash), bank ev_ebitda=NULL
- 77/77 testes green (74 anteriores + 3 novos)

## Task Commits

1. **Task 1: _get_current_price() e _compute_multiples()** - `2027dee` (feat)
2. **Task 2: 3 testes FIN-02** - `d3ca8b9` (feat)

## Files Created/Modified

- `src/financial_engine.py` — _get_current_price(), _compute_multiples() implementados; compute_wacc() stub substituído; run_ticker() wired; import calculate_industrial_metrics/calculate_bank_metrics adicionado
- `tests/test_financial_engine.py` — 3 testes FIN-02 acrescidos (test_industrial_multiples_computed, test_multiples_handles_missing_price, test_bank_multiples_ev_ebitda_null)

## Decisions Made

- `calculate_industrial_metrics()` e `calculate_bank_metrics()` têm assinaturas reais diferentes das documentadas no PLAN.md (requerem `ticker`, `year` e parâmetros individuais, não um objeto dict). Adaptamos a chamada sem modificar os módulos pure-compute (D-11 compliance).
- `ev_revenue` não existe como campo em `IndustrialMetrics` — computado inline no orchestrator como `(market_cap + net_debt) / net_revenue`.
- `market_cap` calculado como `price × shares_outstanding` no orchestrator, pois nenhuma das funções de métricas o retorna diretamente.
- `compute_wacc()` stub retorna `(0.12, 0.105, 0.015, True)` em vez de `NotImplementedError` — mantém `run_ticker()` testável antes do Plan 03-03.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Assinatura real de calculate_industrial_metrics() difere do PLAN.md**
- **Found during:** Task 1 (leitura de calculate_metrics.py)
- **Issue:** PLAN.md documenta interface com parâmetros `price, net_income, book_value, ebitda, net_revenue, net_debt, shares_outstanding, dividends_paid` retornando `IndustrialMetrics` com `market_cap`. A implementação real requer `ticker`, `year` como primeiros parâmetros, aceita parâmetros individuais (não dict), e não retorna `market_cap` como campo.
- **Fix:** Adaptamos `_compute_multiples()` para usar a assinatura real — passamos `ticker=ticker, year=metrics_year` e todos os parâmetros individuais extraídos do dict `ltm`. Calculamos `market_cap` manualmente no orchestrator. Não alteramos `calculate_metrics.py` (D-11).
- **Files modified:** src/financial_engine.py
- **Commit:** 2027dee (Task 1)

**2. [Rule 2 - Missing critical functionality] ev_revenue ausente de IndustrialMetrics**
- **Found during:** Task 1 (leitura de IndustrialMetrics dataclass)
- **Issue:** PLAN.md especifica que `IndustrialMetrics` tem campo `ev_revenue`. O dataclass real não tem esse campo.
- **Fix:** ev_revenue computado inline: `ev_revenue = (market_cap + net_debt) / net_revenue` quando dados disponíveis, None caso contrário.
- **Files modified:** src/financial_engine.py
- **Commit:** 2027dee (Task 1)

---

**Total deviations:** 2 auto-fixed (1 Rule 1 - Bug, 1 Rule 2 - Missing)
**Impact on plan:** Ambos os fixes necessários para conformidade com a interface documentada. Sem scope creep. D-11 mantido (calculate_metrics.py não alterado).

## Issues Encountered

Nenhum bloqueio encontrado. Imports corretos após adição de `calculate_industrial_metrics` e `calculate_bank_metrics` no nível do módulo.

## Known Stubs

Os seguintes stubs existem em `src/financial_engine.py` e serão implementados nos planos subsequentes:

| Stub | Arquivo | Observação | Plano |
|------|---------|------------|-------|
| `compute_wacc()` | financial_engine.py | Retorna fallback (0.12, 0.105, 0.015, True) | Plan 03-03 |
| `_compute_dcf()` | financial_engine.py | raise NotImplementedError | Plans 03-03/04 |
| `compute_signals()` | financial_engine.py | raise NotImplementedError | Plan 03-05 |

## Threat Flags

Nenhuma nova superfície de ataque além das documentadas no threat_model do PLAN.md.
Todas as mitigações T-03-02-01 a T-03-02-04 implementadas:
- T-03-02-01: ticker em parameterized query `(ticker,)` — nunca interpolado
- T-03-02-02: INSERT OR REPLACE com todos parâmetros posicionais
- T-03-02-03: price=None passado para metric functions; retornam None ratios (sem divisão por zero)
- T-03-02-04: `is_gap = 0 AND adj_close IS NOT NULL` — dupla guard no SELECT

## Next Phase Readiness

- **Plan 03-03 (DCF):** Pode começar — compute_wacc() stub pronto, macro_series disponível, _compute_dcf() stub aguarda implementação real
- **Plan 03-04 (Bank model):** Pode começar — calculate_bank_metrics() já integrado e testado neste plano
- **Plan 03-05 (Signals):** Pode começar — compute_signals() stub aguarda implementação

## Self-Check: PASSED

Verificações executadas:

```
[ -f "src/financial_engine.py" ] → FOUND
[ -f "tests/test_financial_engine.py" ] → FOUND
git log | grep "2027dee" → FOUND: feat(03-02): implement _get_current_price()...
git log | grep "d3ca8b9" → FOUND: feat(03-02): add FIN-02 tests...
python -m pytest tests/ -q → 77 passed
```

---
*Phase: 03-financial-engine*
*Completed: 2026-05-11*
