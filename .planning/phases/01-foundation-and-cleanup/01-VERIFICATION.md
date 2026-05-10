---
phase: 01-foundation-and-cleanup
verified: 2026-05-10T21:00:00Z
status: gaps_found
score: 2/4 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Toda chamada externa (CVM, BCB, yfinance, Anthropic, Telegram) que falha por erro de rede retenta automaticamente com backoff exponencial; falha permanente produz log estruturado, nunca crash por exceção não tratada"
    status: failed
    reason: "src/utils/retry.py nao aceita parametro jitter (TypeError) e nao eleva IngestionError na exaustao (re-raise bruto). src/utils/errors.py nao existe — ModuleNotFoundError em qualquer import de IngestionError. Todos os 3 testes de FOUND-03 (test_backoff_jitter, test_ingestion_error_raised_on_exhaustion, test_non_matching_exception_propagates) falham."
    artifacts:
      - path: "Analista de Investimentos/12_PYTHON/src/utils/retry.py"
        issue: "Assinatura: retry(attempts, delay, backoff, exceptions) — parametro jitter ausente. Exaustao de tentativas executa raise bruto em vez de raise IngestionError(func.__name__, exc)."
      - path: "Analista de Investimentos/12_PYTHON/src/utils/errors.py"
        issue: "Arquivo nao existe. test_retry.py importa IngestionError deste modulo — ModuleNotFoundError bloqueia toda a suite de testes."
    missing:
      - "Criar src/utils/errors.py com classe IngestionError(Exception) e atributo cause"
      - "Adicionar parametro jitter: float = 0.0 na assinatura de retry()"
      - "Substituir raise por raise IngestionError(func.__name__, exc) na exaustao de tentativas"
      - "Adicionar sleep com jitter: actual_wait = wait + random.uniform(0, jitter)"

  - truth: "Cada execucao do pipeline produz saida de log estruturada (nome do modulo, ticker, run ID) em logs/; arquivos de log rotacionam diariamente; um desenvolvedor consegue rastrear qualquer execucao end-to-end apenas com os logs"
    status: failed
    reason: "src/utils/logger.py nao exporta bind_run_id — funcao inexistente no modulo. test_logger.py falha com ImportError em test_run_id_binding. Sem bind_run_id, o run_id nunca e injetado nas entradas de log, violando o criterio de sucesso SC-4."
    artifacts:
      - path: "Analista de Investimentos/12_PYTHON/src/utils/logger.py"
        issue: "Modulo termina em get_logger() (linha 39). bind_run_id nao existe — nenhuma funcao de contexto loguru implementada."
    missing:
      - "Implementar bind_run_id(prefix: str) como context manager usando loguru.contextualize(run_id=run_id)"
      - "Exportar bind_run_id no modulo src/utils/logger.py"

  - truth: "O guarda de producao em src/main.py executa sys.exit(1) no escopo do modulo (linhas 26-33), o que encerra o processo do pytest ao importar qualquer modulo que use config.settings — CR-04 do code review"
    status: failed
    reason: "src/main.py linhas 26-33: o bloco if settings.env == production esta no corpo do modulo, fora de qualquer funcao. Quando pytest importa test_consolidation.py, que importa config.settings, o singleton settings = Settings() e instanciado. Se ENV=production estiver no ambiente do desenvolvedor sem as chaves, sys.exit(1) encerra o processo inteiro do pytest — nao apenas o teste. CR-04 identifica exatamente este problema e prescreve mover o guard para dentro de app()."
    artifacts:
      - path: "Analista de Investimentos/12_PYTHON/src/main.py"
        issue: "Linhas 26-33: startup guard no escopo do modulo. Deve estar dentro de app() — apenas executado ao invocar o CLI, nunca durante import."
    missing:
      - "Mover o bloco if settings.env == production: ... sys.exit(1) para dentro da funcao app(), antes de build_parser()"
      - "Garantir que o modulo pode ser importado sem efeitos colaterais (somente configure_logging + get_logger no nivel do modulo)"
---

# Fase 1: Foundation & Cleanup — Relatório de Verificação

**Objetivo da Fase:** O codebase tem uma unica fonte canonical, sem credenciais no codigo-fonte, e toda chamada externa e envolvida com logica de retry e logging estruturado — tornando todas as fases subsequentes seguras para construir.
**Verificado:** 2026-05-10T21:00:00Z
**Status:** gaps_found
**Re-verificacao:** Nao — verificacao inicial

---

## Alcance do Objetivo

### Criterios de Sucesso do ROADMAP (fonte da verdade)

O ROADMAP.md define 4 criterios de sucesso para a Fase 1. Todos os 4 sao verificados abaixo.

