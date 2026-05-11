---
phase: 02
slug: reliable-data-ingestion
status: verified
threats_open: 0
asvs_level: 1
created: 2026-05-11
---

# Phase 2 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| CVM portal → cvm_downloader.py | Untrusted ZIP from dados.cvm.gov.br; CSV parsed after download | Financial statement rows (public data) |
| CVM IPE PDF URL → pdfplumber | External PDF from rad.cvm.gov.br; read-only extraction | Corporate event text (public data) |
| ticker / account_code → sqlite3 | Internal strings from parsed CSVs; tickers from tickers.yaml | Account codes, ticker symbols |
| BCB SGS API → bcb.py | External JSON response from api.bcb.gov.br; numeric values validated before insert | Macro series values (Selic, IPCA, PTAX, CDS, PIB) |
| yfinance → b3_scraper.py | External DataFrame; column names and types may vary; MultiIndex normalized | OHLCV price data |
| news_hunter/banco.db → news_sync.py | Read-only cross-DB access; banco.db written by separate news_hunter subprocess | News article URLs, titles, categories |
| banco.db noticias.link → news_articles.url | Untrusted URL string from news crawler; sanitized by str().strip() | Article URLs (public) |
| scheduler.py → subprocess (news_hunter) | Spawns news_hunter/main.py as external process; list-form args | CLI arguments only |
| schedules.yaml → IntelligenceScheduler | YAML-loaded job names dispatched via _JOB_REGISTRY lookup | Job name strings |
| job functions → ingestion.db | All DB writes via parameterized queries from Plans 01–03; scheduler has no direct SQL | Ingested data rows |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-02-01 | Tampering | cvm_downloader.py sqlite3 execute | mitigate | All INSERT calls use `?` parameterized placeholders — no f-string SQL anywhere; grep gate confirms 0 matches | closed |
| T-02-02 | Tampering | IPE CSV Codigo_CVM field | mitigate | `.astype(str).str.strip().str.zfill(6)` applied before comparison; malformed values normalized | closed |
| T-02-03 | Denial of Service | pdfplumber.open() on large PDFs | mitigate | Cap at `pdf.pages[:10]`; wrapped in broad except → returns "" without blocking ingestion | closed |
| T-02-04 | Information Disclosure | CVM ZIP cached locally | accept | Local-only tool; no multi-user access; ZIP cache avoids redundant downloads | closed |
| T-02-05 | Tampering | VL_CONTA numeric parsing | mitigate | `float(str(...).replace(",", "."))` in try/except; on failure value=None — corrupted numerics never inserted | closed |
| T-02-06 | Tampering | bcb.py INSERT macro_series | mitigate | All execute() calls use `?` parameterized placeholders; grep gate confirmed 0 f-string SQL matches | closed |
| T-02-07 | Tampering | BCB API valor field | mitigate | `float(str(item["valor"]).replace(",", "."))` in try/except; invalid values logged at WARNING and skipped | closed |
| T-02-08 | Tampering | b3_scraper.py INSERT price_ohlcv | mitigate | All execute() calls use `?` parameterized placeholders; grep gate confirmed 0 f-string SQL matches | closed |
| T-02-09 | Denial of Service | BCB SGS API rate limit | mitigate | `_INTER_SERIES_SLEEP = 0.5s` between series calls; @retry(attempts=3, backoff=2.0) handles 429 responses | closed |
| T-02-10 | Denial of Service | yfinance download timeout | mitigate | @retry(attempts=3, delay=3.0, backoff=2.0) on _download(); raises IngestionError on exhaustion | closed |
| T-02-11 | Information Disclosure | pandas_market_calendars failure in is_stale() | accept | All exceptions caught; returns False (safe default — no false stale alarms); logged at WARNING | closed |
| T-02-12 | Tampering | news_sync.py INSERT news_articles | mitigate | All execute() calls use `?` parameterized placeholders; grep gate confirmed 0 f-string SQL matches | closed |
| T-02-13 | Tampering | banco.db accidental write | mitigate | Source connection (`src`) has zero INSERT/UPDATE/DELETE calls; read-only by design; grep gate enforced | closed |
| T-02-14 | Denial of Service | banco.db grows unbounded | accept | `limit=500` default caps rows read per sync call; configurable by caller | closed |
| T-02-15 | Information Disclosure | banco.db path computed from __file__ | accept | Local-only tool; path derived from project root; no credentials exposed | closed |
| T-02-16 | Spoofing | Ticker tag injection via noticias.categoria | mitigate | `_B3_TICKER_RE = re.compile(r"^[A-Z]{4}[0-9]{1,2}$")` — only exact B3 ticker format accepted; arbitrary strings stored as NULL | closed |
| T-02-17 | Elevation of Privilege | job_news_ingest subprocess launch | mitigate | `subprocess.run([sys.executable, "main.py", "--coletar"], ...)` — list form prevents shell injection; never shell=True; cwd pinned to news_hunter/ | closed |
| T-02-18 | Denial of Service | news_hunter subprocess hangs | mitigate | `timeout=300` in subprocess.run; non-zero returncode logged as WARNING; sync step still executes | closed |
| T-02-19 | Tampering | schedules.yaml job name injection | accept | IntelligenceScheduler dispatches only to `_JOB_REGISTRY` keys — unknown YAML job names are silently ignored | closed |
| T-02-20 | Denial of Service | job_cvm_ingest loop per ticker × year | accept | Bounded by active_tickers (~80) × 2 years × 3 period types; RATE_LIMIT_SECONDS=1.5 in CVMDownloader; acceptable for daily batch | closed |
| T-02-21 | Information Disclosure | D-15 summary log includes failed tickers | accept | Logs written to local logs/ directory only — no network transmission; ticker names are not PII | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-02-01 | T-02-04 | CVM ZIP cached locally is a local-only, single-user v1 tool. ZIP cache eliminates redundant downloads without exposing data to other users. | Diego Carvalho | 2026-05-11 |
| AR-02-02 | T-02-11 | pandas_market_calendars exceptions in is_stale() return False (no stale alarm) rather than crashing ingestion. Safe default: a missed stale warning is lower risk than a failed ingestion job. | Diego Carvalho | 2026-05-11 |
| AR-02-03 | T-02-14 | banco.db row volume is bounded by news_hunter's own dedup (SHA-256 hash). limit=500 per sync is configurable and documented. Risk is bounded. | Diego Carvalho | 2026-05-11 |
| AR-02-04 | T-02-15 | banco.db path computed from `__file__` relative to project root. No credentials or secrets involved. Local-only deployment. | Diego Carvalho | 2026-05-11 |
| AR-02-05 | T-02-19 | IntelligenceScheduler enforces an allowlist via _JOB_REGISTRY. Unknown job names from schedules.yaml are ignored — no arbitrary code execution possible. | Diego Carvalho | 2026-05-11 |
| AR-02-06 | T-02-20 | Loop bounded by watchlist size (~80 tickers) × 2 years × 3 period types = ~480 iterations max. CVM rate limit (1.5s/call) makes this a ~12-min daily job — acceptable for batch ingestion. | Diego Carvalho | 2026-05-11 |
| AR-02-07 | T-02-21 | D-15 summary logs written to local logs/ directory. Ticker names (e.g. PETR4, VALE3) are public B3 symbols, not PII. No network egress of log data. | Diego Carvalho | 2026-05-11 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-11 | 21 | 21 | 0 | gsd-secure-phase (automated) |

