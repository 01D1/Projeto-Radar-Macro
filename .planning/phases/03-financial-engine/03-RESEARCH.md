# Phase 3: Financial Engine - Research

**Researched:** 2026-05-11
**Domain:** Financial modeling, quantitative analysis, SQLite schema extension, pure-pandas signals
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Financial Engine writes to new tables in `ingestion.db` — `financial_ltm`, `financial_multiples`, `financial_dcf`, `financial_signals`. Single DB for all data.

**D-02:** One table per output type — structured like `macro_series` and `price_ohlcv`, directly queryable by Phase 4.

**D-03:** Both scheduled + on-demand API. `job_financial_engine()` in `scheduler.py` (triggered daily after ingestion jobs). `run_ticker(ticker)` callable on-demand from Phase 4.

**D-04:** INSERT OR REPLACE keyed by `(ticker, computed_date)`. One row per ticker per day.

**D-05:** Back-fill `normalized_name` in `cvm_statements` via `AccountMapper`. One-time UPDATE at Phase 3 startup.

**D-06:** Wire `AccountMapper` into `cvm_downloader.py` `parse_and_store()` permanently — future ingestion always populates `normalized_name` at write time.

**D-07:** ITR quarters are authoritative for LTM; DFP validates. LTM = rolling sum of trailing 4 ITR quarters. DFP annual used as cross-check: if LTM revenue diverges >5%, flag with `ltm_reconciliation_warning`.

**D-08:** Separate mappers by accounting standard. `AccountMapper` for IFRS (industrial). `BankAccountMapper` for COSIF (bank). `SectorConfig.is_bank_model` routes. Do NOT merge.

**D-09:** `risk_free` = Selic from `macro_series` (series_code=11); CDS Brazil = series_code=29039. Formula: `Ke = Selic + beta × ERP + CDS_Brazil`; `WACC = Ke × (1-D/V) + Kd × (1-t) × (D/V)`. Beta, ERP, tax_rate, debt_to_capital in `sectors.yaml`.

**D-10:** Stale macro fallback to `sectors.yaml` static values + log WARNING.

**D-11:** New `src/financial_engine.py` orchestrator; existing compute modules stay as pure-compute helpers (no changes to `valuation_dcf.py`, `calculate_metrics.py`, `sector_config.py`).

**D-12:** Public API: `run_ticker(ticker: str) -> FinancialResult` + `run_all() -> list[FinancialResult]`.

**D-13:** Technical signals computed in pandas from `price_ohlcv.adj_close`. No `ta-lib` (C compilation issues on Windows). No `pandas-ta` (not installed).

### Claude's Discretion

- None specified — all implementation decisions are locked.

### Deferred Ideas (OUT OF SCOPE)

- Scenario analysis (base/bull/bear) — Phase 3 stores base scenario only.
- Peer/sector relative valuation — v2.
- SQLAlchemy ORM layer — v2.
- FOCUS macro forecast integration — v2.
- Shares outstanding source resolution — researcher to verify during Phase 3 research (see Open Questions).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FIN-01 | LTM financials (revenue, EBITDA, net income, FCF, net debt) as rolling 4-quarter ITR sum, reconciled against DFP, runs automatically after ingestion | D-07 decision + query pattern from cvm_statements verified |
| FIN-02 | Standard multiples (P/E, EV/EBITDA, P/BV, dividend yield, EV/Revenue) updated daily with latest price + LTM | `calculate_industrial_metrics()` / `calculate_bank_metrics()` verified callable |
| FIN-03 | DCF fair value with WACC from Selic+CDS Brazil+ERP, 5-year FCF, terminal value, fair value in BRL and upside % | `run_dcf()` verified callable; macro_series columns confirmed |
| FIN-04 | DCF validates inputs before running (terminal_growth < WACC; WACC > 5%); flags out-of-range output as "FORA DO INTERVALO CONFIAVEL" | Confirmed `run_dcf()` has NO internal guard — `financial_engine.py` must add it |
| FIN-05 | Bank tickers routed to NIM-based / ROE / DDM model; industrial tickers receive EBITDA/FCFF DCF | `SectorConfig.is_bank_model`, `run_ddm()`, `calculate_bank_metrics()` all verified callable |
| FIN-06 | Technical signals: RSI-14, MACD (12/26/9), 50/200-day MA, crossover signal, composite score (0-100) | Pure-pandas implementation verified functional in test |
</phase_requirements>

---

## Summary

Phase 3 builds `src/financial_engine.py` — a new orchestrator that reads from `ingestion.db`, computes LTM financials, valuation multiples, DCF/DDM fair values, and technical signals, then writes results to four new `financial_*` tables. All heavy computation is delegated to existing pure-compute modules (`valuation_dcf.py`, `calculate_metrics.py`, `sector_config.py`) which are verified callable with no I/O dependencies.

The codebase is in excellent shape for this phase. All compute modules exist and are functional. The database schema is confirmed. The scheduler pattern is established. The primary new work is: (1) writing the orchestrator that connects DB reads to compute to DB writes, (2) implementing the LTM aggregation query logic against `cvm_statements`, (3) adding the `financial_*` table DDL to `db.py`, (4) the back-fill of `normalized_name` in `cvm_statements`, and (5) wiring `AccountMapper` into `cvm_downloader.py`.

One critical bug discovered during research: `sector_config.py` opens YAML files without specifying `encoding='utf-8'`, causing `UnicodeDecodeError` on Windows (cp1252 default cannot decode the em-dash and accented characters in `sectors.yaml` and `tickers.yaml`). This must be fixed in Plan 1 as a Wave 0 task before any `SectorConfig.for_ticker()` call succeeds on Windows.

**Primary recommendation:** Build the orchestrator in a single `src/financial_engine.py` that delegates to the existing compute modules. The five plans map cleanly to: (1) LTM + AccountMapper wire-up, (2) multiples computation, (3) DCF engine, (4) bank model, (5) signals + scheduler wiring.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LTM aggregation from CVM statements | API / Backend (`financial_engine.py`) | Database (ingestion.db query) | Pure computation from persisted ingestion data |
| EBITDA derivation (EBIT + D&A) | API / Backend (`financial_engine.py`) | — | No direct EBITDA account code in CVM; must derive |
| WACC derivation from macro_series | API / Backend (`financial_engine.py`) | Database (macro_series) | Live Selic/CDS from DB with static fallback |
| DCF fair value computation | API / Backend (`valuation_dcf.run_dcf()`) | — | Pure-compute, no I/O; called by orchestrator |
| DDM bank model | API / Backend (`valuation_dcf.run_ddm()`) | — | Pure-compute; sector routing via `SectorConfig` |
| Bank/industrial routing | API / Backend (`sector_config.py`) | Config (`sectors.yaml`, `tickers.yaml`) | `SectorConfig.for_ticker()` reads YAML at startup |
| Technical signals (RSI, MACD, MA) | API / Backend (`financial_engine.py`) | Database (price_ohlcv) | Pure pandas; reads adj_close from price_ohlcv |
| Input validation guards (FIN-04) | API / Backend (`financial_engine.py`) | — | Must gate BEFORE calling `run_dcf()` |
| normalized_name back-fill | Database (cvm_statements UPDATE) | API / Backend (AccountMapper) | One-time migration at Phase 3 startup |
| Scheduled execution | Scheduler (`scheduler.py job_financial_engine`) | — | Follows established job pattern from Phase 2 |

