import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from investorManager import InvestorManager
from traderScraper import TraderScraper
from metrics import calculate_metrics

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "Data" / "investors.db"
WALLETS_CSV = Path(__file__).resolve().parent / "wallets.csv"  # columns: name,address

LOOKBACK_DAYS = 30
SECONDS_BETWEEN_WALLETS = 1.0  # be polite to the public RPC endpoint


def get_sol_price_usd():
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "solana", "vs_currencies": "usd"},
            timeout=10
        )
        resp.raise_for_status()
        return resp.json()["solana"]["usd"]
    except Exception as e:
        print(f"Could not fetch SOL price ({e}); USDC trades won't be normalized into SOL.")
        return None


def load_wallets(csv_path):
    wallets = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            wallets.append((row["name"], row["address"]))
    return wallets


def main():
    investor_manager = InvestorManager(DB_PATH)
    scraper = TraderScraper()
    sol_price = get_sol_price_usd()

    wallets = load_wallets(WALLETS_CSV)
    print(f"Loaded {len(wallets)} candidate wallets from {WALLETS_CSV}")

    for name, address in wallets:
        print(f"\n--- {name} ({address}) ---")

        if investor_manager.investor_exists(address):
            print("Already in DB, skipping (delete the row first to re-pull).")
            continue

        try:
            trades = scraper.get_trades(address, days=LOOKBACK_DAYS)
        except Exception as e:
            print(f"Failed to pull trades: {e}")
            continue

        print(f"Found {len(trades)} swap legs in the last {LOOKBACK_DAYS} days")

        metrics = calculate_metrics(trades, sol_price_usd=sol_price)

        investor = investor_manager.create_investor(name, address)

        now = datetime.now(timezone.utc).isoformat()
        investor.date_added = now
        investor.last_updated = now

        if metrics:
            for key, value in metrics.items():
                setattr(investor, key, value)
            print(
                f"win_rate={metrics['win_rate']:.2f} "
                f"trades={metrics['total_trades']} "
                f"sum_profits={metrics['sum_profits']:.3f} SOL"
            )
        else:
            print("Not enough completed round-trip trades in this window to score.")

        investor_manager.save_investor(investor)

        time.sleep(SECONDS_BETWEEN_WALLETS)


if __name__ == "__main__":
    main()
