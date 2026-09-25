import csv
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
load_dotenv()

from investorManager import InvestorManager
from traderScraper import TraderScraper
from metrics import apply_trades, derive_summary
from grading import calculate_quality_score

PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "Data" / "investors.db"
WALLETS_CSV = Path(__file__).resolve().parent / "wallets.csv"  # columns: name,address

LOOKBACK_DAYS = 30            # used only the first time a wallet is added
MAX_RAW_TRANSACTIONS = 5000   # per-wallet, per-run cap - see traderScraper.py
SECONDS_BETWEEN_WALLETS = 0.5

UPDATE_EXISTING = False   # set True to re-pull/re-score wallets already in the db
TOP_COUNT = 100           # ranks 1..TOP_COUNT stay enabled
BENCH_COUNT = 50          # ranks TOP_COUNT+1..TOP_COUNT+BENCH_COUNT are kept, disabled
                          # anyone ranked below that gets deleted from the db entirely

STATE_FIELDS = [
    "wins", "losses", "sum_profits", "hold_time_sum",
    "trade_size_sum", "return_sum", "loss_sum",
    "trade_sizes", "open_positions", "last_trade_timestamp",
]


def empty_state():
    # A fresh dict with its own new list/dict every call - NOT a shared
    # constant. apply_trades mutates open_positions/trade_sizes in place,
    # so reusing the same nested objects across different wallets would
    # silently corrupt one wallet's data with another's.
    return {
        "wins": 0, "losses": 0, "sum_profits": 0, "hold_time_sum": 0,
        "trade_size_sum": 0, "return_sum": 0, "loss_sum": 0,
        "trade_sizes": [], "open_positions": {}, "last_trade_timestamp": 0,
    }


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
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        return [(row["name"], row["address"]) for row in csv.DictReader(f)]


def elapsed_days(date_added_iso):
    added = datetime.fromisoformat(date_added_iso)
    now = datetime.now(timezone.utc)
    return max((now - added).total_seconds() / 86400, 1)


def finalize_leaderboard(investor_manager):
    """
    Re-ranks the ENTIRE investors table (not just wallets touched this
    run) by quality_score, descending:
      - rank 1..TOP_COUNT: enabled
      - rank TOP_COUNT+1..TOP_COUNT+BENCH_COUNT: kept, but disabled
      - anyone ranked lower: deleted outright

    This keeps the db an exact, precise leaderboard rather than an
    ever-growing pile of wallets - only the current top
    (TOP_COUNT + BENCH_COUNT) are ever kept.
    """
    investors = investor_manager.get_all_investors()
    investors.sort(key=lambda inv: inv.quality_score, reverse=True)

    active = 0
    benched = 0
    dropped = 0

    for rank, investor in enumerate(investors):
        if rank < TOP_COUNT:
            investor.enabled = True
            investor_manager.save_investor(investor)
            active += 1
        elif rank < TOP_COUNT + BENCH_COUNT:
            investor.enabled = False
            investor_manager.save_investor(investor)
            benched += 1
        else:
            investor_manager.delete_investor(investor.id)
            dropped += 1

    print(f"\nLeaderboard finalized: {active} active, {benched} benched, {dropped} dropped")


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

        if investor is not None and not UPDATE_EXISTING:
            print("Already tracked and UPDATE_EXISTING is False - skipping")
            continue

        is_new = investor is None
        since = None if is_new else int(datetime.fromisoformat(investor.last_updated).timestamp())
        days = LOOKBACK_DAYS if is_new else None

        try:
            result = scraper.get_trades(
                address, days=days, since=since, max_raw_transactions=MAX_RAW_TRANSACTIONS
            )
        except Exception as e:
            print(f"Failed to pull trades: {e}")
            continue

        new_trades = result["trades"]
        print(f"Found {len(new_trades)} new swap legs" + (" (hit fetch cap)" if result["capped"] else ""))

        # Start from either a fresh empty state (new wallet) or the
        # existing accumulators (wallet already tracked) - NOT from an
        # investor object yet, since we don't want to create/keep a row
        # at all if this wallet still has zero completed trades after
        # this pull. See the total==0 branch below.
        if is_new:
            starting_state = empty_state()
        else:
            starting_state = {field: getattr(investor, field) for field in STATE_FIELDS}
        state = apply_trades(starting_state, new_trades, sol_price_usd=sol_price)

        if state["wins"] + state["losses"] == 0:
            # No completed round-trip trades at all - either this pull
            # found nothing usable (e.g. hit the fetch cap on a wallet
            # whose trades don't fit our swap-detection pattern), or this
            # wallet has never had a matched buy+sell in our window (e.g.
            # a single big dump with no visible prior buy - exactly the
            # "one-hit rug pull" pattern this is meant to screen out).
            # A wallet with zero real signal gets no row at all.
            if is_new:
                print("No completed trades found - not adding to db")
            else:
                print("Still zero completed trades after update - removing from db")
                investor_manager.delete_investor(investor.id)
            continue

        if is_new:
            investor = investor_manager.create_investor(name, address)
            investor.date_added = now

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

    finalize_leaderboard(investor_manager)


if __name__ == "__main__":
    main()