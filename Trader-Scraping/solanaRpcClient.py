import random
import time

import requests


class SolanaRpcClient:
    """
    Minimal JSON-RPC client for Solana with basic rate limiting and
    retry/backoff. Works against the free public RPC endpoint or any
    other RPC URL (Helius, Shyft, QuickNode, etc.) - swap rpc_url if
    the public endpoint ends up throttling too hard for your volume.
    """

    def __init__(self, rpc_url="https://rpc.ankr.com/solana",
                 min_interval=0.5, max_retries=6):
        self.rpc_url = rpc_url
        self.min_interval = min_interval  # seconds between requests
        self.max_retries = max_retries
        self._last_call = 0.0

    def _throttle(self):
        elapsed = time.time() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.time()

    def _call(self, method, params):
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}

        for attempt in range(self.max_retries):
            self._throttle()

            response = requests.post(self.rpc_url, json=payload, timeout=30)

            if response.status_code == 429:
                wait = (2 ** attempt) + random.random()
                print(f"Rate limited, backing off {wait:.1f}s...")
                time.sleep(wait)
                continue

            response.raise_for_status()
            data = response.json()

            if "error" in data:
                raise RuntimeError(f"RPC error calling {method}: {data['error']}")

            return data["result"]

        raise RuntimeError(f"Exceeded max retries calling {method}")

    def call_batch(self, requests_list):
        """
        requests_list: list of (method, params) tuples.
        Returns results in the same order. Falls back to sequential
        calls if the RPC endpoint doesn't support batching well.
        """
        payload = [
            {"jsonrpc": "2.0", "id": i, "method": m, "params": p}
            for i, (m, p) in enumerate(requests_list)
        ]

        self._throttle()

        try:
            response = requests.post(self.rpc_url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            data.sort(key=lambda r: r["id"])
            return [r.get("result") for r in data]
        except Exception:
            return [self._call(m, p) for m, p in requests_list]

    def get_signatures_for_address(self, address, before=None, limit=1000):
        params = [address, {"limit": limit}]
        if before:
            params[1]["before"] = before
        return self._call("getSignaturesForAddress", params)

    def get_transaction(self, signature):
        params = [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
        return self._call("getTransaction", params)