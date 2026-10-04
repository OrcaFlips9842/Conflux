import time

from solanaRpcClient import SolanaRpcClient

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# Ignore dust deltas from rounding/rent
DUST_THRESHOLD = 1e-6


class TraderScraper:
    """
    Pulls swap history for a wallet directly from a Solana RPC node -
    no Birdeye/Helius enhanced-tx dependency - by diffing pre/post
    token and SOL balances on each transaction the wallet touched.

    This only recognizes simple two-leg swaps (one token in, one out,
    against SOL or USDC). Multi-hop routes or swaps against other
    quote tokens are skipped rather than mis-parsed.
    """

    def __init__(self, rpc_client=None):
        self.rpc = rpc_client or SolanaRpcClient()

    def get_trades(self, address, days=30, since=None, page_size=1000, max_raw_transactions=5000):
        """
        Pulls swap history for a wallet.

        - since: unix timestamp cursor (e.g. an investor's last_updated) -
          use this for incremental updates so only new activity is pulled.
          Takes priority over `days` when both are given.
        - days: used for a first-time/full pull when there's no `since`.
        - max_raw_transactions: hard cap on raw transactions fetched per
          call, regardless of how much history that covers. This is what
          actually protects your RPC credits from a high-frequency bot -
          it stops the pull itself, rather than fetching everything and
          truncating afterward. Once hit, `capped` comes back True and
          the returned trades only reflect the most recent activity up
          to the cap.

        Returns {"trades": [...], "capped": bool}.
        """
        cutoff = since if since is not None else int(time.time()) - (days * 24 * 60 * 60)

        trades = []
        pagination_token = None
        raw_count = 0
        capped = False

        while True:
            entries, pagination_token = self.rpc.get_transactions_for_address(
                address, limit=page_size, pagination_token=pagination_token
            )

            if not entries:
                break

            stop = False
            for entry in entries:
                raw_count += 1

                if raw_count > max_raw_transactions:
                    capped = True
                    stop = True
                    break

                block_time = entry.get("blockTime")
                if block_time is None or block_time < cutoff:
                    stop = True
                    break

                # entry shape: {slot, transactionIndex, blockTime, transaction, meta}
                # - same "transaction"/"meta" shape as the old getTransaction
                # result, so _extract_swap needs no changes.
                trade = self._extract_swap(address, entry.get("transaction", {}).get(
                    "signatures", [None]
                )[0], entry)
                if trade:
                    trades.append(trade)

            if stop or not pagination_token:
                break

        trades.sort(key=lambda t: t["timestamp"])
        return {"trades": trades, "capped": capped}

    def _extract_swap(self, address, signature, tx):
        try:
            meta = tx["meta"]
            message = tx["transaction"]["message"]
        except (KeyError, TypeError):
            return None

        if meta is None or meta.get("err") is not None:
            return None

        account_keys = [k["pubkey"] for k in message["accountKeys"]]
        if address not in account_keys:
            return None

        idx = account_keys.index(address)

        sol_delta = (meta["postBalances"][idx] - meta["preBalances"][idx]) / 1e9
        # Back out the network fee if this wallet paid it, so a tiny
        # fee-only movement doesn't get mistaken for trade size.
        if idx == 0:
            sol_delta += meta.get("fee", 0) / 1e9

        token_deltas = self._token_deltas(address, meta)

        # Fold a wrapped-SOL token account into the native SOL delta.
        sol_delta += token_deltas.pop(SOL_MINT, 0.0)
        usdc_delta = token_deltas.pop(USDC_MINT, 0.0)

        # Only handle the simple case: exactly one non-quote token moved.
        if len(token_deltas) != 1:
            return None

        token_mint, token_delta = next(iter(token_deltas.items()))

        if abs(token_delta) < DUST_THRESHOLD:
            return None

        if abs(sol_delta) >= abs(usdc_delta):
            quote_delta, quote_symbol = sol_delta, "SOL"
        else:
            quote_delta, quote_symbol = usdc_delta, "USDC"

        if abs(quote_delta) < DUST_THRESHOLD:
            return None

        block_time = tx.get("blockTime")
        if block_time is None:
            return None

        if token_delta > 0 and quote_delta < 0:
            side = "buy"
        elif token_delta < 0 and quote_delta > 0:
            side = "sell"
        else:
            return None

        return {
            "token": token_mint,           # symbol lookup is a separate, optional step
            "token_address": token_mint,
            "side": side,
            "token_amount": abs(token_delta),
            "quote_amount": abs(quote_delta),
            "quote_symbol": quote_symbol,
            "timestamp": block_time,
            "tx_hash": signature
        }

    def _token_deltas(self, address, meta):
        pre = {b["mint"]: b for b in (meta.get("preTokenBalances") or []) if b.get("owner") == address}
        post = {b["mint"]: b for b in (meta.get("postTokenBalances") or []) if b.get("owner") == address}

        deltas = {}
        for mint in set(pre) | set(post):
            pre_amt = float(pre[mint]["uiTokenAmount"]["uiAmount"] or 0) if mint in pre else 0.0
            post_amt = float(post[mint]["uiTokenAmount"]["uiAmount"] or 0) if mint in post else 0.0
            delta = post_amt - pre_amt
            if abs(delta) >= DUST_THRESHOLD:
                deltas[mint] = delta

        return deltas