### Audit Evidence

Evidence collected from PLAN.md threat models (Plans 01–04) and SUMMARY.md threat surface scans:

- **T-02-01, T-02-06, T-02-08, T-02-12**: SUMMARY files confirm grep gate passed (`grep -n "f\".*INSERT" src/ingestion/*.py` → 0 matches)
- **T-02-03**: SUMMARY-01 explicitly notes "extract_ipe_pdf_text() capped at 10 pages to mitigate T-02-03"
- **T-02-07**: SUMMARY-02 confirms "float(str(item["valor"]).replace(",", ".")) in try/except — invalid values logged and skipped"
- **T-02-09**: SUMMARY-02 confirms `_INTER_SERIES_SLEEP = 0.5` between BCB calls
- **T-02-13**: SUMMARY-03 confirms "Source connection has no INSERT/UPDATE/DELETE calls"
- **T-02-16**: SUMMARY-03 confirms "_B3_TICKER_RE exact-match regex rejects arbitrary categoria strings"
- **T-02-17**: SUMMARY-04 confirms "[sys.executable, 'main.py', '--coletar'], no shell=True"
- **T-02-18**: SUMMARY-04 confirms "timeout=300 in subprocess.run"
- **T-02-19**: SUMMARY-04 documents acceptance rationale

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-05-11
