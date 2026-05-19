# Testing Patterns

**Analysis Date:** 2026-05-06

## Test Framework

**Runner:**
- `pytest` >= 8.0.0
- Config: `Analista de Investimentos/12_PYTHON/pyproject.toml` (`[tool.pytest.ini_options]`)
- `testpaths = ["tests"]` — pytest looks in `tests/` directory

**Coverage Plugin:**
- `pytest-cov` >= 5.0.0 (installed as dev dependency)

**Assertion Library:**
- pytest built-in `assert` statements
- `pytest.approx()` used for float comparisons with tolerance
- `numpy.testing.assert_allclose()` for array-level float comparisons

**Run Commands:**
```bash
# From the project root (12_PYTHON/ or scanner_quant_profit_b3/)
pytest                          # Run all tests in testpaths
pytest tests/test_indicators.py # Run specific file
pytest -v                       # Verbose output
pytest --cov=src --cov-report=term-missing  # With coverage
```

## Test File Organization

**Location:**
- Dedicated `tests/` directory at project root (separate from source)
- `scanner_quant_profit_b3/tests/` — the only project with active test suite
- `Analista de Investimentos/12_PYTHON/` has `[tool.pytest.ini_options]` configured but no `tests/` directory yet

**Naming:**
- Files: `test_{module_name}.py` matching the module under test
  - `test_indicators.py` → `src/quant/indicators.py`
  - `test_strategy.py` → `src/strategies/call_continuity_strategy.py`
  - `test_risk_models.py` → `src/quant/risk_models.py`
  - `test_options_math.py` → `src/quant/options_math.py`
  - `test_db.py` → database integration tests

**Structure:**
```
scanner_quant_profit_b3/
└── tests/
    ├── test_db.py
    ├── test_indicators.py
    ├── test_options_math.py
    ├── test_performance.py
    ├── test_risk_models.py
    └── test_strategy.py
```

No `conftest.py` is present. Fixtures are defined file-locally.

## Test Structure

**Suite Organization — class-per-public-function:**
```python
"""Testes para src/quant/indicators.py"""
import pytest

class TestLogReturns:
    def test_first_is_nan(self, rising_prices): ...
    def test_positive_for_rising(self, rising_prices): ...
    def test_formula(self): ...

class TestSMA:
    def test_last_value(self, rising_prices): ...
    def test_length_preserved(self, rising_prices): ...
```
Each public function/class gets its own `Test<Name>` class. Methods inside are named `test_<specific_behavior>`.

**Patterns:**
- No setup/teardown — use pytest fixtures instead
- Fixtures defined at file level with `@pytest.fixture`
- Class-scoped fixtures declared inside the test class (nested `@pytest.fixture`)
- No `setUp`/`tearDown` — avoid unittest style entirely

## Mocking

**Framework:** No dedicated mock framework observed in the test suite. Tests rely on:
- Synthetic in-memory data (DataFrames, Series)
- SQLite `:memory:` database for integration tests
- Direct fixture data rather than mock objects

**Integration Test Pattern (SQLite in-memory):**
```python
@pytest.fixture
def temp_db():
    """Banco SQLite em memória com dados sintéticos usando o schema real do projeto."""
    con = sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE b3_quotes (...)""")
    # insert synthetic rows
    yield con
    con.close()
```
Used in: `scanner_quant_profit_b3/tests/test_db.py`

**What to Mock:**
- External HTTP calls (CVM, B3 scraper) — use synthetic DataFrames instead of live data
- Database connections — use SQLite `:memory:` for integration tests
- File system reads — pass synthetic data directly to functions

**What NOT to Mock:**
- Core financial math (indicators, Black-Scholes, risk models) — test with real numeric inputs
- Pydantic validators — instantiate real models with test data

## Fixtures and Factories

**Standard Fixture Patterns:**
```python
@pytest.fixture
def rising_prices():
    """Série crescente de preços para testes de indicadores."""
    return pd.Series([10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0])

@pytest.fixture
def volatile_prices():
    """Preços voláteis com semente fixa para reprodutibilidade."""
    np.random.seed(42)
    base = 100.0
    returns = np.random.normal(0.001, 0.02, 50)
    prices = base * np.exp(np.cumsum(returns))
    return pd.Series(prices)
```

