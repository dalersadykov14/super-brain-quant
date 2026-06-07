# Portfolio System Setup Guide

This guide covers the production-hardened version of your Portfolio System with **Authorization Code Flow + PKCE** for Schwab retail accounts, optional real data connectors, and explicit live-trading gating.

---

## Prerequisites

- Python 3.9+
- Schwab account with API access (free tier available)
- Ability to run a local HTTP callback server on `http://localhost:8080`

---

## Step 1: Schwab Developer Portal Setup

1. Go to [developer.schwab.com](https://developer.schwab.com/)
2. Log in with your Schwab credentials
3. Click **Create App** (top right, under "Apps" section)
4. Fill in the form:

   - **Environment**: Select `Production` (default)
   
   - **API Products**: Select both:
     - ✓ Accounts and Trading Production
     - ✓ Market Data Production
   
   - **App Name**: e.g., `Portfolio System`
   
   - **App Description** (optional): e.g., `Automated portfolio selection and Schwab order execution`
   
   - **Order Limit**: Set to `10` requests per minute (sufficient for this system; adjust if needed)
   
   - **Callback URL(s)**: Enter exactly:
     ```
     http://localhost:8080/callback
     ```
     (This is where the PKCE redirect will land)
   
   - **Terms of Use**: Accept and click **Create**

5. After creation, save these three values:
   - **Client ID** (e.g., `abc123def456...`)
   - **Client Secret** (e.g., `xyz789uvw012...`)
   - Your Schwab **account number** (12 digits, from your account page)

**⚠️ Security Note**: Schwab will decommission weak TLS ciphers on June 8, 2026. Ensure your Python `requests` library and system are using TLS 1.2+. This repo uses modern libraries, so no action needed.

---

## Step 2: Install Dependencies

In your `Portfolio_system` folder, open a terminal and run:

```bash
pip install -r requirements.txt
```

This installs: PyYAML, python-dotenv, requests, pandas, scikit-learn, joblib, numpy.

*Optional (for real data features later):*
```bash
pip install yfinance textblob newsapi
python -m textblob.download_corpora
```

---

## Step 3: Configure Environment Variables

Open the `.env` file in your `Portfolio_system` folder and fill in your Schwab credentials:

```env
SCHWAB_CLIENT_ID="your_client_id_here"
SCHWAB_CLIENT_SECRET="your_client_secret_here"
SCHWAB_ACCOUNT_ID="your_account_number"

# Optional: Real data API keys
ALPHA_VANTAGE_API_KEY="your_alpha_vantage_key_here"
NEWS_API_KEY=""
```

**Alpha Vantage Setup** (optional, but improves data quality):
1. Sign up free at [alphavantage.co](https://www.alphavantage.co/api/)
2. Copy your API key
3. Paste it into `.env` as shown above
4. When you run `runtime_check.py`, it will test the key with a harmless `GLOBAL_QUOTE` probe

**NewsAPI Setup** (optional, for sentiment analysis):
1. Sign up free at [newsapi.org](https://newsapi.org/)
2. Copy your API key
3. Paste it into `.env`
4. When you run `runtime_check.py`, it will test connectivity

**Important**: The Callback URL (`http://localhost:8080/callback`) is **NOT** set in `.env` — it's in `config.yaml`. Make sure the URL you entered in your Schwab Developer Portal app matches exactly:

```yaml
# config.yaml
redirect_uri: "http://localhost:8080/callback"
```

Keep the quotes in `.env`. Do NOT commit `.env` to version control.

---

## Step 4: Validate Environment & Dependencies

Run the runtime checker to verify everything is set up correctly:

```bash
python runtime_check.py
```

Expected output:
- All required packages importable ✓
- `config.yaml` loaded ✓
- Schwab gating status reported
- Optional API key connectivity tested (if keys present)

---

## Step 5: First Run in Sandbox Mode (Simulation)

`config.yaml` defaults to `enable_live_trades: false`, so no real orders will be placed. To run the first simulation:

### Load your environment and run:

**Windows (PowerShell):**
```powershell
# Load .env into current session
Get-Content .env | ForEach-Object { $_ -split '=' | ForEach-Object { if ($_ -match '=') { $key, $val = $_ -split '='; [System.Environment]::SetEnvironmentVariable($key.Trim(), $val.Trim()) } } }

# Run the simulation
python simulate_run.py
```

**Windows (Command Prompt):**
```cmd
for /f "tokens=*" %i in (.env) do @set %i
python simulate_run.py
```

**Mac/Linux:**
```bash
export $(grep -v '^#' .env | xargs)
python simulate_run.py
```

### Watch logs in real time:

```bash
# In another terminal, in the same folder:
tail -f portfolio_builder.log
```

### Expected output:
- Rotating logs appear in `portfolio_builder.log`
- At the end, `live_portfolio_state.csv` shows selected tickers
- No real orders are placed (sandbox mode)

---

## Step 6: Test Schwab Authentication (Token-Only Handshake)

Before placing real trades, test the Authorization Code flow interactively:

```bash
python schwab_auth_handshake.py
```

This will:
1. Open your default browser to the Schwab consent URL
2. Wait for you to log in and authorize
3. Capture the redirect code from `http://localhost:8080/callback`
4. Exchange the code for an access token (PKCE-secured)
5. Report success/failure without placing any orders

This validates that your Callback URL, Client ID, and PKCE flow work correctly.

---

## Step 7: Review Configuration

Open `config.yaml` and customize:

```yaml
schwab_api:
  # ✓ Already set to your Schwab endpoints
  requested_scopes: "readonly PlaceTrades"  # ✓ Correct for order placement
  enable_live_trades: false  # ← CHANGE THIS TO true ONLY WHEN READY

portfolio_management:
  sell_losers: true         # Liquidate under-performing holdings
  sell_trigger_threshold: 0.40  # Score threshold for selling
  max_workers: 10           # Parallel evaluation threads

valuation_weights:
  sentiment: 0.40
  value: 0.30
  growth: 0.20
  governance: 0.10
```

---

## Step 8: Customize Ticker Universe

Open `main.py` and find:

```python
target_universe = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD", "META", "AMZN"]
```

Replace with any US equity tickers you want the system to evaluate.

---

## Step 9: Understand Data Placeholders

**Important:** In the current version, market data returns safe fallback values:
- `sentiment_score: 0.0` (no sentiment unless NewsAPI key present)
- `pe_ratio: 18.5` (placeholder)
- Other metrics are static defaults

**To use real data**, wire in:
- **Alpha Vantage** (set `ALPHA_VANTAGE_API_KEY`) for company fundamentals
- **NewsAPI** (set `NEWS_API_KEY`) for sentiment
- **yfinance** (not yet integrated) for price/volume

The system architecture fully supports these; data functions are stubbed and ready.

---

## Step 10: Go Live (⚠️ Carefully)

**Before enabling live trades:**

1. ✅ Verify sandbox runs look correct
2. ✅ Test the auth handshake successfully
3. ✅ Review your ticker universe and position sizing
4. ✅ Ensure your Schwab account has sufficient buying power

**To enable live trading:**

Open `config.yaml` and change:

```yaml
enable_live_trades: false   →   enable_live_trades: true
```

**Then run:**

```bash
# Load env and run main.py (NOT simulate_run.py)
python main.py
```

**Live orders will now be placed.**

---

## Position Sizing

The current code places exactly **1 share per ticker**. Before going live, you may want to adjust `"quantity": 1` in `portfolio_manager.py` `execute_order()` method based on your account size and risk tolerance.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Requests library unavailable` | `pip install requests` |
| `Missing SCHWAB_CLIENT_ID` | Verify `.env` file exists and is readable; reload terminal session |
| `Authorization code not received` | Check that `http://localhost:8080/callback` is in your Schwab app settings exactly; allow 3 min for browser redirect |
| `Schwab token exchange failed: HTTP 401` | Client ID or Secret is invalid; double-check in Schwab portal |
| `HTTP 403 on order placement` | Verify `requested_scopes` includes `PlaceTrades` in `config.yaml` and Schwab app settings |

---

## Key Differences from Earlier Versions

- **OAuth Flow**: Uses Authorization Code Flow with PKCE (industry best practice for retail accounts), not Client Credentials
- **Browser Interaction**: First run will open your browser for Schwab consent
- **Live Trading Gating**: Explicit `enable_live_trades` flag prevents accidental real-money execution
- **Callback Server**: Local HTTP server on `http://localhost:8080` captures auth redirect
- **Optional Data Feeds**: Alpha Vantage, NewsAPI, SEC mappings all optional and safely fallback

---

## Support

Refer to `EXPERT_DEVELOPER_BRIEF.md` for production safety constraints and architecture details.