---

## Standard Stack

### Core (all already installed, verified)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.3.3 | LTM aggregation, signals computation, DataFrame operations | Already installed; confirmed functional |
| numpy | 2.2.6 | Numerical operations within pandas calculations | Already installed as pandas dependency |
| pydantic | 2.13.1 | `FinancialResult` dataclass validation | Already installed and used project-wide |
| loguru | 0.7.3 | Structured logging via `get_logger()` | Phase 1 standard — `bind_run_id("financial")` |
| sqlite3 | stdlib | DB reads/writes for all financial_* tables | Project-wide standard; no ORM in v1 |
| yaml (pyyaml) | installed | Load sectors.yaml / tickers.yaml | `SectorConfig` already depends on it |

### Existing Compute Modules (pure-compute, no changes)

| Module | Key Functions | Returns | Verified |
|--------|--------------|---------|---------|
| `src/valuation/valuation_dcf.py` | `run_dcf()`, `run_ddm()` | `DCFResult`, `DDMResult` dataclasses | Yes — called in test above |
| `src/valuation/calculate_metrics.py` | `calculate_industrial_metrics()`, `calculate_bank_metrics()` | `IndustrialMetrics`, `BankMetricsCalc` dataclasses | Yes — both called in test |
| `src/valuation/sector_config.py` | `SectorConfig.for_ticker()`, `is_bank_model`, `valuation_method`, `dcf_assumptions`, `gordon_assumptions` | `SectorConfig` instance | Imports verified; encoding bug documented |
| `src/normalization/account_mapper.py` | `AccountMapper.map_df()`, `AccountMapper.to_dict()` | `{normalized_name: value}` dict | Yes — verified with test DataFrame |
| `src/normalization/bank_account_mapper.py` | `BankAccountMapper.to_dict()` | `{normalized_name: value}` dict | Yes — verified with test DataFrame |

### No New Libraries Needed

The phase requires no new `pip install`. All computation uses:
- pandas (installed) for signals and LTM aggregation
- existing valuation modules for DCF/DDM
- stdlib sqlite3 for DB I/O
- loguru for logging
- pyyaml for config

`pandas-ta` and `ta-lib` are both absent and excluded (CONTEXT D-13). Pure pandas is sufficient and verified.

**Installation:** None required.

---

## Architecture Patterns

### System Architecture Diagram

```
ingestion.db
├── cvm_statements (ticker, period_type, year, reference_date, normalized_name, value)
├── macro_series   (series_code=11/29039, date, value)
└── price_ohlcv    (ticker, date, adj_close)
           │
           ▼
src/financial_engine.py  ──────────────────────────────────────────────────
           │                                                               │
    run_ticker(ticker)                                              run_all()
           │                                                               │
    [1] SectorConfig.for_ticker(ticker)                    iterates watchlist
    → is_bank_model, valuation_method, dcf_assumptions     calls run_ticker()
           │
    [2] LTM Aggregation
    → query cvm_statements WHERE period_type='ITR'
      ORDER BY reference_date DESC LIMIT 4 quarters
    → AccountMapper or BankAccountMapper.to_dict(df)
    → derive EBITDA = EBIT + D&A (no direct CVM code for EBITDA)
    → DFP cross-check: flag ltm_reconciliation_warning if |LTM-DFP| > 5%
    → write financial_ltm
           │
    [3] WACC Derivation
    → query macro_series WHERE series_code IN (11, 29039)
    → freshness check vs B3BusinessCalendar
    → fallback to sectors.yaml risk_free / country_risk if stale
           │
    [4a] Industrial path (not is_bank_model)
    → input validation: assert terminal_growth < wacc, wacc > 0.05
    → run_dcf(ticker, base_year, base_revenue, base_ebitda, DCFAssumptions, net_debt, shares)
    → confidence_flag = "FORA DO INTERVALO CONFIAVEL" if price_target outside [0.1x, 5.0x] price
    → calculate_industrial_metrics(...)
    → write financial_dcf, financial_multiples
           │
    [4b] Bank path (is_bank_model)
    → run_ddm(ticker, base_year, base_net_income, payout_ratio, coe, g, growth_rates)
    → calculate_bank_metrics(...)
    → write financial_dcf (DDM), financial_multiples (bank)
           │
    [5] Technical Signals
    → query price_ohlcv WHERE ticker AND is_gap=0
      ORDER BY date DESC LIMIT 250
    → pure pandas: RSI-14, MACD(12/26/9), MA50, MA200, crossover
    → composite score (0-100): RSI dir 30pt + MACD cross 30pt + MA200 trend 20pt + MA cross 20pt
    → write financial_signals
           │
           ▼
ingestion.db
├── financial_ltm       (ticker, computed_date, net_revenue, ebitda, net_income, fcf, net_debt, ...)
├── financial_multiples (ticker, computed_date, pe_ratio, ev_ebitda, pb_ratio, div_yield, ...)
├── financial_dcf       (ticker, computed_date, fair_value_brl, upside_pct, wacc, terminal_growth, ...)
└── financial_signals   (ticker, computed_date, rsi_14, macd_line, macd_signal, ma50, ma200, ...)
```

### Recommended Project Structure

```
src/
├── financial_engine.py          # NEW — orchestrator (this phase)
├── ingestion/
│   ├── db.py                   # MODIFIED — add financial_* table DDL
│   └── cvm_downloader.py       # MODIFIED — wire AccountMapper in parse_and_store()
├── valuation/
│   ├── valuation_dcf.py        # UNCHANGED — pure compute
│   ├── calculate_metrics.py    # UNCHANGED — pure compute
│   ├── sector_config.py        # BUG FIX — add encoding='utf-8' to open() calls
│   └── auto_dcf.py             # UNCHANGED — legacy, not in hot path
├── normalization/
│   ├── account_mapper.py       # UNCHANGED — AccountMapper.to_dict() called by orchestrator
│   └── bank_account_mapper.py  # UNCHANGED — BankAccountMapper.to_dict() called by orchestrator
├── scheduler.py                # MODIFIED — add job_financial_engine()
└── utils/
    ├── retry.py                # UNCHANGED
    └── logger.py               # UNCHANGED
config/
├── sectors.yaml                # UNCHANGED — WACC assumptions already per-sector
├── tickers.yaml                # UNCHANGED — bank routing already via type field
└── schedules.yaml              # MODIFIED — add financial_engine cron entry
tests/
├── test_financial_engine.py    # NEW — Wave 0 gap
├── test_financial_db_schema.py # NEW — Wave 0 gap
└── test_financial_signals.py   # NEW — Wave 0 gap
```

