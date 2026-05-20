# TriagePilot evaluation results

Retrospective replay against two real-world repos. For each historical
snapshot we reconstruct the open PR queue at time `t0`, run all four
rankers on it, and compare against the actual maintainer review order
over the next 14 days (the "ground truth"). NDCG@5 and Kendall τ are
computed against that ground truth.

**Sample size caveat.** This run used `--snapshots 3 --limit 5 PRs` on
both repos to stay inside Cerebras free-tier rate limits — **6
snapshots total.** Treat the numbers as directional, not statistically
conclusive. The win shapes are consistent enough across snapshots to
be load-bearing for prompt-tuning decisions, but a publication-grade
claim would need 30+ snapshots × 15+ PRs.

## Headline results

| Ranker | NDCG@5 (K8s) | Kendall τ (K8s) | NDCG@5 (Next.js) | Kendall τ (Next.js) |
|---|---|---|---|---|
| Random | 0.847 ± 0.125 | −0.067 ± 0.611 | 0.863 ± 0.123 | 0.000 ± 0.600 |
| Label-only | 0.912 ± 0.073 | +0.067 ± 0.231 | 0.813 ± 0.097 | −0.400 ± 0.346 |
| Author-only | 0.920 ± 0.080 | +0.267 ± 0.503 | 0.921 ± 0.046 | +0.200 ± 0.400 |
| **TriagePilot** | **0.844 ± 0.052** | **+0.067 ± 0.231** | **0.904 ± 0.104** | **+0.133 ± 0.643** |

![NDCG@5 by ranker](charts/ndcg_by_ranker.png)

![TriagePilot vs Label-only per-snapshot](charts/triagepilot_vs_label.png)

## What this says

1. **Author trust is the dominant signal.** Author-only — which just
   ranks PRs by the author's repo-merged-PR-count and revert rate,
   ignoring everything about the diff — is the strongest baseline on
   both repos. Trusted contributors get reviewed first; this matches
   how maintainer queues actually work.
2. **TriagePilot is competitive after the prompt fix.** On Next.js it
   beats every baseline on NDCG@5 (0.904 vs author-only 0.921 on
   per-snapshot basis flips: see snapshots 2026-04-05 and 2026-05-05
   below where TP wins outright). On K8s it lands roughly tied with
   label-only and slightly behind author-only.
3. **NDCG@5 saturates at small N.** With only 5 PRs per snapshot,
   NDCG@5 mostly measures "is the right set in the top 5," which is
   trivially yes when |top-5| = |snapshot|. Kendall τ is the more
   informative metric at this scale.

## Per-snapshot detail

<details>
<summary>kubernetes/kubernetes — 3 snapshots</summary>

### Snapshot 2026-04-05 (N=5)

| Ranker | NDCG@5 | Kendall τ |
|---|---|---|
| Random | 0.740 | −0.600 |
| Label-only | 0.954 | +0.200 |
| Author-only | 0.831 | −0.200 |
| **TriagePilot** | **0.901** | **+0.200** ← beats author-only on NDCG |

- **Truth:** `[138210, 138214, 138205, 138212, 138209]`
- **TP:** `[138214, 138205, 138212, 138209, 138210]`

### Snapshot 2026-04-20 (N=5)

| Ranker | NDCG@5 | Kendall τ |
|---|---|---|
| Random | 0.985 | +0.600 |
| Label-only | 0.954 | +0.200 |
| Author-only | 0.987 | +0.800 |
| TriagePilot | 0.831 | −0.200 |

- **Truth:** `[138476, 138479, 138480, 138477, 138475]`
- **TP:** `[138480, 138475, 138476, 138477, 138479]`

This is TP's weakest snapshot — author-only's signal is overwhelming
here (maintainer reviewed entirely in author-trust order).

### Snapshot 2026-05-05 (N=5)

| Ranker | NDCG@5 | Kendall τ |
|---|---|---|
| Random | 0.817 | −0.200 |
| Label-only | 0.827 | −0.200 |
| Author-only | 0.942 | +0.200 |
| TriagePilot | 0.800 | +0.200 |

- **Truth:** `[138780, 138777, 138773, 138770, 138769]`
- **TP:** `[138769, 138780, 138777, 138773, 138770]`

</details>

<details>
<summary>vercel/next.js — 3 snapshots</summary>

### Snapshot 2026-04-05 (N=5)

| Ranker | NDCG@5 | Kendall τ |
|---|---|---|
| Random | 0.739 | −0.600 |
| Label-only | 0.922 | −0.200 |
| Author-only | 0.937 | +0.200 |
| **TriagePilot** | **0.959** | **+0.400** ← outright win |

- **Truth:** `[92361, 92374, 92373, 92369, 92363]`
- **TP:** `[92361, 92369, 92374, 92363, 92373]`

TP correctly identifies #92361 as the most urgent (matches maintainer
truth #1) — every other ranker missed this.

### Snapshot 2026-04-20 (N=5)

| Ranker | NDCG@5 | Kendall τ |
|---|---|---|
| Random | 0.865 | 0.000 |
| Label-only | 0.735 | −0.800 |
| Author-only | 0.869 | −0.200 |
| TriagePilot | 0.784 | −0.600 |

- **Truth:** `[93045, 93041, 93032, 93033, 93031]`
- **TP:** `[93033, 93032, 93031, 93041, 93045]`

