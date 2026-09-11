import sqlite3
from pathlib import Path

import os
from dotenv import load_dotenv
load_dotenv()

from investorManager import InvestorManager
from traderScraper import TraderScraper

API_KEY = os.getenv("BIRDEYE_API_KEY")

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
            total_trades INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0,
            sum_profits REAL DEFAULT 0,
            trading_frequency REAL DEFAULT 0,
            average_hold_time REAL DEFAULT 0,
            p90_trade_size REAL DEFAULT 0,
            average_trade_size REAL DEFAULT 0,
            average_return REAL DEFAULT 0,
            average_loss REAL DEFAULT 0
        )
    """)

    db.commit()
    db.close()
setup_database()

# Create manager
investor_manager = InvestorManager(DB_PATH)

scraper = TraderScraper(API_KEY)
trades = scraper.get_trades(
    "DAqCpTpQN1JNCDYLXWir28q1J2eXSufiNNADsSnUQTBZ",
    hours=24 * 7
)
parsed_trades = scraper.parse_trades(trades)

for trade in parsed_trades:
    print(trade)