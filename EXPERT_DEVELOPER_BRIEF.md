python runtime_check.py# Expert Developer Brief: Automated Financial Portfolio Selection System (Production-Grade)

## Overview
You are tasked with building or maintaining a production-grade, automated financial portfolio selection system that combines multi-source data extraction, algorithmic valuation modeling, and machine learning to iteratively construct, refine, and rebalance an investment portfolio.

The system must be modular, highly parallelized, completely observable via rotating logs, and structurally immune to runtime exceptions, memory leaks, and thread-race anomalies.

---

## 1. System Directory Architecture
The implementation must adhere strictly to a decoupled, file-based architecture to isolate dependencies and maintain clean boundaries:

```text
portfolio_system/
│
├── .env                        # Secure environment credentials (API tokens)
├── config.yaml                 # Decoupled thresholds, weights, and API scopes
├── logger_config.py            # Thread-safe rotating file logging layer
├── data_ingestion.py           # Multi-source API clients with caching & backoff
├── valuation_engine.py         # Algorithmic metric evaluation engine
├── ml_trainer.py               # Model generation, optimization, and training
├── ml_inference.py             # Schema-insulated model inference wrapper
├── parallel_runner.py          # Concurrency engine for parallel evaluations
├── portfolio_manager.py        # Iterative rebalance engine with broker integration
└── main.py                     # Entry point and system orchestrator
```

## 2. Core Operational Constraints & Required Safeguards
Any code generated or modified against this brief must enforce the following architectural protections:

### Stack Overflow / Unbounded Loop Prevention
- Anti-Pattern: Never implement the portfolio selection workflow using recursive functions (`return run_portfolio_selection(..., run_number + 1)`).
- Requirement: Use a stateful, iterative while loop bound by an explicit configuration cap (e.g., `max_protection_limit = 5`) and an asset convergence check (`if new_buys_count == 0: break`).

### Mathematical Zero-Division Armor
- Anti-Pattern: Never calculate inverse values directly from raw financial data variables (e.g., `1.0 / pe_ratio`).
- Requirement: Proactively evaluate values. If a Price-to-Earnings (`pe_ratio`) ratio is zero or negative, immediately intercept and assign a neutral fallback value (`0.0`), preventing fatal `ZeroDivisionError` terminations.

### Machine Learning Schema Drift Insulation
- Anti-Pattern: Never pass a raw, unkeyed dictionary or unstructured array into an ML model's prediction pipeline.
- Requirement: Reconstruct all ingestion vectors into an explicitly ordered Pandas DataFrame structured precisely against a static index array (`FEATURE_COLS`) prior to running inference.

### Parallel Thread-Race Protection
- Anti-Pattern: Thread workers must never concurrently modify a shared global collection or active portfolio tracking list.
- Requirement: Execute worker loops over immutable read-only snapshots of the dataset. Wrap mutations of shared in-memory lists inside a mutual exclusion lock (`threading.Lock()`).

### API Authentication Scope Alignment
- Anti-Pattern: Requesting broad or read-only authentication scopes for transactional engines.
- Requirement: OAuth credential payload definitions must explicitly demand execution privileges (e.g., `PlaceTrades` alongside `readonly`) to eliminate standard HTTP 403 authorization failures during order routing.
- Requirement: Retail Schwab OAuth must use Authorization Code Flow with PKCE for live account authorization, not a client credentials grant.

### Live Execution Gating
- Anti-Pattern: Enabling live Schwab order routing by default or via hidden code paths.
- Requirement: The broker implementation must remain in sandbox simulation mode unless `schwab_api.enable_live_trades` is explicitly set to `true` in `config.yaml` for a validated production deployment. Live trading must never occur without this deliberate, audited switch.

### Proactive Token Hydration
- Anti-Pattern: Initializing global caching utilities or API clients before system environment variables are populated.
- Requirement: Force the extraction of environment variables (`load_dotenv()`) at the absolute entry phase of data ingestion compilation.

## 3. Reference Implementations & Specifications

### 3a. Configuration Matrices (`config.yaml`)

```yaml
schwab_api:
  base_url: "https://api.schwabapi.com/trader/v1"
  token_url: "https://api.schwabapi.com/v1/oauth/token"
  requested_scopes: "readonly PlaceTrades" # Required for seamless trade authorization

ml:
  fallback_valuation_threshold: 0.0
  buy_threshold: 0.55

portfolio_management:
  sell_losers: true
  sell_trigger_threshold: 0.40
  max_workers: 10
  cik_cache_ttl_seconds: 86400

valuation_weights:
  sentiment: 0.40
  value: 0.30
  growth: 0.20
  governance: 0.10
```

### 3b. Feature Schema
Every evaluation candidate must process through a structured dictionary containing these precise metrics:
- Identification: `ticker_symbol` (str), `company_name` (str)
- News Sentiment (NWS): `sentiment_score` (float: -1.0 to 1.0), `sentiment_confidence` (float), `news_volume` (int), `news_trend` (float)
- Company Stats (CPS): `pe_ratio` (float), `market_cap` (float), `earnings` (float), `costs` (float), `cash_flow` (float), `revenue_growth` (float), `debt_ratio` (float)
- Legal Structure (LS): `board_size` (int), `ceo_tenure` (float), `governance_score` (float), `employee_count` (int), `management_cred_score` (float)

