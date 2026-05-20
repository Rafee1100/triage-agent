# Architecture & Decisions

A running log of the choices that shaped TriagePilot — *what* was
decided, *why*, what I considered first, and the consequence I'm
living with. Sorted oldest at the top.

## Architecture at a glance

```
┌──────────┐        ┌──────────────────┐        ┌────────────┐
│  Next.js │  SSE   │   FastAPI server │  HTTP  │  GitHub    │
│   web    │◄──────►│  + APScheduler   │◄──────►│  GraphQL   │
└────┬─────┘        └────┬─────────────┘        └────────────┘
     │                   │
     │                   │  LiteLLM (provider-agnostic)
     │                   ▼
     │           ┌───────────────────┐
     │           │  Cerebras (LLM)   │
     │           │  gpt-oss-120b     │
     │           └───────────────────┘
     │                   │
     │                   ▼
     │           ┌───────────────────┐
     └──────────►│  Telegram Bot API │ (scheduled briefs)
                 └───────────────────┘

Persistence: JSON files on disk (server/data/*.json).
No database. No queue. No external cache.
```

Three runtimes:

1. **FastAPI server** (`server/`) — agent pipeline, SSE streams,
   subscription CRUD, APScheduler for morning briefs.
2. **Next.js web app** (`web/`) — manual triage UI, subscription
   modal, EventSource consumer.
3. **Background scheduler** — `AsyncIOScheduler` instance lives
   inside the FastAPI process, no separate worker.

Five agents in the pipeline, fanned out per-PR then synthesized:

```
   DiffAnalyst    ┐
   TicketContext  ├── per-PR (asyncio.gather)
   AuthorProfile  ┘
        │
        ▼
   Synthesizer    (batch over all PRs)
        │
        ▼
   Critic         (sanity check + rank adjustments)
```

---

## Decisions

### 1. Multi-agent decomposition over one big prompt

**Decision.** Split per-PR analysis into three small specialist
agents (DiffAnalyst, TicketContext, AuthorProfile) that produce
typed structured outputs, then fan in to a Synthesizer that ranks
the batch, followed by a Critic that sanity-checks the ranking.

**Why.** A single LLM call can't simultaneously read 30 diffs, 30
linked issues, and 30 author histories within any reasonable
context window. Decomposition gives each agent a focused job, a
small schema, and a short prompt — and the Synthesizer gets to
weigh *structured* intermediate signals rather than re-derive them
from raw text every time.

**Alternatives considered.**
- *One mega-prompt with the entire PR queue.* Hits context limits
  on real repos, blows up cost, and gives no intermediate signal
  for the eval to diagnose.
- *No Critic.* Worked fine in isolation but provided a useful
  rank-adjustment hook for the eval to flag obvious mis-rankings.

**Consequence.** More tool-calls per pipeline run (~3N + 2). The
eval validated the decomposition was doing real work — see
"Baseline Comparison" in the README.

---

### 2. Cerebras gpt-oss-120b as the default LLM

**Decision.** Use `cerebras/gpt-oss-120b` via LiteLLM for all five
agents, default. Env vars `HAIKU_MODEL` / `SONNET_MODEL` allow
switching providers without code changes.

**Why.** Free tier with reliable tool-calling and high throughput.
Anthropic Claude was the original plan, but a 24-hour Quest budget
made the paid tier infeasible.

**Alternatives considered.**
- *Groq* (initial choice). Throttled at 6k TPM, cascaded into
  120s+ per call once I hit 5/15 agents. Switched mid-build.
- *Cerebras llama-3.3-70b.* 404'd — not on free tier. The free-
  tier API returns it from `GET /v1/models` only with a paid key.
  Lesson cached: always `GET /v1/models` before changing provider
  defaults.
- *Cerebras llama3.1-8b.* Tool-calling silently produces malformed
  JSON. Skip.
- *Anthropic Claude.* Better quality almost certainly, but
  prohibitive on the 24-hour budget. The codebase is ready: flip
  the env vars and it just works.

**Consequence.** Cerebras free-tier TPM still gates batch size —
the eval was forced to `--limit 5 PRs` to avoid throttling. The
LiteLLM abstraction means the upgrade path is one env-var change.

