---
phase: 05-delivery-layer
plan: "01"
subsystem: delivery-foundation
tags: [streamlit, fpdf2, dashboard, data-layer, telegram, scheduler, css]
dependency_graph:
  requires: [04-04]
  provides: [05-02, 05-03, 05-04]
  affects: [src/dashboard/data.py, src/delivery/pdf_report.py, src/delivery/telegram_bot.py, src/scheduler.py]
tech_stack:
  added: [fpdf2>=2.7.0]
  patterns: [st.cache_data(ttl=300), try/finally conn.close(), bytes(self.output()), _maybe_send_thesis_alert]
key_files:
  created:
    - Analista de Investimentos/12_PYTHON/src/dashboard/__init__.py
    - Analista de Investimentos/12_PYTHON/src/dashboard/data.py
    - Analista de Investimentos/12_PYTHON/src/delivery/pdf_report.py
    - Analista de Investimentos/12_PYTHON/tests/test_dashboard_data.py
    - Analista de Investimentos/12_PYTHON/tests/test_delivery_pdf.py
    - Analista de Investimentos/12_PYTHON/tests/test_delivery_telegram.py
    - Analista de Investimentos/12_PYTHON/tests/test_scheduler_delivery.py
    - Analista de Investimentos/scanner_quant_profit_b3/_style.py
  modified:
    - Analista de Investimentos/12_PYTHON/pyproject.toml
    - Analista de Investimentos/12_PYTHON/src/delivery/telegram_bot.py
    - Analista de Investimentos/12_PYTHON/src/intelligence_layer.py
    - Analista de Investimentos/12_PYTHON/src/scheduler.py
    - Analista de Investimentos/12_PYTHON/config/schedules.yaml
    - Analista de Investimentos/scanner_quant_profit_b3/app.py
decisions:
  - "test_pdf_contains_required_strings usa pdfplumber em vez de decode(latin-1) — fpdf2 comprime streams com zlib, busca raw bytes nao funciona; pdfplumber ja instalado (pdfplumber>=0.10.0 em pyproject.toml)"
  - "_maybe_send_thesis_alert adicionada em intelligence_layer.py com chamada em run_ticker() apos commit da tese (D-13)"
  - "job_morning_brief() e send_thesis_alert()/send_daily_brief() implementados neste plano (plan 05-01) em vez de planos 05-02/05-03 — integra melhor com os test stubs exigidos"
metrics:
  duration: 15min
  completed_date: "2026-05-18"
  tasks_completed: 2
  files_created: 8
  files_modified: 6
  tests_added: 15
  tests_total: 129
---

# Phase 5 Plan 01: Delivery Foundation — Data Layer, PDF Stub, Test Stubs, App Navigation

**One-liner:** src/dashboard/ query layer com 4 @st.cache_data functions + ReportGenerator FPDF stub + _style.py CSS + 4 test stub files + fpdf2 instalado + app.py com 9 paginas registradas.

---

## Objective

Wave 0 foundation para Phase 5. Cria a camada de acesso a dados (src/dashboard/data.py), o stub do gerador PDF (src/delivery/pdf_report.py), o modulo CSS compartilhado (_style.py), registra as 4 novas paginas em app.py, instala fpdf2, e cria os 4 arquivos de teste stub com as assinaturas corretas.

---

## Tasks Completed

### Task 1: src/dashboard package, data.py, _style.py
**Commit:** 95d89d5 (feat) + 6fb65e6 (fix restore)

Criados:
- `src/dashboard/__init__.py` — pacote Python vazio
- `src/dashboard/data.py` — 4 funcoes @st.cache_data(ttl=300): get_watchlist_summary(), get_asset_detail(ticker), get_macro_panel(), get_opportunities(); todas com try/finally conn.close() e SQL parametrizado (T-05-01)
- `scanner_quant_profit_b3/_style.py` — constante DARK_CSS extraida verbatim do app.py

### Task 2: fpdf2, ReportGenerator, test stubs, app.py nav
**Commit:** 71198cf

