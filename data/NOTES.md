# Dataset notes — annotated rows and provenance events

Failure rows with operator-provided context. A documented failure with a
named cause is worth more to the framework than a clean row; a documented
failure with an *honestly unresolved* cause is worth almost as much.

## 2026-07-30T12:07:39Z · akash1sevd2… (provider.jjozzietech.com.au) · never_reachable

- On-chain lease: dseq `1785413103258`, created 2026-07-30T12:05:03Z,
  tenant `akash1dtf429gnxhdgtfklm50l0tws8ukkl7m7ejk9e9`.
- The provider's only failure in 48 pilot leases (98% reachable, 30s
  median time-to-ready otherwise).
- **Operator investigation** ([comment](https://github.com/orgs/akash-network/discussions/1508)):
  a GPU node on this provider was silently network-partitioned
  ~16 Jul – 1 Aug (libceph ENETUNREACH → Calico down → no default
  routes), while its kubelet kept the node `Ready` — a **silent
  partition**: the scheduler places workloads on a node that cannot run
  them; the ingress URI exists; nothing ever answers.
- **Causation status: unresolved, per the operator's own correction.**
  The partition is log-evidenced; that this specific lease landed on the
  partitioned node is *plausible but not established*. Node-level lookup
  against the dseq above is pending. Recorded here exactly as far as the
  evidence goes, no further.
- Operator remediations shipped: Ceph OSD status cross-check in daily
  health script; per-node outbound heartbeat cron.

### Framework lessons adopted from this case

1. **Failure needs a cause class, not a boolean.** `never_reachable`
   bundles broken providers with transiently-faulted nodes; they should
   score differently.
2. **Retry discriminates cheaply.** A follow-up lease landing on a
   healthy node distinguishes node-scoped from provider-scoped failure.
3. **Recency-weight the scorecard.** One failure inside a two-week
   incident window ≠ a continuous 1-in-48 failure rate.
4. **Attribution data must be captured at write time.** Post-hoc
   attribution proved unreliable *even for the operator, with full log
   access, within a month*. The canary now records the lease dseq and
   the ingress endpoint per row for this reason (same principle that
   forced the gpu_model fix).

## gpu_model provenance events

- 2026-08-30: 99 historical rows backfilled by unambiguous market-inventory
  inference; 123 left NULL (see `README.md`).
- 2026-09-02: all 48 `akash1sevd2…` rows set to `rtx3090` —
  **operator-confirmed** on the record in the proposal thread.
