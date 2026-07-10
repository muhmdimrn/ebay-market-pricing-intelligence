"""
Insert raw scraped JSON ke Supabase table `raw_ebay_listings`.
Setiap row raw disimpan sebagai JSONB, takde dedup kat step ni.

SEBELUM RUN:
1. Isi CONNECTION_STRING bawah (Transaction pooler, port 6543)
2. pip install psycopg2-binary (dah install)
"""

import psycopg2
import json
import sys
import os
from datetime import datetime

# =========================
# Guna GitHub Secrets (env var) kalau ada, fallback ke placeholder untuk local test
# =========================
CONNECTION_STRING = os.environ.get("SUPABASE_CONNECTION_STRING", "ISI_CONNECTION_STRING_DISINI")


def insert_raw(json_file_path):
    with open(json_file_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    print(f"Loaded {len(rows)} row dari {json_file_path}")

    conn = psycopg2.connect(CONNECTION_STRING)
    cur = conn.cursor()

    inserted = 0
    for row in rows:
        item_id = row.get("item_id")
        raw_json = json.dumps(row)

        cur.execute(
            """
            INSERT INTO raw_ebay_listings (item_id, raw_json, scraped_at)
            VALUES (%s, %s, %s)
            """,
            (item_id, raw_json, datetime.now())
        )
        inserted += 1

        if inserted % 500 == 0:
            conn.commit()
            print(f"Committed {inserted} row...")

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nDone. Total {inserted} row inserted ke raw_ebay_listings.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Cara guna: python insert_raw.py <nama_file.json>")
        sys.exit(1)

    insert_raw(sys.argv[1])
