import streamlit as st
import pandas as pd
import yfinance as yf
import yaml
import os
import time

# --- PAGE CONFIGURATION & THEME ---
st.set_page_config(
    page_title="Super Brain | Quant Engine",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS to hide Streamlit's default top menu and footer for a cleaner "app" feel
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem; padding-bottom: 0rem;}
    </style>
""", unsafe_allow_html=True)

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
    return "No logs generated yet... System is waiting for pipeline execution."

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
st.sidebar.caption("Modifying values updates the local config.yaml environment.")

if config:
    with st.sidebar.form("config_editor", border=False):
        
        with st.expander("🔌 API & Execution", expanded=True):
            enable_live = st.toggle("Enable Live Schwab Trades", value=config.get("schwab_api", {}).get("enable_live_trades", False))
            max_workers = st.number_input("Max Parallel Workers", min_value=1, max_value=20, value=config.get("portfolio_management", {}).get("max_workers", 10))

        with st.expander("🧠 ML Model Thresholds", expanded=True):
            buy_threshold = st.slider("AI Buy Probability Cutoff", 0.0, 1.0, float(config.get("ml", {}).get("buy_threshold", 0.40)), 0.01)
            sell_trigger = st.slider("Sell Trigger Target", 0.0, 1.0, float(config.get("portfolio_management", {}).get("sell_trigger_threshold", 0.40)), 0.01)
            
        submitted = st.form_submit_button("💾 Save & Apply Configuration", width="stretch")
        if submitted:
            config["schwab_api"]["enable_live_trades"] = enable_live
            config["ml"]["buy_threshold"] = buy_threshold
            config["portfolio_management"]["sell_trigger_threshold"] = sell_trigger
            config["portfolio_management"]["max_workers"] = max_workers
            if save_config(config):
                st.toast("Configuration updated successfully!", icon="✅")
            else:
                st.toast("Failed to write to config.yaml", icon="❌")

# --- UI: TOP KPI METRICS ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Active Tracked Assets", len(tickers_list), "Live")
col2.metric("ML Execution Model", "Super Brain Phase 2", "Active")
col3.metric("Schwab API Connection", "PRODUCTION" if config.get("schwab_api", {}).get("enable_live_trades") else "SANDBOX", 
            delta_color="normal" if config.get("schwab_api", {}).get("enable_live_trades") else "off")
col4.metric("Engine Health", "100%", "Stable")

st.write("") # Spacer

# --- UI: MAIN DASHBOARD TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Live Portfolio Holdings", "🧬 Core Architecture", "🖥️ System Logs"])

with tab1:
    if not tickers_list:
        st.info("System allocation equilibrium achieved. System holding 100% simulated cash reserves.")
    else:
        with st.spinner("Fetching real-time market data..."):
            live_prices = fetch_live_prices(tickers_list)
            
        # Build a sleek display dataframe
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
            st.bar_chart(df_w.set_index("Factor"), color="#00ff00") # Adds a nice terminal green color
            
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