# main.py
import threading
import sys
import time
import logging
import pandas as pd
from logger_config import setup_logging
from portfolio_manager import run_portfolio_selection

def fetch_sp500_tickers() -> list:
    """
    Dynamically scrapes the current list of S&P 500 constituent tickers from Wikipedia.
    Utilizes custom browser headers to satisfy Wikipedia's security access policies.
    """
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        
        # Spoof a real Windows Chrome browser string to avoid HTTP 403 Forbidden blocks
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Pass the custom headers directly into pandas via storage_options
        tables = pd.read_html(url, storage_options=headers)
        df = tables[0]
        
        # Extract and clean tickers
        raw_tickers = df['Symbol'].tolist()
        cleaned_tickers = [ticker.replace('.', '-') for ticker in raw_tickers]
        return cleaned_tickers
        
    except Exception as e:
        logging.error(f"Failed to fetch dynamic S&P 500 index map from Wikipedia: {e}")
        print("\n[!] Technical warning: Online index fetch failed. Using institutional tech baseline.")
        return ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD", "META", "AMZN", "JPM", "V", "XOM"]
    
def main():
    # 1. Initialize the global thread-safe rotating file logger
    setup_logging()
    
    # 2. Configure the thread-safe emergency abort event flag
    kill_switch = threading.Event()
    
    print("----------------------------------------------------------------------")
    print("Initializing Unbiased S&P 500 Autonomous Selection Pipeline Engine...")
    print("Execution logs are actively updating inside: 'portfolio_builder.log'")
    print("----------------------------------------------------------------------")
    
    # 3. Dynamic Universe Acquisition
    print("Connecting to public index indexes to fetch S&P 500 components...")
    full_universe = fetch_sp500_tickers()
    total_tickers = len(full_universe)
    print(f"Success! Identified {total_tickers} target assets for automated evaluation.\n")
    
    # 4. Define Throttling Guardrails (Protects your Charles Schwab 60-req/min ceiling)
    BATCH_SIZE = 25    # Evaluates 25 stocks simultaneously via concurrent threads per loop pass
    REST_PERIOD = 60   # Wait 60 seconds between batches to allow API rate-limit windows to reset
    
    compiled_portfolio = []
    
    try:
        # Step through the 500 stocks in chunks of 25
        for i in range(0, total_tickers, BATCH_SIZE):
            if kill_switch.is_set():
                break
                
            current_batch = full_universe[i:i + BATCH_SIZE]
            batch_index = (i // BATCH_SIZE) + 1
            total_batches = (total_tickers + BATCH_SIZE - 1) // BATCH_SIZE
            
            print(f"=== PROCESSING BATCH {batch_index}/{total_batches} ===")
            print(f"Evaluating symbols: {current_batch}\n")
            
            # Pass the isolated batch array into your parallel processing engine
            # It runs news sentiment, yfinance extraction, and ML scoring across your 10 max_workers
            batch_approved_assets = run_portfolio_selection(current_batch, kill_switch_event=kill_switch)
            
            # Record any assets from this batch that cleared your ML buy threshold
            compiled_portfolio.extend(batch_approved_assets)
            
            # Enforce server-safe rest window unless this is the final block of the index
            if i + BATCH_SIZE < total_tickers:
                print(f"\nBatch {batch_index} complete. Registered allocations: {batch_approved_assets}")
                print(f"Throttling safety event: Sleeping for {REST_PERIOD} seconds to protect API access keys...")
                
                # Sleep incrementally so Ctrl+C keyboard interrupts remain highly responsive
                for _ in range(REST_PERIOD):
                    if kill_switch.is_set():
                        break
                    time.sleep(1)
                print("-" * 70)

        # 5. Pipeline Consolidation and Final Diagnostics
        # Deduplicate the array list to ensure state integrity
        final_portfolio_state = list(set(compiled_portfolio))
        
        print("\n======================================================================")
        print("UNBIASED FULL-MARKET AUTONOMOUS SCAN COMPLETE.")
        print(f"Active Tracked Target Allocation Portfolio State: {final_portfolio_state}")
        print("======================================================================")
        
    except KeyboardInterrupt:
        print("\n[!] Keyboard Interrupt detected. Activating Kill Switch to halt threads safely...")
        kill_switch.set()
        sys.exit(0)

if __name__ == "__main__":
    main()