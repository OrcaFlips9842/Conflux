import requests
import time


class TraderScraper:

    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://public-api.birdeye.so/trader/txs/seek_by_time"

    def get_trades(self, address, hours=24):

        current_time = int(time.time())
        after_time = current_time - (hours * 60 * 60)

        headers = {
            "X-API-KEY": self.api_key,
            "x-chain": "solana"
        }

        all_items = []
        offset = 0
        limit = 100

        while True:

            params = {
                "address": address,
                "after_time": after_time,
                "tx_type": "swap",
                "limit": limit,
                "offset": offset
            }

            response = requests.get(
                self.url,
                headers=headers,
                params=params
            )

            if not response.ok:
                print("Status:", response.status_code)
                print("Response:", response.text)

            response.raise_for_status()

            data = response.json()

            items = data["data"]["items"]
            all_items.extend(items)

            print(f"Loaded {len(items)} trades (total: {len(all_items)})")

            # Stop if there are no more pages
            if not data["data"]["has_next"]:
                break

            offset += limit

        # Put the collected items back into the same format
        return {
            "data": {
                "items": all_items,
                "has_next": False
            },
            "success": True
        }

    def parse_trades(self, data):

        items = data["data"]["items"]

        transactions = {}

        for item in items:
            tx_hash = item["tx_hash"]

            if tx_hash not in transactions:
                transactions[tx_hash] = []

            transactions[tx_hash].append(item)

        trades = []

        for tx_hash, items in transactions.items():

            trade = self._parse_transaction(tx_hash, items)

            if trade:
                trades.append(trade)

        return trades

    def _parse_transaction(self, tx_hash, items):

        for item in items:

            quote = item["quote"]
            base = item["base"]

            quote_symbol = quote["symbol"].strip()
            base_symbol = base["symbol"].strip()

            # BUY
            if (
                quote["type_swap"] == "from"
                and base["type_swap"] == "to"
                and quote_symbol in ["SOL", "USDC"]
            ):
                return {
                    "token": base_symbol,
                    "token_address": base["address"],
                    "side": "buy",
                    "token_amount": base["ui_amount"],
                    "usd_value": item["volume_usd"],
                    "price": base["price"],
                    "timestamp": item["block_unix_time"],
                    "tx_hash": tx_hash
                }

            # SELL
            if (
                quote["type_swap"] == "to"
                and base["type_swap"] == "from"
                and quote_symbol in ["SOL", "USDC"]
            ):
                return {
                    "token": base_symbol,
                    "token_address": base["address"],
                    "side": "sell",
                    "token_amount": base["ui_amount"],
                    "usd_value": item["volume_usd"],
                    "price": base["price"],
                    "timestamp": item["block_unix_time"],
                    "tx_hash": tx_hash
                }

        return None