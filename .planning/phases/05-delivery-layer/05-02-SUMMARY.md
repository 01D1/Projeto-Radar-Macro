---
phase: 05-delivery-layer
plan: "02"
subsystem: delivery-pages
tags: [streamlit, pandas-styler, plotly, fpdf2, dashboard, pages, dark-theme]
dependency_graph:
  requires: [05-01]
  provides: [05-03, 05-04]
  affects:
    - scanner_quant_profit_b3/pages/inteligencia_watchlist.py
    - scanner_quant_profit_b3/pages/inteligencia_ativo.py
    - scanner_quant_profit_b3/pages/inteligencia_macro.py
    - scanner_quant_profit_b3/pages/inteligencia_oportunidades.py
tech_stack:
  added: []
  patterns:
    - "two-root sys.path bootstrap (SCANNER_ROOT + PIPELINE_ROOT)"
    - "from _style import DARK_CSS + st.markdown(DARK_CSS, unsafe_allow_html=True)"
    - "Pandas Styler.map() for positioning colors (COMPRAR/MANTER/VENDER)"
    - "plotly.graph_objects template=plotly_dark + paper_bgcolor=rgba(0,0,0,0)"
    - "st.expander(expanded=False) for drivers/risks cards"
    - "st.download_button with ReportGenerator try/except guard"
    - "st.progress(score/100) for conviction bars"
    - "module-level main() call for Streamlit page execution"
key_files:
  created:
    - scanner_quant_profit_b3/pages/inteligencia_watchlist.py
    - scanner_quant_profit_b3/pages/inteligencia_ativo.py
    - scanner_quant_profit_b3/pages/inteligencia_macro.py
    - scanner_quant_profit_b3/pages/inteligencia_oportunidades.py
  modified: []
decisions:
  - "main() chamada em nivel de modulo alem do guard if __name__==main — Streamlit executa o modulo diretamente, nao via __main__, entao a chamada de nivel de modulo e obrigatoria"
  - "inteligencia_macro.py renderiza Selic full-width como focal point (UI-SPEC D-11), depois pares 2-col: IPCA+PTAX e CDS+PIB — cada serie com fallback st.caption quando dados ausentes"
  - "inteligencia_ativo.py usa try/except ao redor de ReportGenerator.generate() com st.error() para usuario — nunca expoe traceback (T-05-05 threat mitigation)"
  - "json nao importado em inteligencia_ativo.py — data.py ja desserializa thesis_json antes de retornar (Pitfall 5 prevenido)"
metrics:
  duration: 3min
  completed_date: "2026-05-18"
  tasks_completed: 2
  files_created: 4
  files_modified: 0
  tests_added: 0
  tests_total: 129
---

# Phase 5 Plan 02: Intelligence Pages — 4 Streamlit Pages with Watchlist, Asset Detail, Macro Panel, Opportunities

**One-liner:** 4 paginas Streamlit inteligencia_*.py com sys.path two-root bootstrap, DARK_CSS, Pandas Styler, Plotly dark charts, expanders, PDF download e progress bars de conviccao.

---

## Objective

Criacao das 4 paginas Streamlit de inteligencia de investimentos que consomem a camada de dados criada no Plan 05-01. Cada pagina segue o padrao de bootstrap sys.path dois-roots, injeta o tema dark via DARK_CSS, e importa exclusivamente de src/dashboard/data.py sem definir @st.cache_data proprio.

---

## Tasks Completed

### Task 1: inteligencia_watchlist.py e inteligencia_oportunidades.py
**Commit:** b98d974

Criados:
- `scanner_quant_profit_b3/pages/inteligencia_watchlist.py`
  - two-root sys.path bootstrap (SCANNER_ROOT + PIPELINE_ROOT)
  - st.title("Watchlist de Ativos")
  - get_watchlist_summary() com empty state st.info() + st.stop()
  - pd.DataFrame com rename de 9 colunas per UI-SPEC (ticker, Posicionamento, Confianca, etc.)
  - Formatacao numerica: Valor Justo 2dp, Upside % com +/- prefix, Preco 2dp
  - Pandas Styler.map(_color_positioning) subset=["Posicionamento"]
  - st.dataframe(use_container_width=True, hide_index=True)
  - st.caption com freshness timestamp (DEL-02)

- `scanner_quant_profit_b3/pages/inteligencia_oportunidades.py`
  - two-root sys.path bootstrap
  - st.title("Oportunidades de Investimento")
  - get_opportunities() com empty state
  - Loop sobre opps com st.columns([1, 3, 1, 2])
  - _SIGNAL_COLORS badge dict (DCF_DIVERGENCE/MOMENTUM_CROSSOVER/IPE_EVENT)
  - st.progress(score/100, text=f"{score}/100") per UI-SPEC D-10

### Task 2: inteligencia_ativo.py e inteligencia_macro.py
**Commit:** 03032be

Criados:
- `scanner_quant_profit_b3/pages/inteligencia_ativo.py`
  - two-root sys.path bootstrap
  - st.title("Analise de Ativo")
  - get_watchlist_summary() para tickers do st.selectbox
  - get_asset_detail(ticker) com empty state por ticker
  - st.columns(3): Posicionamento / Valor Justo (R$) / Upside %
  - st.subheader Cenario Otimista + Pessimista com st.markdown
  - st.subheader Drivers com loop st.expander(expanded=False) + _impact_badge (HIGH/MEDIUM/LOW)
  - st.subheader Riscos com loop st.expander + severity badge
  - st.download_button("Baixar Relatorio PDF") via ReportGenerator com try/except st.error()
  - st.caption("Atualizado em: {generated_at}")

- `scanner_quant_profit_b3/pages/inteligencia_macro.py`
  - two-root sys.path bootstrap
  - import plotly.graph_objects as go
  - st.title("Painel Macroeconomico")
  - get_macro_panel() com empty state st.warning()
  - _build_chart() helper: go.Scatter mode=lines, line=#93C5FD, update_layout template=plotly_dark
  - Selic full-width como focal point (D-11 / UI-SPEC)
  - Pares 2-col: IPCA+PTAX (row 2), CDS+PIB (row 3)
  - Fallback st.caption para series vazias

---

## Deviations from Plan

Nenhuma — plano executado exatamente como escrito. Todos os criterios de aceitacao foram atendidos na primeira implementacao.

---

## Known Stubs

Nenhum stub critico. As paginas consomem os dados reais via src/dashboard/data.py. O estado vazio (st.info/st.warning) e comportamento correto quando o pipeline nao foi executado — nao e stub.

---

## Threat Flags

Nenhum novo surface de seguranca introduzido. As paginas consomem apenas leitura via data.py (camada cacheada). Ticker selector e limitado a get_watchlist_summary() (T-05-01 mitigado). PDF usa try/except sem expor traceback (T-05-05 aceito).

---

## Verification Results

```
All 4 pages: syntax OK (ast.parse)
No cache_data in page files: OK (0 matches)
PIPELINE_ROOT bootstrap: all 4 files confirmed
Acceptance criteria: all assertions passed
Test suite (excl. pre-existing test_news_hunter_config failure): 129 passed
```

---

## Self-Check: PASSED

Arquivos criados verificados:
- scanner_quant_profit_b3/pages/inteligencia_watchlist.py: FOUND
- scanner_quant_profit_b3/pages/inteligencia_ativo.py: FOUND
- scanner_quant_profit_b3/pages/inteligencia_macro.py: FOUND
- scanner_quant_profit_b3/pages/inteligencia_oportunidades.py: FOUND

Commits verificados:
- b98d974: FOUND (feat Task 1)
- 03032be: FOUND (feat Task 2)
