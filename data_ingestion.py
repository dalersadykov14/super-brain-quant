# data_ingestion.py
import yfinance as yf
import time
import logging
import threading
import os
from valuation_engine import load_config

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    load_dotenv = None

try:
    import requests
except ModuleNotFoundError:
    requests = None

try:
    import yfinance as yf
except ModuleNotFoundError:
    yf = None

# BUG-8 CORRECTED: Force environment token hydration right at initialization phase
if load_dotenv is not None:
    load_dotenv()

# PERF-4 CORRECTED: Thread-safe global caches protect network-bound ingestion clients.
_GLOBAL_CIK_MAP_CACHE = {
    "mapping": {},
    "expires_at": 0.0
}
_GLOBAL_COMPANY_STATS_CACHE = {}
_GLOBAL_CACHE_LOCK = threading.Lock()

import yfinance as yf

#Fundamental ANalysis 
def fetch_fundamental_metrics(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info
    
    # Extract fundamental valuation features safely
    fundamental_data = {
        "pe_ratio": info.get("trailingPE", 0.0),       # Price-to-Earnings (Is it cheap?)
        "pb_ratio": info.get("priceToBook", 0.0),      # Price-to-Book (Asset value)
        "debt_to_equity": info.get("debtToEquity", 0.0), # Debt health (Is it safe?)
        "profit_margin": info.get("profitMargins", 0.0) # Profitability (Is it making money?)
    }
    return fundamental_data

def safe_fetch_data(fetch_func, ticker: str, retries: int = 3):
    """Executes network calls inside an exponential backoff wrapper."""
    for attempt in range(retries):
        try:
            return fetch_func(ticker)
        except Exception as e:
            wait = 2 ** attempt
            logging.warning(f"Attempt {attempt+1}/{retries} failed for {ticker}: {e}. Retrying in {wait}s.")
            time.sleep(wait)
    logging.error(f"All {retries} connection attempts failed for {ticker}.")
    return None

def fetch_news_sentiment(ticker: str) -> dict:
    """Queries structural financial sentiment parameters (Brief Sec. 3)."""
    # Attempt to use NewsAPI if configured, otherwise fall back to a simple heuristic
    api_key = os.getenv("NEWS_API_KEY")
    if api_key and requests is not None:
        try:
            url = "https://newsapi.org/v2/everything"
            params = {"q": ticker, "sortBy": "relevancy", "pageSize": 50, "apiKey": api_key}
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                articles = resp.json().get("articles", [])
                news_volume = len(articles)
                # crude keyword sentiment heuristic
                pos_k = ["beat", "upgrade", "outperform", "growth", "record"]
                neg_k = ["miss", "downgrade", "recall", "lawsuit", "loss"]
                score = 0.0
                for a in articles:
                    text = (a.get("title", "") + " " + a.get("description", "")).lower()
                    for k in pos_k:
                        if k in text:
                            score += 1
                    for k in neg_k:
                        if k in text:
                            score -= 1
                sentiment_score = 0.0
                if news_volume:
                    sentiment_score = max(-1.0, min(1.0, score / max(1.0, news_volume)))
                return {
                    "sentiment_score": sentiment_score,
                    "sentiment_confidence": 0.5 if news_volume else 0.0,
                    "news_volume": news_volume,
                    "news_trend": 0.0
                }
        except Exception as e:
            logging.warning(f"NewsAPI sentiment fetch failed for {ticker}: {e}")

    # Placeholder fallback
    return {
        "sentiment_score": 0.0,
        "sentiment_confidence": 0.0,
        "news_volume": 0,
        "news_trend": 0.0
    }

def fetch_company_stats(ticker: str) -> dict:
    """Queries underlying valuation accounting statistics (Brief Sec. 3).
    
    PHASE 2 FUNDAMENTAL OVERLAY: Integrates structural business health metrics alongside technical indicators.
    Feature Vector Strategy: [Momentum, Volume, PE_Ratio, Debt_To_Equity, Profit_Margin]
    This enables the ML model to learn advanced combinations (e.g., price spike only profitable if strong margins).
    
    Fallback chain: yfinance → Alpha Vantage → static values
    """
    config = load_config()
    ttl = config.get("portfolio_management", {}).get("cik_cache_ttl_seconds", 86400)
    now = time.time()

    with _GLOBAL_CACHE_LOCK:
        cached = _GLOBAL_COMPANY_STATS_CACHE.get(ticker)
        if cached and cached["expires_at"] > now:
            logging.debug(f"Returning cached company stats for {ticker}.")
            return cached["data"]

    data = None

    # ATTEMPT 1: Try yfinance (free, no API key required)
    if yf is not None:
        try:
            ticker_info = yf.Ticker(ticker)
            info = ticker_info.info
            if info and info.get("trailingPE"):
                # PHASE 2 FUNDAMENTALS: Extract structural business metrics
                data = {
                    # Technical Valuation Metrics (Phase 1)
                    "pe_ratio": float(info.get("trailingPE", 18.5)),
                    "market_cap": float(info.get("marketCap", 85000000000.0)),
                    
                    # Profitability & Cash Flow Strength (Phase 2)
                    "earnings": float(info.get("netIncomeToCommon", 4500000000.0)),
                    "costs": float(info.get("operatingExpenses", 2100000000.0)),
                    "cash_flow": float(info.get("operatingCashflow", 2400000000.0)),
                    
                    # Growth & Health Indicators (Phase 2)
                    "revenue_growth": float(info.get("revenueGrowth", 0.14)),
                    "debt_ratio": float(info.get("debtToEquity", 0.35)),
                    
                    # NEW Phase 2: Fundamental Screening Metrics
                    "profit_margin": max(0.0, float(info.get("profitMargins", 0.12))),  # Profitability baseline
                    "pb_ratio": max(0.0, float(info.get("priceToBook", 2.5))),          # Asset valuation
                    "debt_to_equity": max(0.0, float(info.get("debtToEquity", 0.35)))   # Balance sheet health
                }
                logging.debug(f"Successfully fetched {ticker} stats from yfinance with Phase 2 fundamentals")
        except Exception as e:
            logging.debug(f"yfinance fetch failed for {ticker}: {e}")
            data = None

    # ATTEMPT 2: Try Alpha Vantage if yfinance failed and API key is provided
    if data is None:
        av_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if av_key and requests is not None:
            try:
                url = "https://www.alphavantage.co/query"
                params = {"function": "OVERVIEW", "symbol": ticker, "apikey": av_key}
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    j = resp.json()
                    # Map known fields to our schema with safe conversion
                    def _float_get(key, default=0.0):
                        try:
                            return float(j.get(key, default))
                        except Exception:
                            return default

                    data = {
                        "pe_ratio": _float_get("PERatio", 0.0),
                        "market_cap": _float_get("MarketCapitalization", 0.0),
                        "earnings": _float_get("EPS", 0.0) * _float_get("SharesOutstanding", 0.0) if j.get("EPS") and j.get("SharesOutstanding") else 0.0,
                        "costs": 0.0,
                        "cash_flow": _float_get("OperatingCashFlow", 0.0),
                        "revenue_growth": _float_get("RevenuePTTM", 0.0),  # TTM metric (not growth rate, best approximation available)
                        "debt_ratio": _float_get("DebtToEquity", 0.0),
                        # Phase 2 Fundamentals (Alpha Vantage may not provide all; use safe defaults)
                        "profit_margin": max(0.0, _float_get("ProfitMargin", 0.0)),
                        "pb_ratio": max(0.0, _float_get("PriceToBookRatio", 0.0)),
                        "debt_to_equity": max(0.0, _float_get("DebtToEquity", 0.0))
                    }
                    logging.debug(f"Successfully fetched {ticker} stats from Alpha Vantage with Phase 2 fundamentals")
                else:
                    logging.debug(f"AlphaVantage request failed for {ticker}: HTTP {resp.status_code}")
            except Exception as e:
                logging.debug(f"AlphaVantage fetch failed for {ticker}: {e}")

    # ATTEMPT 3: Fallback to static values (safe default)
    if data is None:
        logging.warning(f"All data sources failed for {ticker}. Using static fallback values.")
        data = {
            "pe_ratio": 18.5,
            "market_cap": 85000000000.0,
            "earnings": 4500000000.0,
            "costs": 2100000000.0,
            "cash_flow": 2400000000.0,
            "revenue_growth": 0.14,
            "debt_ratio": 0.35,
            # Phase 2 Fundamentals (neutral fallback values)
            "profit_margin": 0.10,
            "pb_ratio": 2.0,
            "debt_to_equity": 0.35
        }

    with _GLOBAL_CACHE_LOCK:
        _GLOBAL_COMPANY_STATS_CACHE[ticker] = {
            "data": data,
            "expires_at": now + ttl
        }

    return data

def fetch_legal_structure(ticker: str) -> dict:
    """Queries legal/governance risk metrics from SEC lookup tables (Brief Sec. 3)."""
    global _GLOBAL_CIK_MAP_CACHE
    config = load_config()
    ttl = config.get("portfolio_management", {}).get("cik_cache_ttl_seconds", 86400)
    now = time.time()
    with _GLOBAL_CACHE_LOCK:
        if _GLOBAL_CIK_MAP_CACHE["mapping"] and _GLOBAL_CIK_MAP_CACHE["expires_at"] > now:
            logging.debug("Using cached SEC CIK mapping session.")
        else:
            logging.info("PERF-4: Initializing global SEC mapping session cache.")
            # Try to fetch SEC mapping file; fall back to a small default mapping
            mapping = {}
            if requests is not None:
                try:
                    sec_url = "https://www.sec.gov/files/company_tickers.json"
                    resp = requests.get(sec_url, timeout=10)
                    if resp.status_code == 200:
                        j = resp.json()
                        for _, v in j.items():
                            t = v.get("ticker")
                            cik = v.get("cik_str")
                            if t and cik:
                                mapping[t.upper()] = cik.zfill(10)
                    else:
                        logging.warning(f"SEC company tickers fetch failed: HTTP {resp.status_code}")
                except Exception as e:
                    logging.warning(f"SEC mapping fetch failed: {e}")

            if not mapping:
                mapping = {"AAPL": "0000320193", "MSFT": "0000789019"}

            _GLOBAL_CIK_MAP_CACHE = {
                "mapping": mapping,
                "expires_at": now + ttl
            }

    cik = _GLOBAL_CIK_MAP_CACHE["mapping"].get(ticker.upper())

    # Governance metrics are non-trivial to compute automatically; placeholders are provided
    return {
        "cik": cik,
        "board_size": 8,
        "ceo_tenure": 5.5,
        "governance_score": 0.82,
        "employee_count": 32000,
        "management_cred_score": 0.78
    }

def get_ticker_data(ticker: str) -> dict:
    """Aggregates multi-source client outputs into a flat dictionary schema."""
    nws = fetch_news_sentiment(ticker)
    cps = fetch_company_stats(ticker)
    ls = fetch_legal_structure(ticker)
    
    merged = {**nws, **cps, **ls}
    merged["ticker_symbol"] = ticker
    merged["company_name"] = f"{ticker} Inc."

    # Structural integrity validation (includes Phase 2 fundamentals)
    required_metrics = [
        'sentiment_score', 'pe_ratio', 'governance_score', 'revenue_growth',
        'profit_margin', 'pb_ratio', 'debt_to_equity'  # Phase 2 critical fields
    ]
    for metric in required_metrics:
        if metric not in merged or merged[metric] is None:
            # Assign appropriate defaults based on metric type
            if metric in ['profit_margin', 'pb_ratio', 'debt_to_equity']:
                default = 0.0 if metric == 'debt_to_equity' else 1.0
            else:
                default = 0.0
            logging.warning(f"Data schema anomaly detected for {ticker}: missing {metric}. Imputing {default}.")
            merged[metric] = default
            
    return merged