import sqlite3
from pathlib import Path

from investoryManager import InvestorManager


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
            enabled INTEGER NOT NULL DEFAULT 1
        )
    """)

    db.commit()
    db.close()

# Make sure the database is ready
setup_database()


# Create manager
investor_manager = InvestorManager(DB_PATH)


investors = investor_manager.get_all_investors()

for investor in investors:
    print(investor)