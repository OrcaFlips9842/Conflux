import os
import sys

from pathlib import Path
from dotenv import load_dotenv

sys.path.append(str(Path(__file__).resolve().parent.parent))
from Trader_Scraping.investorManager import *

load_dotenv()
WS_URL = os.getenv("WS_URL")

manager = InvestorManager(db_path=Path(__file__).resolve().parent.parent / "Data" / "investors.db")

investors = manager.get_all_investors()

for i in investors:
    print(i, i.address)

print(len(investors))