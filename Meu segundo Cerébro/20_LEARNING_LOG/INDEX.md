---
title: Diário de Aprendizado
tags:
  - aprendizado
  - log
  - evolução
aliases:
  - Learning Log
  - Diário de Aprendizado
---

# Diário de Aprendizado

> Registro contínuo do que o projeto aprende ao operar.

---

## Como Registrar

Criar entrada com o formato:

```markdown
## AAAA-MM-DD — [Título do Aprendizado]

**Categoria:** biblioteca / fonte / contabilidade / valuation / arquitetura / setor
**Contexto:** onde/como surgiu
**Aprendizado:** o que foi aprendido
**Aplicação futura:** como isso vai mudar a forma de operar
**Linkar para:** skill, workflow ou heurística afetada
```

---

## Categorias

- `biblioteca` — nova biblioteca ou ferramenta útil
- `fonte` — nova fonte de dados ou nuance de fonte existente
- `contabilidade` — armadilha ou peculiaridade contábil
- `valuation` — metodologia, benchmark ou erro de abordagem
- `arquitetura` — melhoria de design do sistema ou código
- `setor` — insight setorial importante

---

## Log

### 2026-04-16 — Estrutura inicial do vault criada

**Categoria:** arquitetura
**Contexto:** Criação do segundo cérebro para o projeto de inteligência financeira.
**Aprendizado:** Um vault de segundo cérebro para este tipo de projeto precisa de 5 camadas distintas (conhecimento, dados, modelagem, inteligência, entrega) para funcionar bem. Misturar essas camadas causa confusão de responsabilidades.
**Aplicação futura:** Sempre checar em qual camada uma nova nota ou módulo pertence antes de criar.
**Linkar para:** [[00_META/ARQUITETURA_DO_CONHECIMENTO]]

---

### 2026-04-16 — Pipeline de Bancos: Erros e Soluções

**Categoria:** fonte / arquitetura
**Contexto:** Construção do pipeline completo de extração de DFPs para 12 bancos brasileiros (ITUB4, BBAS3, BBDC4, SANB11, BPAC11, INTR4, BRSR6, ABCB4, BMGB4, BPAN4, PINE4, ITSA4).

**Aprendizados:**

1. `DFPParser` retorna colunas normalizadas (`account_code`, `account_name`, `value`), não o formato bruto CVM. Qualquer mapper downstream precisa detectar o formato automaticamente via duck typing nas colunas.

2. **PL de bancos: código vs. nome.** Layout varia: Itaú usa `2.08`, BB usa `2.07`, ITSA4 usa `2.03`. Solução: usar o nome da conta (`"patrimônio líquido consolidado"`) com prioridade sobre o código para campos ambíguos (`NAME_PRIORITY_FIELDS`).

3. **Armadilha do código `2.07` no Itaú.** Itaú tem `2.07 = "Passivos sobre Ativos Descontinuados" = 0`. Mapear `2.07 → total_equity` para suportar BB corrompe o Itaú (first-wins, 0 sobrescreve 177bi). Solução: remover `2.07` do mapa de código; confiar apenas no nome.

4. **`net_income = 0` em bancos sem minoritários.** ABCB4, BPAN4: colocam tudo em `3.11` (consolidado), `3.11.01 = 0`. Fallback: `if net_income == 0 and net_income_consolidated != 0: net_income = net_income_consolidated`.

5. **DFC key errada.** `bank_parser` chamava `mapped.get("DFC_MI")` mas `DFPParser` retorna chave `"DFC"`. Erro silencioso: cashflow ficava `None` sem mensagem de erro.

**Aplicação futura:** Ao adicionar novos bancos, verificar o layout de PL na DFP antes de assumir `2.08`. O mapeamento por nome é mais robusto para campos de equity.

**Linkar para:** [[../12_PYTHON/src/normalization/bank_account_mapper]], [[../17_MEMORY/Padroes_identificados]]

---

### 2026-04-16 — Bancos Brasileiros: Diferenças de Análise vs. Industriais

**Categoria:** contabilidade / valuation
**Contexto:** Adaptação do framework de análise industrial para bancos.

**Aprendizados:**

1. **3.01 para bancos ≠ Receita Líquida.** `3.01 = Receitas da Intermediação Financeira` inclui receitas brutas. Não usar como proxy de "top line" para comparação com industriais.

2. **A métrica central de banco é o NII** (Net Interest Income = `3.03` no CVM). Equivale ao Resultado Bruto da Intermediação Financeira (após PDD). O spread bancário é calculado sobre o NII, não sobre o total de intermediação.

3. **ROE é a principal métrica comparativa.** Para comparar bancos de tamanhos diferentes, ROE elimina o efeito do capital regulatório e do mix de funding. ROIC não é diretamente aplicável (banco não tem "capital investido" delimitável da mesma forma).

4. **Alavancagem em bancos é esperada e regulada.** Leverage de 8–12x assets/equity é normal (Basileia III). Não usar os mesmos thresholds de alavancagem de industriais.

5. **BPAC11 (BTG) é único.** É "banco + gestora + advisory + corporate lending". Métricas de banco tradicional (spread de crédito, NIM) são menos representativas. Foco em: receitas por segmento, eficiência por linha de negócio, capital próprio aplicado.

6. **ITSA4 não é banco.** Holding pura com investimentos financeiros. `total_financial_revenues` na prática é dividendos + equivalência patrimonial de Itaú+outros. Não comparar com bancos.

**Aplicação futura:** Ao construir a tabela comparativa de bancos, usar ROE, Eficiência, NIM Proxy e Índice de PDD/Carteira como métricas padrão — não EBITDA ou ROIC.

**Linkar para:** [[../04_GOVERNANCA/FRAMEWORK_GERAL_DE_GOVERNANCA]], [[../03_COMPANIES/ITUB4/DADOS_HISTORICOS]]

---
*Última atualização: 2026-04-16*
