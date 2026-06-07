import logging
from portfolio_manager import SchwabExecutionClient


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    print("Starting Schwab token-only PKCE handshake test.")

    client = SchwabExecutionClient()
    success = client.perform_token_handshake()

    if success:
        print("SUCCESS: Received Schwab access token.")
        print("Access token prefix:", client.access_token[:10] + "..." if client.access_token else "<none>")
    else:
        print("FAILURE: Token handshake did not complete.")


if __name__ == "__main__":
    main()
