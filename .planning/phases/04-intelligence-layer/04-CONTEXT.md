# Phase 4: Intelligence Layer - Context

**Gathered:** 2026-05-11
**Status:** Ready for planning

<domain>
## Phase Boundary

Build `src/intelligence_layer.py` — a new orchestrator that reads Financial Engine outputs from `ingestion.db` (`financial_ltm`, `financial_multiples`, `financial_dcf`, `financial_signals`), calls Claude via `instructor` with a Pydantic-enforced thesis schema, applies hash-gating to control API calls, stores versioned thesis history in `ingestion.db`, and computes opportunity signals (price-vs-DCF, momentum, IPE event) with conviction scores.

The phase does NOT change how data is ingested or computed — it purely consumes what Phase 3 produced and generates structured intelligence on top of it.

</domain>

<decisions>
## Implementation Decisions

### Thesis Pydantic Schema
- **D-01:** **Structured sub-objects for drivers and risks — NOT flat strings.** `class Driver(BaseModel): title: str, description: str, impact: Literal['HIGH','MEDIUM','LOW']` and `class Risk(BaseModel): title: str, description: str, severity: Literal['HIGH','MEDIUM','LOW']`. Rationale: Phase 5 renders each field separately (title as heading, description as body, impact as badge).
- **D-02:** **`InvestmentThesis` schema fields (locked):**
  - `bull_case: str` — optimist investment narrative
  - `bear_case: str` — pessimist / risk narrative
  - `drivers: list[Driver]` — 3–5 entries, each with title + description + impact
  - `risks: list[Risk]` — 3–5 entries, each with title + description + severity
  - `fair_value_brl: float` — must be injected from DCF, not LLM-generated
  - `methodology_disclosure: str` — which model was used (DCF/DDM) and key inputs
  - `positioning: Literal['COMPRAR', 'MANTER', 'VENDER']`
  - `confidence: Literal['ALTA', 'MEDIA', 'BAIXA']`
  - `rationale: str` — 2–3 sentences explaining the positioning decision
  - `summary_one_line: str` — one sentence for Telegram alerts (Phase 5 uses this directly)
- **D-03:** **`fair_value_brl` in thesis is injected, never LLM-synthesized.** The prompt injects DCF `fair_value_brl` from `financial_dcf` and instructs Claude to echo it exactly. Post-generation cross-check: if `thesis.fair_value_brl` deviates from `financial_dcf.fair_value_brl` by >10%, flag the thesis and log WARNING. The thesis is still stored but marked with `dcf_deviation_flag = True`.

### instructor Wiring
- **D-04:** **New `IntelligenceClient` class inside `src/intelligence_layer.py` — `LLMClient` stays unchanged.** `IntelligenceClient` wraps `instructor.from_anthropic(anthropic.Anthropic(...))` with its own retry logic. `LLMClient` continues to serve `morning_call.py`, `post_generator.py`, `thesis_builder.py` (legacy). No shared state between the two clients.
- **D-05:** **Hard-fail on instructor validation failure.** If `instructor` cannot parse a valid `InvestmentThesis` after `max_retries` attempts, raise `IngestionError`. No partial or empty thesis is ever written to storage. Consistent with: ROADMAP §Phase 4 SC-1 "generation never silently returns a partial or empty thesis".
- **D-06:** **`instructor.from_anthropic()` with `mode=instructor.Mode.ANTHROPIC_TOOLS`** — standard tool-use mode for Anthropic. Do NOT use `instructor.Mode.JSON` (requires manual JSON extraction and loses validation retry loop).