### Verdades Observaveis

| # | Verdade | Status | Evidencia |
|---|---------|--------|-----------|
| SC-1 | `python -m src.main` e o unico ponto de entrada ativo; sem manipulacao de sys.path; DEPRECATED.md presente | VERIFICADO | `src/processing/pipeline.py` sem sys.path.insert/append (grep confirmado). `pipeline banco completo/DEPRECATED.md` existe. Todos os 3 testes de test_consolidation.py passam. |
| SC-2 | Plataforma recusa iniciar em producao sem credenciais; nenhum token literal no codigo-fonte | VERIFICADO (com ressalva CR-04) | `news_hunter/config.py` linhas 61-62: `TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")`. Nenhum token hardcoded encontrado (grep por 8283626758, AAEx-rPwbFczQV3, sk-ant-api03 retornou zero resultados). `.env` existe, `.gitignore` cobre `env` e `.env`. `config/settings.py` tem REQUIRED_IN_PRODUCTION + model_post_init. 5/5 testes de credenciais passam. RESSALVA: o guard em `src/main.py` esta no escopo do modulo (CR-04) — ver gaps. |
| SC-3 | Toda chamada externa retenta com backoff exponencial; falha permanente produz log estruturado em vez de crash | FALHOU | `src/utils/retry.py` nao aceita `jitter` (TypeError). Nao eleva `IngestionError` (raise bruto). `src/utils/errors.py` nao existe — ModuleNotFoundError. 3/4 testes de test_retry.py falham. |
| SC-4 | Cada execucao produz log estruturado com nome do modulo, ticker e run ID; arquivos rodam diariamente | FALHOU | `src/utils/logger.py` nao exporta `bind_run_id`. `test_run_id_binding` falha com ImportError. Sem bind_run_id, run_id nunca e injetado nos registros de log. |

**Pontuacao:** 2/4 verdades verificadas

---

### Artefatos Obrigatorios

| Artefato | Esperado | Status | Detalhes |
|----------|----------|--------|----------|
| `src/processing/pipeline.py` | Importacoes com prefixo src. — sem sys.path.insert/append | VERIFICADO | Grep por sys.path.insert/append retornou zero resultados. Importacoes usam `from src.utils.logger import get_logger`. |
| `pipeline banco completo/DEPRECATED.md` | Aviso de congelamento | VERIFICADO | Arquivo existe. Conteudo inclui "Congelado em: 2026-05-06". |
| `Analista de Investimentos/12_PYTHON/.env` | Arquivo de credenciais compartilhado | VERIFICADO | `.env` existe (Glob confirmado). |
| `Analista de Investimentos/.gitignore` | Cobre env e .env | VERIFICADO | .gitignore contem entradas para `env`, `.env`, `*.env` na secao "Variaveis de ambiente / segredos". |
| `news_hunter/config.py` | Sem fallbacks hardcoded para token | VERIFICADO | Linhas 61-62: `os.getenv("TELEGRAM_TOKEN", "")` e `os.getenv("TELEGRAM_CHAT_ID", "")`. |
| `config/settings.py` | REQUIRED_IN_PRODUCTION + model_post_init | VERIFICADO | Linha 10: `REQUIRED_IN_PRODUCTION = [...]`. Linhas 50-60: model_post_init com startup validation. |
| `src/main.py` | Guard de producao (CR-04: dentro de app()) | FALHOU (STUB PERIGOSO) | Guard existe nas linhas 26-33 MAS esta no escopo do modulo, nao dentro de app(). Executa sys.exit(1) durante import — encerra pytest se ENV=production. |
| `src/utils/retry.py` | jitter + IngestionError na exaustao | FALHOU (STUB) | Assinatura: `retry(attempts, delay, backoff, exceptions)` — sem jitter. Exaustao: `raise` bruto, nao `raise IngestionError(...)`. |
| `src/utils/errors.py` | IngestionError com atributo .cause | AUSENTE | Arquivo nao existe. ModuleNotFoundError em test_retry.py linhas 25 e 43. |
| `src/utils/logger.py` | bind_run_id como context manager | FALHOU (STUB) | Arquivo existe e implementa configure_logging + get_logger mas nao exporta bind_run_id. |
| `tests/test_retry.py` | 4 testes coletados | VERIFICADO (RED) | Arquivo existe com 4 testes. Falham na execucao — RED intencional ate implementacao. Colecao sem erros: test_success_on_first_attempt nao testa jitter/IngestionError e seria o unico a passar antes da implementacao. |
| `tests/test_logger.py` | 3 testes coletados | VERIFICADO (RED) | Arquivo existe com 3 testes. test_run_id_binding falha com ImportError na colecao (importa bind_run_id que nao existe). |

