# portfolio_manager.py
import os
import logging
import pandas as pd
import webbrowser
import http.server
import socketserver
import urllib.parse
import threading
import time
import random
import secrets
import hashlib
import base64
from valuation_engine import load_config, valuation_model
from ml_inference import ml_decision
from data_ingestion import get_ticker_data, safe_fetch_data
from parallel_runner import process_tickers_parallel

try:
    import requests
except ModuleNotFoundError:
    requests = None

class SchwabExecutionClient:
    """Directly manages secure authentication protocol tokens and routes execution orders."""
    def __init__(self):
        self.config = load_config()["schwab_api"]
        self.base_url = self.config["base_url"]
        self.account_id = os.getenv("SCHWAB_ACCOUNT_ID", "SIMULATED_ACC_ID")
        self.access_token = None 

    def _refresh_oauth_token(self, timeout_seconds: int = 180):
        """Requests high-security tokens utilizing verified environment configuration setups."""
        if requests is None:
            logging.error("Requests library unavailable; cannot refresh Schwab OAuth token.")
            return

        # Prefer Authorization Code Flow for retail Schwab accounts
        if self.config.get("oauth_flow") == "authorization_code":
            client_id = os.getenv("SCHWAB_CLIENT_ID")
            client_secret = os.getenv("SCHWAB_CLIENT_SECRET")
            redirect_uri = self.config.get("redirect_uri")
            auth_url = self.config.get("auth_url")
            scope = self.config.get("requested_scopes")

            if not (client_id and redirect_uri and auth_url):
                logging.error("Missing SCHWAB_CLIENT_ID / redirect config for authorization_code flow.")
                return

            # PKCE: generate a code verifier and challenge
            code_verifier = secrets.token_urlsafe(64)
            code_verifier = code_verifier[:128]
            code_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("utf-8")).digest()
            ).decode("utf-8").rstrip("=")

            # Build consent URL
            state = secrets.token_urlsafe(16)
            params = {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "scope": scope,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256"
            }
            consent_url = auth_url + "?" + urllib.parse.urlencode(params)

            # Local HTTP server to capture the redirect with code
            code_container = {"code": None, "state": None}

            class OAuthHandler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    qs = urllib.parse.urlparse(self.path).query
                    params = urllib.parse.parse_qs(qs)
                    code = params.get("code", [None])[0]
                    st = params.get("state", [None])[0]
                    code_container["code"] = code
                    code_container["state"] = st
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"Authorization received. You can close this window.")

            parsed = urllib.parse.urlparse(redirect_uri)
            server_address = (parsed.hostname, parsed.port)

            httpd = socketserver.TCPServer(server_address, OAuthHandler)

            def _serve():
                try:
                    httpd.handle_request()
                except Exception:
                    pass

            t = threading.Thread(target=_serve, daemon=True)
            t.start()

            logging.info(f"Opening browser for Schwab authorization: {consent_url}")
            webbrowser.open(consent_url)

            # Wait for redirect or timeout
            waited = 0
            while waited < timeout_seconds and code_container["code"] is None:
                time.sleep(1)
                waited += 1

            httpd.server_close()

            code = code_container.get("code")
            if not code:
                logging.error("Authorization code not received within timeout period.")
                return

            # Exchange code for token using PKCE verifier
            try:
                token_data = {
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "code_verifier": code_verifier
                }
                if client_secret:
                    token_data["client_secret"] = client_secret

                token_res = requests.post(
                    self.config["token_url"],
                    data=token_data,
                    timeout=15
                )
                if token_res.status_code == 200:
                    self.access_token = token_res.json().get("access_token")
                else:
                    logging.error(f"Schwab token exchange failed: HTTP {token_res.status_code} / {token_res.text}")
            except Exception as e:
                logging.error(f"Error exchanging authorization code for token: {e}")
            return

        # Fallback: client_credentials (may not be supported for retail accounts)
        url = self.config["token_url"]
        payload = {
            'grant_type': 'client_credentials',
            'scope': self.config.get("requested_scopes")
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        try:
            response = requests.post(
                url, data=payload, headers=headers,
                auth=(os.getenv("SCHWAB_CLIENT_ID"), os.getenv("SCHWAB_CLIENT_SECRET")),
                timeout=10
            )
            if response.status_code == 200:
                self.access_token = response.json().get("access_token")
            else:
                logging.error(f"Schwab Authorization Pipeline failure: HTTP Status Code {response.status_code}")
        except Exception as e:
            logging.error(f"Critical execution connection error during Schwab handshake sequence: {e}")

    def perform_token_handshake(self, timeout_seconds: int = 180) -> bool:
        """Performs a non-destructive PKCE auth code handshake without placing any orders."""
        logging.info("Starting Schwab PKCE token-only handshake.")
        self._refresh_oauth_token(timeout_seconds=timeout_seconds)
        if self.access_token:
            logging.info("Schwab PKCE handshake completed successfully.")
            return True
        logging.error("Schwab PKCE handshake failed; no access token was obtained.")
        return False

    def execute_order(self, ticker: str, instruction: str) -> bool:
        """Constructs and passes execution trade payloads directly to Schwab Retail Gateways."""
        if not self.config.get("enable_live_trades", False):
            logging.warning("Schwab live trading disabled via config. Sandbox simulation mode active.")
            return True

        if requests is None:
            logging.error("Requests library unavailable; cannot execute Schwab order.")
            return False

        if not self.access_token:
            self._refresh_oauth_token()
            if not self.access_token:
                logging.error("Unable to obtain Schwab access token. Order not executed.")
                return False

        logging.info(f"API INSTRUCTION SENT: Transmitting {instruction} action for {ticker} over Schwab Portal.")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "orderType": "MARKET",
            "session": "NORMAL",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [{
                "instruction": instruction,
                "quantity": 1,
                "instrument": {"symbol": ticker, "assetType": "EQUITY"}
            }]
        }

        try:
            res = requests.post(
                f"{self.base_url}/accounts/{self.account_id}/orders",
                json=payload,
                headers=headers,
                timeout=15
            )
            if res.status_code in [200, 201, 202]:
                return True
            logging.error(f"Schwab order failed: HTTP {res.status_code} / {res.text}")
            return False
        except Exception as e:
            logging.error(f"Schwab order execution error: {e}")
            return False