### Prompt Template
- **D-07:** **Jinja2 template in `src/templates/thesis_prompt.j2`** (checked into the Python `src/` tree). Not in vault `11_PROMPTS/`. Rationale: computation-critical prompt must be version-controlled alongside the code it drives; no vault path dependency.
- **D-08:** **Full snapshot injection.** The rendered prompt injects ALL of the following:
  - LTM financials: net_revenue, ebitda, net_income, fcf, net_debt (from `financial_ltm`)
  - Multiples: P/E, EV/EBITDA, P/BV, dividend_yield (from `financial_multiples`)
  - DCF: fair_value_brl, upside_pct, wacc, terminal_growth, confidence_flag (from `financial_dcf`)
  - Macro: Selic, IPCA_12m, CDS_brasil (latest from `macro_series`)
  - Technical signals: RSI, MACD trend, momentum_score (from `financial_signals`)
  - Last 3 news headlines: article title + published_at (from `news_articles` for the ticker)
  - Ticker metadata: sector, is_bank_model (from `config/tickers.yaml` + `config/sectors.yaml`)
  - Explicit instruction: "O `fair_value_brl` na tese DEVE ser exatamente R$ {dcf_fair_value:.2f} — não crie nem altere este valor."

### Hash-Based Gate & Cost Controls
- **D-09:** **Input hash = SHA-256 of (fair_value_brl + upside_pct + top-5 multiples + selic + cds + momentum_score + top-3 news URLs).** This matches ROADMAP §Phase 4 SC-3: "DCF result + top multiples + macro snapshot + top 3 headlines + signals". Serialized as a stable JSON string before hashing to avoid float precision drift.
- **D-10:** **Hash stored in `thesis_versions` table (see D-11). Gate logic: query `MAX(generated_at)` for ticker where `input_hash = current_hash` — if found, skip generation.**
- **D-11:** **2-per-day cap enforced per ticker.** Count rows in `thesis_versions` where `ticker = X AND DATE(generated_at) = today`. If >= 2, skip and log INFO "cap diário atingido para {ticker}".

### Thesis Versioning
- **D-12:** **`thesis_versions` table schema:**
  ```sql
  CREATE TABLE IF NOT EXISTS thesis_versions (
      id TEXT PRIMARY KEY,
      ticker TEXT NOT NULL,
      version_num INTEGER NOT NULL,
      generated_at TEXT NOT NULL,
      input_hash TEXT NOT NULL,
      positioning TEXT NOT NULL,
      confidence TEXT NOT NULL,
      fair_value_brl REAL NOT NULL,
      dcf_deviation_flag INTEGER DEFAULT 0,
      thesis_json TEXT NOT NULL,  -- full InvestmentThesis as JSON
      diff_summary TEXT,          -- human-readable diff vs previous version
      UNIQUE(ticker, version_num)
  )
  ```
- **D-13:** **`version_num` is auto-incremented per ticker** — query `MAX(version_num)` for ticker and add 1. `diff_summary` = field-by-field diff of current vs previous thesis JSON (positioning, fair_value_brl, bull_case summary, bear_case summary, count of drivers/risks).
- **D-14:** **`thesis_latest` view (not a second table)** — `CREATE VIEW thesis_latest AS SELECT * FROM thesis_versions WHERE (ticker, version_num) IN (SELECT ticker, MAX(version_num) FROM thesis_versions GROUP BY ticker)`. Phase 5 reads from `thesis_latest`.

### Opportunity Signals
- **D-15:** **Signals live in `intelligence_layer.py`** — `compute_opportunity_signals(ticker) -> list[OpportunitySignal]` called after thesis generation in `run_ticker()`. Both read the same `financial_*` tables. Single scheduler job covers both thesis + signals.
- **D-16:** **`OpportunitySignal` schema:**
  ```python
  class OpportunitySignal(BaseModel):
      ticker: str
      signal_type: Literal['DCF_DIVERGENCE', 'MOMENTUM_CROSSOVER', 'IPE_EVENT']
      description: str  # one sentence explanation
      conviction_score: int  # 0-100
      generated_at: str
  ```
- **D-17:** **Conviction score = weighted sum:**
  - `DCF_DIVERGENCE`: price vs DCF divergence >20% → up to 40pts (proportional to divergence magnitude, capped at 40)
  - `MOMENTUM_CROSSOVER`: MA crossover (golden/death) + momentum_score >=60 or <=40 → up to 30pts
  - `IPE_EVENT`: any IPE event in last 30 calendar days → 30pts (binary, date-filtered from `cvm_statements` where `event_type = 'IPE'`)
  - Signals only emitted if conviction_score >= 40
- **D-18:** **Top-3 signals stored in `opportunity_signals` table**, keyed by `(ticker, computed_date)` with `INSERT OR REPLACE`. Same date-partitioning pattern as `financial_*` tables.

