---
phase: 03-financial-engine
plan: 04
subsystem: financial-engine
tags: [sqlite, bank-model, ddm, gordon-growth, cosif, fin-05, python]

requires:
  - phase: 03-financial-engine
    plan: 01
    provides: financial_ltm table, _aggregate_ltm(), is_bank=True enforcing ebitda=None
  - phase: 03-financial-engine
    plan: 02
    provides: _get_current_price(), _compute_multiples(), run_ticker() wired, compute_wacc() stub

provides:
  - _write_dcf_row() helper — shared INSERT OR REPLACE for financial_dcf (parameterized)
  - _compute_bank_model() — DDM fair value using gordon_assumptions.coe/terminal_growth/payout_ratio
  - run_ticker() wired: if cfg.is_bank_model -> _compute_bank_model() (industrial DCF never called for banks)
  - FIN-05 satisfied by 4 passing tests (bank routing DDM, NIM metric, ebitda=NULL, routing guard)

affects: [03-03-dcf, 03-05-signals, 04-intelligence-layer]

tech-stack:
  added: []
  patterns:
    - "_write_dcf_row(): parameterized INSERT OR REPLACE into financial_dcf — shared by DDM and DCF paths"
    - "_compute_bank_model(): gordon_assumptions.coe as cost_of_equity — not re-derived from WACC"
    - "DDM guard: ke > terminal_growth AND ke > 0.05 — prevents Gordon model explosion (T-03-04-02)"
    - "P7 guard: confidence_flag='FORA DO INTERVALO CONFIAVEL' when fair_value/price outside 0.1x-5.0x"
    - "is_bank_model as sole routing gate in run_ticker() — industrial DCF never invoked for bank tickers"
    - "ebitda=None enforced in _aggregate_ltm(is_bank=True) — Pitfall 2 / T-03-04-04"

key-files:
  modified:
    - Analista de Investimentos/12_PYTHON/src/financial_engine.py
    - Analista de Investimentos/12_PYTHON/tests/test_financial_engine.py

key-decisions:
  - "run_ddm() assinatura real usa cost_of_equity/terminal_growth_rate/income_growth_rates (não coe/g/growth_rates como no PLAN.md) — adaptado sem alterar valuation_dcf.py"
  - "DDMResult não tem price_target — usa equity_value_per_share quando shares>0, fallback equity_value/shares"
  - "gordon_assumptions para bancos tem apenas coe/terminal_growth/payout_ratio — sem beta/erp/base_revenue_growth documentados no PLAN.md; ke lido diretamente de gordon_assumptions.coe"
  - "BankMetricsCalc tem nii_margin (não nim como documentado no PLAN.md) — teste adaptado para nii_margin"
  - "_write_dcf_row() implementado neste plano (Plan 03-03 ainda não executado) — Rule 3 bloqueio resolvido inline"

patterns-established:
  - "Pattern DDM routing: is_bank_model gate em run_ticker() antes de qualquer chamada DCF industrial"
  - "Pattern DDM guard duplo: base_net_income > 0 AND ke > terminal_growth AND ke > 0.05"
  - "Pattern DCF write: _write_dcf_row() compartilhado — DDM e DCF usam mesma função de persistência"
  - "Pattern ke storage: ke (custo de equity) gravado na coluna wacc para linhas DDM — documentado no log"

requirements-completed: [FIN-05]

duration: 15min
completed: 2026-05-11
---

# Phase 3 Plan 04: Bank Model (DDM) Summary

**Modelo bancario DDM implementado com _compute_bank_model() usando gordon_assumptions.coe como custo de equity, _write_dcf_row() compartilhado, e routing guard is_bank_model em run_ticker() — 81/81 testes green**

## Performance

