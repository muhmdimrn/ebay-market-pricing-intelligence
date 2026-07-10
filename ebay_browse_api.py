"""
eBay Browse API — Active Listings Puller
Guna OAuth Client Credentials flow (App-level token, takyah user login).
Pull active listing untuk 5 kategori, output raw JSON.

SEBELUM RUN:
1. Isi APP_ID dan CERT_ID bawah (dari eBay Developer account, lepas approval)
2. pip install requests
"""

import requests
import base64
import json
import time
import os
from datetime import date, datetime

# =========================
# Guna GitHub Secrets (env var) kalau ada, fallback ke placeholder untuk local test
# =========================
APP_ID = os.environ.get("EBAY_APP_ID", "ISI_APP_ID_DISINI")
CERT_ID = os.environ.get("EBAY_CERT_ID", "ISI_CERT_ID_DISINI")

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

# 5 kategori locked, sama macam sebelum ni
CATEGORIES = {
    "Electronics": "293",
    "Fashion": "11450",
    "Home & Garden": "11700",
    "Toys": "220",
    "Sports": "888",
}

TARGET_PER_CATEGORY = 2000
PAGE_SIZE = 200  # max limit sebenar Browse API (bukan 50)


def get_oauth_token():
    """Dapatkan application access token guna Client Credentials grant."""
    credentials = f"{APP_ID}:{CERT_ID}"
    encoded = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded}",
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }

    resp = requests.post(TOKEN_URL, headers=headers, data=data, timeout=15)
    resp.raise_for_status()
    return resp.json()["access_token"]


def search_category(token, category_id, category_name, target_rows):
    """Pull active listing untuk satu kategori, paginate guna offset."""
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
    }

    results = []
    offset = 0

    while len(results) < target_rows:
        params = {
            "category_ids": category_id,
            "limit": PAGE_SIZE,
            "offset": offset,
        }
        resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=15)

        if resp.status_code != 200:
            print(f"[{category_name}] offset {offset} failed, status {resp.status_code}: {resp.text[:200]}")
            break

        data = resp.json()
        items = data.get("itemSummaries", [])

        if not items:
            print(f"[{category_name}] no more item at offset {offset}, stop")
            break

        snapshot_date = date.today().isoformat()

        for item in items:
            row = {
                "item_id": item.get("itemId"),
                "listing_title": item.get("title"),
                "category": category_name,
                "price": item.get("price", {}).get("value"),
                "currency": item.get("price", {}).get("currency"),
                "shipping_cost": (
                    item.get("shippingOptions", [{}])[0].get("shippingCost", {}).get("value")
                    if item.get("shippingOptions") else 0
                ),
                "condition": item.get("condition"),
                "seller_location": item.get("itemLocation", {}).get("country"),
                "item_creation_date": item.get("itemCreationDate"),
                "snapshot_date": snapshot_date,
                "scraped_at": datetime.now().isoformat(),
            }
            results.append(row)

        print(f"[{category_name}] offset {offset}: +{len(items)} row, total {len(results)}")
        offset += PAGE_SIZE
        time.sleep(0.1)  # jaga rate limit API, kurangkan sebab jauh bawah 5000/hari

    return results[:target_rows]


def main():
    token = get_oauth_token()
    print("OAuth token dapat, mula pull data...\n")

    all_rows = []
    for name, cid in CATEGORIES.items():
        rows = search_category(token, cid, name, TARGET_PER_CATEGORY)
        all_rows.extend(rows)

    out_path = "ebay_latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_rows, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Total row: {len(all_rows)}. Saved to {out_path}")


if __name__ == "__main__":
    main()
