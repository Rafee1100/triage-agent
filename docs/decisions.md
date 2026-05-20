# Architecture & decisions

A log of the non-obvious choices in TriagePilot. Each entry is what
I picked, what I considered first, and what I'd have to live with
because of it. Written in roughly the order the decisions came up.

## The shape of the system

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
     └──────────►│  Telegram Bot API │
                 └───────────────────┘
```

Persistence is JSON files on disk under `server/data/`. No database,
no queue, no external cache. There are exactly two runtimes — the
Next.js web app and the FastAPI server. The scheduler runs inside
the FastAPI process; it doesn't get its own.

The agent pipeline goes:

```
   DiffAnalyst    ┐
   TicketContext  ├── per-PR, in parallel
   AuthorProfile  ┘
        │
        ▼
   Synthesizer    (batch over all PRs)
        │
        ▼
   Critic
```

---

## 1. Five agents instead of one big prompt

Splitting per-PR work into specialists (DiffAnalyst, TicketContext,
AuthorProfile) and then aggregating with a Synthesizer plus a Critic
was the call I made first. A single LLM call can't fit 30 diffs, 30
issues, and 30 author histories in one context, and even if it
could, you'd be asking the model to do everything implicitly with no
intermediate signal to check.

The cheap version is one mega-prompt with the whole PR queue. I
rejected it because it gives the eval nothing to look at — when the
ranking is wrong, you have no idea which signal was misread.

The Critic feels redundant in isolation, but it's a useful hook for
the eval: when it disagrees with the Synthesizer, that's a marker
worth looking at.

Cost of this design: about 3N + 2 tool calls per pipeline run. Worth
it. The eval confirmed the decomposition was doing real work — see
the ChatGPT comparison in the README.

## 2. Cerebras gpt-oss-120b as the default model

All five agents point at `cerebras/gpt-oss-120b` through LiteLLM by
default. Anthropic Claude would almost certainly be better quality,
but the 24-hour budget wouldn't cover it. Cerebras free tier was
the next thing.

A few things broke before I landed here:

- Llama 3.3 70B isn't on Cerebras free tier. The free-tier
  `/v1/models` endpoint hides it; the paid-key call returns it.
  Cost me half an hour. The lesson is now in my session memory:
  always call `/v1/models` directly before changing provider
  defaults.
- Llama 3.1 8B emits malformed JSON on tool calls. Tried it,
  abandoned it.
- Groq was the first provider I tried. 6k TPM. It throttled hard
  on the per-PR fan-out and I burned an hour tuning backoff
  before giving up and switching.

`gpt-oss-120b` is the one Cerebras free-tier model with reliable
tool-calling. The LiteLLM abstraction means upgrading to Claude
later is a one-line env-var change.

The trade-off I'm still paying for: free-tier TPM caps the eval
batch size. The current eval is `--limit 5 PRs` per snapshot.

## 3. Pydantic + tool-calling, no free-form parsing

Every agent returns a typed `BaseModel`. The LLM is forced through
LiteLLM's tool-call interface and the response is validated on the
way back. No regex parsing, no JSON-extraction heuristics, no
prompts that say "respond in this format please."

The reason is that an unsupervised eval loop needs schema
validation or it can't tell signal from noise. Tool-calling is also
a tighter grammar than JSON mode on most providers, including
Cerebras.

The cost: tool-calling models still drift from their schema in
small ways. The two patterns I had to add validators for:

- `risk_tags` and `keywords_extracted` sometimes come back as bare
  strings instead of lists. `field_validator(mode="before")`
  wraps them in a single-element list.
- The synthesizer occasionally emits `score` instead of `rank`.
  Currently logged and dropped from the snapshot. The honest fix
  is a retry-with-correction loop. Still on the todo list.

## 4. SSE, not WebSocket

The pipeline streams server → browser only. There's no
client-to-server channel sharing the same connection. SSE is the
right shape for that — zero handshake overhead, no upgrade
negotiation, works through proxies that drop WebSocket connections
(Vercel and Render are both flaky on WS in my experience).

WebSocket would have been overkill. Long-polling would have been
worse on latency and load.

The one thing that bit me: `EventSource`'s `addEventListener("error", ...)`
fires both on transport drops and on a custom SSE event literally
named `error`. I'd been emitting a `error` event from the backend
for application-level failures, and the two were colliding. Every
real backend error showed "stream connection lost" on the client.
Fix was to rename the backend event to `pipeline_failed` and split
the client handler.

## 5. JSON files, no database

Subscriptions live in `server/data/subscriptions.json`. Eval
snapshots live in `server/data/*.json`. No SQLite, no Postgres.

The first proposal I got was a four-table schema with a users
table, an audit log, and migration scaffolding. Wrong shape for a
single-tenant demo. The whole `SubscriptionStore` is about 80 lines
and uses a file-replace-on-write pattern.

The risk I'm carrying: bot tokens are stored unencrypted. I
documented this in the UI as "keep this instance private" and
gitignored `server/data/*.json` so I can't accidentally push real
tokens. For a real product this needs per-user secret encryption
plus a GitHub App OAuth flow. Not in scope for the Quest.

## 6. APScheduler inside the FastAPI process

The scheduler is an `AsyncIOScheduler` instance that lives inside
the same FastAPI process. On startup it hydrates from the
subscription store; jobs are added/removed via the same CRUD
endpoints that serve the UI.

Celery plus Redis would have been the textbook answer. Four moving
parts instead of one, with nothing to show for the extra
complexity at this scale.

The downside is that the scheduler dies if the FastAPI process
dies. On Render's free tier, the process spins down after 15
minutes of idle, which would mean missed morning briefs. The
workaround is a cron-job.org ping to `/health` every 10 minutes to
keep the instance warm. It's not elegant. It's free.

## 7. Retrospective replay as the eval

The eval reconstructs the queue of open PRs at a historical
moment, runs every ranker over the same PRs, and scores each
ranking against what the maintainers actually did over the next
14 days. The ground truth is the maintainers' own behavior.

Alternatives I rejected:

- Human-labeled rankings. Slow, biased, doesn't scale.
- Synthetic PRs. They tell you nothing about real failure modes,
  and the polarity bug in the v1 prompt only became visible on
  real data.
- Time-to-merge. Confounded by PR size — large PRs take longer to
  review for reasons unrelated to urgency. First maintainer action
  is a better proxy for "what did they actually prioritize."

The downside is cost. Each snapshot is real LLM calls plus real
GitHub API calls. The current run is 6 snapshots of 5 PRs, which
is directional but doesn't satisfy a statistician. The std bars
overlap. A real version would be 30 snapshots of 15 PRs, which
needs a paid Cerebras tier or a different provider.

## 8. Trust as a positive signal (the polarity fix)

The first version of the synthesizer prompt scored trust as
`+ 0.10 * (1 - trust_score)`. The theory was that unfamiliar
contributors need more scrutiny and therefore higher priority.
The eval said no.

Kendall τ on Kubernetes for the v1 prompt: −0.500. That's not noise.
It's the model ranking PRs almost exactly the reverse of how
maintainers actually reviewed them. What the data was telling me
is that maintainers review trusted contributors first because their
code lands faster, so trust is a positive signal, not an inverse
one.

I flipped the term to `+ 0.20 * trust_score` and rebalanced
blast-radius from 0.40 → 0.30 to keep the sum at 1.0. Every metric
improved on both repos. Kubernetes Kendall τ went from −0.500 to
+0.067; Next.js from −0.133 to +0.133. Full diff in
[eval_results.md](eval_results.md#failure-mode-found-and-fixed).

This is the part of the build I'm happiest with. The eval wasn't a
checkbox. It found a real bug, drove a real fix, and the fix moved
the numbers in the right direction on the first try.

## 9. LiteLLM as the model router

Every LLM call goes through `litellm.acompletion(...)`. Models are
strings (`cerebras/gpt-oss-120b`, `anthropic/claude-haiku-4-5-...`),
not provider SDK classes.

This is mostly defensive — I knew there was a real chance I'd have
to switch providers mid-build. (I did, twice.) The Groq to Cerebras
swap was a one-line model-string change.

The cost is a thin layer of LiteLLM-isms in the codebase: retry
codes, error parsing. Worth the abstraction.

## 10. Render after Fly's trial cap

Fly was the original target. Their trial Machines stop after 5
minutes of runtime and I couldn't get a credit card on the account
in time. Render's free tier (750 hr/month) was the next move.

The render.yaml Blueprint format made deployment about three lines
of YAML, but the Dockerfile's exec-form `CMD` doesn't expand
`$PORT`, so the first deploy crashed in a restart loop until I
switched to shell-form. Free-tier idle spin-down is dealt with by
the cron-job.org ping.

Other options I dismissed: Railway (free tier doesn't include
24/7 services anymore), Vercel functions (wrong shape — APScheduler
needs a long-lived process).

## 11. Next.js 16 + Tailwind v4 + Base UI

Latest stable web stack. App Router for the streaming UI. shadcn
moved off Radix recently, so the underlying primitive is Base UI
now and that's what I used.

The thing nobody warned me about: Tailwind v4 silently changed
button cursor defaults. `cursor-pointer` is no longer implied. I
noticed because the live UI had the wrong cursor everywhere; the
fix was to add it to the Button variants explicitly. Small thing,
but the kind of papercut that's worth writing down.