### Scheduler Integration
- **D-19:** **`job_intelligence()` added to `scheduler.py`** with `bind_run_id("intelligence")` at top. Cron: `0 21 * * 1-5` (21:00 Mon–Fri — after `job_financial_engine()` at 20:00). Calls `run_all()` which iterates watchlist tickers.
- **D-20:** **Public API: `run_ticker(ticker: str) -> ThesisResult` + `run_all() -> list[ThesisResult]`** where `ThesisResult` wraps `InvestmentThesis + OpportunitySignal list + metadata (skipped, reason)`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Roadmap
- `.planning/REQUIREMENTS.md` §INT-01 through INT-06 — acceptance criteria for this phase
- `.planning/ROADMAP.md` §Phase 4 — goal, 5 planned deliverables, success criteria
- `.planning/PROJECT.md` — constraints (Python-only, reuse existing logic, SQLite→Supabase-compatible, no overengineering)

### Prior Phase Context (decisions that carry forward)
- `.planning/phases/01-foundation-and-cleanup/01-CONTEXT.md` — retry infrastructure, `bind_run_id`, `IngestionError` patterns
- `.planning/phases/02-reliable-data-ingestion/02-CONTEXT.md` — ingestion.db schema rules (TEXT UUID PK, no AUTOINCREMENT, INSERT OR REPLACE, ISO date strings)
- `.planning/phases/03-financial-engine/03-CONTEXT.md` — D-03 (run_ticker + job pattern), D-04 (INSERT OR REPLACE keyed by ticker+date), D-12 (public API shape), financial_* table schemas

### Intelligence & LLM
- `Analista de Investimentos/12_PYTHON/src/content/llm_client.py` — existing LLMClient (DO NOT modify — IntelligenceClient is separate)
- `Analista de Investimentos/12_PYTHON/src/content/thesis_builder.py` — **legacy** thesis builder (markdown output to vault, not structured). Reference only for understanding existing prompt patterns. Phase 4 replaces this for the new structured flow.
- `Analista de Investimentos/12_PYTHON/src/analysis/insight_engine.py` — rule-based insights (Phase 4 enriches these with LLM but does not replace the existing rules engine)

### Financial Engine Outputs (Phase 4 reads these)
- `Analista de Investimentos/12_PYTHON/src/financial_engine.py` — `run_ticker()` public API, `FinancialResult` dataclass
- `Analista de Investimentos/12_PYTHON/src/ingestion/db.py` — `init_db()`, `get_connection()`, `DB_PATH` — Phase 4 extends with `thesis_versions`, `opportunity_signals`, `thesis_latest` view
- `Analista de Investimentos/12_PYTHON/data/ingestion.db` — live database; Phase 4 reads `financial_ltm`, `financial_multiples`, `financial_dcf`, `financial_signals`, `macro_series`, `news_articles`

### Configuration
- `Analista de Investimentos/12_PYTHON/config/tickers.yaml` — watchlist tickers + sector metadata
- `Analista de Investimentos/12_PYTHON/config/sectors.yaml` — sector assumptions (bank vs industrial routing)
- `Analista de Investimentos/12_PYTHON/config/schedules.yaml` — add `intelligence` cron entry (21:00 Mon–Fri)
- `Analista de Investimentos/12_PYTHON/pyproject.toml` — `instructor` package NOT yet listed; must be added

### Utilities
- `Analista de Investimentos/12_PYTHON/src/utils/retry.py` — `@retry` decorator for Anthropic API calls
- `Analista de Investimentos/12_PYTHON/src/utils/logger.py` — `bind_run_id("intelligence")`, `get_logger()`
- `Analista de Investimentos/12_PYTHON/src/utils/errors.py` — `IngestionError` (raised on instructor validation failure)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `llm_client.py` — `LLMClient` with prompt caching, retry, model selection. Phase 4 creates a parallel `IntelligenceClient` that wraps `instructor.from_anthropic()`. The retry pattern (exponential backoff, 429/529 handling) should be replicated in `IntelligenceClient`.
- `financial_engine.py` — `run_ticker(ticker)` returns `FinancialResult` with all computed outputs. Phase 4 calls this or reads from `financial_*` tables directly (reading from DB preferred to avoid triggering re-computation).
- `sector_config.py` — `SectorConfig.for_ticker(ticker)` returns `is_bank_model`, `sector_type`. Phase 4 uses this to customize the thesis prompt (bank vs industrial framing).
- `db.py` — `get_connection()` context manager, `_CREATE_SQL` DDL pattern. Phase 4 adds `thesis_versions`, `opportunity_signals` tables and `thesis_latest` view following the same pattern.