# Lazy singleton initialization pattern
_schwab_broker = None

def get_schwab_broker():
    global _schwab_broker
    if _schwab_broker is None:
        _schwab_broker = SchwabExecutionClient()
    return _schwab_broker

def execute_portfolio_rebalance(current_holdings: list, config: dict) -> list:
    """MISSING-9 IMPLEMENTED: Liquidation pass drops tracking validation for decaying assets."""
    if not config.get("portfolio_management", {}).get("sell_losers", False):
        return current_holdings

    retained_portfolio = []
    sell_threshold = config["portfolio_management"].get("sell_trigger_threshold", 0.40)
    
    logging.info(f"Evaluating portfolio quality metrics across {len(current_holdings)} active holdings.")

    for ticker in current_holdings:
        data = safe_fetch_data(get_ticker_data, ticker)
        if data is None:
            retained_portfolio.append(ticker) # Safe-side hold if external network endpoints fail
            continue
            
        val_score = valuation_model(data)
        viable = ml_decision(data, val_score, threshold=sell_threshold)
        
        if viable:
            retained_portfolio.append(ticker)
        else:
            logging.warning(f"LIQUIDATION PASS ACTION: {ticker} score decayed. Routing a liquidation order.")
            if get_schwab_broker().execute_order(ticker, "SELL"):
                logging.info(f"Successfully closed exposure position for asset: {ticker}")
            else:
                retained_portfolio.append(ticker) # Keep tracking local allocation index if API execution errors occur
                
    return retained_portfolio

def run_portfolio_selection(ticker_dataset: list, kill_switch_event=None) -> list:
    """Main execution workflow pipeline loops (Brief Sec. 8)."""
    config = load_config()
    buy_threshold = config.get("ml", {}).get("buy_threshold", 0.55)
    max_workers = config.get("portfolio_management", {}).get("max_workers", 10)
    
    current_holdings = []
    current_cycle = 1
    max_protection_limit = 5 

    # RECURSION ERROR CORRECTED: Stateful while loop explicitly eliminates stack overflow vulnerability vectors
    while current_cycle <= max_protection_limit:
        if kill_switch_event and kill_switch_event.is_set():
            logging.warning("System termination flag received via app Kill Switch Event.")
            break
            
        logging.info(f"===== STARTING STATE ENGINE PASS CYCLE: {current_cycle} =====")
        
        # Step 1: Manage liquidation requirements across existing assets
        current_holdings = execute_portfolio_rebalance(current_holdings, config)
        
        # Step 2: Extract and process new asset targets
        unowned_candidates = [t for t in ticker_dataset if t not in current_holdings]
        if not unowned_candidates:
            logging.info("Every provided portfolio target is actively allocated. Loop complete.")
            break
            
        approved_buys = process_tickers_parallel(unowned_candidates, buy_threshold, max_workers)
        
        # Step 3: Run execution routers on new asset target purchases
        new_buys_count = 0
        for ticker in approved_buys:
            if get_schwab_broker().execute_order(ticker, "BUY"):
                current_holdings.append(ticker)
                new_buys_count += 1

        # Persist state parameters locally
        pd.DataFrame(current_holdings, columns=["ticker"]).to_csv("live_portfolio_state.csv", index=False)
        logging.info(f"Pipeline State Complete: Tracked Assets={len(current_holdings)} | Processed Buys={new_buys_count}")
        
        # Convergence Check: If composition stops shifting, safely exit the run
        if new_buys_count == 0:
            logging.info("Portfolio state equilibrium achieved. Exiting tracking loop cleanly.")
            break
            
        current_cycle += 1

    return current_holdings