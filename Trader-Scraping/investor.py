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
        self.wins = 0
        self.losses = 0
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

        
        #Running information variables
        self.hold_time_sum = 0
        self.trade_size_sum = 0
        self.return_sum = 0  
        self.loss_sum = 0     
        
        self.trade_sizes = []
        self.open_positions = {}

        self.capped_at_limit = False
     
    @property
    def total_trades(self):
        return self.wins + self.losses   
        
    def __repr__(self):
        return f"Investor(id={self.id}, name='{self.name}', address='{self.address}')"