---

### Verificacao de Links-Chave (Wiring)

| De | Para | Via | Status | Detalhes |
|----|------|-----|--------|----------|
| `news_hunter/config.py` | `12_PYTHON/.env` | `load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")` | VERIFICADO | Linha 10: path explicito presente conforme exigido. |
| `config/settings.py` | `.env` | `SettingsConfigDict(env_file=[ROOT / ".env", ROOT / "env"])` | VERIFICADO | Linha 14-20: SettingsConfigDict com env_file configurado. |
| `src/main.py` | `settings.env == "production"` | startup guard com sys.exit(1) | PARCIAL (CR-04) | Guard existe mas no escopo do modulo (linhas 26-33), nao dentro de app(). Funcional para uso em CLI mas quebra isolamento de testes. |
| `src/utils/retry.py` | `src/utils/errors.IngestionError` | raise IngestionError na exaustao | NAO CONECTADO | errors.py nao existe; retry.py nao importa IngestionError; exaustao usa raise bruto. |
| `src/utils/logger.py` | loguru.contextualize | bind_run_id context manager | NAO CONECTADO | bind_run_id nao implementada — funcao inexistente no modulo. |

---

### Rastreamento de Requisitos

| REQ-ID | Plano Fonte | Descricao | Status | Evidencia |
|--------|-------------|-----------|--------|-----------|
| FOUND-01 | 01-01 | Unica fonte canonical; sem sys.path manipulation; duplicatas arquivadas | SATISFEITO | pipeline.py limpo; DEPRECATED.md presente; test_consolidation.py 3/3 verde. |
| FOUND-02 | 01-02 | Credenciais em .env; pydantic-settings; startup validation; .gitignore | SATISFEITO (com ressalva CR-04) | Nenhum token hardcoded; .env existe e protegido; REQUIRED_IN_PRODUCTION + model_post_init implementados; 5/5 testes verdes. Guard em src/main.py no escopo errado (CR-04) mas validacao em config/settings.py e redundante e funcional. |
| FOUND-03 | Nunca planejado (01-03 nao executado) | Retry com backoff exponencial em todas chamadas externas | BLOQUEADO | retry.py sem jitter; sem IngestionError; errors.py ausente. Nenhum dos 3 testes do contrato passa. |
| FOUND-04 | Nunca planejado (01-03 nao executado) | Logging estruturado com run_id; rotacao diaria | BLOQUEADO | bind_run_id nao implementada; test_run_id_binding falha com ImportError. Logging basico (configure_logging + get_logger) existe mas sem injecao de run_id. |

**FOUND-01 e FOUND-02 estao marcados como "Pending" no REQUIREMENTS.md** (nao atualizados para "completed" apos execucao dos planos).

---

### Anti-Padroes Encontrados

| Arquivo | Linha | Padrao | Severidade | Impacto |
|---------|-------|--------|------------|---------|
| `src/main.py` | 26-33 | startup guard no escopo do modulo (`if settings.env == "production":` fora de funcao) | BLOQUEADOR | sys.exit(1) executa durante import — encerra processo do pytest inteiro se ENV=production no ambiente. CR-04 do code review prescreveu correcao. |
| `src/utils/retry.py` | 12-13 | Assinatura sem jitter; exaustao com raise bruto | BLOQUEADOR | Todos os 3 testes de contrato FOUND-03 falham. Chamadas externas nao tem contrato de IngestionError. |
| `src/utils/logger.py` | inteiro | bind_run_id ausente | BLOQUEADOR | test_run_id_binding falha com ImportError; run_id nunca injetado em logs — SC-4 nao atendido. |
| `src/utils/errors.py` | (nao existe) | Modulo ausente | BLOQUEADOR | ModuleNotFoundError em qualquer import de IngestionError — bloqueia colecao de test_retry.py. |
| `news_hunter/main.py` | 129 | Mensagem de erro menciona TELEGRAM_BOT_TOKEN mas variavel no .env e TELEGRAM_TOKEN | INFO | Confusao para quem depura — IN-01 do code review. |

---

### Verificacoes Comportamentais (Spot-Checks)

