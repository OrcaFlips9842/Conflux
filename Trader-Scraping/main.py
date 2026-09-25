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
            capped_at_limit INTEGER DEFAULT 0,
            last_trade_timestamp INTEGER DEFAULT 0
        )
    """)

    db.commit()
    db.close()
setup_database()

# Create manager
investor_manager = InvestorManager(DB_PATH)

# --------------------------------------------------------------
# Single-wallet smoke test - no persistence, just a quick sanity check.
# For the real 100-wallet run (including incremental updates for wallets
# already in the db), use populate_investors.py instead.
# --------------------------------------------------------------

scraper = TraderScraper()

wallet = "GDnQ4uPb1WhLFpRqo2FqoWWQZAr4EfQtC3GK7xFWtcu5"

result = scraper.get_trades(wallet, days=21)
trades = result["trades"]

