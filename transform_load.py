"""
Transform raw_ebay_listings -> ebay_listings (clean table).
Baca raw JSONB, clean field, compute derived column, insert dengan dedup.

SEBELUM RUN:
1. Isi CONNECTION_STRING bawah (sama macam insert_raw.py)
"""

import psycopg2
import psycopg2.extras
import json
import os
from datetime import datetime

# =========================
# Guna GitHub Secrets (env var) kalau ada, fallback ke placeholder untuk local test
# =========================
CONNECTION_STRING = os.environ.get("SUPABASE_CONNECTION_STRING", "ISI_CONNECTION_STRING_DISINI")


def clean_price(value):
    """Convert price string ke float, handle None/invalid."""
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def get_price_bucket(price):
    """Segmentasi harga: Low / Mid / High."""
    if price is None:
        return None
    if price < 20:
        return "Low"
    elif price < 100:
        return "Mid"
    else:
        return "High"


def clean_condition(raw_condition):
    """Standardize condition text."""
    if not raw_condition:
        return "Unknown"
    text = raw_condition.lower()
    if "new" in text:
        return "New"
    elif "refurb" in text:
        return "Refurbished"
    elif "used" in text:
        return "Used"
    else:
        return raw_condition  # kekal asal kalau tak match kategori biasa


def clean_date(date_str):
    """Parse ISO date string ke date object, return None kalau invalid."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def transform_and_load():
    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Ambik raw row yang scraped hari ini je (elak re-process semua setiap kali run)
    cur.execute("""
        SELECT item_id, raw_json, scraped_at
        FROM raw_ebay_listings
        WHERE scraped_at::date = CURRENT_DATE
    """)
    raw_rows = cur.fetchall()
    print(f"Jumpa {len(raw_rows)} raw row untuk transform hari ini.")

    insert_cur = conn.cursor()
    cleaned_count = 0
    skipped_count = 0

    for row in raw_rows:
        data = row["raw_json"]
        if isinstance(data, str):
            data = json.loads(data)

        item_id = data.get("item_id")
        price = clean_price(data.get("price"))
        shipping_cost = clean_price(data.get("shipping_cost")) or 0.0

        if not item_id or price is None:
            skipped_count += 1
            continue  # skip row invalid, item_id/price wajib ada

        total_price = round(price + shipping_cost, 2)
        condition = clean_condition(data.get("condition"))
        item_creation_date = clean_date(data.get("item_creation_date"))
        snapshot_date = data.get("snapshot_date")
        price_bucket = get_price_bucket(price)

        insert_cur.execute("""
            INSERT INTO ebay_listings (
                item_id, listing_title, category, price, shipping_cost,
                total_price, condition, seller_location, item_creation_date,
                snapshot_date, price_bucket
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (item_id, snapshot_date) DO NOTHING
        """, (
            item_id,
            data.get("listing_title"),
            data.get("category"),
            price,
            shipping_cost,
            total_price,
            condition,
            data.get("seller_location"),
            item_creation_date,
            snapshot_date,
            price_bucket,
        ))
        cleaned_count += 1

    conn.commit()
    insert_cur.close()
    cur.close()
    conn.close()

    print(f"\nDone. {cleaned_count} row clean & inserted (dedup applied).")
    print(f"{skipped_count} row skipped (invalid item_id/price).")


if __name__ == "__main__":
    transform_and_load()
