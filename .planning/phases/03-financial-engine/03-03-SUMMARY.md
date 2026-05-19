---
phase: 03-financial-engine
plan: 03
subsystem: financial-engine
tags: [sqlite, dcf, wacc, validation, input-guard, ev-ebitda, macro-series, python, fin-03, fin-04]

requires:
  - phase: 03-financial-engine
    plan: 01
    provides: financial_ltm table, _aggregate_ltm(), SectorConfig, financial_* schema
  - phase: 03-financial-engine
    plan: 02
    provides: _get_current_price(), _compute_multiples(), _is_stale_date(), compute_wacc() stub
  - phase: 03-financial-engine
    plan: 04
    provides: _write_dcf_row() helper (shared INSERT OR REPLACE for financial_dcf)

provides:
  - compute_wacc() — real WACC derivation from macro_series Selic (11) + CDS Brasil (29039); fallback to sectors.yaml
  - _validate_dcf_inputs() — pre-flight guard blocking run_dcf() when terminal_growth >= WACC or WACC <= 5%
  - _compute_dcf_industrial() — handles dcf_fcff and ev_ebitda_multiple paths for non-bank tickers
  - run_ticker() wired: non-bank tickers now call _compute_dcf_industrial() (was stub/pass before)
  - FIN-03 and FIN-04 satisfied by 5 passing tests

affects: [03-05-signals, 04-intelligence-layer]

tech-stack:
  added: []
  patterns:
    - "compute_wacc(): SELECT series_code IN (11, 29039) ORDER BY date DESC; keep latest per series_code"
    - "_is_stale_date() reused (not duplicated) as staleness check for macro freshness"
    - "_validate_dcf_inputs() called twice in dcf_fcff: pre-flight (pre-run_dcf) + post-flight (range check)"
    - "EV/EBITDA: cfg.ev_ebitda_assumptions (sector level) not a.ev_ebitda_assumptions (dcf_assumptions level)"
    - "DCFAssumptions constructor: sectors.yaml keys (risk_free, erp, cost_of_debt) mapped to field names (risk_free_rate, equity_risk_premium, pre_tax_cost_of_debt)"
    - "Live WACC override: risk_free_rate adjusted so DCFAssumptions.wacc == compute_wacc() output"

key-files:
  modified:
    - Analista de Investimentos/12_PYTHON/src/financial_engine.py
    - Analista de Investimentos/12_PYTHON/tests/test_financial_engine.py

key-decisions:
  - "cfg.ev_ebitda_assumptions is at sector level via cfg.ev_ebitda_assumptions property — not inside cfg.dcf_assumptions dict (sectors.yaml structure)"
  - "_is_stale_date() reused as macro staleness check instead of creating duplicate _is_macro_stale() — same logic, avoids duplication"
  - "DCFAssumptions fields (risk_free_rate, equity_risk_premium, pre_tax_cost_of_debt) differ from sectors.yaml keys (risk_free, erp, cost_of_debt) — mapping applied in _compute_dcf_industrial()"
  - "Live WACC override: ke_live = selic_used + beta*erp + cds_used; risk_free_rate = ke_live - beta*erp — ensures DCFAssumptions.wacc == compute_wacc() result (D-09 compliance)"
  - "_validate_dcf_inputs() pre-flight returns INPUT_INVALIDO and writes row early-return — run_dcf() never called with invalid inputs (FIN-04 / T-DCF-01)"
  - "is_bank_model gate reused in run_ticker(): else branch now calls _compute_dcf_industrial() instead of pass stub"

patterns-established:
  - "Pattern WACC: live macro + sector fallback pattern now consistent across bank (ke from gordon_assumptions.coe) and industrial (compute_wacc() from macro_series)"
  - "Pattern validation gate: INPUT_INVALIDO check before any external computation that could divide by zero"
  - "Pattern EV/EBITDA: cfg.ev_ebitda_assumptions at sector-level property, not nested inside dcf_assumptions"
  - "Pattern DCFAssumptions: sectors.yaml key -> field name mapping established in _compute_dcf_industrial()"

requirements-completed: [FIN-03, FIN-04]

duration: 18min
completed: 2026-05-11
---

# Phase 3 Plan 03: DCF Engine (Industrial) Summary

**compute_wacc() derivando WACC de macro_series Selic+CDS com fallback sectors.yaml, _validate_dcf_inputs() bloqueando run_dcf() antes de divisão por zero (FIN-04/T-DCF-01), e _compute_dcf_industrial() com paths dcf_fcff e ev_ebitda_multiple — 86/86 testes green**

## Performance

