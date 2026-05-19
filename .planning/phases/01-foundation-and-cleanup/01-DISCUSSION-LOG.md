# Phase 1: Foundation & Cleanup - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-06
**Phase:** 1-Foundation & Cleanup
**Areas discussed:** pipeline banco completo/ fate, Logging framework, news_hunter/ credentials scope, Custom retry vs tenacity

---

## pipeline banco completo/ Fate

| Option | Description | Selected |
|--------|-------------|----------|
| Archive entirely | Move to `_ARQUIVO_*/` alongside the other archived copies. Rebuild Streamlit + Excel in Phase 5. | |
| Freeze but keep in place | Add deprecation notice, stop new development. Keep it runnable. | ✓ |
| Migrate Streamlit app first | Extract Streamlit dashboard into src/ before archiving. Expands Phase 1 scope significantly. | |

**User's choice:** Freeze but keep in place

**Q: Still running in production?**
| Option | Selected |
|--------|----------|
| Yes, still running — generates Excel valuation outputs | ✓ |
| No, effectively abandoned | |

**Q: Fix stale Windows Task Scheduler entry?**
| Option | Selected |
|--------|----------|
| Yes — add to Plan 1 scope | ✓ |
| No — out of scope | |

**Q: Migrate pipeline banco completo/ credentials to .env?**
| Option | Selected |
|--------|----------|
| Yes — migrate along with src/ and news_hunter/ | ✓ |
| src/ and news_hunter/ only | |

**Notes:** The pipeline is actively generating Excel outputs. Credentials migration is in scope but no other logic changes. Windows Task Scheduler fix is specifically to update the path from `C:\Users\55819\Downloads\...` to the vault path.

---

## Logging Framework

| Option | Description | Selected |
|--------|-------------|----------|
| Replace loguru with structlog | Aligns with roadmap spec. Requires migrating all get_logger() calls. | |
| Keep loguru, add run ID injection | loguru already works. Add contextvars-based run ID. Less migration work. | ✓ |
| You decide | Claude picks based on project constraints. | |

**User's choice:** Keep loguru, add run ID injection

**Q: How should run ID be injected?**
| Option | Selected |
|--------|----------|
| contextvars + loguru.contextualize() | ✓ |
| Pass run_id as parameter through signatures | |

**Q: Log retention policy?**
| Option | Selected |
|--------|----------|
| 7-day retention | ✓ |
| 30-day retention | |
| Keep all logs | |

**Q: Migrate pipeline banco completo/ to loguru?**
| Option | Selected |
|--------|----------|
| Keep stdlib logging (frozen — don't touch) | ✓ |
| Migrate pipeline banco completo/ too | |

**Notes:** The roadmap's "structlog" language is treated as a requirement for structured/machine-parseable logs with context binding — loguru satisfies this without a library swap.

---

## news_hunter/ Credentials Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Fix credentials only (config.py) | Patch config.py, leave news_hunter/ standalone. Phase 2 handles integration. | |
| Fix credentials + wire into src/ scheduler | Remove token and integrate into src/scheduler.py job_news_fetcher. Expands scope. | |
| Fix credentials + unify into single .env | Remove hardcoded token; all sub-systems read same .env. No scheduler integration yet. | ✓ |

**User's choice:** Fix credentials + unify into single .env

**Q: Scope — only config.py or all files?**
| Option | Selected |
|--------|----------|
| Only fix config.py | |
| Audit all news_hunter/ files for hardcoded values | ✓ |

**Q: Startup guard for news_hunter/?**
| Option | Selected |
|--------|----------|
| Yes — guard news_hunter/main.py startup too | ✓ |
| No — src/ guard only | |

**Notes:** The live token at `news_hunter/config.py:60–61` is the known blocker but a full audit is warranted. Scheduler integration explicitly deferred to Phase 2.

---

## Custom Retry vs. tenacity

| Option | Description | Selected |
|--------|-------------|----------|
| Replace with tenacity | Standard production retry library. Requires updating all call sites. | |
| Extend the existing decorator | Add exponential backoff to src/utils/retry.py. Zero migration work. | ✓ |
| You decide | Claude picks based on complexity vs value. | |

**User's choice:** Extend the existing decorator

**Q: Retry behavior?**
| Option | Selected |
|--------|----------|
| 3 attempts, exponential backoff (2s/4s/8s), with jitter | ✓ |
| 5 attempts, fixed 2s delay | |
| Configurable per call site | |

**Q: After all retries exhausted?**
| Option | Selected |
|--------|----------|
| Raise IngestionError with structured log entry | ✓ |
| Silent fallback to last cached value | |

**Q: Apply to pipeline banco completo/ too?**
| Option | Selected |
|--------|----------|
| src/ only (frozen — don't touch legacy pipeline) | ✓ |
| Both src/ and pipeline banco completo/ | |

**Notes:** tenacity migration deferred as tech debt. The Phase 1 requirement is exponential backoff + structured error surfacing, which the extended decorator can satisfy.

---

## Claude's Discretion

None — user made explicit choices on all questions.

## Deferred Ideas

- **news_hunter/ scheduler integration** → Phase 2 (Reliable Data Ingestion)
- **tenacity migration** → future tech debt cleanup
- **structlog formal adoption** → future if loguru + contextvars proves insufficient
- **pipeline banco completo/ full archival** → after Phase 5 Streamlit + PDF replaces it