**Config Fixture Pattern:**
```python
@pytest.fixture
def qcfg():
    """Configuração completa de parâmetros de estratégia para testes."""
    return {
        "capital_inicial": 10_000,
        "risco_por_trade": 0.005,
        ...
    }
```

**Key practices:**
- Always use fixed seeds (`np.random.seed(N)`) for reproducibility in random data fixtures
- Fixtures that build on other fixtures use fixture composition (pass fixture as parameter)
- Docstrings on fixtures explain what they represent and why, not just what they are

**Location:**
- Fixtures defined at top of each `test_*.py` file — no shared `conftest.py`
- When multiple test classes in one file need the same fixture, it is defined at module scope

## Coverage

**Requirements:** No coverage threshold enforced (no `--cov-fail-under` configured)

**View Coverage:**
```bash
pytest --cov=src --cov-report=term-missing
pytest --cov=src --cov-report=html  # produces htmlcov/
```

## Test Types

**Unit Tests:**
- Pure function tests: indicators, math utilities, risk model formulas
- Scope: single function, no I/O
- Examples: `TestLogReturns`, `TestBlackScholes`, `TestKelly`, `TestSMA`

**Integration Tests:**
- Tests involving SQLite database queries and real schema
- Tests involving multi-function chains (analyze_stock + score_and_classify)
- Examples: `test_db.py`, `TestScoreAndClassify`

**E2E / Smoke Tests:**
- `pipeline banco completo/teste_pipeline.py` — not a pytest file; a standalone script
- Exercises the full valuation pipeline with synthetic Bradesco data
- Run directly: `python teste_pipeline.py`
- Not collected by pytest (no `test_` prefix at class/function level)

## Common Patterns

**Float Comparisons:**
```python
# Exact tolerance
assert result == pytest.approx(np.log(110 / 100), rel=1e-6)

# Absolute tolerance
assert abs((c.price - p.price) - expected) < 0.01

# Array comparison
np.testing.assert_allclose(diff.loc[common_idx].values, h.loc[common_idx].values, rtol=1e-6)
```

**Boundary / Edge Case Testing:**
```python
def test_zero_vol_raises_gracefully(self):
    bs = black_scholes(S=35.0, K=35.0, T=30/365, r=0.1475, sigma=0.0, option_type="CALL")
    assert bs.price >= 0  # must not raise

def test_empty_series(self):
    assert value_at_risk(pd.Series([], dtype=float)) == 0.0
```
Always include: empty input, zero denominator, past expiration / boundary conditions.

**Invalid Input Returns None (not raises):**
```python
def test_invalid_entry_returns_none(self, stock_up, qcfg):
    bad_option = pd.Series({..., "close": 0.0})  # invalid price
    result = score_and_classify(bad_option, stock_up, qcfg)
    assert result is None
```
Functions that score/classify return `None` for invalid inputs instead of raising. Tests verify this contract explicitly.

**Naming conventions inside test methods:**
- `test_<condition>_<expected>`: `test_rising_high_rsi`, `test_stop_below_entry`
- `test_has_<key_or_attribute>`: `test_has_required_keys`, `test_has_status`
- `test_<property>_range`: `test_final_score_range`, `test_bounds`

## Coverage Gaps

**`src/` package (12_PYTHON):**
- No test files exist for any module in `src/`: `metrics_engine.py`, `risk_engine.py`, `cvm_downloader.py`, `llm_client.py`, `valuation/`, `parsers/`, `normalization/`
- The `[tool.pytest.ini_options]` is configured but the `tests/` directory is absent
- `pipeline banco completo/` is only covered by the manual smoke script `teste_pipeline.py`

**Covered (scanner_quant_profit_b3):**
- `src/quant/indicators.py` — comprehensive
- `src/quant/options_math.py` — comprehensive including edge cases
- `src/quant/risk_models.py` — comprehensive
- `src/strategies/call_continuity_strategy.py` — functional + integration paths
- `src/db/` — integration-level via `test_db.py`

---

*Testing analysis: 2026-05-06*
