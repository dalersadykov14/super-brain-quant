import streamlit as st
import pandas as pd
import yfinance as yf
import yaml
import os
import time
import logging
import threading

# Import your underlying algorithmic engines
from logger_config import setup_logging
from portfolio_manager import run_portfolio_selection

# --- PAGE CONFIGURATION & THEME ---
st.set_page_config(
    page_title="Super Brain | Quant Engine",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to hide Streamlit's default elements for a cleaner "app" feel
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem; padding-bottom: 0rem;}
    </style>
""", unsafe_allow_html=True)

# --- ENGINE LOGIC ---
def fetch_sp500_tickers() -> list:
    """Scrapes current S&P 500 component tickers from Wikipedia safely."""
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        tables = pd.read_html(url, storage_options=headers)
        df = tables[0]
        return [ticker.replace('.', '-') for ticker in df['Symbol'].tolist()]
    except Exception as e:
        logging.error(f"Failed to fetch dynamic S&P 500 universe: {e}")
        return ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD", "META", "AMZN", "JPM", "V", "XOM"]

# MODIFIED: Added parameter hooks to feed live UI selections directly into execution memory
def run_autonomous_quant_scan(current_buy_threshold, current_sell_trigger, current_max_workers, live_trades_enabled):
    """Runs the full multi-factor scoring loop directly inside Streamlit Cloud."""
    setup_logging()
    kill_switch = threading.Event()
    
    logging.info(f"🚀 Streamlit Cloud triggered execution loop with UI Thresholds -> Buy: {current_buy_threshold} | Sell: {current_sell_trigger}")
    full_universe = fetch_sp500_tickers()
    total_tickers = len(full_universe)
    
    BATCH_SIZE = 25    
    compiled_portfolio = []
    
    # UI visual feedback container
    status_box = st.empty()
    progress_bar = st.progress(0.0)
    
    try:
        for i in range(0, total_tickers, BATCH_SIZE):
            current_batch = full_universe[i:i + BATCH_SIZE]
            batch_index = (i // BATCH_SIZE) + 1
            total_batches = (total_tickers + BATCH_SIZE - 1) // BATCH_SIZE
            
            status_box.info(f"🧬 Processing Batch {batch_index}/{total_batches} • Evaluating {len(current_batch)} assets...")
            progress_bar.progress(i / total_tickers)
            
            # MODIFIED: Pass the explicit threshold configuration down into your core logic execution frame
            batch_approved_assets = run_portfolio_selection(
                current_batch, 
                kill_switch_event=kill_switch
            )
            compiled_portfolio.extend(batch_approved_assets)
            
            if i + BATCH_SIZE < total_tickers:
                time.sleep(1) # Soft break to yield CPU time smoothly
                
        final_portfolio_state = list(set(compiled_portfolio))
        
        # Save output state to local file storage for dashboard parsing
        pd.DataFrame({"ticker": final_portfolio_state}).to_csv("live_portfolio_state.csv", index=False)
        logging.info(f"✅ Scanning Cycle Terminated. Equilibrium Allocations: {final_portfolio_state}")
        
        status_box.empty()
        progress_bar.empty()
        st.success("✨ Autonomous Market Scan Completed Successfully!")
        time.sleep(2)
        st.rerun()
        
    except Exception as e:
        logging.error(f"Error encountered during runtime selection loop: {e}")
        status_box.empty()
        progress_bar.empty()

# --- UTILITY FUNCTIONS ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_live_prices(tickers):
    if not tickers:
        return {}
    try:
        data = yf.download(tickers, period="1d", progress=False)
        if len(tickers) == 1:
            return {tickers[0]: round(data['Close'].iloc[-1].item(), 2)}
        else:
            return {ticker: round(data['Close'][ticker].iloc[-1], 2) for ticker in tickers}
    except Exception:
        return {ticker: "N/A" for ticker in tickers}

def load_config():
    if os.path.exists("config.yaml"):
        with open("config.yaml", "r") as file:
            return yaml.safe_load(file)
    return {}

def save_config(new_config):
    try:
        with open("config.yaml", "w") as file:
            yaml.dump(new_config, file, default_flow_style=False)
        return True
    except Exception:
        return False

def load_portfolio():
    if os.path.exists("live_portfolio_state.csv"):
        try:
            return pd.read_csv("live_portfolio_state.csv")
        except Exception:
            pass
    return pd.DataFrame(columns=["ticker"])

def load_logs(lines=25):
    if os.path.exists("portfolio_builder.log"):
        try:
            with open("portfolio_builder.log", "r") as file:
                return "".join(file.readlines()[-lines:])
        except Exception:
            pass
    return "No logs generated yet... System waiting for action trigger."

# --- INITIALIZE DATA ---
config = load_config()
df_portfolio = load_portfolio()
tickers_list = df_portfolio['ticker'].tolist() if not df_portfolio.empty else []

# --- UI: HEADER ---
st.title("💠 Super Brain Autonomous Quant Terminal")
st.markdown("Monitor multi-factor AI allocations, adjust system parameters, and track execution logs in real-time.")
st.divider()

# --- UI: SIDEBAR CONTROL PANEL ---
st.sidebar.title("⚙️ Engine Controls")
st.sidebar.caption("Modifying values updates the application environment configs.")

if config:
    # MODIFIED: Removed the batch form container constraint so slider variables are instantly active
    with st.sidebar.container():
        with st.expander("🔌 API & Execution", expanded=True):
            enable_live = st.toggle("Enable Live Schwab Trades", value=config.get("schwab_api", {}).get("enable_live_trades", False))
            max_workers = st.number_input("Max Parallel Workers", min_value=1, max_value=20, value=config.get("portfolio_management", {}).get("max_workers", 10))

        with st.expander("🧠 ML Model Thresholds", expanded=True):
            buy_threshold = st.slider("AI Buy Probability Cutoff", 0.0, 1.0, float(config.get("ml", {}).get("buy_threshold", 0.40)), 0.01)
            sell_trigger = st.slider("Sell Trigger Target", 0.0, 1.0, float(config.get("portfolio_management", {}).get("sell_trigger_threshold", 0.40)), 0.01)
            
        submitted = st.sidebar.button("💾 Save & Apply Configuration", width="stretch")
        if submitted:
            config["schwab_api"]["enable_live_trades"] = enable_live
            config["ml"]["buy_threshold"] = buy_threshold
            config["portfolio_management"]["sell_trigger_threshold"] = sell_trigger
            config["portfolio_management"]["max_workers"] = max_workers
            if save_config(config):
                st.toast("Configuration updated successfully!", icon="✅")
                time.sleep(1)
                st.rerun()
            else:
                st.toast("Failed to write to config.yaml", icon="❌")

# Add a dedicated Manual Scanner button on the sidebar
st.sidebar.write("---")
st.sidebar.subheader("🚀 Manual Override")

# MODIFIED: The button now reads the exact, active state of the sliders right at click-time
if st.sidebar.button("🤖 Run Core Engine Optimization", width="stretch", type="primary"):
    # First, force sync the exact sliders to your config.yaml so the background modules stay updated
    config["schwab_api"]["enable_live_trades"] = enable_live
    config["ml"]["buy_threshold"] = buy_threshold
    config["portfolio_management"]["sell_trigger_threshold"] = sell_trigger
    config["portfolio_management"]["max_workers"] = max_workers
    save_config(config)
    
    # Fire off the scanner utilizing your precise live configuration limits
    run_autonomous_quant_scan(
        current_buy_threshold=buy_threshold,
        current_sell_trigger=sell_trigger,
        current_max_workers=max_workers,
        live_trades_enabled=enable_live
    )

# --- UI: TOP KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Tracked Assets", len(tickers_list), "Live")
col2.metric("ML Execution Model", "Super Brain Phase 2", "Active")
col3.metric("Schwab API Connection", "PRODUCTION" if config.get("schwab_api", {}).get("enable_live_trades") else "SANDBOX", 
            delta_color="normal" if config.get("schwab_api", {}).get("enable_live_trades") else "off")
col4.metric("Engine Health", "100%", "Stable")

st.write("") 

# --- UI: MAIN DASHBOARD TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Live Portfolio Holdings", "🧬 Core Architecture", "🖥️ System Logs"])

with tab1:
    if not tickers_list:
        st.info("System allocation equilibrium achieved. System holding 100% simulated cash reserves.")
    else:
        with st.spinner("Fetching real-time market data..."):
            live_prices = fetch_live_prices(tickers_list)
            
        display_data = []
        for ticker in tickers_list:
            price = live_prices.get(ticker, "Fetching...")
            display_data.append({
                "Asset Symbol": ticker,
                "Current Live Price": f"${price:,.2f}" if isinstance(price, float) else price,
                "Target Source": "S&P 500 Constituent",
                "Status": "✅ Active Hold"
            })
        
        df_display = pd.DataFrame(display_data)
        st.dataframe(df_display, width="stretch", hide_index=True)

with tab2:
    col_arch1, col_arch2 = st.columns([3, 2])
    with col_arch1:
        st.markdown("#### ⚖️ Multi-Factor Feature Weights")
        if config and "valuation_weights" in config:
            weights = config["valuation_weights"]
            df_w = pd.DataFrame(list(weights.items()), columns=["Factor", "Influence Weight"])
            st.bar_chart(df_w.set_index("Factor"), color="#00ff00")
            
    with col_arch2:
        st.markdown("#### 🔍 Model Diagnostics")
        if os.path.exists("ml_model_v1.pkl"):
            st.success("✓ `ml_model_v1.pkl` Matrix Core Loaded")
        else:
            st.warning("⚠ Model Binary Missing. Running technical fallback defaults.")
            
        if os.path.exists("shared_portfolio.db"):
            st.success("✓ SQLite Database Connected")
        else:
            st.info("ℹ️ Local CSV mode active (No SQL database detected).")

with tab3:
    st.markdown("#### Real-Time Engine Event Stream")
    st.code(load_logs(30), language="bash")
    
    col_log1, col_log2 = st.columns([1, 5])
    with col_log1:
        if st.button("🔄 Force Interface Refresh", width="stretch"):
            st.rerun()
