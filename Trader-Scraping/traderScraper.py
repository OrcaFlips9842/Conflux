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

    def get_trades(self, address, days=30, batch_size=1):
        # batch_size=1 sends getTransaction calls one at a time. The
        # public RPC endpoint seems to rate-limit a batched request
        # (several calls in one HTTP POST) harder than the same calls
        # sent sequentially - bump this back up to 5-10 once you're on
        # a dedicated RPC provider instead of the public endpoint.
        cutoff = int(time.time()) - (days * 24 * 60 * 60)

        signatures = self._get_signatures_since(address, cutoff)

        trades = []
        for i in range(0, len(signatures), batch_size):
            batch = signatures[i:i + batch_size]
            requests_list = [
                ("getTransaction", [
                    sig,
                    {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
                ])
                for sig in batch
            ]
            results = self.rpc.call_batch(requests_list)

            for sig, tx in zip(batch, results):
                if tx is None:
                    continue
                trade = self._extract_swap(address, sig, tx)
                if trade:
                    trades.append(trade)

        trades.sort(key=lambda t: t["timestamp"])
        return trades

    def _get_signatures_since(self, address, cutoff):
        signatures = []
        before = None

        while True:
            page = self.rpc.get_signatures_for_address(address, before=before, limit=1000)

            if not page:
                break

            stop = False
            for entry in page:
                block_time = entry.get("blockTime")
                if block_time is None or block_time < cutoff:
                    stop = True
                    break
                if entry.get("err") is None:
                    signatures.append(entry["signature"])

            if stop or len(page) < 1000:
                break

            before = page[-1]["signature"]

        return signatures

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