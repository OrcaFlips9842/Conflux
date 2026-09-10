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
            SELECT
                id,
                name,
                address,
                enabled,
                date_added,
                last_updated,
                quality_score,
                total_trades,
                win_rate,
                sum_profits,
                trading_frequency,
                average_hold_time,
                p90_trade_size,
                average_trade_size,
                average_return,
                average_loss
            FROM investors
            WHERE id = ?
        """, (investor_id,))

        row = cursor.fetchone()
        db.close()

        if row is None:
            return None

        investor = Investor(
            investor_id=row[0],
            name=row[1],
            address=row[2],
            enabled=bool(row[3])
        )

        investor.date_added = row[4]
        investor.last_updated = row[5]
        investor.quality_score = row[6]
        investor.total_trades = row[7]
        investor.win_rate = row[8]
        investor.sum_profits = row[9]
        investor.trading_frequency = row[10]
        investor.average_hold_time = row[11]
        investor.p90_trade_size = row[12]
        investor.average_trade_size = row[13]
        investor.average_return = row[14]
        investor.average_loss = row[15]

        return investor
        
    def get_all_investors(self):
        db = sqlite3.connect(self.db_path)

        cursor = db.execute("""
            SELECT
                id,
                name,
                address,
                enabled,
                date_added,
                last_updated,
                quality_score,
                total_trades,
                win_rate,
                sum_profits,
                trading_frequency,
                average_hold_time,
                p90_trade_size,
                average_trade_size,
                average_return,
                average_loss
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

            investor.date_added = row[4]
            investor.last_updated = row[5]
            investor.quality_score = row[6]
            investor.total_trades = row[7]
            investor.win_rate = row[8]
            investor.sum_profits = row[9]
            investor.trading_frequency = row[10]
            investor.average_hold_time = row[11]
            investor.p90_trade_size = row[12]
            investor.average_trade_size = row[13]
            investor.average_return = row[14]
            investor.average_loss = row[15]

            investors.append(investor)

        return investors
    
    def save_investor(self, investor):
        db = sqlite3.connect(self.db_path)

        db.execute("""
            UPDATE investors
            SET
                name = ?,
                address = ?,
                enabled = ?,
                date_added = ?,
                last_updated = ?,
                quality_score = ?,
                total_trades = ?,
                win_rate = ?,
                sum_profits = ?,
                trading_frequency = ?,
                average_hold_time = ?,
                p90_trade_size = ?,
                average_trade_size = ?,
                average_return = ?,
                average_loss = ?
            WHERE id = ?
        """, (
            investor.name,
            investor.address,
            int(investor.enabled),
            investor.date_added,
            investor.last_updated,
            investor.quality_score,
            investor.total_trades,
            investor.win_rate,
            investor.sum_profits,
            investor.trading_frequency,
            investor.average_hold_time,
            investor.p90_trade_size,
            investor.average_trade_size,
            investor.average_return,
            investor.average_loss,
            investor.id
        ))

        db.commit()
        db.close()
        
    def delete_investor(self, investor_id):
        db = sqlite3.connect(self.db_path)

        db.execute("""
            DELETE FROM investors
            WHERE id = ?
        """, (investor_id,))

        db.commit()
        db.close()
        
    def investor_exists(self, address):
        db = sqlite3.connect(self.db_path)

        cursor = db.execute("""
            SELECT 1
            FROM investors
            WHERE address = ?
        """, (address,))

        exists = cursor.fetchone() is not None

        db.close()

        return exists
    
    def get_investor_by_address(self, address):
        db = sqlite3.connect(self.db_path)

        cursor = db.execute("""
            SELECT
                id,
                name,
                address,
                enabled,
                date_added,
                last_updated,
                quality_score,
                total_trades,
                win_rate,
                sum_profits,
                trading_frequency,
                average_hold_time,
                p90_trade_size,
                average_trade_size,
                average_return,
                average_loss
            FROM investors
            WHERE address = ?
        """, (address,))

        row = cursor.fetchone()
        db.close()

        if row is None:
            return None

        investor = Investor(
            investor_id=row[0],
            name=row[1],
            address=row[2],
            enabled=bool(row[3])
        )

        investor.date_added = row[4]
        investor.last_updated = row[5]
        investor.quality_score = row[6]
        investor.total_trades = row[7]
        investor.win_rate = row[8]
        investor.sum_profits = row[9]
        investor.trading_frequency = row[10]
        investor.average_hold_time = row[11]
        investor.p90_trade_size = row[12]
        investor.average_trade_size = row[13]
        investor.average_return = row[14]
        investor.average_loss = row[15]

        return investor