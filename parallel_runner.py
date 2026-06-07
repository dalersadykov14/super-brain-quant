# parallel_runner.py
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from data_ingestion import get_ticker_data, safe_fetch_data
from valuation_engine import valuation_model
from ml_inference import ml_decision

portfolio_lock = threading.Lock()

def _worker_pipeline(ticker: str, threshold: float) -> tuple:
    """Handles independent ticker calculation tracking cycles across isolated scopes."""
    data = safe_fetch_data(get_ticker_data, ticker)
    if data is None:
        return ticker, False
        
    v_score = valuation_model(data)
    passes_filter = ml_decision(data, v_score, threshold)
    return ticker, passes_filter

def process_tickers_parallel(ticker_dataset: list, threshold: float, max_workers: int = 10) -> list:
    """Evaluates candidates using a clean read-only loop structure to prevent race conditions."""
    approved_list = []
    
    # RACE CONDITION CORRECTED: Process data via a clean read-only iteration over the dataset list
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {executor.submit(_worker_pipeline, t, threshold): t for t in ticker_dataset}
        
        for future in as_completed(future_to_ticker):
            ticker, is_included = future.result()
            if is_included:
                with portfolio_lock:
                    approved_list.append(ticker)
                    
    return approved_list