import json
import sqlite3

from investor import Investor

INVESTOR_COLUMNS = """
    id, name, address, enabled, date_added, last_updated,
    quality_score, wins, losses, sum_profits, trading_frequency,
    average_hold_time, p90_trade_size, average_trade_size,
    average_return, average_loss, win_rate,
    hold_time_sum, trade_size_sum, return_sum, loss_sum,
    trade_sizes_json, open_positions_json, capped_at_limit
"""


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
        cursor = db.execute(f"SELECT {INVESTOR_COLUMNS} FROM investors WHERE id = ?", (investor_id,))
        row = cursor.fetchone()
        db.close()
        return self._row_to_investor(row) if row else None

    def get_all_investors(self):
        db = sqlite3.connect(self.db_path)
        cursor = db.execute(f"SELECT {INVESTOR_COLUMNS} FROM investors ORDER BY id")
        rows = cursor.fetchall()
        db.close()
        return [self._row_to_investor(row) for row in rows]

    def get_investor_by_address(self, address):
        db = sqlite3.connect(self.db_path)
        cursor = db.execute(f"SELECT {INVESTOR_COLUMNS} FROM investors WHERE address = ?", (address,))
        row = cursor.fetchone()
        db.close()
        return self._row_to_investor(row) if row else None

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
                wins = ?,
                losses = ?,
                sum_profits = ?,
                trading_frequency = ?,
                average_hold_time = ?,
                p90_trade_size = ?,
                average_trade_size = ?,
                average_return = ?,
                average_loss = ?,
                win_rate = ?,
                hold_time_sum = ?,
                trade_size_sum = ?,
                return_sum = ?,
                loss_sum = ?,
                trade_sizes_json = ?,
                open_positions_json = ?,
                capped_at_limit = ?
            WHERE id = ?
        """, (
            investor.name,
            investor.address,
            int(investor.enabled),
            investor.date_added,
            investor.last_updated,
            investor.quality_score,
            investor.wins,
            investor.losses,
            investor.sum_profits,
            investor.trading_frequency,
            investor.average_hold_time,
            investor.p90_trade_size,
            investor.average_trade_size,
            investor.average_return,
            investor.average_loss,
            investor.win_rate,
            investor.hold_time_sum,
            investor.trade_size_sum,
            investor.return_sum,
            investor.loss_sum,
            json.dumps(investor.trade_sizes),
            json.dumps(investor.open_positions),
            int(investor.capped_at_limit),
            investor.id
        ))

        db.commit()
        db.close()

    def delete_investor(self, investor_id):
        db = sqlite3.connect(self.db_path)
        db.execute("DELETE FROM investors WHERE id = ?", (investor_id,))
        db.commit()
        db.close()

    def investor_exists(self, address):
        db = sqlite3.connect(self.db_path)
        cursor = db.execute("SELECT 1 FROM investors WHERE address = ?", (address,))
        exists = cursor.fetchone() is not None
        db.close()
        return exists

    def _row_to_investor(self, row):
        investor = Investor(
            investor_id=row[0],
            name=row[1],
            address=row[2],
            enabled=bool(row[3])
        )

        investor.date_added = row[4]
        investor.last_updated = row[5]
        investor.quality_score = row[6]
        investor.wins = row[7]
        investor.losses = row[8]
        investor.sum_profits = row[9]
        investor.trading_frequency = row[10]
        investor.average_hold_time = row[11]
        investor.p90_trade_size = row[12]
        investor.average_trade_size = row[13]
        investor.average_return = row[14]
        investor.average_loss = row[15]
        investor.win_rate = row[16]
        investor.hold_time_sum = row[17]
        investor.trade_size_sum = row[18]
        investor.return_sum = row[19]
        investor.loss_sum = row[20]
        investor.trade_sizes = json.loads(row[21]) if row[21] else []
        investor.open_positions = json.loads(row[22]) if row[22] else {}
        investor.capped_at_limit = bool(row[23])

        return investor