import sqlite3
from investor import Investor

class InvestorManager:
    def __init__(self, db_path):
        self.db_path = db_path

    def create_investor(self, name, address):
        db = sqlite3.connect(self.db_path)

        cursor = db.execute("""
            INSERT INTO investors (name, address)
            VALUES (?, ?)
        """, (name, address))

        investor_id = cursor.lastrowid

        db.commit()
        db.close()

        return Investor(
            investor_id=investor_id,
            name=name,
            address=address
        )
    
    def get_investor(self, investor_id):
        db = sqlite3.connect(self.db_path)

        cursor = db.execute("""
            SELECT id, name, address, enabled
            FROM investors
            WHERE id = ?
        """, (investor_id,))

        row = cursor.fetchone()

        db.close()

        if row is None:
            return None

        return Investor(
            investor_id=row[0],
            name=row[1],
            address=row[2],
            enabled=bool(row[3])
        )
        
    def get_all_investors(self):
        db = sqlite3.connect(self.db_path)

        cursor = db.execute("""
            SELECT id, name, address, enabled
            FROM investors
            ORDER BY id
        """)

        rows = cursor.fetchall()

        db.close()

        investors = []

        for row in rows:
            investor = Investor(
                investor_id=row[0],
                name=row[1],
                address=row[2],
                enabled=bool(row[3])
            )

            investors.append(investor)

        return investors