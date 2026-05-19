# TriagePilot

> Your labels lie. TriagePilot tells you the truth, every morning at 9 AM.

**Live demo:** https://triagepilot.vercel.app
**Loom walkthrough (5 min):** _[link]_
**Eval results:** [docs/eval_results.md](docs/eval_results.md)

---

## Problem Definition & Target User

_[Fill from PLAN.md Section 2 — keep to 200 words. Anchor on the senior engineer's morning queue.]_

## Why This Problem Matters

_[3 bullet points or 150 words:_
- _Cost of mis-prioritization (PR rot, conflicts, slipped releases)_
- _Why labels fail (stale, politically inflated, lack context)_
- _Why this is an AI problem, not an automation problem]_

## How the Solution Works

_[Architecture diagram (paste ASCII from PLAN.md Section 3)._
_2 paragraphs on the multi-agent flow._
_Link to /docs/architecture.md for deep-dive.]_

## AI-Native Workflow

**Tools, models, agents:**
- Anthropic Claude Sonnet 4.5 (synthesizer + critic agents)
- Anthropic Claude Haiku 4.5 (per-PR analysis agents)
- GitHub GraphQL API
- Python 3.11 + FastAPI
- Next.js 15 + TypeScript + Tailwind + shadcn/ui

**Agents:**
1. **Diff Analyst** — reads the unified diff, estimates effort and blast radius
2. **Ticket Context** — reads the linked issue, detects label-vs-reality mismatch
3. **Author Profile** — reads the author's history, scores trust
4. **Synthesizer** — combines all signals, produces ranked queue with reasoning
5. **Critic** — sanity-checks the ranking before output

**AI tools used during development:** _[fill from BUILD_LOG]_

## Evaluation Method & Results

_[Paste numbers from Phase 9 eval runs._
_Include the comparison table._
_Include at least one chart.]_

| Ranker | NDCG@5 (Kubernetes) | NDCG@5 (Next.js) |
|---|---|---|
| Random | 0.XX | 0.XX |
| Label-only | 0.XX | 0.XX |
| Author-only | 0.XX | 0.XX |
| **TriagePilot** | **0.XX** | **0.XX** |

### The Killer Moment

_[1–2 screenshots of cases where TriagePilot beat the maintainers' actual review order.]_

## Baseline Comparison: Why Not Just Use ChatGPT?

_[The experiment described in PLAN.md Section 7.]_

## Limitations & Next Iteration Ideas

- **Cold-start problem:** Author trust scores assume history exists. New contributors are scored neutrally.
- **No private repo support yet:** Read-only public-repo focus for the Quest. Linear/Jira adapter exists in `server/src/ticket_sources/` and is 2 hours from wiring up.
- **Single-reviewer assumption:** Ranking is global, not per-reviewer-expertise.
- **Evening feedback loop:** Stretch goal, not shipped in v1.

## Quick Start

```bash
git clone https://github.com/<you>/triagepilot
cd triagepilot

# server
cp server/.env.example server/.env  # add GITHUB_TOKEN and ANTHROPIC_API_KEY

# web
cp web/.env.local.example web/.env.local

make install
make eval   # runs the full eval suite
make dev    # web at :3000, server at :8000
```

## Architecture

See [docs/architecture.md](docs/architecture.md).

## License

MIT
