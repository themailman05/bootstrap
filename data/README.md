# Canary datasets

## `canary_live.csv`

The full, continuously-updated canary dataset — refreshed daily by
[`export-canary.yml`](../.github/workflows/export-canary.yml) after the
12:05 UTC run. Each row is one real, paid GPU lease: deployed, probed for
reachability, closed.

**Provenance of `gpu_model`, read this before using that column:**

- Rows **from 2026-08-30T16:00Z onward**: measured — extracted from the
  winning bid's on-chain resource attributes at lease time.
- Rows **before 2026-08-30** with a value: *inferred* via backfill — the
  provider advertised exactly one GPU model in market snapshots within
  ±6h of the run. Single-model providers only; unambiguous or nothing.
- Empty values: multi-model providers where inference would be guessing
  (123 rows, honestly left blank). The chain could not help: closed
  deployments age out of the Console API quickly, so bid-level recovery
  after the fact was impossible. Moral: provenance must be recorded at
  capture time.

Other caveats: sampling mode (cheapest vs explore) is not recorded in
these rows (the standalone [`canary.py`](../canary.py) schema adds it,
along with `dseq`); per-provider n varies widely; the canary's GPU
profile only reaches providers who serve GPUs.

## `canary_pilot_2026-07-24_to_2026-08-22.csv`

The frozen pilot snapshot cited by [PROPOSAL.md](../PROPOSAL.md) —
kept immutable for reproducibility of the proposal's claims. Superset
data with corrections lives in `canary_live.csv`.

## Canary transparency

All shoestring-canary probes are placed by tenant wallet
**`akash1dtf429gnxhdgtfklm50l0tws8ukkl7m7ejk9e9`** via the Akash Console
API (13-digit timestamp-style dseqs). Providers: if you see a short lease
from this address — a few minutes, a tiny CPU workload, then a clean
close — that was a measurement probe, it paid for its minutes, and your
result is in `canary_live.csv`. Questions or disputes: open an issue.