## 4. Module Execution Design

### Data Ingestion Layer (`data_ingestion.py`)
Must use thread-safe caching layers to prevent endpoint rate limiting, backed by a robust exponential backoff loop for network resiliency:

```python
import time
import logging
import threading

_GLOBAL_CIK_MAP_CACHE = {"mapping": {}, "expires_at": 0.0}
_GLOBAL_CACHE_LOCK = threading.Lock()

def safe_fetch_data(fetch_func, ticker: str, retries: int = 3):
    for attempt in range(retries):
        try:
            return fetch_func(ticker)
        except Exception as e:
            wait = 2 ** attempt
            logging.warning(f"Attempt {attempt+1}/{retries} failed for {ticker}: {e}. Retrying in {wait}s.")
            time.sleep(wait)
    logging.error(f"Critical: All {retries} connection attempts failed for {ticker}.")
    return None
```

### Valuation Engine (`valuation_engine.py`)

```python
def valuation_model(features: dict) -> float:
    # Explicit zero/negative protection to trap ZeroDivisionErrors
    pe = features.get("pe_ratio", 1.0)
    value_score = 0.0 if pe <= 0 else (1.0 / pe)

    # Compute score using external config weights
    config = load_config()
    w = config.get("valuation_weights", {})

    score = (
        w.get("sentiment", 0.4) * features.get("sentiment_score", 0.0) +
        w.get("value", 0.3) * value_score +
        w.get("growth", 0.2) * features.get("revenue_growth", 0.0) +
        w.get("governance", 0.1) * features.get("governance_score", 0.0)
    )
    return float(score)
```

### ML Inference Engine (`ml_inference.py`)

```python
FEATURE_COLS = [
    'sentiment_score', 'sentiment_confidence', 'news_volume', 'news_trend',
    'pe_ratio', 'market_cap', 'earnings', 'costs', 'cash_flow',
    'revenue_growth', 'debt_ratio', 'board_size', 'ceo_tenure', 
    'governance_score', 'employee_count', 'management_cred_score', 'valuation_score'
]

def ml_decision(features: dict, valuation_score: float, threshold: float = 0.5) -> bool:
    if ml_model is None:
        return valuation_score > load_config().get("ml", {}).get("fallback_valuation_threshold", 0.0)

    # Build explicitly ordered dataframe row to prevent feature alignment drift
    row = {k: [features.get(k, 0.0)] for k in FEATURE_COLS if k != 'valuation_score'}
    row['valuation_score'] = [valuation_score]
    df_vector = pd.DataFrame(row)[FEATURE_COLS]

    return ml_model.predict_proba(df_vector)[0][1] > threshold
```

### Workflow Controller (`portfolio_manager.py`)

```python
def run_portfolio_selection(ticker_dataset: list, kill_switch_event=None) -> list:
    current_holdings = []
    current_cycle = 1
    max_protection_limit = 5

    # Fixed-state iteration entirely eliminates recursion stack risk
    while current_cycle <= max_protection_limit:
        if kill_switch_event and kill_switch_event.is_set():
            logging.warning("Kill switch signaled. Halting operations safely.")
            break

        # 1. Execute performance liquidation pass
        current_holdings = execute_portfolio_rebalance(current_holdings, load_config())

        # 2. Extract and evaluate new candidates in parallel
        unowned_candidates = [t for t in ticker_dataset if t not in current_holdings]
        if not unowned_candidates:
            break

        approved_buys = process_tickers_parallel(unowned_candidates, buy_threshold)

        # 3. Route orders and track state convergence
        new_buys_count = 0
        for ticker in approved_buys:
            if broker.execute_order(ticker, "BUY"):
                current_holdings.append(ticker)
                new_buys_count += 1

        if new_buys_count == 0:
            logging.info("Portfolio state achieved equilibrium. Exiting tracking loop cleanly.")
            break

        current_cycle += 1
    return current_holdings
```

## 5. Technology Stack & Packages
- Data Processing & ML: `pandas`, `scikit-learn`, `joblib`
- Concurrency & Context: `concurrent.futures`, `threading`, `python-dotenv`, `pyyaml`
- Logging System: Standard Python `logging` initialized with a 5MB size-bound `RotatingFileHandler` across a maximum of 5 history backups.

## 6. Production Readiness Checklist
- `PyYAML`, `requests`, `pandas`, `scikit-learn`, `joblib`, and `numpy` must be installed in the runtime environment.
- `SCHWAB_CLIENT_ID`, `SCHWAB_CLIENT_SECRET`, and `SCHWAB_ACCOUNT_ID` must be set securely via `.env` or environment variables before live deployment.
- `config.yaml` must declare `schwab_api.enable_live_trades: false` by default and only switch to `true` after a documented production review.
- The current default broker implementation is intentionally sandboxed; real Schwab connectivity requires activating the live trade payload block and verifying API token acquisition.

***

This document serves as an airtight reference blueprint. Any modifications, enhancements, or future expansions to the codebase must preserve these baseline boundaries to avoid introducing fatal regression errors.
