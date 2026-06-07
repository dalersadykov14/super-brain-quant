from logger_config import setup_logging
from portfolio_manager import run_portfolio_selection


def main():
    setup_logging()
    target_universe = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMD"]

    print("Starting sandbox simulation run...")
    final_portfolio = run_portfolio_selection(target_universe)
    print("Simulation complete.")
    print("Selected portfolio:", final_portfolio)


if __name__ == "__main__":
    main()