Criados/modificados:
- `pyproject.toml` — fpdf2>=2.7.0 adicionado a dependencies
- `src/delivery/pdf_report.py` — ReportGenerator(FPDF) com 8 metodos de secao, generate() e generate_from_fixture() retornando bytes(self.output()) — nunca escreve em disco (T-05-03)
- `src/delivery/telegram_bot.py` — send_thesis_alert() e send_daily_brief() adicionados
- `src/intelligence_layer.py` — _maybe_send_thesis_alert() adicionada + chamada em run_ticker() apos commit (D-13)
- `src/scheduler.py` — job_morning_brief() adicionado a _JOB_REGISTRY
- `config/schedules.yaml` — morning_brief cron "15 8 * * 1-5" adicionado
- `tests/test_dashboard_data.py` — 5 testes DEL-01/DEL-02
- `tests/test_delivery_telegram.py` — 4 testes DEL-03/DEL-04
- `tests/test_delivery_pdf.py` — 3 testes DEL-05
- `tests/test_scheduler_delivery.py` — 3 testes DEL-04
- `scanner_quant_profit_b3/app.py` — 4 inteligencia_* pages em _PAGES; ratio [1.6] -> [1.4]

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_pdf_contains_required_strings falhou com decode(latin-1)**
- **Found during:** Task 2 — verificacao dos testes
- **Issue:** fpdf2 2.8.x comprime streams de texto com zlib. O metodo `pdf_bytes.decode("latin-1", errors="replace")` do plano nao extrai texto legivel — busca por "CVM" e "PETR4" retornava False
- **Fix:** Substituido por pdfplumber (ja instalado em pyproject.toml) para extrair texto antes das assertivas
- **Files modified:** tests/test_delivery_pdf.py
- **Commit:** 71198cf

**2. [Rule 1 - Bug] Commit 95d89d5 deletou arquivos da Fase 4 por staging implicito**
- **Found during:** Task 1 — logo apos commit
- **Issue:** O git do sub-repo "Analista de Investimentos" tinha arquivos da Fase 4 (intelligence_layer.py, thesis_prompt.j2, test_intelligence_layer.py, test_scheduler_intelligence.py, etc.) em estado MM (staged deletions de branches anteriores). Ao commitar apenas os 3 arquivos da Tarefa 1, o git incluiu essas deletions implicitas
- **Fix:** Restaurados todos os arquivos da Fase 4 a partir do commit 573e4fb (ultimo bom); commit de correcao 6fb65e6
- **Files restored:** intelligence_layer.py, thesis_prompt.j2, test_intelligence_layer.py, test_scheduler_intelligence.py, schedules.yaml, pyproject.toml, db.py, scheduler.py, test_db_schema.py
- **Commit:** 6fb65e6

**3. [Rule 2 - Missing critical functionality] send_thesis_alert, send_daily_brief e _maybe_send_thesis_alert implementados no Plan 05-01**
- **Found during:** Task 2 — criacao dos test stubs
- **Issue:** test_delivery_telegram.py requer send_thesis_alert() e test_scheduler_delivery.py requer job_morning_brief() — sem a implementacao real os testes nao podiam nem compilar
- **Fix:** Implementados em telegram_bot.py, intelligence_layer.py e scheduler.py como parte dos requisitos do plano (nao apenas stubs)
- **Commit:** 71198cf

---

## Known Stubs

Nenhum stub critico. O ReportGenerator.generate_from_fixture() usa dados de fixture internos (nao banco de dados) — comportamento intencional para testes sem DB live. As paginas inteligencia_*.py serao criadas no Plan 05-02.

---

## Threat Flags

Nenhum novo surface de seguranca introduzido alem dos ja documentados no plano (T-05-01, T-05-03, T-05-04).

---

## Verification Results

```
fpdf2 Version: 2.8.7 (instalado)
imports OK: src/dashboard/data.py, src/delivery/pdf_report.py
test results: 15 passed (15 novos testes), 129 total (excluindo 1 pre-existente out-of-scope)
```

---

## Self-Check: PASSED

Arquivos criados verificados:
- src/dashboard/__init__.py: FOUND
- src/dashboard/data.py: FOUND
- src/delivery/pdf_report.py: FOUND
- scanner_quant_profit_b3/_style.py: FOUND
- tests/test_dashboard_data.py: FOUND
- tests/test_delivery_telegram.py: FOUND
- tests/test_delivery_pdf.py: FOUND
- tests/test_scheduler_delivery.py: FOUND

Commits verificados:
- 95d89d5: FOUND (feat Task 1)
- 6fb65e6: FOUND (fix restore Phase 4)
- 71198cf: FOUND (feat Task 2)
