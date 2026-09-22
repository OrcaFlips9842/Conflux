def apply_trades(state, trades, sol_price_usd=None):
    """
    Incrementally folds a batch of new trades into an existing running
    state. Works the same whether `state` is a fresh, empty state (a
    brand-new wallet) or one loaded from the investors table (an
    existing wallet being updated with only its newest trades) - that's
    what lets this run repeatedly while a live trading bot keeps
    trading, without re-fetching or re-processing full history each time.

    state keys: wins, losses, sum_profits, hold_time_sum, trade_size_sum,
    return_sum, loss_sum, trade_sizes (list), open_positions (dict).
    """

    open_positions = state.get("open_positions", {})
    wins = state.get("wins", 0)
    losses = state.get("losses", 0)
    sum_profits = state.get("sum_profits", 0)
    hold_time_sum = state.get("hold_time_sum", 0)
    trade_size_sum = state.get("trade_size_sum", 0)
    return_sum = state.get("return_sum", 0)
    loss_sum = state.get("loss_sum", 0)
    trade_sizes = state.get("trade_sizes", [])

    normalized = []
    for t in trades:
        amount = t["quote_amount"]
        if t["quote_symbol"] == "USDC" and sol_price_usd:
            amount = amount / sol_price_usd
        normalized.append({**t, "quote_sol": amount})

    normalized.sort(key=lambda t: t["timestamp"])

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
            pnl = proceeds - cost_basis
            return_pct = pnl / cost_basis if cost_basis else 0
            hold_time = t["timestamp"] - lot["timestamp"]

            if pnl > 0:
                wins += 1
                return_sum += return_pct
            else:
                losses += 1
                loss_sum += return_pct

            sum_profits += pnl
            hold_time_sum += hold_time
            trade_size_sum += cost_basis

            trade_sizes.append(cost_basis)
            if len(trade_sizes) > 5000:
                trade_sizes.pop(0)  # bounded, most-recent sample for percentile calc

            lot["amount"] -= matched_amount
            lot["cost"] -= cost_basis
            remaining -= matched_amount

            if lot["amount"] <= 1e-9:
                open_positions[token].pop(0)

        # Unmatched sell remainder (position opened before our tracked
        # history began) is dropped rather than guessed at.

    # Drop emptied-out token entries so open_positions doesn't grow forever
    open_positions = {k: v for k, v in open_positions.items() if v}

    return {
        "wins": wins,
        "losses": losses,
        "sum_profits": sum_profits,
        "hold_time_sum": hold_time_sum,
        "trade_size_sum": trade_size_sum,
        "return_sum": return_sum,
        "loss_sum": loss_sum,
        "trade_sizes": trade_sizes,
        "open_positions": open_positions,
    }


def derive_summary(state, elapsed_days):
    """
    Turns the running accumulators in `state` into the read-friendly
    fields the investors table stores (win_rate, averages, etc). Call
    this right after apply_trades(), any time before saving an investor.
    """
    total = state["wins"] + state["losses"]

    if total == 0:
        return {
            "win_rate": 0,
            "average_hold_time": 0,
            "average_trade_size": 0,
            "p90_trade_size": 0,
            "average_return": 0,
            "average_loss": 0,
            "trading_frequency": 0,
        }

    return {
        "win_rate": state["wins"] / total,
        "average_hold_time": state["hold_time_sum"] / total,
        "average_trade_size": state["trade_size_sum"] / total,
        "p90_trade_size": _percentile(state["trade_sizes"], 90) if state["trade_sizes"] else 0,
        "average_return": (state["return_sum"] / state["wins"]) if state["wins"] else 0,
        "average_loss": (state["loss_sum"] / state["losses"]) if state["losses"] else 0,
        "trading_frequency": total / max(elapsed_days, 1),
    }


def _percentile(values, pct):
    values = sorted(values)
    k = (len(values) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(values) - 1)
    if f == c:
        return values[f]
    return values[f] + (values[c] - values[f]) * (k - f)