---

### 3. Pydantic v2 + tool calling for structured agent outputs

**Decision.** Every agent returns a typed `pydantic.BaseModel`.
The LLM is forced through LiteLLM's tool-call interface; I never
parse free-form text.

**Why.** Schema validation on the way back. Tool-calling models
emit JSON that fits a schema by construction, so 90%+ of outputs
just parse; the remaining 10% are caught by `ValidationError` and
retried.

**Alternatives considered.**
- *Free-form text + regex parsing.* Brittle, drifts as prompts
  change, no validation.
- *JSON mode without tool calls.* Some providers (Cerebras
  included) implement tool-calling but not strict JSON mode, and
  tool-calling has better grammar conformance.

**Consequence.** Two recurring failure modes that needed
defensive code:
- `risk_tags` and `keywords_extracted` sometimes come back as
  bare strings instead of lists. Fixed with `mode="before"`
  Pydantic validators that wrap strings in single-element lists.
- The synthesizer occasionally emits `score` instead of `rank`.
  Currently logged + dropped from the batch. *Todo:* retry-with-
  correction loop.

---

### 4. SSE for the streaming UI, not WebSocket

**Decision.** Server-Sent Events via `sse-starlette` on the
backend, native `EventSource` on the frontend.

**Why.** One-way streaming (server → browser) is all I need:
agent progress events, never client-to-server events on the same
channel. SSE has zero handshake overhead and works through
proxies that block WebSocket upgrades (Render, Vercel both
flaky on WS).

**Alternatives considered.**
- *WebSocket.* Overkill, more failure modes, worse proxy story.
- *Long-polling.* Higher latency, more server load.

**Consequence.** One subtle bug: `EventSource`'s native `onerror`
fires on transport drops, but `addEventListener("error", ...)`
also fires on a custom SSE event named `error`. I was emitting
`error` as a pipeline-failure event, which collided. Fix: renamed
the backend event to `pipeline_failed`.

---

### 5. JSON file persistence, no database

**Decision.** Persist subscriptions to `server/data/subscriptions.json`.
Persist eval snapshot data to `server/data/*.json`. No database.

**Why.** Demo-scale; single-tenant; the cost of backing up a
sqlite file in a Render volume is higher than the cost of
re-fetching from GitHub. JSON is the right shape for this scale.

**Alternatives considered.**
- *SQLite.* More overhead, requires migrations as the schema
  evolves, and no real benefit at this scale.
- *Postgres.* Way overkill.

**Consequence.** The `SubscriptionStore` uses a simple
file-replace-on-write pattern. Tokens are stored unencrypted —
documented in the UI as "keep this instance private."
`.gitignore` excludes `server/data/*.json` to prevent committing
real tokens. *Next iteration:* per-user secret encryption +
GitHub App OAuth flow.

---

### 6. APScheduler in-process, not a separate worker

**Decision.** `AsyncIOScheduler` runs inside the FastAPI process,
hydrated from `SubscriptionStore` on startup.

**Why.** Zero ops surface. The same process that serves
`/subscriptions` CRUD also fires the jobs. No Celery, no Redis,
no Procfile complexity. Subscriptions are persisted to disk so
they survive restarts.

**Alternatives considered.**
- *Celery + Redis.* Industry standard, but four moving parts
  where one suffices.
- *External cron* (e.g., `cron-job.org` hitting an endpoint).
  Tighter coupling to a third-party scheduler; harder to test.

**Consequence.** The scheduler dies if the FastAPI process dies
or sleeps. On Render free tier this matters: the process
spins down after 15 min idle. Solution: `cron-job.org` pings the
`/health` endpoint every 10 min to keep the process warm. This
isn't elegant — it's the price of free tier.

---

### 7. Retrospective-replay eval against real repos

**Decision.** For each historical `t0`, reconstruct the open PR
queue at that moment, run all rankers on it, and score against
the actual maintainer review order over the next 14 days.

**Why.** Synthetic eval data ("rank these fake PRs") lies. Real
maintainer behavior is the only honest ground truth for a
ranking problem like this. NDCG@5 + Kendall τ are the right
shape because I care about ordering, not classification.

