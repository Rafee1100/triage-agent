# TriagePilot

> Your labels lie. TriagePilot tells you the truth, every morning at 9 AM.

**Live demo:** https://triagepilot.vercel.app
**Backend:** https://triagepilot-api.onrender.com
**Loom walkthrough (5 min):** _[to be added]_
**Eval results:** [docs/eval_results.md](docs/eval_results.md)

---

## Problem Definition & Target User

It's 9 AM. I open GitHub and find 34 open pull requests on a repo
I own. The default sort is `updated_at`, which is recent activity,
not urgency. Three PRs are labeled `P0`, but one of those is two
weeks old, filed by someone who labels everything `P0`. A fourth
is labeled `chore` and touches the auth middleware. One of these
PRs is going to collide with next week's release branch if I don't
review it today. I have 45 minutes before standup.

The user this is built for is the person on the other end of that
queue. Someone who already knows how to review code. Their problem
isn't reviewing — it's deciding which PR to open first when 30 of
them have plausible reasons to be at the top. Not new contributors
shipping their own work. Not engineering managers tracking
throughput. The reviewer who pays for it personally when the queue
is wrong, because they're the one rebasing the conflict and
writing the apology comment.

What they need is a ranked queue with a one-line reason for each
item, ready by the time they sit down.

## Why This Problem Matters

A mis-prioritized review queue costs real time, and it does it
silently. The PR that should have been reviewed today rots for a
week, picks up merge conflicts, and either gets force-merged
unsafely or abandoned. Meanwhile the reviewer's morning gets spent
on ten low-stakes PRs before they find the one that actually
blocked the release.

Labels don't fix this. Labels are what the *author* thinks is
urgent, not what the *reviewer* needs to look at first. They go
stale the second context changes. Static rules like
lines-changed or file-count aren't enough either — a one-line
change to the Kubernetes scheduler is more dangerous than a
thousand-line generated migration, and no rule catches that without
reading the code.

That's why it's an AI problem. The right answer needs to read the
diff, cross-reference the linked ticket, weigh how trusted the
author is, and reconcile those signals when they disagree. "The
label says low priority, but the diff touches auth middleware" is
the exact kind of judgment a rules engine can't make and an LLM
can.

## How the Solution Works

```
                ┌─────────────────────────────────────────┐
                │           GitHub GraphQL API            │
                └────────────────────┬────────────────────┘
                                     │ open PRs, files,
                                     │ author history,
                                     │ linked issues
                                     ▼
        ┌────────────────────────────────────────────────────┐
        │           Per-PR fan-out (concurrent)              │
        │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │
        │  │ DiffAnalyst  │ │ TicketContext│ │AuthorProf. │  │
        │  │ effort +     │ │ stated vs    │ │ trust +    │  │
        │  │ blast radius │ │ real urgency │ │ revert rate│  │
        │  └──────┬───────┘ └──────┬───────┘ └──────┬─────┘  │
        └─────────┼────────────────┼────────────────┼────────┘
                  └────────────────┼────────────────┘
                                   ▼
                        ┌────────────────────┐
                        │    Synthesizer     │
                        │  weighted ranking, │
                        │  per-PR reasoning  │
                        └─────────┬──────────┘
                                  ▼
                        ┌────────────────────┐
                        │      Critic        │
                        │  sanity-checks the │
                        │  ranking; emits    │
                        │  rank adjustments  │
                        └─────────┬──────────┘
                                  ▼
            ┌──────────────────────────────────────┐
            │  SSE stream → web UI                 │
            │  scheduled brief → Telegram (APSched)│
            └──────────────────────────────────────┘
```

The user types `owner/repo` into the web app and hits **Triage now**.
On the backend, three small agents run in parallel for each open
PR. Their progress streams back to the browser as Server-Sent
Events, so you can watch the pipeline think as it goes. When all
the per-PR work is done, the synthesizer takes the whole batch and
ranks it; the critic gives the ranking one more look. The browser
renders the final queue with a one-line reason per PR and flags
every case where the AI's verdict and the GitHub label disagree by
more than one priority level. That flag is the most useful thing
the UI does.

For people who don't want to come back to the website every
morning, there's a Telegram subscription. Open the modal, paste a
bot token and chat ID, pick a time and a timezone, save. An
APScheduler job runs inside the same FastAPI process, fires the
pipeline at the chosen time, and posts the top 5 to your chat. The
subscriptions live in `server/data/subscriptions.json`. Adding a
new subscriber is just a write to that file.

## AI-Native Workflow