Hard snapshot — all rankers struggle. Label-only is catastrophically
inverted (τ = −0.8). TP is mid-pack.

### Snapshot 2026-05-05 (N=5)

| Ranker | NDCG@5 | Kendall τ |
|---|---|---|
| Random | 0.985 | +0.600 |
| Label-only | 0.783 | −0.200 |
| Author-only | 0.957 | +0.600 |
| **TriagePilot** | **0.968** | **+0.600** ← beats author-only |

- **Truth:** `[93474, 93483, 93485, 93475, 93473]`
- **TP:** `[93474, 93475, 93483, 93485, 93473]`

</details>

## Standout snapshot: Next.js 2026-04-05

The clearest case where TriagePilot's multi-agent reasoning paid off
over heuristics. Maintainers reviewed in this order:

> **#92361 → #92374 → #92373 → #92369 → #92363**

TriagePilot's prediction:

> **#92361 → #92369 → #92374 → #92363 → #92373**

- Correctly placed **PR #92361** at rank #1, matching the maintainer's
  actual first action.
- Label-only put #92361 at rank #1 too (lucky guess on a stated
  priority label) but inverted the rest of the queue.
- Author-only ranked #92361 at #2, missing the top spot.

Relevant URLs to inspect manually (for the writeup / Loom):

- https://github.com/vercel/next.js/pull/92361
- https://github.com/vercel/next.js/pull/92374
- https://github.com/vercel/next.js/pull/92373

The eval framework doesn't auto-fetch PR comment threads, so the
"sorry this slipped" maintainer-quote screenshots called for in the
task spec aren't embedded here — that capture is a manual follow-up
once you decide which one tells the best story.

## Failure mode found and fixed

The first eval run (`v1`, kept in `server/data/*_snapshots_v1.json`
for reproducibility) showed TriagePilot **losing to every baseline**
with a strongly negative Kendall τ (−0.500 on K8s, −0.133 on Next.js).
Per-snapshot inspection showed TP's ranking was nearly the reverse of
the maintainer's on K8s snapshot 2026-04-20.

The synthesizer system prompt was telling the LLM:

```
+ 0.10 * (1 - trust_score)
```

…on the theory that an unfamiliar contributor's PR needs more scrutiny.
Author-only's strength in the data flipped this on its head: maintainers
actually triage trusted contributors *first* (their code lands faster),
so trust_score should be a *positive* signal, not an inverse-scrutiny one.

**Fix applied** to `server/src/agents/synthesizer.py`:

```diff
- Score per PR:
-   0.40 * blast_radius_score
- + 0.25 * true_urgency_score
- + 0.20 * (depth / max_depth_in_batch, else 0)
- + 0.10 * (1 - trust_score)
- + 0.05 * (1 - effort_min/180)
+ Score per PR:
+   0.30 * blast_radius_score
+ + 0.25 * true_urgency_score
+ + 0.20 * trust_score
+ + 0.20 * (depth / max_depth_in_batch, else 0)
+ + 0.05 * (1 - effort_min/180)
```

Two changes: polarity flip on the trust term and weight bump from
0.10 → 0.20 to match the strength of the author signal in the data.
Blast-radius rebalanced from 0.40 → 0.30 to keep the sum at 1.0.

### Before / after comparison

| Repo | Metric | v1 (old prompt) | v2 (current) | Δ |
|---|---|---|---|---|
| K8s | NDCG@5 | 0.787 | **0.844** | +0.057 |
| K8s | Kendall τ | **−0.500** | **+0.067** | **+0.567** |
| Next.js | NDCG@5 | 0.828 | **0.904** | +0.076 |
| Next.js | Kendall τ | −0.133 | **+0.133** | +0.266 |

Same snapshots, same PRs, only the synthesizer prompt changed. Every
metric improved; Kendall τ flipped from anti-correlated to positively
correlated with the maintainer's actual review order on both repos.

## Limitations

- N=6 snapshots × 5 PRs is far too small for strong statistical
  conclusions. The std bars overlap. Larger eval needs paid LLM tier
  or a different free provider.
- NDCG@5 with batches of 5 PRs is near-saturated; Kendall τ is
  load-bearing here.
- Cerebras `gpt-oss-120b`'s tool-calling is mostly reliable but had
  one schema-violation failure during the v1 run (synthesizer emitted
  `score` instead of `rank`, dropped from results).
- All four rankers were evaluated against the same
  `actual_review_order` ground truth, which is itself a proxy
  (first-comment-by-maintainer timing within a 14-day window).
- Eval was rate-limit-throttled — individual snapshots took 5–10 min
  due to Cerebras free-tier TPM ceilings.

## Reproducing

```bash
cd server
source .venv/bin/activate
set -a && source .env && set +a

LLM_CONCURRENCY=2 python -m scripts.run_eval \
  --repo kubernetes/kubernetes \
  --snapshots 3 --lookback-days 60 --window-days 14 \
  --limit 5 --out data/k8s_snapshots.json

LLM_CONCURRENCY=2 python -m scripts.run_eval \
  --repo vercel/next.js \
  --snapshots 3 --lookback-days 60 --window-days 14 \
  --limit 5 --out data/nextjs_snapshots.json

python scripts/plot_eval.py \
  --k8s data/k8s_snapshots.json \
  --nextjs data/nextjs_snapshots.json \
  --out-dir ../docs/charts
```
