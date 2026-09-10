class Investor:
    def __init__(self, investor_id, name, address, enabled=True):
        # Identity
        self.id = investor_id
        self.name = name
        self.address = address
        self.enabled = enabled
        self.date_added = None
        self.last_updated = None
        
        self.quality_score = 0

        # Trading performance
        self.total_trades = 0
        self.win_rate = 0
        self.sum_profits = 0

        # Trading behavior
        self.trading_frequency = 0
        self.average_hold_time = 0
        
        # Position sizing
        self.p90_trade_size = 0
        self.average_trade_size = 0

        self.average_return = 0
        self.average_loss = 0

    def __repr__(self):
        return f"Investor(id={self.id}, name='{self.name}', address='{self.address}')"