### Pattern 1: job_financial_engine() — Scheduler Job Pattern

```python
# Source: established Phase 2 pattern in scheduler.py (job_bcb_macro, job_b3_prices)
def job_financial_engine() -> str:
    from src.financial_engine import run_all
    from src.utils.logger import bind_run_id, get_logger as _get

    _log = _get(__name__)
    with bind_run_id("financial") as run_id:
        _log.info(f"[financial_engine] iniciado — run_id={run_id}")
        t0 = time.time()
        results = run_all()
        ok = sum(1 for r in results if r.success)
        fail = len(results) - ok
        duration_ms = int((time.time() - t0) * 1000)
        _log.info(
            "[financial_engine] summary",
            source="financial_engine",
            tickers_ok=ok,
            tickers_failed=fail,
            duration_ms=duration_ms,
            status="ok" if fail == 0 else "partial",
        )
        return f"financial_engine: ok={ok} failed={fail}"
```

### Pattern 2: LTM Aggregation SQL Query

```python
# Source: verified against cvm_statements schema in db.py
# Trailing 4 ITR quarters for a ticker
QUERY_LTM_ITR = """
    SELECT reference_date, normalized_name, value
    FROM cvm_statements
    WHERE ticker = ?
      AND period_type = 'ITR'
      AND normalized_name IS NOT NULL
      AND reference_date IN (
          SELECT DISTINCT reference_date
          FROM cvm_statements
          WHERE ticker = ? AND period_type = 'ITR'
          ORDER BY reference_date DESC
          LIMIT 4
      )
    ORDER BY reference_date DESC
"""

# DFP cross-check query (latest annual)
QUERY_DFP_ANNUAL = """
    SELECT normalized_name, value
    FROM cvm_statements
    WHERE ticker = ?
      AND period_type = 'DFP'
      AND normalized_name IS NOT NULL
      AND reference_date = (
          SELECT MAX(reference_date)
          FROM cvm_statements
          WHERE ticker = ? AND period_type = 'DFP'
      )
"""
```

### Pattern 3: WACC Derivation with Stale Fallback

```python
# Source: confirmed from macro_series schema, sectors.yaml structure, D-09/D-10 decisions
def compute_wacc(ticker: str, conn: sqlite3.Connection) -> tuple[float, float, float, bool]:
    """Returns (wacc, selic_used, cds_used, used_fallback)."""
    cfg = SectorConfig.for_ticker(ticker)
    a = cfg.dcf_assumptions  # or gordon_assumptions for banks

    # Query macro — series_code 11 = Selic, 29039 = CDS Brasil (stored in decimal, not bps)
    rows = conn.execute("""
        SELECT series_code, value, date FROM macro_series
        WHERE series_code IN (11, 29039)
        ORDER BY date DESC
    """).fetchall()

    macro = {r["series_code"]: (r["value"], r["date"]) for r in rows}
    selic_raw, selic_date = macro.get(11, (None, None))
    cds_raw, cds_date = macro.get(29039, (None, None))

    stale = _is_stale(selic_date) or _is_stale(cds_date)
    if stale or selic_raw is None or cds_raw is None:
        # Fallback to sectors.yaml static values (D-10)
        log.warning(f"[{ticker}] macro stale — usando fallback sectors.yaml")
        selic = a.get("risk_free", 0.10)
        cds = a.get("country_risk", 0.02)
        used_fallback = True
    else:
        selic = selic_raw        # already in decimal (e.g. 0.1065 for 10.65%)
        cds = cds_raw            # stored /10_000 at ingestion time (D: 02-02 decision)
        used_fallback = False

    beta = a.get("beta", 1.0)
    erp = a.get("erp", 0.055)
    kd = a.get("cost_of_debt", 0.115)
    tax = a.get("tax_rate", 0.27)
    dv = a.get("debt_to_capital", 0.25)

    ke = selic + beta * erp + cds
    wacc = ke * (1 - dv) + kd * (1 - tax) * dv
    return wacc, selic, cds, used_fallback
```

### Pattern 4: Input Validation Guards (FIN-04)

```python
# Source: FIN-04 requirement; confirmed run_dcf() has NO internal guard
def _validate_dcf_inputs(ticker: str, wacc: float, terminal_growth: float,
                          current_price: float, price_target: float) -> str | None:
    """Returns confidence_flag string or None if valid."""
    if wacc <= 0.05:
        log.error(f"[{ticker}] DCF inválido: WACC={wacc:.2%} <= 5%")
        return "INPUT_INVALIDO"
    if terminal_growth >= wacc:
        log.error(f"[{ticker}] DCF inválido: terminal_growth={terminal_growth:.2%} >= WACC={wacc:.2%}")
        return "INPUT_INVALIDO"
    if current_price and current_price > 0:
        ratio = price_target / current_price
        if ratio < 0.1 or ratio > 5.0:
            return "FORA DO INTERVALO CONFIAVEL"
    return None  # valid
```

### Pattern 5: Pure-Pandas Technical Signals