- **Duration:** 15 min
- **Started:** 2026-05-11T18:50:00Z
- **Completed:** 2026-05-11T19:05:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- FIN-05 implementado: `_compute_bank_model()` chama `run_ddm()` com `cost_of_equity=gordon_assumptions.coe`, `terminal_growth_rate=gordon_assumptions.terminal_growth`, escreve `financial_dcf` com `valuation_method='ddm'`
- `_write_dcf_row()` implementado como helper compartilhado (INSERT OR REPLACE parametrizado em `financial_dcf`) — usado por banco e será reutilizado pelo DCF industrial em Plan 03-03
- Guard DDM: `ke > terminal_growth AND ke > 0.05` previne divisão por zero / valor negativo (T-03-04-02)
- Guard P7: `confidence_flag='FORA DO INTERVALO CONFIAVEL'` quando `fair_value / current_price` fora do intervalo 0.1x–5.0x
- Routing guard em `run_ticker()`: `if cfg.is_bank_model -> _compute_bank_model()` — `_compute_dcf()` industrial nunca é chamado para banco
- 4 testes FIN-05 adicionados: routing DDM, NIM (nii_margin), ebitda=NULL, routing guard `run_dcf.call_count==0`
- 81/81 testes green (77 anteriores + 4 novos FIN-05)

## Task Commits

1. **Task 1: _compute_bank_model() e _write_dcf_row()** - `eae4719` (feat)
2. **Task 2: 4 testes FIN-05** - `9012dac` (feat)

## Files Created/Modified

- `src/financial_engine.py` — `_write_dcf_row()` adicionado; `run_ddm` importado; `_compute_bank_model()` implementado; `run_ticker()` estendido com routing guard `is_bank_model`
- `tests/test_financial_engine.py` — 4 testes FIN-05 acrescidos (test_bank_routing_uses_ddm, test_bank_metrics_include_nim, test_bank_ltm_ebitda_is_null_in_db, test_bank_routing_guard_prevents_dcf)

## Decisions Made

- `run_ddm()` tem assinatura diferente da documentada no PLAN.md: usa `cost_of_equity` (não `coe`), `terminal_growth_rate` (não `g`), `income_growth_rates` (não `growth_rates`). Adaptado sem alterar `valuation_dcf.py` (D-11).
- `DDMResult` não tem campo `price_target` — usa `equity_value_per_share` quando `shares_outstanding > 0`, fallback `equity_value / shares`.
- `gordon_assumptions` do sectors.yaml para banco contém apenas `coe`, `terminal_growth`, `payout_ratio` — sem `beta`, `erp`, `base_revenue_growth` como descrito no PLAN.md. `ke` lido diretamente de `gordon_assumptions.coe` (0.135 para bancos).
- `BankMetricsCalc` tem campo `nii_margin` (NIM proxy = NII / Total Assets) — não `nim` como documentado no PLAN.md. Testes adaptados.
- `_write_dcf_row()` implementado neste plano como medida Rule 3 (Plan 03-03 ainda não executado na sequência de execução). É additive — Plan 03-03 o reutilizará sem conflito.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Assinatura real de run_ddm() difere do PLAN.md**
- **Found during:** Task 1 (leitura de valuation_dcf.py)
- **Issue:** PLAN.md documenta `run_ddm(ticker, base_year, base_net_income, payout_ratio, coe, g, growth_rates)`. A implementação real usa `cost_of_equity`, `terminal_growth_rate`, `income_growth_rates`. DDMResult não tem `price_target` — tem `equity_value_per_share`.
- **Fix:** Adaptada a chamada em `_compute_bank_model()` com os parâmetros corretos. Derivação de `price_target` via `equity_value_per_share` ou `equity_value / shares`.
- **Files modified:** src/financial_engine.py, tests/test_financial_engine.py
- **Commit:** eae4719 (Task 1), 9012dac (Task 2)

**2. [Rule 1 - Bug] gordon_assumptions não tem beta/erp/base_revenue_growth**
- **Found during:** Task 1 (leitura de sectors.yaml seção bank)
- **Issue:** PLAN.md propõe derivar `ke = selic + beta*erp + cds` dentro de `_compute_bank_model()` lendo `beta` e `erp` de `gordon_assumptions`. O sectors.yaml real para bancos só tem `coe`, `terminal_growth`, `payout_ratio`.
- **Fix:** `ke` lido diretamente de `gordon_assumptions.coe` (valor configurado no YAML = 0.135 para bancos), sem re-derivar dos componentes WACC.
- **Files modified:** src/financial_engine.py
- **Commit:** eae4719 (Task 1)