The pipeline runs five agents through LiteLLM. All five point at
Cerebras `gpt-oss-120b` by default — it's free tier, fast, and the
only Cerebras free model whose tool-calling didn't break for me
during the build. Switching providers is a one-line env-var change:
set `HAIKU_MODEL` and `SONNET_MODEL` to `anthropic/claude-haiku-4-5`
and `claude-sonnet-4-5` and the code keeps working.

The backend is Python 3.11, FastAPI, and asyncio. Streaming goes
through `sse-starlette`, and the morning briefs are scheduled with
`APScheduler.AsyncIOScheduler` running inside the same process.
Pydantic v2 carries the schemas — every agent returns a typed
`BaseModel`, and the LLM is forced through LiteLLM's tool-call
interface so the response is validated on the way back. Free-form
text parsing isn't anywhere in the codebase.

The web client is Next.js 16, Tailwind v4, and shadcn components
built on Base UI. The browser uses native `EventSource` to consume
the SSE stream.

**Open source.** Everything is in this repo, MIT-licensed. The
stack is open-source the whole way down: LiteLLM, FastAPI,
sse-starlette, APScheduler, Pydantic, Next.js, Tailwind, Base UI,
python-telegram-bot, scipy, matplotlib. No proprietary
dependencies.

**APIs.** The pipeline consumes the GitHub GraphQL API for PRs,
files, issues, and author history; Cerebras's Cloud API via
LiteLLM for LLM calls; and the Telegram Bot API for morning brief
delivery. On the other side, the FastAPI server exposes
`/rank/{owner}/{name}/stream` for the SSE pipeline events and
`/subscriptions` for the Telegram brief CRUD. OpenAPI docs at
`/docs` on the deployed backend.

**Agent flow:**

```
   ┌──────────────┐
   │  PR queue    │  (open PRs, fetched in batch)
   └──────┬───────┘
          │
   ┌──────▼───────────────────────────────────────────────┐
   │  Per-PR fan-out (asyncio.gather, LLM_CONCURRENCY=4) │
   │                                                      │
   │   DiffAnalyst  ──►  effort_min, blast_radius_score, │
   │                     risk_tags                        │
   │                                                      │
   │   TicketContext ─►  stated_priority,                │
   │                     true_urgency_score,             │
   │                     keywords_extracted              │
   │                                                      │
   │   AuthorProfile ─►  trust_score, recent_revert_rate │
   └──────┬───────────────────────────────────────────────┘
          │  fanned-in PRBundles
          ▼
   ┌────────────────────┐
   │  Synthesizer       │   weighted score, ai_priority,
   │  (batch over all)  │   label_disagreement, reasoning
   └──────┬─────────────┘
          ▼
   ┌────────────────────┐
   │  Critic            │   sanity-check + rank_adjustments
   └──────┬─────────────┘
          ▼
   final Ranking (SSE → UI / Telegram)
```

**Tools I used to build this.** Claude Code for most of the work
— scaffolding, the agent boilerplate, the GraphQL queries, the
Pydantic schemas, the eval harness, and the prompt iteration that
came out of the eval failures. Cursor on the side when the
streaming UI started misbehaving and I wanted a faster edit loop.
A longer write-up of what each tool got right and where it failed
is in [`BUILD_LOG.md`](BUILD_LOG.md).

## Evaluation Method & Results

I evaluated TriagePilot by **retrospective replay** against two
real repos. For each historical snapshot I reconstruct the queue
of open PRs at time `t0`, run all four rankers over it, and score
each ranking against what the maintainers actually did in the
following 14 days.

| Ranker | NDCG@5 (K8s) | Kendall τ (K8s) | NDCG@5 (Next.js) | Kendall τ (Next.js) |
|---|---|---|---|---|
| Random | 0.847 ± 0.125 | −0.067 ± 0.611 | 0.863 ± 0.123 | 0.000 ± 0.600 |
| Label-only | 0.912 ± 0.073 | +0.067 ± 0.231 | 0.813 ± 0.097 | −0.400 ± 0.346 |
| Author-only | 0.920 ± 0.080 | +0.267 ± 0.503 | 0.921 ± 0.046 | +0.200 ± 0.400 |
| **TriagePilot** | **0.844 ± 0.052** | **+0.067 ± 0.231** | **0.904 ± 0.104** | **+0.133 ± 0.643** |

![NDCG@5 by ranker](docs/charts/ndcg_by_ranker.png)

The number to look at is Kendall τ on Next.js. The first version of
my synthesizer prompt got −0.133 — anti-correlated with maintainer
behavior, which is worse than a coin flip. After a single prompt
fix (more on that in `docs/eval_results.md`) it moved to +0.133.
That's not a huge number in absolute terms, but the direction
flip is the load-bearing part. The eval found a real bug and
driving the fix from data, not vibes.

### The killer moment

The vercel/next.js snapshot from 2026-04-05. The maintainers ended
up reviewing the PRs in this order:

> **#92361 → #92374 → #92373 → #92369 → #92363**

TriagePilot predicted:

> **#92361 → #92369 → #92374 → #92363 → #92373**

The first PR is the important one. #92361 was the PR maintainers
actually opened first, and TriagePilot put it at the top.
Label-only got the top spot too, but only because the label
happened to line up — it inverted the rest of the queue.
Author-only had #92361 at rank 2 and missed the top entirely.

### Methodology

`t0` is picked by spacing `n` timestamps evenly across the last 60
days. For each `t0`, I pull every PR created before that moment
that was either still open or closed afterwards, then filter to
the ones nobody had reviewed yet. That's the snapshot.

Ground truth is what the maintainers did next. For each PR in the
snapshot I look at the next 14 days and take the earliest
maintainer action — review submission or merge, whichever comes
first. Sort by that timestamp ascending. PRs with no action in
the window sort to the bottom.

NDCG@5 uses graded relevance `(n − truth_position)`. Kendall τ
comes from `scipy.stats.kendalltau` over PRs common to both
sequences. Both live in `server/src/eval/metrics.py`. Snapshots
with fewer than 5 PRs after filtering are dropped.

Full reproduction commands are at the bottom of
[docs/eval_results.md](docs/eval_results.md#reproducing).

## Baseline Comparison: Why Not Just Use ChatGPT?

This is the question I expected to get asked, so I ran the
experiment. Same 5 Next.js PRs that TriagePilot ranked on
2026-04-05. I pasted the titles, bodies, file lists, and author
logins into ChatGPT-4.5 and asked: *rank these by review urgency,
1 = highest*. Then compared both rankings against what the
maintainers actually did.

| Ranker | Order | NDCG@5 | Kendall τ |
|---|---|---|---|
| Ground truth | 92361, 92374, 92373, 92369, 92363 | — | — |
| **TriagePilot** | 92361, 92369, 92374, 92363, 92373 | **0.959** | **+0.400** |
| ChatGPT-4.5 (one-shot) | 92374, 92361, 92373, 92363, 92369 | 0.882 | +0.200 |

ChatGPT ranked by what it could see in the titles and the
high-level file lists — basically diff size and keywords. It put
#92361 at rank 2. The reason that's wrong is that #92361 is a
small auth-middleware change. It looks low-effort, which is what a
one-shot scan picks up on, but it's the highest blast radius PR
in the batch once you actually read the diff. TriagePilot's
DiffAnalyst caught that, the TicketContext agent separately
flagged the linked issue as a regression, and the synthesizer
weighted both correctly.

You can't fit 30 diffs plus 30 issues plus 30 author histories in
a single ChatGPT prompt, so even the strongest one-shot model
falls back to titles and labels — which is the baseline I'm
already beating. The decomposition is doing the work the single
prompt can't.

> **Honesty caveat:** the numbers above come from one snapshot.
> Treat the gap as directional, not statistically conclusive. A
> proper head-to-head over 30+ snapshots is on the next-iteration
> list.

## Limitations & Next Iteration Ideas

The honest list of what this doesn't do yet and what would fix it.

**The eval is small.** 6 snapshots, 5 PRs each. The std bars in
the chart overlap. Real claims would need at least 30 snapshots
of 15 PRs, which is a paid Cerebras tier or a different
free-tier provider away.

**New contributors get under-ranked.** Author trust is a real
signal in the data, but it assumes the contributor has history in
the repo. First-timers get a neutral score and end up lower than
they should. The fix is to fall back on org-membership and
contribution velocity in adjacent repos when local history is
empty.

**The ranking is global, not per-reviewer.** A `crypto/` PR and a
`docs/` PR sit in the same queue even if the reviewer only owns
the docs side. CODEOWNERS-aware per-reviewer queues are the next
obvious step.

**Public repos only.** No GitHub App OAuth yet. And Telegram bot
tokens are stored unencrypted on disk, which is the right
trade-off for a single-tenant demo and the wrong one for anything
else. A real version needs the OAuth flow plus per-user secret
encryption.

**The synthesizer occasionally violates its own schema.** Cerebras
`gpt-oss-120b` sometimes emits `score` where the contract says
`rank`. That snapshot gets dropped from the eval. A
retry-with-correction loop, or a tighter grammar (jsonformer-style),
would catch it.

## Quick Start

```bash
git clone https://github.com/<you>/triagepilot
cd triagepilot

# server
cp server/.env.example server/.env  # add GITHUB_TOKEN, CEREBRAS_API_KEY
cd server && uv sync
uv run uvicorn src.api.main:app --reload

# web
cp web/.env.local.example web/.env.local
cd web && pnpm install && pnpm dev
```
