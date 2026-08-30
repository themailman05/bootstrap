# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
"""Export the live canary dataset from its PostgREST mirror to data/canary_live.csv.

Run by .github/workflows/export-canary.yml daily; runnable locally too:
    SUPABASE_URL=... SUPABASE_KEY=... python scripts/export_canary.py

The CSV is the source of truth for consumers; the database is just where
the operational canary happens to write. Stable ordering (ts, provider)
keeps diffs reviewable.
"""
import csv
import os
import sys

import requests

URL = os.environ["SUPABASE_URL"].rstrip("/")
KEY = os.environ["SUPABASE_KEY"]
TABLE = os.environ.get("CANARY_TABLE", "akash_canary_result")
OUT = os.environ.get("OUT", "data/canary_live.csv")

FIELDS = ["ts", "provider_owner", "gpu_model", "bid_price_uact_per_block",
          "reachable", "time_to_ready_seconds", "failure_reason"]

rows, off = [], 0
while True:
    r = requests.get(
        f"{URL}/rest/v1/{TABLE}",
        params={"select": ",".join(FIELDS), "order": "ts.asc,provider_owner.asc",
                "offset": off, "limit": 1000},
        headers={"apikey": KEY, "Authorization": f"Bearer {KEY}"},
        timeout=60,
    )
    r.raise_for_status()
    page = r.json()
    rows.extend(page)
    off += 1000
    if len(page) < 1000:
        break

if not rows:
    sys.exit("refusing to write an empty export (upstream table empty or unreachable)")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    for row in rows:
        w.writerow({k: row.get(k) for k in FIELDS})
print(f"wrote {len(rows)} rows -> {OUT}")
