# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
"""shoestring-canary -- measure Akash provider reliability with real leases.

Each run places one REAL, minimal GPU deployment (the same cheapest-bid
logic a broker would use), measures whether the workload actually becomes
reachable and how long that takes, then closes the lease. Not self-reported
uptime -- an actual paid test of the marketplace, a few cents per run.

With probability --explore-p (default 0.5) a run tests a RANDOM
non-cheapest bidder instead, so the reliability picture covers the whole
market rather than whoever is cheapest this week. Every row records which
mode it was, so analyses can separate them (a lesson from our pilot
dataset, which didn't).

NO DATABASE REQUIRED. Rows append to a local CSV (default: data/canary.csv,
same format as the published pilot data plus dseq and mode columns). If you
want a shared store, set SUPABASE_URL and SUPABASE_KEY (any PostgREST
endpoint works) and rows are ALSO posted to the table named by
CANARY_TABLE (default shoestring_canary):

    CREATE TABLE shoestring_canary (
        id BIGSERIAL PRIMARY KEY,
        ts TIMESTAMPTZ NOT NULL,
        dseq TEXT,
        provider_owner TEXT NOT NULL,
        gpu_model TEXT,
        mode TEXT,
        bid_price_uact_per_block REAL,
        reachable BOOLEAN NOT NULL,
        time_to_ready_seconds REAL,
        failure_reason TEXT
    );

Usage:
    export AKASH_API_KEY=...      # console.akash.network
    ./canary.py run [--explore-p 0.5] [--out data/canary.csv]

Run it on a schedule (6x/day gives a useful picture within weeks):
    17 */4 * * *  cd /path/to/shoestring && ./canary.py run
"""
import argparse
import csv
import os
import random
import sys
import time
from datetime import datetime, timezone

import requests

import shoestring as ss

CANARY_SDL = """---
version: "2.0"
services:
  web:
    image: python:3.11-slim
    command: ["/bin/bash", "-c"]
    args: ["python3 -m http.server 80"]
    expose:
      - port: 80
        as: 80
        to:
          - global: true
profiles:
  compute:
    web:
      resources:
        cpu:
          units: 1
        memory:
          size: 1Gi
        storage:
          size: 2Gi
        gpu:
          units: 1
          attributes:
            vendor:
              nvidia:
                - model: a100
                - model: h100
                - model: h200
                - model: rtx4090
                - model: rtx3090
                - model: rtx5090
                - model: rtx6000
                - model: pro6000se
                - model: v100
                - model: t4
  placement:
    akash:
      pricing:
        web:
          denom: uact
          amount: {price}
deployment:
  web:
    akash:
      profile: web
      count: 1
"""

FIELDS = ["ts", "dseq", "provider_owner", "gpu_model", "mode",
          "bid_price_uact_per_block", "reachable", "time_to_ready_seconds",
          "failure_reason"]


def record(row, out_path):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    new = not os.path.exists(out_path)
    with open(out_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow(row)
    # optional shared sink -- entirely supplemental, never required
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY")
    if url and key:
        table = os.environ.get("CANARY_TABLE", "shoestring_canary")
        try:
            requests.post(
                f"{url.rstrip('/')}/rest/v1/{table}",
                headers={"apikey": key, "Authorization": f"Bearer {key}",
                         "Content-Type": "application/json",
                         "Prefer": "return=minimal"},
                json=row, timeout=30,
            ).raise_for_status()
        except requests.RequestException as e:
            print(f"[canary] warning: DB sink failed ({e}); CSV row is safe")


def run(args):
    dseq = provider = gpu_model = mode = None
    bid_price = ttr = None
    reachable = False
    failure_reason = None
    start = time.time()

    try:
        dseq, manifest = ss.create_deployment(
            CANARY_SDL.format(price=args.max_price), deposit_usd=5)

        deadline = time.time() + args.bid_wait
        bids = []
        while time.time() < deadline and not bids:
            time.sleep(10)
            bids = ss.get_bids(dseq)
        if not bids:
            failure_reason = "no_bids"
            return

        ranked = sorted(bids, key=lambda b: float(b["bid"]["price"]["amount"]))
        if len(ranked) > 1 and random.random() < args.explore_p:
            chosen, mode = random.choice(ranked[1:]), "explore"
        else:
            chosen, mode = ranked[0], "cheapest"
        provider = chosen["bid"]["id"]["provider"]
        bid_price = float(chosen["bid"]["price"]["amount"])
        gpu_model = ss.extract_gpu_model(chosen)

        ss.accept_bid(dseq, manifest, provider)

        endpoint = ss.get_endpoint(dseq, timeout_s=90)
        if not endpoint:
            failure_reason = "no_endpoint"
            return

        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                r = requests.get(endpoint, timeout=8)
                # an app-level response, not the provider's fallback page:
                # python http.server's listing carries this exact marker
                if r.status_code == 200 and "Directory listing" in r.text:
                    reachable = True
                    ttr = round(time.time() - start, 1)
                    break
            except requests.RequestException:
                pass
            time.sleep(10)
        if not reachable:
            failure_reason = failure_reason or "never_reachable"

    except Exception as e:
        failure_reason = f"exception:{type(e).__name__}:{e}"[:200]
    finally:
        if dseq:
            ss.close_deployment(dseq)

    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "dseq": dseq,
        "provider_owner": provider or "none",
        "gpu_model": gpu_model,
        "mode": mode,
        "bid_price_uact_per_block": bid_price,
        "reachable": reachable,
        "time_to_ready_seconds": ttr,
        "failure_reason": failure_reason,
    }
    record(row, args.out)
    print(f"[canary] dseq={dseq} provider={provider} mode={mode} "
          f"gpu={gpu_model} reachable={reachable} ttr={ttr} "
          f"reason={failure_reason}")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="one canary lease: deploy, probe, close, record")
    r.add_argument("--explore-p", type=float, default=0.5,
                   help="probability of testing a random non-cheapest bid")
    r.add_argument("--bid-wait", type=int, default=60)
    r.add_argument("--max-price", type=int, default=20000)
    r.add_argument("--out", default="data/canary.csv")
    r.set_defaults(fn=run)
    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