```python
# Source: verified via test execution above
def compute_signals(prices: pd.Series) -> dict:
    """
    prices: pd.Series indexed by date, values = adj_close (from price_ohlcv)
    Requires minimum ~250 rows for MA200 validity.
    """
    prices = prices.sort_index()  # ascending date order

    # RSI-14 (Wilder's smoothing = EWM com=13)
    delta = prices.diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=13, adjust=False).mean()
    rsi = 100 - (100 / (1 + gain / loss.replace(0, float('nan'))))

    # MACD (12, 26, 9)
    ema12 = prices.ewm(span=12, adjust=False).mean()
    ema26 = prices.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - macd_signal

    # Moving averages
    ma50 = prices.rolling(50).mean()
    ma200 = prices.rolling(200).mean()

    # Crossover detection (current vs previous)
    golden_cross = (ma50.iloc[-1] > ma200.iloc[-1]) and (ma50.iloc[-2] <= ma200.iloc[-2])
    death_cross = (ma50.iloc[-1] < ma200.iloc[-1]) and (ma50.iloc[-2] >= ma200.iloc[-2])

    # Composite momentum score (0-100)
    # RSI direction: above 50 = 30pts
    rsi_score = 30 if rsi.iloc[-1] > 50 else 0
    # MACD crossover: histogram > 0 = 30pts (bullish momentum)
    macd_score = 30 if macd_hist.iloc[-1] > 0 else 0
    # MA200 trend: price > MA200 = 20pts
    ma200_score = 20 if prices.iloc[-1] > ma200.iloc[-1] else 0
    # MA50/200 cross: golden=20, death=0, neutral=10
    cross_score = 20 if golden_cross else (0 if death_cross else 10)
    composite = rsi_score + macd_score + ma200_score + cross_score

    return {
        "rsi_14": round(rsi.iloc[-1], 2),
        "macd_line": round(macd_line.iloc[-1], 4),
        "macd_signal": round(macd_signal.iloc[-1], 4),
        "macd_histogram": round(macd_hist.iloc[-1], 4),
        "ma_50": round(ma50.iloc[-1], 2),
        "ma_200": round(ma200.iloc[-1], 2),
        "golden_cross": int(golden_cross),
        "death_cross": int(death_cross),
        "momentum_score": composite,
    }
```

### Pattern 6: Database Schema Extension (financial_* tables)

```sql
-- Source: mirrors existing table conventions in db.py (TEXT PK, ISO dates, no AUTOINCREMENT)
-- Add to _CREATE_SQL in db.py

CREATE TABLE IF NOT EXISTS financial_ltm (
    id                      TEXT PRIMARY KEY,
    ticker                  TEXT NOT NULL,
    computed_date           TEXT NOT NULL,
    net_revenue             REAL,
    ebitda                  REAL,
    net_income              REAL,
    fcf                     REAL,
    net_debt                REAL,
    gross_debt              REAL,
    cash                    REAL,
    shareholders_equity     REAL,
    shares_outstanding      REAL,
    ltm_reconciliation_warning INTEGER DEFAULT 0,
    ltm_warning_detail      TEXT,
    ingested_at             TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ltm_dedup ON financial_ltm(ticker, computed_date);

CREATE TABLE IF NOT EXISTS financial_multiples (
    id              TEXT PRIMARY KEY,
    ticker          TEXT NOT NULL,
    computed_date   TEXT NOT NULL,
    price           REAL,
    market_cap      REAL,
    pe_ratio        REAL,
    ev_ebitda       REAL,
    pb_ratio        REAL,
    dividend_yield  REAL,
    ev_revenue      REAL,
    ingested_at     TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_multiples_dedup ON financial_multiples(ticker, computed_date);

CREATE TABLE IF NOT EXISTS financial_dcf (
    id                  TEXT PRIMARY KEY,
    ticker              TEXT NOT NULL,
    computed_date       TEXT NOT NULL,
    valuation_method    TEXT,
    fair_value_brl      REAL,
    upside_pct          REAL,
    wacc                REAL,
    terminal_growth     REAL,
    selic_used          REAL,
    cds_used            REAL,
    used_fallback       INTEGER DEFAULT 0,
    confidence_flag     TEXT,
    ingested_at         TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dcf_dedup ON financial_dcf(ticker, computed_date);

CREATE TABLE IF NOT EXISTS financial_signals (
    id              TEXT PRIMARY KEY,
    ticker          TEXT NOT NULL,
    computed_date   TEXT NOT NULL,
    rsi_14          REAL,
    macd_line       REAL,
    macd_signal     REAL,
    macd_histogram  REAL,
    ma_50           REAL,
    ma_200          REAL,
    golden_cross    INTEGER,
    death_cross     INTEGER,
    momentum_score  INTEGER,
    ingested_at     TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_dedup ON financial_signals(ticker, computed_date);
```

### Anti-Patterns to Avoid

- **Calling run_dcf() without validation:** `run_dcf()` has no guard for terminal_growth >= WACC. Division by (wacc - g) will produce infinity or blow up. Always validate first.
- **Opening sectors.yaml / tickers.yaml without encoding='utf-8':** Both files contain UTF-8 characters (em-dashes, accented characters in comments). Windows defaults to cp1252 which cannot decode them. This is a confirmed bug in `sector_config.py` — fix it in Wave 0 before any `SectorConfig` call.
- **Using `from parsers.dfp_parser import ...` in account_mapper.py:** This import fails unless `src/` is on sys.path. The correct import in the context of `src/financial_engine.py` is `from src.parsers.dfp_parser import ACCOUNT_MAP`. Alternatively, call `account_mapper.py` via the full `src.normalization.account_mapper` path (which works when sys.path has the project root).
- **Storing EBITDA as a direct CVM account:** EBITDA has no direct account code in the CVM ACCOUNT_MAP (verified). EBITDA must be derived: `EBITDA = EBIT (3.05) + D&A (6.01.01.02)`. D&A comes from the DFC section — if DFC rows are missing for a ticker, EBITDA will be NULL.
- **Assuming macro_series is fresh:** The DB is populated by Phase 2 ingestion. The financial engine must check freshness before using Selic/CDS values and fall back gracefully (D-10).
- **Not filtering `is_gap=0` for signal computation:** `price_ohlcv` contains gap rows where `adj_close IS NULL` and `is_gap=1`. RSI/MACD calculations will produce NaN cascades if gap rows are included.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DCF FCFF computation | Custom DCF loop | `valuation_dcf.run_dcf()` | Already tested, handles edge cases, returns full DCFResult |
| DDM bank model | Custom dividend discount model | `valuation_dcf.run_ddm()` | Handles terminal value safely (checks coe > g) |
| Industrial metric ratios | Custom ratio calculations | `calculate_metrics.calculate_industrial_metrics()` | Handles all edge cases (zero divisions, None defaults) |
| Bank metric ratios | Custom bank ratio calculations | `calculate_metrics.calculate_bank_metrics()` | NIM, PDD/carteira, efficiency ratio all handled |
| Sector/ticker routing | Custom type dispatch | `SectorConfig.for_ticker()` | Already reads tickers.yaml + sectors.yaml with fallback |
| IFRS account normalization | Custom code lookup | `AccountMapper.to_dict(df)` | 3-strategy priority (exact, prefix, regex); battle-tested |
| COSIF bank account normalization | Custom code lookup | `BankAccountMapper.to_dict(df)` | Handles per-bank layout differences (Itau vs BB vs Bradesco) |
| Retry wrapper | Custom retry logic | `@retry(attempts=3, delay=2.0)` from `src/utils/retry.py` | Phase 1 standard with jitter and IngestionError propagation |
| Logging | Custom logging | `get_logger(__name__)` + `bind_run_id("financial")` | Phase 1 standard with run_id context |