- **Duration:** 18 min
- **Started:** 2026-05-11T19:10:00Z
- **Completed:** 2026-05-11T19:28:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- FIN-03 implementado: `compute_wacc()` busca Selic (series_code=11) e CDS Brasil (series_code=29039) de `macro_series`; detecta staleness via `_is_stale_date()`; faz fallback para `cfg.dcf_assumptions["risk_free"]`/`["country_risk"]` com WARNING log quando dados estão desatualizados
- FIN-04 implementado: `_validate_dcf_inputs()` retorna `"INPUT_INVALIDO"` quando `terminal_growth >= wacc` ou `wacc <= 5%`; retorna `"FORA DO INTERVALO CONFIAVEL"` quando `price_target/current_price` fora de `[0.1, 5.0]`
- `_compute_dcf_industrial()` handles path `ev_ebitda_multiple`: `fair_value = (ebitda * target_multiple - net_debt) / shares` com guard `shares > 0` (T-03-03-05)
- `_compute_dcf_industrial()` handles path `dcf_fcff`: `_validate_dcf_inputs()` chamado ANTES de `run_dcf()` — early return com NULL fair_value se INPUT_INVALIDO (T-DCF-01)
- `run_ticker()` atualizado: bloco `else: pass` substituído por `_compute_dcf_industrial(ticker, conn, ltm, cfg, computed_date)`
- 5 testes FIN-03/FIN-04 adicionados e passando — WACC correto, fallback com used_fallback=True, validação INPUT_INVALIDO, flag FORA DO INTERVALO, NULL fair_value escrito
- 86/86 testes green (81 anteriores + 5 novos)

## Task Commits

1. **Task 1: compute_wacc(), _validate_dcf_inputs(), _compute_dcf_industrial()** - `50f649e` (feat)
2. **Task 2: 5 testes FIN-03/FIN-04** - `1004522` (feat)

## Files Created/Modified

- `src/financial_engine.py` — `compute_wacc()` stub substituído pela implementação real; `_validate_dcf_inputs()` adicionado; `_compute_dcf_industrial()` adicionado; `run_dcf, DCFAssumptions` importados; `run_ticker()` wired para industrial DCF
- `tests/test_financial_engine.py` — 5 testes FIN-03/FIN-04 acrescidos (test_wacc_from_macro_series, test_wacc_stale_macro_fallback, test_dcf_input_validation_blocks_run, test_dcf_confidence_flag_out_of_range, test_dcf_invalid_input_writes_null_fair_value)

## Decisions Made

- `cfg.ev_ebitda_assumptions` é propriedade de nível setor (via `SectorConfig.ev_ebitda_assumptions`) — não está dentro de `cfg.dcf_assumptions`. O sectors.yaml tem a chave `ev_ebitda_assumptions` no nível do setor (ex: `oil_gas`), não aninhada dentro de `dcf_assumptions`. Adaptado sem alterar sectors.yaml (D-11).
- `_is_stale_date()` reutilizado como verificador de staleness de macro em vez de criar `_is_macro_stale()` duplicado — mesma lógica, sem duplicação.
- `DCFAssumptions` tem campos com nomes diferentes das chaves do sectors.yaml: `risk_free_rate` (não `risk_free`), `equity_risk_premium` (não `erp`), `pre_tax_cost_of_debt` (não `cost_of_debt`). Mapeamento aplicado em `_compute_dcf_industrial()`.
- Override do WACC live: `ke_live = selic_used + beta*erp + cds_used`; `risk_free_rate = ke_live - beta*erp` — garante que `DCFAssumptions.wacc` == resultado de `compute_wacc()`, em conformidade com D-09.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] cfg.ev_ebitda_assumptions é propriedade de nível setor, não dcf_assumptions**
- **Found during:** Task 1 (leitura de sectors.yaml e sector_config.py)
- **Issue:** O PLAN.md documenta `ev_ebitda_a = a.get("ev_ebitda_assumptions", {})` onde `a = cfg.dcf_assumptions`. O sectors.yaml real para `oil_gas`/`mining` tem `ev_ebitda_assumptions` no nível do setor, não dentro de `dcf_assumptions`. `a.get("ev_ebitda_assumptions")` retornaria sempre `{}`.
- **Fix:** Alterado para `ev_ebitda_a = cfg.ev_ebitda_assumptions` (propriedade direta de SectorConfig).
- **Files modified:** src/financial_engine.py
- **Commit:** 50f649e (Task 1)

