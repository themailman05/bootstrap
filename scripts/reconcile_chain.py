# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
"""Audit dataset completeness against the chain.

The chain is the ground-truth ledger of every lease the canary wallet ever
created; the dataset is what the canary managed to record. This script
finds the difference — leases that exist on-chain with no corresponding
row (lost records: crashed runs, failed inserts) — and prints a
completeness figure per era.

Matching: rows recorded since 2026-08-30 carry their dseq and match
exactly. Older rows (the pilot era didn't record dseqs) match on
provider + time: the dseq IS the creation timestamp in ms, and the row's
ts was written 0-8 minutes after creation.

Usage:
    ./scripts/reconcile_chain.py [--wallet akash1...] [--csv data/canary_live.csv]
"""
import argparse
import csv
import sys
from datetime import datetime, timezone

import requests

API = "https://akash-api.polkachu.com"


def chain_leases(wallet):
    leases, key = [], None
    while True:
        params = {"filters.owner": wallet, "pagination.limit": "500"}
        if key:
            params["pagination.key"] = key
        r = requests.get(f"{API}/akash/market/v1beta5/leases/list",
                         params=params, timeout=60)
        r.raise_for_status()
        d = r.json()
        for l in d.get("leases", []):
            lid = l["lease"].get("id") or l["lease"].get("lease_id")
            leases.append({"dseq": int(lid["dseq"]),
                           "provider": lid["provider"],
                           "state": l["lease"]["state"]})
        key = (d.get("pagination") or {}).get("next_key")
        if not key:
            return leases


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--wallet", default="akash1dtf429gnxhdgtfklm50l0tws8ukkl7m7ejk9e9")
    ap.add_argument("--csv", action="append",
                    default=None,
                    help="dataset CSV(s); default: canary_live.csv + canary.csv")
    ap.add_argument("--exclude", default="data/nonprobe_leases.csv",
                    help="known non-probe leases (workloads) to skip")
    ap.add_argument("--since", default="2026-07-24",
                    help="ignore chain leases before this date (pre-dataset era)")
    args = ap.parse_args()

    leases = chain_leases(args.wallet)
    since_ms = datetime.fromisoformat(args.since + "T00:00:00+00:00").timestamp() * 1000
    leases = [l for l in leases if l["dseq"] >= since_ms]
    print(f"chain: {len(leases)} leases since {args.since}")

    import os
    paths = args.csv or [p for p in ("data/canary_live.csv", "data/canary.csv")
                         if os.path.exists(p)]
    rows = []
    for p in paths:
        rows += list(csv.DictReader(open(p)))
    print(f"dataset: {len(rows)} rows from {paths}")
    if os.path.exists(args.exclude):
        skip = {int(r["dseq"]) for r in csv.DictReader(open(args.exclude))}
        leases = [l for l in leases if l["dseq"] not in skip]
        print(f"excluded {len(skip)} known workload leases")
    # export lag: don't flag chain leases newer than the newest recorded row
    newest = max(datetime.fromisoformat(r["ts"]).timestamp() * 1000 for r in rows)
    fresh = [l for l in leases if l["dseq"] > newest]
    leases = [l for l in leases if l["dseq"] <= newest]
    if fresh:
        print(f"deferred {len(fresh)} leases newer than the dataset's newest row")

    matched = set()
    missing = []
    for l in sorted(leases, key=lambda x: x["dseq"]):
        hit = None
        for i, r in enumerate(rows):
            if i in matched or r["provider_owner"] != l["provider"]:
                continue
            row_ms = datetime.fromisoformat(r["ts"]).timestamp() * 1000
            if r.get("dseq") and r["dseq"] not in ("", "None"):
                if int(float(r["dseq"])) == l["dseq"]:
                    hit = i
                    break
            elif 0 <= row_ms - l["dseq"] <= 8 * 60 * 1000:
                hit = i
                break
        if hit is not None:
            matched.add(hit)
        else:
            missing.append(l)

    print(f"matched: {len(matched)}  |  on-chain leases with NO dataset row: {len(missing)}")
    for l in missing:
        t = datetime.fromtimestamp(l["dseq"] / 1000, timezone.utc)
        print(f"  LOST  dseq={l['dseq']}  {t.isoformat()[:19]}Z  {l['provider'][:20]}  {l['state']}")
    total = len(leases)
    if total:
        print(f"completeness: {100 * (total - len(missing)) / total:.1f}%")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
