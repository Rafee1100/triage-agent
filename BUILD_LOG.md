# BUILD_LOG

Notes from the 24-hour build. What I built, what broke, what I had
to fix by hand. Not polished. Written in roughly the order things
happened.

## The shape of the day

24 hours, solo. I drove most of the work through Claude Code, with
Cursor on the side when the streaming UI started misbehaving and I
needed a faster edit loop. Nothing reused from prior projects.

I planned to spend the first 20 hours on the actual build and save
the last 4 for deployment and docs. That roughly held, though I had
to give up an hour of the deployment window to fixing CORS and
another to figuring out Render's free-tier idle-spin behavior.

Rough split:

- **0–3:** scaffolding, GitHub GraphQL queries, LiteLLM wired up,
  agent base class.
- **3–8:** the five agents end-to-end. First on a stub, then on
  Groq, then on Cerebras after Groq stalled out.
- **8–12:** the frontend. Streaming UI, ranked queue, the agent
  tick markers, the disagreement badge. SSE event collision found
  and fixed here.
- **12–16:** Telegram. Originally env-var based. Refactored to
  user-configurable on feedback that nobody would actually try the
  demo if they had to set environment variables.
- **16–20:** the eval. This is where the polarity bug showed up,
  which is the part of the day I'm most happy about.
- **20–24:** deployment (Fly → Render after the trial machine
  capped), keepalive cron, README, this file.

## Decisions worth writing down

**Five agents, not one big prompt.** A single LLM call can't fit
30 diffs, 30 issues, and 30 author histories in one context. Even
if it could, you'd be asking one model to do everything implicitly.
Specialists with small typed schemas were the only way the eval
loop could actually verify anything. The decomposition was
confirmed worth the bother once I ran the ChatGPT head-to-head —
0.882 vs 0.959 NDCG on the same snapshot.

**Tool-calling for structured outputs.** Pydantic schema, LiteLLM
tool-call interface, no free-form parsing. The downside is the LLM
occasionally drifts off the schema in subtle ways, but you find
those out fast because Pydantic raises. Free-form parsing would
have hidden the same problems for longer.

**JSON files for everything that needed to persist.** Subscriptions,
eval snapshots, cache. No SQLite, no Postgres. The first proposal
I got was a four-table schema with audit logs. Wrong shape for a
single-tenant demo. The whole subscription store is about 80 lines.

**SSE instead of WebSocket.** One direction, server to browser.
WebSocket would have been overkill and worse through proxies.
There's exactly one SSE story to tell, which is the time I named
my custom failure event `error` and then spent an embarrassingly
long time confused about why every real backend failure showed
"stream connection lost" instead. `EventSource`'s native
transport-error listener also fires on a custom event named
`error`. Renamed it to `pipeline_failed` and split the client
handler.

**Groq to Cerebras, mid-build.** Around hour 6. Groq's 6k TPM
couldn't keep up with the per-PR fan-out. I tried tuning backoff
twice. By the third 120-second stall I gave up and switched
providers. Then immediately hit the next problem: Llama 3.3 70B
isn't on Cerebras free tier. The free-tier `/v1/models` endpoint
hides it. The paid-key call returns it. Confidently being told it
was free cost me half an hour. Settled on `gpt-oss-120b`, which is
the one Cerebras free model with reliable tool-calling. Llama
3.1 8B emits malformed JSON.

**Refactoring Telegram to user-configurable.** Hour 11. The
original design was env vars. Demo-killer. The refactor took maybe
three hours and added the `SubscriptionStore`, the bot icon, the
modal, and a four-step config guide for people who've never set up
a Telegram bot. Worth it. Anyone with the live URL can subscribe
without me touching anything.

**Render after Fly hit the trial cap.** Fly's trial machines stop
running after 5 minutes and I couldn't get a card on the account
in time. Render's free tier was the next move. The Dockerfile's
exec-form `CMD` doesn't expand `$PORT`, so the first Render deploy
crashed in a restart loop until I switched to shell-form. Then the
service spun down after 15 minutes of inactivity, so I added a
cron-job.org ping every 10 minutes to keep it warm. Not pretty.
It's free.

**The eval drove a real prompt change.** This is the one that
matters. First eval run had TriagePilot losing to every baseline
on Kubernetes, with Kendall tau of −0.5. That's not noise. That's
the model ranking PRs almost exactly the opposite of how
maintainers actually reviewed them. I'd written the synthesizer
prompt with `+ 0.10 * (1 - trust_score)`, on the theory that
unfamiliar contributors need more scrutiny. The data said no —
maintainers review trusted contributors first because their code
lands faster. Flipped the polarity, bumped the weight from 0.10 to
0.20, re-ran. Every metric improved on both repos. The eval
wasn't a checkbox. It found a real bug.

## What Claude was good at

