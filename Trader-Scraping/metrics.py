import statistics


def calculate_metrics(trades, sol_price_usd=None):
    """
    trades: list of dicts as returned by TraderScraper.get_trades(),
    all for a single wallet.

    sol_price_usd: optional current SOL/USD price. If given, USDC-quoted
    trades are converted to SOL-equivalent using this single snapshot
    rate so everything nets out in one unit. This is a rough
    approximation (one price applied across the whole window) - fine
    for an initial pass, not for precise historical PnL.

    Returns a dict matching the numeric columns on the investors table,
    or None if there weren't enough completed round-trip trades to
    score yet. Position matching is FIFO per token.
    """

    normalized = []
    for t in trades:
        amount = t["quote_amount"]
        if t["quote_symbol"] == "USDC" and sol_price_usd:
            amount = amount / sol_price_usd
        normalized.append({**t, "quote_sol": amount})

    normalized.sort(key=lambda t: t["timestamp"])

    open_positions = {}   # token -> list of {amount, cost, timestamp}
    closed_trades = []    # completed round trips

    for t in normalized:
        token = t["token"]
        open_positions.setdefault(token, [])

        if t["side"] == "buy":
            open_positions[token].append({
                "amount": t["token_amount"],
                "cost": t["quote_sol"],
                "timestamp": t["timestamp"]
            })
            continue

        # sell: match against open lots, FIFO
        remaining = t["token_amount"]
        proceeds_per_unit = t["quote_sol"] / t["token_amount"] if t["token_amount"] else 0

        while remaining > 1e-9 and open_positions[token]:
            lot = open_positions[token][0]
            matched_amount = min(remaining, lot["amount"])

            cost_per_unit = lot["cost"] / lot["amount"] if lot["amount"] else 0
            cost_basis = cost_per_unit * matched_amount
            proceeds = proceeds_per_unit * matched_amount

            closed_trades.append({
                "size": cost_basis,
                "pnl": proceeds - cost_basis,
                "return_pct": (proceeds - cost_basis) / cost_basis if cost_basis else 0,
                "hold_time": t["timestamp"] - lot["timestamp"]
            })

            lot["amount"] -= matched_amount
            lot["cost"] -= cost_basis
            remaining -= matched_amount

            if lot["amount"] <= 1e-9:
                open_positions[token].pop(0)

        # Any unmatched sell amount (e.g. position opened before our
        # lookback window) is dropped rather than guessed at.

    if not closed_trades:
        return None

    wins = [c for c in closed_trades if c["pnl"] > 0]
    losses = [c for c in closed_trades if c["pnl"] <= 0]
    trade_sizes = [c["size"] for c in closed_trades if c["size"] > 0]
    hold_times = [c["hold_time"] for c in closed_trades]

    span_days = max((normalized[-1]["timestamp"] - normalized[0]["timestamp"]) / 86400, 1)

    return {
        "total_trades": len(closed_trades),
        "win_rate": len(wins) / len(closed_trades),
        "sum_profits": sum(c["pnl"] for c in closed_trades),
        "trading_frequency": len(normalized) / span_days,
        "average_hold_time": statistics.mean(hold_times) if hold_times else 0,
        "p90_trade_size": _percentile(trade_sizes, 90) if trade_sizes else 0,
        "average_trade_size": statistics.mean(trade_sizes) if trade_sizes else 0,
        "average_return": statistics.mean([c["return_pct"] for c in wins]) if wins else 0,
        "average_loss": statistics.mean([c["return_pct"] for c in losses]) if losses else 0,
    }


def _percentile(values, pct):
    values = sorted(values)
    k = (len(values) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)