**Key insight:** The compute layer is already built and tested. The Financial Engine's job is exclusively orchestration: read from DB → call compute → validate → write to DB.

---

## Critical Bugs and Gaps Found During Research

### BUG-01: sector_config.py opens YAML without encoding='utf-8' (CONFIRMED)

**File:** `src/valuation/sector_config.py` lines 38-39 and 43-44
**Impact:** `UnicodeDecodeError` on Windows when `_load_sectors()` or `_load_ticker_map()` is called
**Fix:** Change `with open(_SECTORS_PATH) as f:` to `with open(_SECTORS_PATH, encoding="utf-8") as f:` (two occurrences)
**Severity:** BLOCKING — no SectorConfig call will work on Windows without this fix

### GAP-01: EBITDA not in ACCOUNT_MAP — must derive (VERIFIED)

**What:** `ACCOUNT_MAP` in `dfp_parser.py` has no entry mapping to `ebitda`. Only `ebit` (code 3.05) and `depreciation_amortization_cfo` (code 6.01.01.02) exist.
**Impact:** LTM EBITDA = `ebit + depreciation_amortization_cfo`. If DFC section is absent for a ticker/period, EBITDA will be NULL and flagged.
**Fix needed in orchestrator:** `ebitda = financials.get("ebit", 0) + financials.get("depreciation_amortization_cfo", 0)`. Document that EBITDA = 0 when both are absent (not just D&A absent).

### GAP-02: account_mapper.py uses bare `from parsers.dfp_parser import ...` (VERIFIED)

**File:** `src/normalization/account_mapper.py` line 32
**Impact:** Import fails unless `src/` directory is explicitly on `sys.path`
**Fix:** The financial engine must ensure sys.path includes `src/` OR use `from src.parsers.dfp_parser import ACCOUNT_MAP` in a monkeypatched import within the orchestrator. Simpler: run the back-fill query via direct SQL UPDATE + Python loop without using AccountMapper's import chain directly — OR fix the import path.
**Recommended:** Fix `account_mapper.py` line 32 to `from src.parsers.dfp_parser import ACCOUNT_MAP as CODE_MAP` in Wave 0.

### GAP-03: Shares outstanding not populated in ingestion.db (UNRESOLVED — see Open Questions)

**What:** `financial_ltm` schema includes `shares_outstanding`. There is no current source for this in `ingestion.db`. `run_dcf()` needs `shares_outstanding` to compute `price_target`.
**Options:** (a) Read from `price_ohlcv` by computing market_cap / price (yfinance does return market_cap), (b) Read from CVM BP (`1.xx` section — total shares × par value), (c) Keep as NULL and skip `price_target` derivation, falling back to EV-based comparison.
**Impact on Phase 4:** Without price_target, upside_pct cannot be computed against current price. This is a significant gap.

### GAP-04: apscheduler not installed on this machine (MINOR)

**Confirmed:** `apscheduler: NOT INSTALLED` on the development machine
**Impact:** `start_scheduler()` will fail at runtime; tests that call `IntelligenceScheduler.build()` will fail
**Fix:** `pip install apscheduler>=3.10.0` (already in pyproject.toml dependencies)

---

## Common Pitfalls

### Pitfall 1: LTM Quarter Deduplication

**What goes wrong:** CVM ITR data can have multiple versions for the same quarter (different VERSAO column). The `cvm_statements` UNIQUE INDEX uses `(ticker, period_type, year, account_code, reference_date)` — so different reference dates within the same calendar year can produce more than 4 unique quarters if a restated report uses a different `reference_date`.

**Why it happens:** CVM allows companies to refile. Phase 2 uses INSERT OR IGNORE so the first ingested version wins.

**How to avoid:** When selecting trailing 4 ITR quarters, use `DISTINCT reference_date` ordered by `reference_date DESC LIMIT 4`. This selects the 4 most recent unique reference dates (e.g., 2024-09-30, 2024-06-30, 2024-03-31, 2023-12-31).

**Warning signs:** LTM revenue dramatically higher than DFP annual (>30% divergence) → likely counting 5+ quarters.

### Pitfall 2: Banks Have No EBITDA

**What goes wrong:** Code applying `ebitda` to bank tickers (BBAS3, ITUB4, etc.) produces NULL or wrong values because COSIF DRE has no EBIT, no EBITDA structure.

**Why it happens:** Bank DRE flows through intermediation revenues → NII → result before taxes. The IFRS-derived EBITDA concept doesn't apply.

**How to avoid:** `SectorConfig.is_bank_model` must gate ALL EBITDA-based calculations. For bank LTM: compute `nii_gross`, `net_income`, `fee_income` — not EBITDA. For bank multiples: use P/BV and P/E (not EV/EBITDA). The `financial_ltm` table stores EBITDA as NULL for banks.

**Warning signs:** EBITDA field populated for ITUB4, BBAS3, BBDC4 — this indicates routing failure.

### Pitfall 3: DFC Rows Often Missing for Quarterly (ITR)

**What goes wrong:** ITR submissions do not always include the DFC section. This means `cfo`, `capex`, and `depreciation_amortization_cfo` normalized_names will be absent for some quarters, making FCF computation impossible.

**Why it happens:** CVM mandates DFC for annual (DFP) but it's common for ITRs to omit it.

**How to avoid:** FCF = CFO - |capex|. If either is NULL for a quarter, mark `fcf = NULL` in `financial_ltm`. For EBITDA: if D&A from DFC is NULL, attempt to derive from DFP annual D&A annualized divided by 4 as a heuristic — or flag as NULL.

**Warning signs:** `fcf = 0` for all tickers across all quarters → likely treating NULLs as 0.

### Pitfall 4: CDS Brasil Stored as Decimal, Not Basis Points

**What goes wrong:** Using raw CDS value directly as percentage produces 100× error. E.g., CDS = 1.5% stored as 0.00015 (stored as raw/10_000 per Phase 2 decision `[02-02]`).

**Why it happens:** BCB SGS series 29039 provides CDS in basis points. Phase 2 converts: `raw / 10_000` at insert time. The stored value in `macro_series` is already in decimal format (e.g., 0.0155 for 155 bps CDS).