### Established Patterns
- Job functions: `job_<name>()` in `scheduler.py` with `bind_run_id("intelligence")` at top, D-15 summary log at end
- DB schema: `TEXT PRIMARY KEY` UUIDs (`str(uuid.uuid4())`), ISO date strings, no AUTOINCREMENT, `INSERT OR REPLACE`/`INSERT OR IGNORE`
- Public API: `run_ticker(ticker: str) -> Result` + `run_all() -> list[Result]` (matches Phase 3's `financial_engine.py`)
- Lazy imports inside job functions (pattern from Phase 3 Plan 03-05)
- All SQL parameterized — never f-string with ticker (T-DCF-02 anti-pattern applies to intelligence layer too)

### Integration Points
- `src/intelligence_layer.py` reads from: `financial_ltm`, `financial_multiples`, `financial_dcf`, `financial_signals`, `macro_series`, `news_articles`
- `src/intelligence_layer.py` writes to: `thesis_versions` (versioned thesis history), `opportunity_signals` (top-3 signals per ticker per day), reads via `thesis_latest` view
- `src/scheduler.py`: add `job_intelligence()` to `_JOB_REGISTRY`, add cron entry to `schedules.yaml`
- `pyproject.toml`: add `instructor>=1.0.0` to dependencies (verify latest stable version during research)

### Key Warning: instructor Not Yet Installed
`instructor` is not in `pyproject.toml` dependencies. The researcher must verify the current stable version and confirm it is compatible with `anthropic>=0.39.0` before the planner locks the dependency.

</code_context>

<specifics>
## Specific Ideas

- **`IntelligenceClient` sketch:**
  ```python
  import instructor
  import anthropic

  class IntelligenceClient:
      def __init__(self):
          from config.settings import settings
          self._raw = anthropic.Anthropic(api_key=settings.anthropic_api_key)
          self._client = instructor.from_anthropic(self._raw, mode=instructor.Mode.ANTHROPIC_TOOLS)

      def generate_thesis(self, ticker: str, prompt: str, system: str) -> InvestmentThesis:
          return self._client.messages.create(
              model="claude-sonnet-4-6",
              max_tokens=4096,
              system=system,
              messages=[{"role": "user", "content": prompt}],
              response_model=InvestmentThesis,
          )
  ```
- **Hash computation:** `hashlib.sha256(json.dumps(hash_dict, sort_keys=True, ensure_ascii=False).encode()).hexdigest()` where `hash_dict` contains float values rounded to 2 decimal places to avoid float precision noise.
- **`thesis_versions` diff_summary:** compare `old.positioning != new.positioning`, `abs(old.fair_value_brl - new.fair_value_brl) / old.fair_value_brl`, `old.bull_case[:100] != new.bull_case[:100]`. Store as human-readable string: e.g., "Positioning: MANTER→COMPRAR; Fair value: R$42.50→R$48.30 (+13.6%)"
- **`opportunity_signals` table schema:**
  ```sql
  CREATE TABLE IF NOT EXISTS opportunity_signals (
      id TEXT PRIMARY KEY,
      ticker TEXT NOT NULL,
      computed_date TEXT NOT NULL,
      signal_type TEXT NOT NULL,
      description TEXT NOT NULL,
      conviction_score INTEGER NOT NULL,
      ingested_at TEXT NOT NULL,
      UNIQUE(ticker, computed_date, signal_type)
  )
  ```
- **Jinja2 template location:** `Analista de Investimentos/12_PYTHON/src/templates/thesis_prompt.j2` — create `src/templates/` directory as part of Plan 04-01.

</specifics>

<deferred>
## Deferred Ideas

- **Multi-scenario thesis (bull/base/bear DCF comparison in thesis)** — `thesis_builder.py` legacy has this via `build_dcf_scenarios()`. Phase 4 uses base scenario only. Multi-scenario thesis is v2.
- **Peer comparison section in thesis** — cross-sector multiples comparison. v2 requirement.
- **LLM-enriched insights** — `insight_engine.py` was designed with "Fase 4" enrichment in mind. Phase 4 focuses on the structured thesis; insight enrichment is a natural follow-on but out of this phase's scope.
- **Thesis quality scoring / feedback loop** — auto-rating thesis quality over time. Future phase.

</deferred>



---

*Phase: 4-Intelligence Layer*
*Context gathered: 2026-05-11*

## Avaliação rápida do contexto (resumido)

Ponto forte: plano bem estruturado, com decisões claras (schema Pydantic, hash-gate, versionamento, regras de sinal) e integração definida com DB e scheduler — dá boa rastreabilidade e auditabilidade.

## Pontos de atenção / riscos
- Consistência de floats e serialização (D-09): diferenças de rounding podem gerar hashes diferentes; exigir normalização explícita (2 casas, salvar como string no hash).
- Dependência instructor/anthropic ainda não no pyproject (Canonical refs): bloqueador para CI/CD; validar versão compatível antes de merge.
- Falha dura em validação (D-05): correto, mas exigir plano de observabilidade (logs + métricas) para evitar perda de cobertura ao falhar em massa.
- Rate-limits & custos (D-04/D-09): revisão de retry/backoff e quota por ticker + global budget.
- DCF injection (D-03): cuidado com formatos monetários/locale na prompt (ex.: R$ 1.234,56 vs 1234.56) — normalize para en-US numeric string no payload.

## Recomendações práticas (priorizadas)
1. Implementar utilitário compartilhado: normalize_for_hash(obj, float_decimals=2) — aplicar antes de SHA256 (evita flakiness).
2. Adicionar testes unitários:
  - geração de hash idempotente com diferentes float precisions;
  - fluxo happy/fail do IntelligenceClient com mock `instructor` (incluindo validação fail → IngestionError).
3. Criar migration SQL + teste de integração para `thesis_versions` e `opportunity_signals`.
4. Cobrir edge-cases de DCF deviation: workflow para >10% (marcar flag, enviar alerta por log/telemetry).
5. Instrumentação mínima: contador de chamadas LLM por ticker, tempo médio, % de validação-failures, custo estimado (localmente calculado por token).
6. Prompt testing: colar exemplos de payload DCF+multiples+news num conjunto de fixtures e registrar respostas esperadas (incluindo caso que ignora fair_value_brl).

## Checklist de aceitação sugerido
- [ ] Prompt template em src/templates/thesis_prompt.j2 com placeholders validados.
- [ ] IntelligenceClient implementado com retry e testes de mock.
- [ ] Hash-gating funcional: mesma hash → skip; diferente → gerar; cap diário aplicado.
- [ ] Thesis armazenada em thesis_versions com version_num auto-incrementado por ticker e diff_summary calculado.
- [ ] Computação de opportunity_signals executa e grava top-3 por dia.
- [ ] job_intelligence adicionado ao scheduler e cron testado localmente.
- [ ] pyproject atualizado e build CI passando (inclui instructor).

## Pequenas sugestões de melhoria textual no prompt
- Forçar formato numérico: "fair_value_brl: 1234.56 (usar ponto como separador decimal)"
- Incluir instrução clara de idiomas: "Responda em Português. Campos estruturados apenas em JSON compatível com o esquema Pydantic."
- Pedir explicitamente: "Não adicione campos extras; responda apenas o objeto InvestmentThesis."

## Próximos passos imediatos
- Escolher versão do pacote `instructor` compatível e atualizar pyproject.
- Implementar utilitário de normalização + testes de hash.
- Criar fixtures de prompt/resposta para testes de integração with mocked instructor.

Conclusão: estrutura sólida e bem pensada. Focar em determinismo (hash/serialização), observabilidade (falhas de validação) e controls de custo antes do rollout.