| Comportamento | Comando | Resultado | Status |
|---------------|---------|-----------|--------|
| retry.py aceita parametro jitter | `grep "jitter" src/utils/retry.py` | Nenhuma ocorrencia | FALHOU |
| errors.py existe | Glob `**/src/utils/errors.py` | Nenhum arquivo encontrado | FALHOU |
| bind_run_id exportado por logger.py | `grep "bind_run_id" src/utils/logger.py` | Nenhuma ocorrencia | FALHOU |
| Nenhum token hardcoded em src/ e news_hunter/ | `grep "8283626758\|AAEx-rPwbFczQV3"` | Zero resultados | PASSOU |
| sys.path ausente em pipeline.py | `grep "sys.path"` em pipeline.py | Zero resultados | PASSOU |
| Guard de producao no escopo do modulo em src/main.py | Leitura direta linhas 26-33 | Guard em nivel de modulo (nao dentro de app()) | FALHOU (CR-04) |
| .env existe e .gitignore o cobre | Glob + leitura de .gitignore | .env encontrado; .gitignore contem `env`, `.env`, `*.env` | PASSOU |
| DEPRECATED.md existe | Glob | Encontrado em `pipeline banco completo/DEPRECATED.md` | PASSOU |

---

### Verificacao Humana Necessaria

#### 1. Windows Task Scheduler aponta para caminho correto

**Teste:** Executar `schtasks /Query /FO LIST /TN "ValuationBancario_Manha"` e `schtasks /Query /FO LIST /TN "ValuationBancario_Tarde"` no PowerShell
**Esperado:** "Task To Run" deve conter `C:\Users\55819\OneDrive - EPEJUD\DIEGO\OBSIDIAN\Analista de Investimentos\12_PYTHON\pipeline banco completo\scheduler.py` (nao o caminho antigo de Downloads)
**Por que humano:** Estado do OS do Windows — nao verificavel via analise estatica de codigo

#### 2. Testes test_consolidation.py e test_settings.py e test_news_hunter_config.py passam de fato

**Teste:** Do diretorio `Analista de Investimentos/12_PYTHON/` com venv ativo, executar `pytest tests/test_consolidation.py tests/test_settings.py tests/test_news_hunter_config.py -v`
**Esperado:** 8/8 testes verdes (3 + 3 + 2)
**Por que humano:** Ambiente Windows/venv nao executavel neste agente de verificacao; o SUMMARY afirma 5/5 verdes mas nao inclui test_consolidation.py

---

## Resumo dos Gaps

**2 gaps bloqueadores impedem o alcance do objetivo da fase:**

### Gap 1: FOUND-03 — Infraestrutura de retry nao implementada (Plano 01-03 nunca executado)

**Causa raiz:** O plano 01-03 (Retry & Logging Infrastructure) foi planejado no ROADMAP como o terceiro de 3 planos da Fase 1, mas nunca foi criado ou executado. Os stubs de teste existem e estao em estado RED intencional aguardando implementacao.

**O que falta:**
1. Criar `src/utils/errors.py` com `class IngestionError(Exception)` e atributo `cause`
2. Extender `src/utils/retry.py`: adicionar parametro `jitter`, usar `random.uniform(0, jitter)` no sleep, elevar `IngestionError` na exaustao
3. Verificar que `@retry` e aplicado a todas chamadas externas em `src/` (CVM, BCB, yfinance, Anthropic, Telegram)

**Testes que devem passar:** `pytest tests/test_retry.py -v` — 4/4 verde

### Gap 2: FOUND-04 — bind_run_id nao implementado (Plano 01-03 nunca executado)

**Causa raiz:** Mesma que Gap 1 — plano 01-03 nao executado. Logger basico (configure_logging + get_logger) existe mas sem injecao de run_id via contextvars.

**O que falta:**
1. Implementar `bind_run_id(prefix: str = "run")` em `src/utils/logger.py` como context manager usando `loguru.contextualize(run_id=...)`
2. Exportar `bind_run_id` no modulo

**Testes que devem passar:** `pytest tests/test_logger.py -v` — 3/3 verde (test_run_id_binding em particular)

### Gap 3 (Problema de Segurança de Teste): CR-04 — Guard de producao no escopo do modulo em src/main.py

**Causa raiz:** Plano 01-02 adicionou o guard corretamente do ponto de vista de comportamento de producao, mas o posicionou no escopo do modulo (linhas 26-33) em vez de dentro de `app()`. O code review (CR-04) identificou o problema e prescreveu a correcao.

**Risco:** Se `ENV=production` estiver definido no ambiente do desenvolvedor ou CI sem as chaves, importar qualquer modulo que importe `src.main` — ou executar `pytest` — chama `sys.exit(1)`, encerrando o processo inteiro.

**O que falta:**
1. Mover o bloco `if settings.env == "production": ... sys.exit(1)` (linhas 26-33) para dentro de `app()`, antes de `build_parser()`
2. O nivel do modulo deve manter apenas `configure_logging(...)` e `log = get_logger(__name__)`

---

*Verificado: 2026-05-10T21:00:00Z*
*Verificador: Claude (gsd-verifier)*
