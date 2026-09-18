import requests

class TraderScraper:

    SOL_MINT = "So11111111111111111111111111111111111111112"
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.helius.xyz/v0/addresses/{}/transactions"

    def get_trades(self, address, limit=100):

        url = self.url.format(address)

        params = {
            "api-key": self.api_key,
            "limit": limit
        }

        response = requests.get(url, params=params)

        if not response.ok:
            print("Status:", response.status_code)
            print("Response:", response.text)

        response.raise_for_status()

        return response.json()
    
    def parse_transaction(self, wallet, transaction):

        token_changes = {}

        for transfer in transaction.get("tokenTransfers", []):

            mint = transfer.get("mint")
            amount = transfer.get("tokenAmount", 0)

            if not mint or not amount:
                continue

            if transfer.get("fromUserAccount") == wallet:
                token_changes[mint] = token_changes.get(mint, 0) - amount

            if transfer.get("toUserAccount") == wallet:
                token_changes[mint] = token_changes.get(mint, 0) + amount

        return {
            "signature": transaction["signature"],
            "timestamp": transaction["timestamp"],
            "type": transaction["type"],
            "source": transaction["source"],
            "native_change": transaction.get("feePayer") == wallet,
            "token_changes": token_changes
        }