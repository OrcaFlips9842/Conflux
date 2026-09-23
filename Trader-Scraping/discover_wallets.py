import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

VYBE_API_KEY = os.getenv("VYBE_API_KEY")
VYBE_BASE_URL = "https://api.vybenetwork.xyz/v4"

OUTPUT_CSV = Path(__file__).resolve().parent / "wallets.csv"

RESOLUTION = "30d"    # matches the ~month lookback used elsewhere in this project
PAGE_SIZE = 1000       # Vybe's max results per request
MIN_TRADES = 15        # drop wallets without enough of a track record to trust


def fetch_top_traders():
    all_traders = []
    page = 0

    while True:
        response = requests.get(
            f"{VYBE_BASE_URL}/wallets/top-traders",
            headers={"X-API-KEY": VYBE_API_KEY},
            params={
                "resolution": RESOLUTION,
                "sortByDesc": "realizedPnlUsd",
                "limit": PAGE_SIZE,
                "page": page,
            },
            timeout=30
        )

        if not response.ok:
            print("Vybe API error:", response.status_code, response.text)
            response.raise_for_status()

        data = response.json()

        # NOTE: Vybe's public docs require login to show the exact response
        # shape, so this is a best guess. The script prints the first raw
        # entry below so you can confirm the field names line up - if
        # Vybe's actual keys differ, this is the only place to adjust.
        page_traders = data if isinstance(data, list) else data.get("data", [])

        if not page_traders:
            break

        all_traders.extend(page_traders)
        print(f"  fetched page {page}: {len(page_traders)} traders (running total: {len(all_traders)})")

        if len(page_traders) < PAGE_SIZE:
            break  # last page was partial, nothing more to fetch

        page += 1

    return all_traders


def make_name(trader):
    name = trader.get("accountName")
    if name:
        return name
    address = trader["accountAddress"]
    return f"{address[:4]}...{address[-4:]}"


def main():
    if not VYBE_API_KEY:
        raise SystemExit("Set VYBE_API_KEY in your .env before running this.")

    traders = fetch_top_traders()
    print(f"Vybe returned {len(traders)} traders before filtering")

    if traders:
        print("\nSample entry (confirm these field names match what's used below):")
        print(traders[0])
        print()

    qualified = [t for t in traders if t.get("metrics", {}).get("tradesCount", 0) >= MIN_TRADES]

    print(f"{len(qualified)} of {len(traders)} passed the {MIN_TRADES}+ trade filter - writing all of them")

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "address"])
        for t in qualified:
            address = t.get("accountAddress")
            if not address:
                continue
            writer.writerow([make_name(t), address])

    print(f"Wrote {len(qualified)} wallets to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()