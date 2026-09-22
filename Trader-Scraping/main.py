import sqlite3
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from investorManager import InvestorManager
from traderScraper import TraderScraper
from metrics import apply_trades, derive_summary

from grading import calculate_quality_score
from investor import Investor

# Database location
PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "Data" / "investors.db"


# Create database tables
def setup_database():
    db = sqlite3.connect(DB_PATH)
 
    db.execute("""
        CREATE TABLE IF NOT EXISTS investors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL UNIQUE,
            enabled INTEGER NOT NULL DEFAULT 1,
 
            date_added TEXT,
            last_updated TEXT,
 
            quality_score REAL DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            sum_profits REAL DEFAULT 0,
            trading_frequency REAL DEFAULT 0,
            average_hold_time REAL DEFAULT 0,
            p90_trade_size REAL DEFAULT 0,
            average_trade_size REAL DEFAULT 0,
            average_return REAL DEFAULT 0,
            average_loss REAL DEFAULT 0,
            win_rate REAL DEFAULT 0,
 
            hold_time_sum REAL DEFAULT 0,
            trade_size_sum REAL DEFAULT 0,
            return_sum REAL DEFAULT 0,
            loss_sum REAL DEFAULT 0,
            trade_sizes_json TEXT DEFAULT '[]',
            open_positions_json TEXT DEFAULT '{}',
            capped_at_limit INTEGER DEFAULT 0
        )
    """)
 
    db.commit()
    db.close()
setup_database()
 
# Create manager
investor_manager = InvestorManager(DB_PATH)


# Main Code
# --------------------------------------------------------------
# This is now just a single-wallet smoke test - no API key needed,
# since TraderScraper talks to a Solana RPC node directly. For the
# real 100-wallet population run, use populate_investors.py instead,
# which does this same get_trades -> calculate_metrics -> save loop
# for every wallet in wallets.csv.
# --------------------------------------------------------------

scraper = TraderScraper()

wallet = "C4Svaa7djC8d3CVxaohrsedccaKqimNoJrWe9iNPdix5"

result = scraper.get_trades(wallet, days=21)
trades = result["trades"]

print(f"Found {len(trades)} swap legs" + (" (hit fetch cap)" if result["capped"] else ""))
 
for trade in trades:
    print("==============================")
    print("TX:", trade["tx_hash"])
    print("SIDE:", trade["side"])
    print("TOKEN:", trade["token"])
    print("TOKEN AMOUNT:", trade["token_amount"])
    print(f"QUOTE: {trade['quote_amount']} {trade['quote_symbol']}")
 
state = apply_trades(
    {"wins": 0, "losses": 0, "sum_profits": 0, "hold_time_sum": 0,
     "trade_size_sum": 0, "return_sum": 0, "loss_sum": 0,
     "trade_sizes": [], "open_positions": {}},
    trades
)
summary = derive_summary(state, elapsed_days=21)
 
print("\n--- METRICS ---")
print(f"wins: {state['wins']}")
print(f"losses: {state['losses']}")
print(f"sum_profits: {state['sum_profits']}")
for key, value in summary.items():
    print(f"{key}: {value}")
 
# calculate_quality_score() reads investor.wins/losses/win_rate/etc off an
# Investor object, not a raw dict - build a throwaway one from this run's
# state/summary just to grade it. This isn't saved anywhere; for real
# grading tied to a db row, use populate_investors.py.
investor = Investor(investor_id=None, name="smoke-test", address=wallet)
for field, value in state.items():
    setattr(investor, field, value)
for field, value in summary.items():
    setattr(investor, field, value)
investor.capped_at_limit = result["capped"]
 
print(f"\nquality_score: {calculate_quality_score(investor)}")