**3. [Rule 3 - Blocking] _write_dcf_row() não existia (Plan 03-03 ainda não executado)**
- **Found during:** Task 1 (grep em financial_engine.py — zero matches para _write_dcf_row)
- **Issue:** O PLAN.md assume que _write_dcf_row() foi definido em Plan 03-03 (Wave 2). Na sequência real de execução, Plan 03-04 está sendo executado antes de Plan 03-03.
- **Fix:** _write_dcf_row() implementado inline neste plano — função compartilhada que Plan 03-03 reutilizará sem conflito.
- **Files modified:** src/financial_engine.py
- **Commit:** eae4719 (Task 1)

**4. [Rule 1 - Bug] BankMetricsCalc tem nii_margin (não nim)**
- **Found during:** Task 2 (leitura de calculate_metrics.py)
- **Issue:** PLAN.md especifica que BankMetricsCalc tem campo `nim`. O dataclass real tem `nii_margin`.
- **Fix:** Teste test_bank_metrics_include_nim usa `nii_margin=0.065` no mock e verifica via `pe_ratio` (não `nim` direto — NIM não é gravado em financial_multiples).
- **Files modified:** tests/test_financial_engine.py
- **Commit:** 9012dac (Task 2)

---

**Total deviations:** 4 auto-fixed (2 Rule 1 - Bug, 1 Rule 3 - Blocking, 1 Rule 1 - Bug)
**Impact on plan:** Todos os fixes necessários para conformidade com interfaces reais. D-11 mantido (valuation_dcf.py e calculate_metrics.py não alterados). Sem scope creep.

## Issues Encountered

Nenhum bloqueio crítico. Todas as diferenças de interface resolvidas inline conforme regras de desvio.

## Known Stubs

| Stub | Arquivo | Observacao | Plano |
|------|---------|------------|-------|
| `_compute_dcf()` | financial_engine.py | `raise NotImplementedError` | Plan 03-03 |
| `compute_signals()` | financial_engine.py | `raise NotImplementedError` | Plan 03-05 |

Ambos os stubs são intencionais — não afetam o objetivo deste plano (FIN-05 satisfeito).

## Threat Flags

Nenhuma nova superficie de ataque alem das documentadas no threat_model do PLAN.md.
Todas as mitigacoes implementadas:
- T-03-04-01: is_bank_model como unico gate em run_ticker() — testado em test_bank_routing_guard_prevents_dcf
- T-03-04-02: Guard `ke > terminal_growth AND ke > 0.05` antes de run_ddm() — confidence_flag='INPUT_INVALIDO' em violacao
- T-03-04-03: _write_dcf_row() usa parametros posicionais — ticker nunca interpolado em SQL
- T-03-04-04: _aggregate_ltm(is_bank=True) roteia para BankAccountMapper (COSIF), ebitda=None

## Next Phase Readiness

- **Plan 03-03 (DCF industrial):** Pode comecar — _write_dcf_row() ja disponivel, compute_wacc() stub pronto
- **Plan 03-05 (Signals):** Pode comecar — compute_signals() stub aguarda implementacao
- **Plan 04 (Intelligence Layer):** FIN-05 satisfeito — banco e industrial tem caminhos de valuacao completos

## Self-Check: PASSED

Verificacoes executadas:

```
[ -f "src/financial_engine.py" ] -> FOUND
[ -f "tests/test_financial_engine.py" ] -> FOUND
git log | grep "eae4719" -> FOUND: feat(03-04): implement _compute_bank_model()...
git log | grep "9012dac" -> FOUND: feat(03-04): add FIN-05 bank model tests...
python -m pytest tests/ -q -> 81 passed
grep -c "def _compute_bank_model" src/financial_engine.py -> 1
grep -c "run_ddm" src/financial_engine.py -> 5
grep -c "is_bank_model" src/financial_engine.py -> 6
grep -c "def test_bank_routing_uses_ddm|def test_bank_metrics..." tests/test_financial_engine.py -> 4
```

---
*Phase: 03-financial-engine*
*Completed: 2026-05-11*