**2. [Rule 1 - Bug] DCFAssumptions field names diferem das chaves sectors.yaml**
- **Found during:** Task 1 (leitura de valuation_dcf.py — DCFAssumptions dataclass)
- **Issue:** PLAN.md assume construção via `a[k]` para campos. Os campos de `DCFAssumptions` são `risk_free_rate`, `equity_risk_premium`, `pre_tax_cost_of_debt`, `governance_premium` — mas sectors.yaml usa `risk_free`, `erp`, `cost_of_debt`. Construção via dict mapping direto falharia com KeyError.
- **Fix:** Construção explícita de `DCFAssumptions` com mapeamento de chaves sectors.yaml → nomes de campos do dataclass. Adicionado override do `risk_free_rate` para garantir que `DCFAssumptions.wacc` coincide com `compute_wacc()`.
- **Files modified:** src/financial_engine.py
- **Commit:** 50f649e (Task 1)

**3. [Rule 1 - Bug] _is_macro_stale() seria duplicata de _is_stale_date()**
- **Found during:** Task 1 (leitura do código existente em financial_engine.py)
- **Issue:** PLAN.md propõe criar `_is_macro_stale()` helper. O arquivo já tem `_is_stale_date()` com lógica idêntica (mesmos imports, mesma lógica de try/except, mesmo retorno). Criar duplicata viola DRY.
- **Fix:** `compute_wacc()` usa `_is_stale_date()` existente para verificar staleness de macro. Nenhuma função duplicada criada.
- **Files modified:** src/financial_engine.py (não criado _is_macro_stale)
- **Commit:** 50f649e (Task 1)

---

**Total deviations:** 3 auto-fixed (3 Rule 1 - Bug)
**Impact on plan:** Todos os fixes necessários para corretude. D-11 mantido. Sem scope creep.

## Issues Encountered

Nenhum bloqueio. `_write_dcf_row()` já estava disponível (implementado em Plan 03-04 como Rule 3 preemptivo). Todos os imports corretos após adição de `run_dcf, DCFAssumptions` no `import` de `valuation_dcf`.

## Known Stubs

| Stub | Arquivo | Observacao | Plano |
|------|---------|------------|-------|
| `compute_signals()` | financial_engine.py | `raise NotImplementedError` | Plan 03-05 |

Stub intencional — não afeta o objetivo deste plano (FIN-03/FIN-04 satisfeitos).

## Threat Flags

Nenhuma nova superfície de ataque além das documentadas no threat_model do PLAN.md.
Todas as mitigações implementadas:
- T-DCF-01: `_validate_dcf_inputs()` chamado ANTES de `run_dcf()` em dcf_fcff; early-return com NULL quando `terminal_growth >= wacc` — testado em test_dcf_invalid_input_writes_null_fair_value
- T-DCF-02: `_write_dcf_row()` usa parâmetros posicionais — ticker nunca interpolado em SQL; grep confirmou 0 matches de f-string SQL
- T-DCF-03: fallback lê de `a.get("risk_free", 0.105)` onde `a` é `cfg.dcf_assumptions` do sectors.yaml — 0.105 é last-resort guard
- T-03-03-04: `_is_stale_date()` checa freshness antes de usar macro; se stale → fallback sectors.yaml com WARNING log
- T-03-03-05: guard `if shares and shares > 0` antes de divisão em EV/EBITDA — fair_value=NULL com WARNING se shares ausente

## Next Phase Readiness

- **Plan 03-05 (Signals):** Pode começar — compute_signals() stub aguarda implementação
- **Plan 04 (Intelligence Layer):** FIN-03/FIN-04 satisfeitos — compute_wacc() real disponível; DCF industrial com input validation operacional; bank + industrial têm caminhos de valuation completos

## Self-Check: PASSED

Verificacoes executadas:

```
[ -f "src/financial_engine.py" ] -> FOUND
[ -f "tests/test_financial_engine.py" ] -> FOUND
git log | grep "50f649e" -> FOUND: feat(03-03): implement compute_wacc()...
git log | grep "1004522" -> FOUND: feat(03-03): add FIN-03 and FIN-04 tests...
python -m pytest tests/ -q -> 86 passed
grep -c "def compute_wacc" src/financial_engine.py -> 1
grep -c "def _validate_dcf_inputs" src/financial_engine.py -> 1
grep -c "def _compute_dcf_industrial" src/financial_engine.py -> 1
grep -c "def _write_dcf_row" src/financial_engine.py -> 1
grep -c "INPUT_INVALIDO" src/financial_engine.py -> 7 (>= 2 required)
grep -c "FORA DO INTERVALO CONFIAVEL" src/financial_engine.py -> 3 (>= 1 required)
grep -c "terminal_growth >= wacc" src/financial_engine.py -> 3 (>= 1 required)
```

---
*Phase: 03-financial-engine*
*Completed: 2026-05-11*