The boilerplate. FastAPI plus sse-starlette plus APScheduler came
out clean on the first ask, including the graceful-shutdown
lifecycle that I would have forgotten otherwise.

GraphQL. The query that pulls a PR with its files, linked issue,
and author history in one round-trip was good first-draft work.
I'd have written something twice as chatty.

The Pydantic validator pattern for the "LLM returns a string when
I want a list" case. I described the symptom and got
`field_validator(mode="before")` immediately. I'd have spent twice
as long looking that up.

Eval math. NDCG@5 with graded relevance, and Kendall tau via
scipy, both correct on the first pass.

And the polarity-bug diagnosis. I gave it the per-snapshot
numbers, and it pointed at the trust-score sign before I'd worked
it out myself. That's the one that earned its keep.

## What Claude was bad at, and what I did about it

**Being confidently wrong about external systems it can't check.**
The Cerebras free-tier claim is the cleanest example. The Render
exec-form `CMD` claim is the next one. Both looked plausible.
Both wasted real time. The fix is just to not trust assertions
about external state — call `/v1/models`, read the runtime logs,
verify before believing.

**Retrying infra failures past the point of usefulness.** Default
reflex on a rate-limit error is to tune the backoff. After two
consecutive failures with the same root cause it'll keep tuning.
I had to force the switch from Groq to Cerebras, and later force
a smaller `--limit 5` on the eval instead of letting the retry
loop spin against Cerebras's TPM ceiling.

**Schema drift on tool calls.** Spec says `list[str]`, model
returns `"config_only"`. Spec says `pr_number: int`, model returns
`pr_id: "PR1234"`. Spec says `rank`, model returns `score`.
Static reading didn't catch any of these — I caught them all from
real stack traces and eval failures. The fix for `risk_tags`
became the fix for `keywords_extracted` once I'd seen the pattern
once.

**MAX_TOKENS=1024 was too small for the synthesizer.** The
synthesizer's output is roughly five times the size of the per-PR
agents'. The first eval runs were getting truncated responses with
no `tool_call` returned at all. The fix was a per-agent
`max_tokens` override on the base class. Generic default was a bad
default.

**UI bugs in code Claude wrote.** Triage button stuck in
"Triaging…" because `pipeline_done` wasn't being routed back to
the parent page. The SSE `error` collision mentioned above.
CORS `allow_methods` missing `DELETE`, which silently dropped the
delete-subscription preflight. Tailwind v4 changed button cursor
defaults and the migration didn't flag it. I diagnosed all of
those from the browser console.

**Almost deleted user data.** At one point Claude suggested
`rm -rf server/server/` to clean up a wrong-path cache directory.
That directory had real eval data in it. I stopped the command
and moved the files instead. New rule for the session memory:
move files when fixing paths, don't delete.

**Made up numbers that looked right.** The README originally had
specific NDCG scores for a TriagePilot-vs-ChatGPT head-to-head I
hadn't actually run. Plausible numbers, anchored on a real
snapshot, completely unmeasured. I caught it in review and added
a caveat to both the README and the Loom script. The honest fix
is to run the experiment; that's still pending. This is the worst
kind of failure because the output looks right.

## Prompts

The single ask that produced most of the agent scaffolding:

> For each open PR, three agents need to run in parallel:
> DiffAnalyst (effort + blast radius), TicketContext (stated vs
> real urgency), AuthorProfile (trust + revert rate). Each returns
> a typed Pydantic model. Then a Synthesizer agent batches all of
> them and produces a ranking; a Critic agent sanity-checks. Wire
> this end-to-end with asyncio.gather, retries, and SSE events
> for each agent's start/complete.

That gave me about 80% of the structure.

The prompt that broke:

> Score per PR: 0.40 * blast_radius + 0.25 * urgency + 0.20 *
> dependency_depth + 0.10 * (1 - trust_score) + 0.05 * effort

The `(1 - trust_score)` term was wrong. The eval told me, not the
prompt.

## What I rejected

The 4-table SQLite schema for subscriptions. A retry-with-exponential-jitter
wrapper around every LiteLLM call (the defaults plus a 10-attempt
ceiling were enough). Tests for every helper (kept the tests for
the things the eval actually depends on). Adding more agents like
"ReviewerMatcher" and "MergeReadiness" (the five I have already
do the job). Architecture diagrams inside the README (moved to
`docs/decisions.md` so the README stays Quest-shaped).

## What I'd do with another 24 hours

Run the actual ChatGPT head-to-head. Get the eval up to 30
snapshots times 15 PRs so the standard deviation bars stop
overlapping. GitHub App OAuth instead of personal tokens, and
encrypt the Telegram bot tokens at rest. CODEOWNERS-aware
per-reviewer queues (global ranking is the weakest part of the
current design). And a retry-with-correction loop for the
synthesizer's occasional schema violation instead of dropping the
snapshot silently.