**Alternatives considered.**
- *Human-labeled ranking.* Slow, biased, doesn't scale.
- *Synthetic PRs.* Provides no signal about real-world failure
  modes (and indeed the v1 polarity bug only became visible on
  real data — see decision #8).
- *Time-to-merge as truth.* Confounded by PR size — large PRs
  take longer for reasons unrelated to review urgency. First
  review action is closer to "what did the maintainer prioritize."

**Consequence.** Eval is expensive (real LLM calls) and rate-
limit-throttled. Currently 6 snapshots × 5 PRs total — directional
but not statistically conclusive. Standard-deviation bars overlap.

---

### 8. Synthesizer prompt polarity (trust_score as positive signal)

**Decision.** Trust score weighted *positively* (+0.20), not
*inversely* as scrutiny-needed.

**Why.** The v1 prompt had `+ 0.10 * (1 - trust_score)` on the
theory that low-trust authors need more scrutiny. Eval showed
this produced rankings *anti-correlated* with maintainer
behavior (Kendall τ = −0.500 on K8s). Maintainers review trusted
contributors *first* because their code lands faster — so
trust is a positive signal, not an inverse one.

**Alternatives considered.**
- *Drop the trust term entirely.* Would lose useful signal —
  Author-only baseline was a strong ranker in the data.
- *Higher weight (0.30+).* Risk of devolving into Author-only.
  0.20 was the smallest bump that moved tau from negative to
  positive on both repos.

**Consequence.** Single prompt edit, no code change. Kendall τ
flipped from −0.500 → +0.067 (K8s) and −0.133 → +0.133 (Next.js).
Full diff in [eval_results.md § Failure mode found and fixed](eval_results.md#failure-mode-found-and-fixed).
The lesson: eval-driven prompt-tuning beats armchair theorizing.

---

### 9. LiteLLM as the model router

**Decision.** All LLM calls go through `litellm.acompletion(...)`.
Models are referenced as opaque strings (`cerebras/gpt-oss-120b`,
`anthropic/claude-haiku-4-5-...`).

**Why.** Provider-agnostic by construction. Tool-calling, retries,
streaming all work the same across providers. Switching costs
zero code — only env-var changes.

**Alternatives considered.**
- *Direct Anthropic SDK.* Locks in one provider, no fallback.
- *Custom HTTP shim.* Reinventing LiteLLM badly.

**Consequence.** A thin layer of LiteLLM-isms in the codebase
(retry codes, error parsing). Worth it — the Groq → Cerebras
migration was a one-line model swap.

---

### 10. Render over Fly.io for the backend host

**Decision.** Deploy the FastAPI server to Render via
`render.yaml` Blueprint.

**Why.** Fly.io's trial tier capped Machines at 5 minutes of
runtime, and adding a credit card wasn't an option. Render's
free tier gives 750 hr/month and the Blueprint format made
deployment three lines of YAML.

**Alternatives considered.**
- *Fly.io.* The original target. Killed by the trial cap.
- *Railway.* Free tier doesn't include 24/7 services anymore.
- *Vercel functions.* Wrong shape — APScheduler needs a long-
  lived process.

**Consequence.** Free-tier instances spin down after 15 min idle,
which means a `cron-job.org` keepalive ping. The Dockerfile uses
shell-form `CMD` so Render's `$PORT` env var gets expanded
correctly at runtime.

---

### 11. Frontend: Next.js 16 + Tailwind v4 + Base UI

**Decision.** Next.js App Router, Tailwind v4, shadcn-style
components built on Base UI primitives.

**Why.** Latest stable stack. App Router for SSE-friendly
streaming. Base UI primitives because shadcn moved off Radix
recently and Base UI is the cleanest replacement.

**Consequence.** Tailwind v4 changed cursor defaults — buttons
no longer get `cursor: pointer` by default. Had to add it
explicitly to the Button variants and to plain `<button>`
example-repo links.

---

## How to add a new decision

When a non-obvious choice is made, add an entry here. Keep the
five fields: Decision, Why, Alternatives considered, Consequence.
The Consequence section is the most important — it's where
future-you (or a new contributor) finds out *what to expect*
from this codebase that wouldn't be obvious from reading the code.
