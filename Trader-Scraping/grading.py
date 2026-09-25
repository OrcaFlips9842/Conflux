"""
First-pass quality scoring. This is intentionally a simple, tunable
starting point - not a final answer - so revisit the weights below once
you've seen it run across real Vybe-sourced wallets.
"""

import time

MIN_SAMPLE_SIZE = 30          # completed trades needed for full confidence
TARGET_PAYOFF_RATIO = 3.0     # average_return / abs(average_loss) considered "excellent"
CAPPED_PENALTY = 0.7          # multiplier applied if the wallet hit the raw-tx fetch cap
RECENCY_WINDOW_DAYS = 3       # score decays to 0 by this many days of inactivity -
                               # scoring-only, no hard db cutoff (even good traders
                               # take breaks; this just costs them rank, not a slot)


def calculate_quality_score(investor):
    """
    Returns a 0-100 score, combining:
      - win rate (up to 40 pts)
      - payoff ratio - how much bigger wins are than losses (up to 40 pts)
      - a sample-size confidence multiplier, so a wallet with 3 trades and
        one lucky 100x doesn't outrank a consistent 200-trade wallet
      - a recency multiplier, so a wallet that made one big trade weeks
        ago and has gone quiet since (the "rug and vanish" pattern) fades
        toward 0 even if its historical numbers look great. This decays
        sharply rather than linearly - a day or two quiet costs some
        rank, several days quiet costs most of it, but nobody is ever
        hard-removed just for taking a short break
      - a penalty if the wallet hit the raw-transaction fetch cap, since
        that usually means a high-frequency bot and/or an incomplete
        (most-recent-only) view of its history
    """
    total_trades = investor.wins + investor.losses

    if total_trades == 0:
        return 0

    win_rate_score = investor.win_rate * 40

    if investor.average_loss < 0:
        payoff_ratio = investor.average_return / abs(investor.average_loss)
    else:
        payoff_ratio = investor.average_return  # no losses on record yet

    payoff_score = min(payoff_ratio / TARGET_PAYOFF_RATIO, 1) * 40 if payoff_ratio > 0 else 0

    confidence = min(total_trades / MIN_SAMPLE_SIZE, 1)

    score = (win_rate_score + payoff_score) * confidence

    days_since_last_trade = (time.time() - investor.last_trade_timestamp) / 86400 if investor.last_trade_timestamp else float("inf")
    recency = max(0.0, 1 - (days_since_last_trade / RECENCY_WINDOW_DAYS)) ** 2
    score *= recency

    if investor.capped_at_limit:
        score *= CAPPED_PENALTY

    return round(max(score, 0), 2)