**How to avoid:** Use the stored value directly in WACC calculation: `cds = row["value"]` (it's already in decimal). Do NOT divide by 100 again.

**Warning signs:** WACC outputs > 50% or < 0% → likely CDS unit error.

### Pitfall 5: run_dcf() Produces Infinity/Division by Zero

**What goes wrong:** If `terminal_growth_rate >= wacc`, the Gordon Growth terminal value formula `fcff / (wacc - g)` divides by zero or produces negative terminal value.

**Why it happens:** `run_dcf()` has no guard (confirmed in research). If sectors.yaml `terminal_growth: 0.055` and computed WACC is, say, 0.04 (due to Selic at 6% and low CDS), the guard is violated.

**How to avoid:** In `financial_engine.py`, validate BEFORE calling `run_dcf()`: `assert terminal_growth < wacc`. If invalid, log ERROR, write NULL fair_value with `confidence_flag = "INPUT_INVALIDO"`. Skip `run_dcf()` entirely for that ticker.

**Warning signs:** `fair_value_brl = None` with `confidence_flag = "INPUT_INVALIDO"` in the output table is correct behavior. `fair_value_brl` with 12+ digits is not.

### Pitfall 6: sector_config.py Encoding Bug on Windows

**What goes wrong:** `SectorConfig.for_ticker()` raises `UnicodeDecodeError` on first call.

**Why it happens:** `_load_sectors()` and `_load_ticker_map()` open YAML files with the system default encoding (cp1252 on Windows). Both YAML files contain UTF-8 multi-byte characters.

**How to avoid:** Fix both `open()` calls in `sector_config.py` to use `encoding="utf-8"` in Wave 0 before any test or implementation code calls SectorConfig.

---

## Code Examples

### Example: Full LTM aggregation from cvm_statements

```python
# Source: cvm_statements schema from db.py (verified)
def _aggregate_ltm(ticker: str, conn: sqlite3.Connection,
                   is_bank: bool) -> dict[str, float]:
    """Aggregate trailing 4 ITR quarters into LTM dict."""
    # Step 1: Get the 4 most recent reference dates for ITR
    dates = conn.execute("""
        SELECT DISTINCT reference_date
        FROM cvm_statements
        WHERE ticker = ? AND period_type = 'ITR' AND normalized_name IS NOT NULL
        ORDER BY reference_date DESC
        LIMIT 4
    """, (ticker,)).fetchall()

    if len(dates) < 4:
        log.warning(f"[{ticker}] apenas {len(dates)} trimestres ITR disponíveis")

    ref_dates = tuple(r["reference_date"] for r in dates)

    # Step 2: Fetch all accounts for these quarters
    placeholders = ",".join("?" * len(ref_dates))
    rows = conn.execute(f"""
        SELECT reference_date, normalized_name, value
        FROM cvm_statements
        WHERE ticker = ? AND period_type = 'ITR'
          AND normalized_name IS NOT NULL
          AND reference_date IN ({placeholders})
    """, (ticker, *ref_dates)).fetchall()

    # Step 3: Sum flow items across 4 quarters; take latest snapshot for balance items
    FLOW_ITEMS = {"net_revenue", "ebit", "net_income", "cfo", "capex",
                  "depreciation_amortization_cfo", "dividends_paid",
                  # Bank flow items
                  "nii_gross", "loan_loss_provision", "fee_income",
                  "total_financial_revenues", "total_financial_expenses"}
    SNAPSHOT_ITEMS = {"cash", "short_term_debt", "long_term_debt",
                      "total_equity", "total_assets", "loan_portfolio_gross"}

    flow: dict[str, float] = {}
    snapshot: dict[str, dict] = {}

    for row in rows:
        name = row["normalized_name"]
        val = row["value"] or 0.0
        ref = row["reference_date"]
        if name in FLOW_ITEMS:
            flow[name] = flow.get(name, 0.0) + val
        elif name in SNAPSHOT_ITEMS:
            # Keep latest date's value
            if name not in snapshot or ref > snapshot[name]["date"]:
                snapshot[name] = {"date": ref, "value": val}

    result = dict(flow)
    for name, sv in snapshot.items():
        result[name] = sv["value"]

    # Derive EBITDA (no direct CVM code)
    result["ebitda"] = result.get("ebit", 0.0) + result.get("depreciation_amortization_cfo", 0.0)
    # Derive FCF
    result["fcf"] = result.get("cfo", 0.0) - abs(result.get("capex", 0.0))
    # Derive net_debt
    result["gross_debt"] = result.get("short_term_debt", 0.0) + result.get("long_term_debt", 0.0)
    result["net_debt"] = result["gross_debt"] - result.get("cash", 0.0)

    return result
```

### Example: INSERT OR REPLACE for financial_ltm

```python
# Source: db.py INSERT OR REPLACE pattern (D-04 decision)
import uuid
from datetime import datetime, timezone

def _write_ltm(conn: sqlite3.Connection, ticker: str, computed_date: str,
               ltm: dict, warning: int, warning_detail: str | None) -> None:
    conn.execute("""
        INSERT OR REPLACE INTO financial_ltm
        (id, ticker, computed_date, net_revenue, ebitda, net_income, fcf,
         net_debt, gross_debt, cash, shareholders_equity, shares_outstanding,
         ltm_reconciliation_warning, ltm_warning_detail, ingested_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(uuid.uuid4()), ticker, computed_date,
        ltm.get("net_revenue"), ltm.get("ebitda"), ltm.get("net_income"),
        ltm.get("fcf"), ltm.get("net_debt"), ltm.get("gross_debt"),
        ltm.get("cash"), ltm.get("total_equity"),
        ltm.get("shares_outstanding"),
        warning, warning_detail,
        datetime.now(timezone.utc).isoformat(),
    ))
    conn.commit()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Parquet file storage for prices | `price_ohlcv` table in ingestion.db | Phase 2 (2026-05-11) | Financial engine reads from DB, not files |
| Manual valuation in `auto_dcf.py` | Orchestrated via `financial_engine.py` | Phase 3 (this phase) | auto_dcf.py kept as legacy reference only |
| normalized_name=None at ingestion | AccountMapper called in parse_and_store | Phase 3 wire-up | Back-fill existing records + new records normalized at write |
| EBITDA from arbitrary text parsing | EBIT + D&A from normalized CVM codes | Phase 3 | More robust than pattern matching on raw DRE |

**Deprecated / Not in hot path:**
- `auto_dcf.py`: Legacy orchestrator. No longer called after Phase 3. Kept for reference (ScenarioResult, ValuationResult dataclasses may be referenced by Phase 5 PDF report).
- `job_analyze()` in scheduler.py: Still calls `auto_dcf.run_valuation()`. Phase 3 adds `job_financial_engine()` as the replacement. `job_analyze()` remains but is superseded for financial computation.

---

## Runtime State Inventory

> Phase 3 is not a rename/refactor phase. This section is not applicable.

N/A — Phase 3 adds new tables and a new module. No existing identifiers are renamed. No OS-registered state, secrets, or build artifacts are affected.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | CDS Brasil (series_code=29039) stored value is already in decimal form (e.g., 0.0155 for 155 bps) as per Phase 2 STATE.md decision `[02-02]` | Pattern 3 (WACC derivation) | WACC would be 10,000× wrong if still in basis points |
| A2 | `shares_outstanding` for price_target computation will come from yfinance metadata or CVM BPA balance sheet data — neither is currently stored in ingestion.db | Open Questions | price_target = NULL for all tickers until resolved |
| A3 | `financial_ltm.shareholders_equity` = `total_equity` from `cvm_statements` (code 2.03 for industrials, 2.08 for banks via BankAccountMapper) — minority interest not stripped | LTM schema | For banks, total_equity includes minority; downstream needs to handle |
| A4 | The `sectors.yaml` static `risk_free` value (0.065) is the appropriate fallback when Selic macro data is stale | Pattern 3 (stale fallback) | May be meaningfully stale if Selic has moved significantly |

**If this table has 4 items:** Items A2 and A3 require user/planner attention before execution. A1 and A4 are cross-referenced from prior phase decisions.

---

## Open Questions

1. **Shares Outstanding Source (CRITICAL for price_target)**
   - What we know: `run_dcf()` requires `shares_outstanding` to compute `price_target = equity_value / shares_outstanding`. Neither `ingestion.db` nor any table currently stores this.
   - What's unclear: CVM BPA includes total capital (`1.xx`) but not share count directly. yfinance returns `info["sharesOutstanding"]` but this is stored nowhere in the current schema.
   - Recommendation: Add `shares_outstanding` as a yfinance metadata fetch in `b3_scraper.py` or as a separate column in `price_ohlcv`/a new `ticker_metadata` table. Alternatively, compute from CVM: total PL / book value per share (requires knowing BVPS from CVM). **Planner should add a Wave 0 task to store shares_outstanding from yfinance `ticker.info["sharesOutstanding"]`** before Plan 3 (DCF) executes.

2. **How to handle tickers with < 4 ITR quarters in DB**
   - What we know: The DB is empty at research time. Some newly added tickers may only have 1-3 ITR quarters after initial ingestion.
   - What's unclear: Should LTM computation proceed with < 4 quarters (annualized), skip the ticker, or flag it?
   - Recommendation: Proceed with available quarters, compute `ltm_quarters_used` field (1-4), and flag `ltm_reconciliation_warning = 1` when < 4 quarters used. Planner should include this field in `financial_ltm` schema.

3. **Sector types with `valuation_method` other than `dcf_fcff` or `gordon_growth`**
   - What we know: `sectors.yaml` defines 4 valuation methods: `gordon_growth` (bank, holding, utilities), `dcf_fcff` (industrial, retail, healthcare, education, agro, technology, fintech), `ev_ebitda_multiple` (oil_gas, mining, telecom, real_estate), `ddm` (utilities secondary).
   - What's unclear: Phase 3 plans cover `dcf_fcff` (Plan 3) and `gordon_growth`/DDM (Plan 4). How to handle `ev_ebitda_multiple` tickers (PETR4, VALE3, VIVT3, GGBR4, etc.) — 21 active tickers.
   - Recommendation: For `ev_ebitda_multiple` tickers, compute EV = EBITDA × `ev_ebitda_assumptions.target_multiple_base`, then `fair_value = (EV - net_debt) / shares_outstanding`. Store `valuation_method = "ev_ebitda"` in `financial_dcf`. This should be implemented in Plan 3 alongside DCF, or in Plan 4 alongside bank model. Planner should decide.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| pandas | LTM aggregation, signals | Yes | 2.3.3 | — |
| numpy | Signal computation | Yes | 2.2.6 | — |
| pydantic | FinancialResult dataclass | Yes | 2.13.1 | — |
| loguru | Structured logging | Yes | 0.7.3 | — |
| pyyaml | SectorConfig YAML loading | Yes (via inference) | installed | — |
| apscheduler | Scheduler job registration | No | — | Cannot run scheduled mode; tests can mock |
| pandas-ta | Technical signals | No | — | Pure pandas (confirmed working) |
| ta-lib | Technical signals | No | — | Pure pandas (confirmed working, CONTEXT D-13) |
| sqlite3 | ingestion.db I/O | Yes (stdlib) | stdlib | — |

**Missing dependencies with no fallback:**
- `apscheduler` — required for `start_scheduler()` at runtime. Tests that call `IntelligenceScheduler.build()` will fail without it. Add `pip install apscheduler>=3.10.0` to Wave 0 setup task.

**Missing dependencies with fallback:**
- `pandas-ta`, `ta-lib` — pure pandas implementation verified and sufficient (CONTEXT D-13).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (no version pinned, stdlib + fixtures) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (minimal config, testpaths unset) |
| Quick run command | `python -m pytest tests/ -q -k "financial"` |
| Full suite command | `python -m pytest tests/ -q` |

**Confirmed:** 65/65 existing tests pass. Phase 3 tests must not break any existing tests.

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FIN-01 | LTM aggregates 4 ITR quarters correctly | unit | `pytest tests/test_financial_engine.py::test_ltm_aggregates_four_quarters -x` | Wave 0 |
| FIN-01 | LTM reconciliation warning fired when divergence > 5% | unit | `pytest tests/test_financial_engine.py::test_ltm_dfp_reconciliation_warning -x` | Wave 0 |
| FIN-01 | normalized_name back-fill updates cvm_statements | unit | `pytest tests/test_financial_engine.py::test_normalized_name_backfill -x` | Wave 0 |
| FIN-01 | AccountMapper wired into cvm_downloader parse_and_store | unit | `pytest tests/test_financial_engine.py::test_account_mapper_wired_in_downloader -x` | Wave 0 |
| FIN-02 | Multiples computed correctly for industrial ticker | unit | `pytest tests/test_financial_engine.py::test_industrial_multiples_computed -x` | Wave 0 |
| FIN-02 | Missing price produces flagged record (not zero-division) | unit | `pytest tests/test_financial_engine.py::test_multiples_handles_missing_price -x` | Wave 0 |
| FIN-03 | DCF fair value computed for industrial ticker | unit | `pytest tests/test_financial_engine.py::test_dcf_fair_value_industrial -x` | Wave 0 |
| FIN-03 | WACC derived from macro_series correctly | unit | `pytest tests/test_financial_engine.py::test_wacc_from_macro_series -x` | Wave 0 |
| FIN-03 | Stale macro falls back to sectors.yaml with WARNING log | unit | `pytest tests/test_financial_engine.py::test_wacc_stale_macro_fallback -x` | Wave 0 |
| FIN-04 | DCF skipped when terminal_growth >= WACC | unit | `pytest tests/test_financial_engine.py::test_dcf_input_validation_blocks_run -x` | Wave 0 |
| FIN-04 | Confidence flag set when fair value outside 0.1x-5.0x price | unit | `pytest tests/test_financial_engine.py::test_dcf_confidence_flag_out_of_range -x` | Wave 0 |
| FIN-05 | Bank ticker routed to DDM (not DCF) | unit | `pytest tests/test_financial_engine.py::test_bank_routing_uses_ddm -x` | Wave 0 |
| FIN-05 | Bank metrics include NIM and efficiency_ratio | unit | `pytest tests/test_financial_engine.py::test_bank_metrics_include_nim -x` | Wave 0 |
| FIN-06 | RSI-14 computed correctly | unit | `pytest tests/test_financial_signals.py::test_rsi_14_computation -x` | Wave 0 |
| FIN-06 | MACD (12/26/9) computed correctly | unit | `pytest tests/test_financial_signals.py::test_macd_12_26_9 -x` | Wave 0 |
| FIN-06 | MA50/200 and golden cross detected | unit | `pytest tests/test_financial_signals.py::test_ma_crossover_detection -x` | Wave 0 |
| FIN-06 | Composite momentum score sums to 0-100 | unit | `pytest tests/test_financial_signals.py::test_momentum_score_range -x` | Wave 0 |
| FIN-06 | Gap rows excluded from signal computation | unit | `pytest tests/test_financial_signals.py::test_gap_rows_excluded -x` | Wave 0 |
| D-01 | financial_* tables created by init_db() | unit | `pytest tests/test_financial_db_schema.py::test_financial_tables_created -x` | Wave 0 |
| D-02 | financial_ltm columns directly queryable (no JSON blob) | unit | `pytest tests/test_financial_db_schema.py::test_financial_ltm_columns -x` | Wave 0 |
| D-04 | INSERT OR REPLACE on (ticker, computed_date) | unit | `pytest tests/test_financial_db_schema.py::test_insert_or_replace_dedup -x` | Wave 0 |
| D-12 | job_financial_engine registered in _JOB_REGISTRY | unit | `pytest tests/test_financial_engine.py::test_job_registered -x` | Wave 0 |
| D-12 | job_financial_engine emits D-15 summary log | unit | `pytest tests/test_financial_engine.py::test_job_summary_log -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -q -k "financial"` (runs only Phase 3 test files)
- **Per wave merge:** `python -m pytest tests/ -q` (full suite, 65 + new tests)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_financial_engine.py` — covers FIN-01 through FIN-05, D-12 job wiring
- [ ] `tests/test_financial_signals.py` — covers FIN-06 (RSI, MACD, MA, momentum score)
- [ ] `tests/test_financial_db_schema.py` — covers D-01, D-02, D-04 (financial_* table schema)
- [ ] Fix: `src/valuation/sector_config.py` encoding bug — must be fixed before any SectorConfig test passes on Windows
- [ ] Fix: `src/normalization/account_mapper.py` bare `parsers` import — fix import path
- [ ] Install: `pip install apscheduler>=3.10.0` if scheduler integration tests are needed

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Phase 3 is an internal compute layer — no user-facing auth |
| V3 Session Management | No | No sessions; pure data pipeline |
| V4 Access Control | No | Single-user v1; ingestion.db is local SQLite |
| V5 Input Validation | Yes | DCF input validation guards (terminal_growth < WACC, WACC > 5%) required by FIN-04 |
| V6 Cryptography | No | No secrets stored in financial_engine.py |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Division by zero in DCF terminal value | Tampering (data integrity) | Input validation guard: assert terminal_growth < wacc before calling run_dcf() |
| SQL injection via ticker parameter | Tampering | Always use parameterized queries: `conn.execute(SQL, (ticker,))` — never f-string with ticker |
| Hardcoded fallback values | Information Disclosure | Keep static WACC fallback in sectors.yaml only, not as Python literals in code |

**No external API calls in Phase 3** (financial_engine.py reads from DB, not from remote APIs). The `@retry` decorator is not needed in the financial engine itself — only in ingestion-layer callers that hit external endpoints. Phase 3 compute is pure local DB reads and pure Python math.

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED: codebase inspection] `valuation_dcf.py` — `run_dcf()` signature, `DCFAssumptions`, `DCFResult`, `run_ddm()` — all verified callable via test execution
- [VERIFIED: codebase inspection] `calculate_metrics.py` — `calculate_industrial_metrics()`, `calculate_bank_metrics()` — both verified callable via test execution
- [VERIFIED: codebase inspection] `sector_config.py` — `SectorConfig.for_ticker()`, `is_bank_model`, `valuation_method` — logic verified; encoding bug confirmed on Windows
- [VERIFIED: codebase inspection] `account_mapper.py` — `AccountMapper.to_dict()` — verified callable when sys.path includes `src/`
- [VERIFIED: codebase inspection] `bank_account_mapper.py` — `BankAccountMapper.to_dict()` — verified callable
- [VERIFIED: codebase inspection] `db.py` — all 4 table schemas, column names, UNIQUE INDEX patterns confirmed
- [VERIFIED: codebase inspection] `scheduler.py` — `_JOB_REGISTRY` structure, `bind_run_id` pattern, D-15 log format confirmed
- [VERIFIED: bash execution] pandas 2.3.3 — RSI-14, MACD (12/26/9), MA50/MA200 all computable in pure pandas
- [VERIFIED: bash execution] ingestion.db — 4 tables confirmed, 0 rows (test environment)
- [VERIFIED: codebase inspection] `tickers.yaml` — 89 active tickers, 11 bank tickers, all sector types match sectors.yaml
- [VERIFIED: codebase inspection] `sectors.yaml` — 14 sector types, all with dcf_assumptions or gordon_assumptions
- [VERIFIED: bash execution] 65/65 existing tests pass — Phase 3 must not regress these

### Secondary (MEDIUM confidence)

- [CITED: .planning/phases/03-financial-engine/03-CONTEXT.md] All D-01 through D-13 decisions — verified against codebase
- [CITED: .planning/STATE.md `[02-02]`] CDS Brasil series 29039 stored as decimal (raw/10_000) — cited from Phase 2 decision log

### Tertiary (LOW confidence)

- [ASSUMED] A4: sectors.yaml static `risk_free: 0.065` is a reasonable Selic fallback for May 2026 — Selic has moved significantly since the file was written (file says "10.5%" in comments but code value is 6.5%)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all modules verified callable via bash execution
- Architecture: HIGH — patterns derived directly from confirmed codebase structure
- Pitfalls: HIGH — most pitfalls confirmed via code inspection (encoding bug, no guard in run_dcf, no EBITDA code, CDS decimal storage)
- Open questions: HIGH — accurately reflect what is and is not in the codebase

**Research date:** 2026-05-11
**Valid until:** 2026-06-11 (stable stack; sectors.yaml WACC assumptions may drift with Selic changes)
