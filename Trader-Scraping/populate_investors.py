import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from investorManager import InvestorManager
from traderScraper import TraderScraper
from metrics import apply_trades, derive_summary
from grading import calculate_quality_score

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "Data" / "investors.db"
WALLETS_CSV = Path(__file__).resolve().parent / "wallets.csv"  # columns: name,address

LOOKBACK_DAYS = 21            # used only the first time a wallet is added
MAX_RAW_TRANSACTIONS = 5000   # per-wallet, per-run cap - see traderScraper.py
SECONDS_BETWEEN_WALLETS = 0.5

STATE_FIELDS = [
    "wins", "losses", "sum_profits", "hold_time_sum",
    "trade_size_sum", "return_sum", "loss_sum",
    "trade_sizes", "open_positions",
]


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
    with open(csv_path, newline="") as f:
        return [(row["name"], row["address"]) for row in csv.DictReader(f)]


def elapsed_days(date_added_iso):
    added = datetime.fromisoformat(date_added_iso)
    now = datetime.now(timezone.utc)
    return max((now - added).total_seconds() / 86400, 1)


def main():
    investor_manager = InvestorManager(DB_PATH)
    scraper = TraderScraper()
    sol_price = get_sol_price_usd()

    wallets = load_wallets(WALLETS_CSV)
    print(f"Loaded {len(wallets)} candidate wallets from {WALLETS_CSV}")

    now = datetime.now(timezone.utc).isoformat()

    for name, address in wallets:
        print(f"\n--- {name} ({address}) ---")

        investor = investor_manager.get_investor_by_address(address)

        if investor is None:
            # First time seeing this wallet - full lookback pull.
            investor = investor_manager.create_investor(name, address)
            investor.date_added = now
            since, days = None, LOOKBACK_DAYS
        else:
            # Already tracked - only pull what happened since last run.
            since = int(datetime.fromisoformat(investor.last_updated).timestamp())
            days = None

        try:
            result = scraper.get_trades(
                address, days=days, since=since, max_raw_transactions=MAX_RAW_TRANSACTIONS
            )
        except Exception as e:
            print(f"Failed to pull trades: {e}")
            continue

        new_trades = result["trades"]
        #print(f"Found {len(new_trades)} new swap legs" + (" (hit fetch cap)" if result["capped"] else ""))

        state = {field: getattr(investor, field) for field in STATE_FIELDS}
        state = apply_trades(state, new_trades, sol_price_usd=sol_price)

        for field in STATE_FIELDS:
            setattr(investor, field, state[field])

        summary = derive_summary(state, elapsed_days(investor.date_added))
        for key, value in summary.items():
            setattr(investor, key, value)

        investor.capped_at_limit = investor.capped_at_limit or result["capped"]
        investor.last_updated = now
        investor.quality_score = calculate_quality_score(investor)

        investor_manager.save_investor(investor)

        print(
            f"wins={investor.wins} losses={investor.losses} "
            f"win_rate={investor.win_rate:.2f} sum_profits={investor.sum_profits:.3f} SOL "
            f"quality_score={investor.quality_score}"
        )

        time.sleep(SECONDS_BETWEEN_WALLETS)


if __name__ == "__main__":
    main()