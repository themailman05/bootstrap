# Community Pool Proposal: shoestring — one-command LLM inference on Akash

*Draft for GitHub Discussions review, following the
[proposal best practices](https://github.com/orgs/akash-network/discussions/170).
Not yet submitted on-chain.*

## TL;DR

**shoestring** is an open-source (MIT), single-file tool that takes a user from
zero to a private, agent-ready LLM endpoint on an Akash GPU in one command and
about six minutes — measured at **\$0.16/hour** for a 27B coding model with 64k
context (64k is partly a bonus of that model's hybrid-mamba architecture;
M1 publishes honest context tables for dense models too, alongside Llama /
DeepSeek / GLM presets). The same machinery has already trained a
production ML model on Akash leases for ~\$30. We request **\$41,200**
(paid in AKT) to take it from
working prototype to a polished v1.0 with hardened multi-engine support, a
`shoestring train` mode for small-model training and distillation, a published
provider-reliability dataset from a month of automated canary deployments, and
tutorial content that makes "rent a GPU on Akash for the price of a coffee"
the easiest on-ramp in the ecosystem.

Repo: https://github.com/themailman05/shoestring — **already public**,
including the raw canary pilot dataset (`data/`). The pilot schema did not
record per-lease dseqs — an honesty gap we note rather than hide; the M2
dataset records dseqs from day one so every row is verifiable against the
chain, and the worked examples in this proposal publish theirs.

## Overview

The single biggest gap between "Akash has the cheapest GPUs anywhere" and
"people actually use them" is the first hour of user experience. Today that
hour involves SDL authoring, manifest/lease mechanics with under-documented
failure modes, GPU attributes that don't disclose VRAM, and pricing in a
denom (`uact`, micro-USD per block) that most users misread. We know because
we hit every one of these building shoestring — and encoded the fixes so the
next person doesn't have to.

What exists **today, working end-to-end**:

- `shoestring.py deploy` → bids surveyed, cheapest reliable provider selected,
  model served ~6 minutes later; `shoestring.py close` → billing stops.
- **Serving engines:** llama.cpp (GGUF, runs on \$0.16/hr 24GB cards) and vLLM
  (AWQ/FP8/NVFP4 — which also speaks the Anthropic protocol, so Claude Code
  connects to an Akash GPU natively).
- **Private by default option:** `--tailscale` joins the container to the
  user's tailnet as an ephemeral node; the model server binds to loopback and
  is unreachable from the public internet. WireGuard end-to-end.
- **VRAM-adaptive:** the container reads the winning card's VRAM at boot and
  sizes context accordingly (24GB→32k … 80GB+→262k), because on-chain GPU
  attributes don't disclose memory.
- **Data-driven provider selection:** cheapest-bid-wins informed by a month
  of automated canary deployments (6/day, real leases, real reachability
  checks). The pilot data — 176 leases, small per-provider n, sampling mode
  labeled — *suggests* price and reliability are uncorrelated on this
  marketplace (the cheapest tier was ~98% reachable in our sample; one
  provider bidding 6x market went 0-for-8). M2 exists to establish this
  rigorously, at scale, in public.
- Ready-to-paste configs for **opencode** and **Claude Code** printed on
  every successful deploy.

And beyond inference, we have already used the same machinery for **real ML
training on Akash**: a small production audio model, distilled from a much
larger teacher, was trained entirely on Akash GPU leases — Jupyter-driven
runs, canary-informed provider selection, automatic checkpoint/artifact
salvage before teardown — for roughly **\$30 of total marketplace spend**.
That model ships today in a production iOS/macOS app built by the proposer
(name and model details withheld while a patent application is pending;
available privately to reviewers — and disclosed plainly: M3 generalizes
infrastructure built for our own product, and the community receives the
generalized tool under MIT), running in real time on phone CPUs. Small-model training is exactly the workload
where Akash's spot pricing shines: the entire multi-round campaign cost
less than one hour of reserved H100 time on a hyperscaler. M3's worked
example makes this claim reproducible by anyone, with its lease dseqs
published.

**All of the above was self-funded, and no compensation is requested for
any pre-proposal work.** It is presented as evidence of execution
capability and as de-risking: this proposal funds the hardening and
generalization of a thing that already works, not a plan.

### How this differs from existing Akash tooling

Akash Console, its templates, and awesome-akash are real on-ramps, and
where a capability belongs upstream we will contribute it there (see M4)
rather than maintain a parallel implementation. What none of them do
today, and shoestring does: VRAM-adaptive context sizing (working around
the chain's silence on GPU memory), tailnet-only private serving,
measured-reliability provider selection, agent-ready config output
(Claude Code / opencode) on every deploy, and training runs with automatic
checkpoint salvage.

Why this benefits Akash: every shoestring user is new GPU demand (inference
*and* training), the tool's field notes double as ecosystem documentation,
and the canary methodology gives the community something it currently
lacks — *independent, continuous, published reliability data on providers*.

## Goal / Mission

Make Akash the default answer to "where do I run an open-weights model
cheaply?" by making the first deploy trivial, private, and honest about
costs — and by publishing the reliability data that lets users trust the
marketplace's cheapest bids.

## Detailed Deliverables

**M1 — shoestring v1.0 (hardened tool)**
- All four engines integration-tested on live leases (llamacpp is
  battle-tested today; the vLLM engines are SDL-validated but need funded
  GPU-hours to verify serving across card classes).
- `--gpu` targeting flag, multi-model presets beyond Qwen (Llama, DeepSeek,
  GLM families), `--list` (show your open leases), resume/reattach.
- Packaging: `uvx shoestring`, Homebrew tap; CI that dry-run-validates every
  SDL variant.
- **Headscale support** (self-hosted, open-source control plane; same
  clients) so the private-serving mode has no proprietary dependency, with
  the restrictive ACL shipped as the default documented path rather than a
  footnote.
- **Criteria-based provider filtering replaces the named blacklist**: v1.0
  ships with an *empty* static list and an opt-in filter of the form
  "avoid providers below X% measured reachability over the last N days,"
  driven by the public canary data — transparent criteria, self-healing
  when a provider improves, and a published contest/cure process. No
  hardcoded provider addresses in a community-funded tool.
- Threat-model documentation expansion (provider trust, key handling,
  ACL recipes; the llama-server `/v1/models` auth gap and peers).

**M2 — Provider reliability canary (public dataset + dashboard)**
- Generalize our canary (currently: real GPU lease every 4h, cheapest-bid
  and explore modes, reachability + time-to-ready + price recorded) into a
  standalone `shoestring-canary` anyone can run.
- Publish the live dataset (Postgres → public dashboard + daily CSV export)
  with per-provider reachability, pricing history, and GPU-model truth data
  (advertised attribute vs. nvidia-smi reality).
- Monthly summary reports to the community (sig-providers).
- **Continuity is a named gate, not a hope**: daily CSV exports live in a
  public repo so the dataset outlives any dashboard; hosting is budgeted
  for 12 months (not one quarter); and at quarter-end the operational
  canary is offered for handoff to sig-providers (or another community
  operator), with `shoestring-canary` as the runnable artifact that makes
  the handoff real. If no operator accepts, we publish a shutdown-and-
  archive plan rather than letting stale data masquerade as live.

**M3 — `shoestring train`: small-model training utility**
- Generalize the workflow that trained our production audio model into a
  first-class subcommand: `shoestring train` boots a GPU Jupyter/script
  box with (a) dataset staging from any S3-compatible bucket, (b)
  **automatic checkpoint/artifact salvage** to the user's bucket on every
  epoch and at teardown (leases are ephemeral; our workflow has already
  survived a destroyed 81GB dataset with zero checkpoint loss), (c)
  canary-informed provider preference, and (d) the same tailnet-only
  privacy mode as inference.
- Target the sweet spot that campaign proved out: fine-tunes, distills,
  and sub-1B-parameter models where a whole training round costs dollars —
  the workload class where "spot GPU on Akash" beats every alternative on
  price and nobody has packaged the ergonomics.
- Worked example shipped with the docs: distilling a small model from a
  large teacher end-to-end on an Akash lease, with real costs published.

**M4 — Adoption content**
- "GPU for the price of a coffee" tutorial series: opencode on Akash, Claude
  Code on Akash via vLLM's Anthropic endpoint, private inference over
  Tailscale — blog posts + a screencast each.
- Upstream documentation PRs to Akash docs for the failure modes we mapped
  (canonical-manifest requirement, zero-global-services rule, uact denom
  semantics, GPU VRAM attribute gap).

## Timeline and Milestones

One quarter, four milestones, payment tranches tied to delivery:

Gates are written to be checkable by strangers, not self-attested:

| Milestone | Weeks | Deliverable gate | Tranche |
| --- | --- | --- | --- |
| M1: v1.0 | 1–6 | tagged release + reproduction doc, with **at least one independent community reproduction** of a deploy on each engine posted in Discussions | 35% |
| M2: canary | 4–10 | public dashboard live + 30 days of published data (dseq-verifiable) + continuity/handoff plan published | 25% |
| M3: train | 6–12 | `shoestring train` shipped + worked distillation example **rerun by a named third party from the docs alone**, costs and dseqs published | 25% |
| M4: content | 8–13 | 4 tutorials published + docs PRs **merged, or open ≥30 days with maintainer review requested** | 15% |

Progress reported monthly in the
[Community Pool Spend Reporting](https://github.com/akash-network/community-pool-spend-reporting)
repo per the standard process.

## Funding Amount Requested

**\$41,200**, paid in AKT (tranche-dated conversion; see below).

### Cost breakdown

| Item | Calculation | Amount |
| --- | --- | --- |
| Engineering (M1–M4) | 200 hours × \$200/hr | \$40,000 |
| Marketplace test spend | live leases across engines/cards/providers for integration testing, 90 days of canary leases, and the worked training-distillation example (~\$0.10–2.50/hr × ~550 lease-hours) | \$800 |
| Dashboard hosting | **12 months** of a small public dashboard + DB | \$400 |
| **Total** | | **\$41,200** |

The rate reflects senior consulting work delivered solo; all code MIT-licensed, all
data CC-BY. Notably, the marketplace test spend flows straight back to Akash
providers.

### Price risk and non-delivery

- **Tranche-dated conversion**: each tranche's AKT amount is computed at
  its own payout date's market rate, so neither side carries a quarter of
  AKT price risk. We will not return for a top-up if AKT falls.
- **Non-delivery**: funds for any milestone whose gate is not met are
  never claimed and remain in (or are returned to) the community pool.
  Monthly reports in the community-pool-spend-reporting repo either show
  gate progress or say plainly that it slipped.

## Research and Ideation (already done)

This proposal follows a month of self-funded groundwork:

- ~30 days of automated canary data: 176 real GPU leases, per-provider
  reachability and pricing (the pilot dataset behind the reliability
  filter and the price-vs-reliability finding; published raw in the repo's
  `data/` directory. Pilot rows lack dseqs — the M2 schema records them).
- 127,000 market snapshots (provider × GPU model × availability, 15-min
  resolution) showing, e.g., a100 availability halving over three weeks.
- Seven live deployments of shoestring itself in one day of iteration,
  debugging four distinct failure modes now encoded in the tool — total
  marketplace spend for that entire day: under \$5.
- A complete small-model training campaign run on Akash leases (the audio
  model above): multi-round teacher→student distillation, Jupyter-driven,
  with provider selection fed by the canary shortlist and full artifact
  salvage — the working system `shoestring train` will generalize.

## Supporting References

- Repository + README with measured benchmarks: https://github.com/themailman05/shoestring
- Model/serving context: Simon Willison on Qwen 3.8 27B —
  https://simonwillison.net/2026/Aug/16/qwen-38-27b/
- vLLM's native Anthropic endpoint (the Claude Code connection):
  https://docs.vllm.ai/en/stable/serving/integrations/claude_code/
- Proposal process followed: https://github.com/orgs/akash-network/discussions/170

## Review Plan

1. Post this draft to GitHub Discussions (akash-network org) and Discord
   (#ecosystem).
2. Present at the next sig-clients and sig-community calls; demo the
   six-minute cold start live.
3. Incorporate feedback for two weeks, seek steering-committee read.
4. Submit on-chain (1,000 AKT deposit) once the discussion converges.

## About

Liam Sargent — decentralized-compute veteran: winner of several Sia
decentralized-storage hackathons and formerly the first employee at
[Filebase](https://filebase.com), where he worked on file-packing
efficiency and protocol-level integrations across decentralized storage
providers. Currently a solo founder/engineer running production workloads
and this GPU tooling on Kubernetes + Akash.
GitHub: [@themailman05](https://github.com/themailman05).
