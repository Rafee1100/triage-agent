# TriagePilot — Quest 1 Build Plan

> **One-liner:** A multi-agent AI that reads your open PRs (diff + linked issue + author history + cross-PR dependencies), and produces a ranked, justified review queue that occasionally disagrees with the ticket labels — delivered as a morning Telegram brief.

> **Target user:** Senior engineers and tech leads who get more PRs than they can review carefully, and whose ticket labels (Jira/Linear/GitHub Issues) are often stale, inflated, or wrong.

> **Tagline for the Loom:** *"Your labels lie. TriagePilot tells you the truth, every morning at 9 AM."*

---

## 1. Quest 1 Compliance Map

This is the contract. Every requirement maps to a deliverable.

| Quest 1 Requirement | Where It's Satisfied |
|---|---|
| Real problem, real user | Section 2 (Problem Statement) + dogfooded by the builder |
| AI used meaningfully (agent / workflow / eval loop / custom prompting) | Section 4 (Multi-agent architecture) + Section 6 (Eval loop) |
| Deployed live | Section 8 (Deploy: Fly.io) |
| Public GitHub repo | Section 11 (Repo structure) |
| `README.md` with all 7 sections | Section 11 (README skeleton) |
| `BUILD_LOG.md` honest journey | Section 12 (BUILD_LOG template) |
| 5-minute Loom | Section 13 (Loom script) |
| Working live URL | Section 8 (Fly.io deploy) |
| Document AI tools used (Cursor / Claude Code / etc.) | BUILD_LOG section "AI Tools Used" |

---

## 2. Problem Statement

Every senior engineer wakes up to a queue of 10–30 open PRs. The labels say "High / Medium / Low" but real urgency rarely matches:

- A "Low" priority PR touches authentication middleware and blocks two other PRs
- A "High" priority PR is a CI config tweak the author can self-merge
- A PR by a new contributor on a critical module deserves more eyes than a senior's typo fix in docs
- A 2-line PR labeled "Critical" takes 10 minutes; a 2000-line refactor labeled "Medium" takes 2 hours

Reviewers compensate by manually scanning every morning — burning 20–30 minutes of cognitive load before any real work happens. Most are wrong anyway: PRs slip, get stale, conflict, and become 2× the work to merge.

**The wedge:** Labels are metadata. The actual signal lives in the diff, the ticket text, the author's history, and the cross-PR dependency graph. AI can read all four and produce a ranking that beats the labels.

---

## 3. Solution Architecture

```
                                ┌──────────────────────────┐
                                │  GitHub GraphQL Fetcher  │
                                │  - Open PRs              │
                                │  - Linked issues         │
                                │  - Diffs (file paths)    │
                                │  - Author history        │
                                │  - PR cross-references   │
                                └────────────┬─────────────┘
                                             │
                                  ┌──────────▼──────────┐
                                  │  Feature Extractor  │
                                  │  Per-PR structured  │
                                  │  feature record     │
                                  └──────────┬──────────┘
                                             │
            ┌────────────────────────────────┼────────────────────────────────┐
            │                                │                                │
            ▼                                ▼                                ▼
   ┌────────────────┐              ┌────────────────┐              ┌────────────────┐
   │  Diff Analyst  │              │ Ticket Context │              │ Author Profile │
   │  (Haiku)       │              │ Agent (Haiku)  │              │ Agent (Haiku)  │
   │  effort,       │              │ stated vs true │              │ trust score,   │
   │  blast radius  │              │ urgency        │              │ failure rate   │
   └────────┬───────┘              └────────┬───────┘              └────────┬───────┘
            │                               │                               │
            └───────────────┬───────────────┴───────────────┬───────────────┘
                            │                               │
                            ▼                               ▼
                   ┌─────────────────────┐         ┌────────────────────┐
                   │ Dependency Detector │         │  Synthesizer Agent │
                   │  (deterministic +   │────────▶│  (Sonnet 4.5)      │
                   │   semantic)         │         │  produces ranking  │
                   └─────────────────────┘         │  + reasoning       │
                                                   └──────────┬─────────┘
                                                              │
                                                              ▼
                                                  ┌──────────────────────┐
                                                  │   Critic Agent       │
                                                  │   (Sonnet 4.5)       │
                                                  │   sanity-check pass  │
                                                  └──────────┬───────────┘
                                                             │
                                                             ▼
                                                ┌────────────────────────┐
                                                │  Final Ranked Queue    │
                                                │  - Position            │
                                                │  - PR + reasoning      │
                                                │  - Disagreement flag   │
                                                └────────────┬───────────┘
                                                             │
                                          ┌──────────────────┼──────────────────┐
                                          ▼                  ▼                  ▼
                                  ┌──────────────┐   ┌───────────────┐   ┌──────────────┐
                                  │  Web UI      │   │ Telegram Bot  │   │  Eval Harness│
                                  │  (Fly.io)    │   │ 9 AM brief    │   │ retrospective│
                                  └──────────────┘   └───────────────┘   │ replay       │
                                                                         └──────────────┘
```

**Why this passes the "AI used meaningfully" bar:**
1. **Multi-agent specialization** — five agents with distinct roles, not one mega-prompt
2. **Workflow** — orchestrated pipeline, not a single API call
3. **Custom prompting** — each agent has a tuned system prompt with rejection criteria
4. **Evaluation loop** — retrospective replay vs maintainer behavior produces real numbers, drives prompt iteration
5. **Self-improvement** — evening feedback loop (stretch goal, see Phase 9)

---

## 4. Tech Stack

**Single repository, two deploy targets.** The repo contains `/web` (Next.js → Vercel) and `/server` (Python/FastAPI → Fly.io). One `git push` triggers both deploys.

| Layer | Choice | Why |
|---|---|---|
| Backend language | Python 3.11 | Async + concurrent agent dispatch matches the I/O-bound workload; mature Anthropic SDK |
| Backend framework | FastAPI + `asyncio.gather` | Native SSE streaming, async-first, single-file entry |
| LLM | Anthropic Claude (Sonnet 4.5 + Haiku 4.5) | Sonnet for reasoning (synthesizer, critic); Haiku for per-PR analysis (cost + parallelism) |
| GitHub API | `httpx` + `gql` async | GraphQL single-round-trip for PR + issue + diff + author |
| Schema enforcement | Pydantic v2 | Strict JSON schemas for every agent output |
| Storage | SQLite + on-disk JSON cache | Zero-ops persistence in 24h |
| Frontend framework | Next.js 15 (App Router) + TypeScript | Server Components + streaming UI; canonical Vercel target |
| Frontend styling | Tailwind + shadcn/ui | Polished cards in minutes, not hours |
| Frontend streaming | Vercel AI SDK (consumer side) | Reads SSE from the FastAPI backend, renders tokens live |
| Telegram bot | python-telegram-bot | One-file integration on the FastAPI side |
| Scheduler | APScheduler (in-process) | No external cron infra |
| Backend deploy | Fly.io + single Dockerfile | Free tier, always-on, no timeout cap |
| Frontend deploy | Vercel + Root Directory: `web` | Free tier, instant `git push` deploys |
| Monorepo tooling | `pnpm` (web) + `uv` (server) + root `Makefile` | Two ecosystems, one developer experience |
| Eval metrics | `scipy.stats.kendalltau` + custom NDCG | Standard ranking metrics |

**One-paragraph rationale for the README:** *"I picked Python/FastAPI on Fly.io for the backend because the workload is 95% I/O-bound on Anthropic and GitHub calls — exactly where Python's asyncio shines. I picked Next.js + shadcn/ui on Vercel for the frontend because it produces a polished UI in less time than vanilla HTML and gives reviewers the demo URL they expect. The split avoids Vercel's serverless timeout entirely: heavy multi-agent work runs on Fly.io with no execution cap, while the static + interactive frontend ships on Vercel's globally-distributed free tier."*

---

## 5. 24-Hour Timeline

The clock is your real adversary. This is sized so you hit "deployed and runnable" by hour 18, leaving hours 19–24 for the eval results, README, BUILD_LOG, and Loom.

### Phase 0 — Setup (Hour 0 → 1.5)

The monorepo adds 30 minutes vs single-stack but pays back later. Do this carefully — broken cross-origin fetch at hour 22 is the worst-case outcome and this phase prevents it.

- [ ] Create public GitHub repo `triagepilot`
- [ ] Initialize **monorepo skeleton** with two directories:
  - `server/` — Python/FastAPI app, `pyproject.toml` via `uv init`
  - `web/` — Next.js app via `pnpm create next-app@latest web --typescript --tailwind --app --src-dir=false --import-alias="@/*"`
- [ ] Add root-level files: `README.md` (skeleton from Section 11), `LICENSE` (MIT), `.gitignore`, `Makefile` with shared targets (`make dev`, `make deploy-server`, `make deploy-web`, `make eval`)
- [ ] Add `server/.env.example` placeholders: `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `ALLOWED_ORIGIN`
- [ ] Add `web/.env.local.example` placeholders: `NEXT_PUBLIC_API_URL`
- [ ] Install `shadcn/ui` in `web/`: `pnpm dlx shadcn@latest init` then add `card`, `button`, `badge`, `input`, `skeleton`
- [ ] Get a GitHub personal access token (scope: `public_repo`) and an Anthropic API key
- [ ] Set up Fly.io: `fly launch --no-deploy` from `server/` (creates `triagepilot-api` app and `fly.toml`)
- [ ] Set up Vercel: import the GitHub repo in the Vercel dashboard, set **Root Directory** to `web`, set env `NEXT_PUBLIC_API_URL` to a placeholder (will update after Fly deploy)
- [ ] **CORS smoke test:** before writing any agent code, deploy a hello-world FastAPI returning `{"ok": true}` to Fly.io and a one-page Next.js app on Vercel that fetches it. Confirm the cross-origin fetch succeeds. *This step is non-negotiable* — CORS bugs at hour 22 kill submissions.
- [ ] **Commit 1:** `chore: monorepo scaffold with web/ (Next.js) and server/ (FastAPI)`

### Phase 1 — GitHub Data Pipeline (Hour 1 → 4)

- [ ] Implement GraphQL client (`src/github/client.py`) — single function: `fetch_pr_context(repo, pr_number) -> dict`
- [ ] Implement bulk fetcher: `fetch_open_prs_at(repo, timestamp) -> list[PRContext]` (for retrospective replay)
- [ ] Implement author history aggregator: `fetch_author_stats(repo, username) -> AuthorProfile`
- [ ] Add disk cache (joblib or simple JSON-on-disk) so re-runs are free
- [ ] Test on Kubernetes — fetch 20 open PRs end-to-end, confirm structure
- [ ] **Commits 2, 3, 4:** GraphQL client → PR + issue fetch → diff + author history fetch

### Phase 2 — Feature Extraction (Hour 4 → 5.5)

- [ ] Build `src/features/extractor.py` — turns raw GH data into a flat feature dict per PR:
  - `lines_added`, `lines_deleted`, `files_changed`, `file_paths`
  - `touches_auth`, `touches_db_migration`, `touches_config_only` (path heuristics)
  - `linked_issue_labels`, `linked_issue_priority`, `linked_issue_body_summary`
  - `author_merged_pr_count`, `author_revert_rate`, `author_avg_review_comments`
  - `pr_age_days`, `days_since_last_activity`
  - `mentioned_by_other_open_prs` (cross-reference)
- [ ] **Commits 5, 6:** feature extraction → cross-PR dependency detection

### Phase 3 — Multi-Agent Reasoning (Hour 5.5 → 11)

Build agents one at a time. Each agent has its own file, system prompt, and unit test.

- [ ] `src/agents/base.py` — shared abstractions (Agent class, retry, JSON schema enforcement)
- [ ] `src/agents/diff_analyst.py` (Haiku) — outputs `{effort_minutes_estimate, blast_radius_score, risk_tags}`
- [ ] `src/agents/ticket_context.py` (Haiku) — outputs `{true_urgency_score, label_disagreement_reason}`
- [ ] `src/agents/author_profile.py` (Haiku) — outputs `{trust_score, recommended_reviewer_depth}`
- [ ] `src/agents/synthesizer.py` (Sonnet 4.5) — consumes all sub-agent outputs + features, produces ranked queue with reasoning per PR
- [ ] `src/agents/critic.py` (Sonnet 4.5) — reviews the ranking, flags ranking errors, optionally swaps positions
- [ ] Orchestrator: `src/pipeline.py` — runs Haiku agents in parallel per PR, then synthesizer + critic
- [ ] **Commits 7–12:** scaffold → diff analyst → ticket context → author profile → synthesizer → critic

### Phase 4 — Evaluation Harness (Hour 11 → 14)

This is the section that wins the submission. Do it before the UI.

- [ ] `src/eval/snapshot.py` — for a given `(repo, timestamp)`, reconstruct the open-PR set as it existed then
- [ ] `src/eval/ground_truth.py` — compute the actual review/merge order of those PRs over the following N days
- [ ] `src/eval/baselines.py` — implement three baselines:
  - `random_ranker` (control)
  - `label_only_ranker` (sort by ticket priority label)
  - `author_only_ranker` (sort by author seniority + PR count)
- [ ] `src/eval/metrics.py` — `kendall_tau()` and `ndcg_at_k()`
- [ ] `scripts/run_eval.py` — runs all rankers over 5–8 snapshots, dumps a results table
- [ ] **Commits 13–15:** harness → baselines → metrics

### Phase 5 — Backend API (Hour 14 → 15.5)

- [ ] `server/src/api/main.py` — FastAPI app with CORS middleware allowing the Vercel origin
- [ ] `GET /rank/{owner}/{repo}` — returns the ranked queue as JSON (non-streaming, for quick fetch)
- [ ] `GET /rank/{owner}/{repo}/stream` — Server-Sent Events endpoint emitting `agent_started`, `agent_completed`, `pr_ranked`, `final_ranking` events
- [ ] `GET /health` — liveness probe for Fly.io
- [ ] In-memory TTL cache (10 min) keyed by `(owner, repo)`
- [ ] **Commits 16, 17:** API endpoints + SSE → caching layer

### Phase 6 — Frontend (Hour 15.5 → 17.5)

Next.js + shadcn/ui gets us a real-product look in less time than vanilla HTML.

- [ ] `web/app/page.tsx` — single page with a repo URL input and a Triage button
- [ ] `web/app/api/rank/route.ts` — optional proxy route (hides backend URL from browser); for the Quest, direct fetch to `NEXT_PUBLIC_API_URL` is fine
- [ ] `web/components/PRCard.tsx` — shadcn/ui Card showing:
  - Position pill (#1, #2, ...)
  - PR title + author + GitHub link
  - "Why this rank" reasoning (from synthesizer, streamed in)
  - Disagreement Badge when AI rank ≠ label priority
  - Effort minutes + blast-radius badge
- [ ] `web/components/RankedQueue.tsx` — consumes the SSE stream; shows skeletons until each agent completes
- [ ] `web/lib/api-client.ts` — typed fetch + EventSource wrapper
- [ ] Loading states with `Skeleton` from shadcn while agents are running
- [ ] Mobile-responsive by default (Tailwind grid)
- [ ] **Commit 18:** `feat(web): Next.js ranked queue with streaming reasoning (shadcn/ui)`

### Phase 7 — Telegram Bot (Hour 17.5 → 18.5)

- [ ] `server/src/telegram/bot.py` — single function `send_morning_brief(chat_id, ranking)`
- [ ] APScheduler job firing daily at 09:00 PKT (configurable via env)
- [ ] Admin endpoint `POST /trigger-brief` for demo/recording
- [ ] **Commit 19:** Telegram bot + scheduler

### Phase 8 — Deploy (Hour 18.5 → 20)

Two deploys. Order matters: Fly.io first (to get the backend URL), then update Vercel env, then Vercel deploy.

- [ ] `server/Dockerfile` — single-stage Python image, `uv sync --frozen`, `uvicorn` entrypoint
- [ ] `server/fly.toml` — `triagepilot-api` app, 256MB RAM, no auto-stop (keeps cold starts down)
- [ ] `server/.dockerignore` — excludes `tests/`, `data/`, `scripts/`, `__pycache__/`
- [ ] From `server/`: `fly secrets set GITHUB_TOKEN=... ANTHROPIC_API_KEY=... TELEGRAM_BOT_TOKEN=... ALLOWED_ORIGIN=https://triagepilot.vercel.app -a triagepilot-api`
- [ ] `fly deploy` from `server/` → live at `https://triagepilot-api.fly.dev`
- [ ] In Vercel dashboard: set `NEXT_PUBLIC_API_URL=https://triagepilot-api.fly.dev` → trigger redeploy
- [ ] Smoke-test: open `https://triagepilot.vercel.app` from phone, paste `kubernetes/kubernetes`, confirm streaming works
- [ ] **Commits 20, 21:** `chore(deploy): Dockerfile + fly.toml for FastAPI backend` → `deploy: ship v0.1-mvp (Fly.io backend + Vercel web)` — tag `v0.1-mvp`

### Phase 9 — Eval Runs + Polish (Hour 20 → 22)

- [ ] Run the full eval on **Kubernetes** (8 historical snapshots, 14-day forward windows)
- [ ] Run a second eval on **Next.js** to show generalizability
- [ ] Build a results table (Markdown + a chart) — save to `docs/eval_results.md`
- [ ] Hunt for "killer moments" — find 1–2 cases where the agent ranked a PR top-3 that the maintainers reviewed late
- [ ] Iterate one prompt based on a failure pattern you observed
- [ ] **Commits 22, 23, 24:** Kubernetes eval → Next.js eval → prompt fix

### Phase 10 — Docs + Loom (Hour 22 → 24)

- [ ] Fill in the README from the skeleton in Section 11 — actual numbers, actual screenshots
- [ ] Write BUILD_LOG.md following the template in Section 12 — honest, specific, includes failures
- [ ] Add architecture diagram (`docs/architecture.png` or in README as ASCII)
- [ ] Record 5-minute Loom following script in Section 13
- [ ] Final commit pushing everything
- [ ] Verify all submission requirements in Section 1 are green
- [ ] **Commits 25–30:** docs polish + BUILD_LOG + Loom link + final tag

---

## 6. Evaluation Methodology (this is the section that wins)

### 6.1 Retrospective Replay

**The principle:** Senior reviewers reveal their true priorities through which PRs they review first. We use that revealed behavior as ground truth.

**The procedure:**

1. Pick a target repo (Kubernetes).
2. Pick `N=8` historical timestamps `T₀` spread across the last 60 days.
3. For each `T₀`:
   - Reconstruct the set of open, unreviewed PRs at that moment from GitHub history.
   - Cap the set at 30 PRs (representative morning queue size).
   - Run our agent → produces a predicted ranking.
   - Look forward 14 days from `T₀`. Record the actual order in which maintainers reviewed/merged those PRs.
   - Compute Kendall tau and NDCG@5 between predicted and actual.
4. Average across snapshots.

**Why this is bulletproof:** the ground truth is the maintainers' own behavior. Reviewers cannot accuse you of cherry-picking — anyone can re-run on different snapshots and verify.

### 6.2 Baselines (these are the comparison table in your README)

| Baseline | What it does | Expected NDCG@5 |
|---|---|---|
| Random | Shuffle PRs uniformly | ~0.20 |
| Label-only | Sort by GitHub priority label | ~0.40 |
| Author-only | Sort by author's merged-PR count | ~0.35 |
| **TriagePilot (ours)** | Multi-agent ranking | **target: ≥ 0.60** |

If you don't beat the label-only baseline by a meaningful margin, the submission is in trouble. If you do, the gap is your headline number.

### 6.3 Qualitative Eval — "The Killer Moment"

While running quantitative eval, hunt for cases where:
- Your agent ranked a PR top-3 but maintainers reviewed it 4+ days later
- The maintainer comments on that PR contain phrases like "sorry this slipped", "should have caught this sooner", "this got missed"

Find 1–2 such cases. They become the centerpiece of your Loom and the lead screenshot in the README.

### 6.4 Baseline Comparison vs ChatGPT Directly (Quest requirement)

In the README, include this experiment:

> *"What happens if you just paste the list of PR titles + labels into ChatGPT and ask 'which should I review first?'"*

Run that exact experiment. Capture the response. Compare against TriagePilot's ranking on the same input. The difference: ChatGPT can't see diffs, author history, or cross-PR dependencies, so it falls back to the labels — which is the very baseline our system beats. Demonstrate this directly. Half a page in the README.

---

## 7. Baseline Comparison Plan (the exact README content)

The README will contain a section titled exactly: **"Baseline Comparison: Why Not Just Use ChatGPT?"**

It will show:
1. The same PR list given to GPT-4 / Claude with a generic prompt
2. The ranking it produced
3. The ranking TriagePilot produced on the same input
4. A side-by-side table of disagreements
5. NDCG@5 for both against ground truth

Expected result: ChatGPT's ranking will closely mirror the label-only baseline, because it has no way to read diffs or author history without integrations. TriagePilot wins because of the integration work, not because of cleverer prompting.

---

## 8. Deployment Plan

**Two URLs, one repo, two CI pipelines triggered by the same `git push`.**

| Component | URL | Platform | Free tier |
|---|---|---|---|
| Web (Next.js) | `https://triagepilot.vercel.app` | Vercel | Yes — Hobby tier |
| API (FastAPI) | `https://triagepilot-api.fly.dev` | Fly.io | Yes — 3 shared VMs |

### 8.1 Vercel — Frontend

- **Project setup:** Import the GitHub repo via Vercel dashboard. Set **Root Directory** to `web` in Project Settings → General. Framework Preset auto-detects Next.js.
- **Build commands:** auto-detected (`pnpm install` + `pnpm build` + `pnpm start`).
- **Environment variables (Project Settings → Environment Variables):**
  - `NEXT_PUBLIC_API_URL` = `https://triagepilot-api.fly.dev`
- **Deploys:** Every `git push` to `main` triggers a Vercel build. Vercel only rebuilds when files inside `web/` change (set up via Ignored Build Step: `git diff --quiet HEAD^ HEAD -- web/`).
- **Optional:** Add a `vercel.json` at the repo root for explicit control if the auto-detection misbehaves.

### 8.2 Fly.io — Backend

- **App name:** `triagepilot-api`
- **Config:** `server/fly.toml` with `app = "triagepilot-api"`, `auto_stop_machines = false`, `min_machines_running = 1` (prevents cold starts during demo).
- **Dockerfile location:** `server/Dockerfile`. Build context = `server/`.
- **Secrets (set via CLI from `server/`):**
  ```bash
  fly secrets set \
    GITHUB_TOKEN=ghp_... \
    ANTHROPIC_API_KEY=sk-ant-... \
    TELEGRAM_BOT_TOKEN=... \
    TELEGRAM_CHAT_ID=... \
    ALLOWED_ORIGIN=https://triagepilot.vercel.app \
    -a triagepilot-api
  ```
- **CORS:** FastAPI middleware allows only `ALLOWED_ORIGIN`. Set this *before* the first deploy or the web app's fetch will be blocked.
- **Deploy command:** `cd server && fly deploy`.
- **Optional auto-deploy on push:** add `.github/workflows/fly-deploy.yml` that runs `flyctl deploy --remote-only --config server/fly.toml` on changes to `server/**`. Skip for the 24h build unless you have time at hour 23.

### 8.3 Deploy Order (this matters)

The first time only, deploy in this order:

1. `cd server && fly deploy` → get the URL `https://triagepilot-api.fly.dev`
2. In Vercel dashboard, set `NEXT_PUBLIC_API_URL` to that URL
3. Trigger a Vercel redeploy (push an empty commit or click "Redeploy")
4. Visit `https://triagepilot.vercel.app` — confirm end-to-end works

On subsequent pushes, both deploy independently and order doesn't matter.

### 8.4 Backup Hosting (if Fly.io has issues at hour 22)

| Backup | Cold-start cost | Setup time |
|---|---|---|
| Render (free) | 30–60s after 15min idle — **bad for demo** | 5 min |
| Railway (paid trial) | Fast | 5 min, but burns the $5 credit |
| Hugging Face Spaces | Fast, but Gradio-flavored | 15 min |

Recommendation: pre-test Fly.io at hour 14 (after CORS smoke test passes). If it works once, it'll work at submission.

### 8.5 Pre-Submission Smoke Tests

- [ ] Open `https://triagepilot.vercel.app` in incognito — page loads, no console errors
- [ ] Type `kubernetes/kubernetes`, click Triage — streaming reasoning appears within 5s
- [ ] Final ranking renders within 60s
- [ ] Disagreement badges show on at least one PR
- [ ] Open the same URL on mobile — responsive layout works
- [ ] Trigger Telegram brief via `POST /trigger-brief` — message arrives
- [ ] From a fresh clone: `make install && make eval` completes without errors

---

## 9. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| GitHub API rate limits during eval | Medium | High | Persistent disk cache; pre-fetch snapshots in Phase 1; use authenticated requests (5000/hr) |
| Claude API costs balloon | Low | Medium | Haiku for per-PR analysis; cap eval at 30 PRs per snapshot; budget alarm at $25 |
| Eval result is worse than label-only baseline | Medium | **Critical** | Phase 9 has a "prompt fix" commit reserved for this. If still bad: be honest in BUILD_LOG, frame as "v1 didn't beat baseline; here are the 3 hypotheses for v2." Honesty > faking. |
| Multi-agent orchestration is slow (60s+ per query) | Medium | Medium | Parallelize Haiku agents per PR via `asyncio.gather`; SSE streaming so user sees progress; aggressive caching |
| Fly.io deploy fails at hour 22 | Low | High | Hello-world deploy in Phase 0 (CORS smoke test); fallback to Hugging Face Space in <30 min if Fly breaks |
| **CORS blocks Vercel → Fly.io at hour 22** | **Medium** | **High** | **Phase 0 CORS smoke test is mandatory. Set `ALLOWED_ORIGIN` as Fly secret before agent code is written.** |
| **Env var drift between Vercel and Fly.io** | **Medium** | **Medium** | **Document both `.env.example` files at commit 1. Single source of truth for URLs (`NEXT_PUBLIC_API_URL` on Vercel; `ALLOWED_ORIGIN` on Fly).** |
| **Vercel rebuilds on every push, even server-only changes** | **Low** | **Low** | **Configure Vercel Ignored Build Step: `git diff --quiet HEAD^ HEAD -- web/`. Saves Vercel build minutes; not critical.** |
| **Monorepo confusion: running commands from wrong directory** | **Medium** | **Low** | **Top-level `Makefile` exposes `make dev`, `make deploy-web`, `make deploy-server`, `make eval`. Never type `cd` manually.** |
| Telegram bot integration eats time | Medium | Low | If running out of time at hour 18, ship without Telegram, mention in "Next Iteration." Web UI is the demo. |
| Loom recording takes 3 takes | High | Low | Write the script in Phase 0 in your head; record at hour 23 in one shot |

---

## 10. Definition of Done

The submission is complete when **all** of these are true:

- [ ] Public GitHub repo exists at `github.com/<you>/triagepilot`
- [ ] `README.md` has all 7 Quest-required sections filled in with real content
- [ ] `BUILD_LOG.md` exists with honest 24h timeline
- [ ] Live URL works for a stranger (test in incognito)
- [ ] At least 5 eval snapshots run, results table in README
- [ ] At least 1 "killer moment" identified and screenshot in README
- [ ] Baseline comparison (vs label-only + vs ChatGPT) is in README with numbers
- [ ] 5-minute Loom recorded and linked in README
- [ ] Repo has between 25 and 30 commits, conventional commit messages
- [ ] `make eval` runs end-to-end on a fresh clone
- [ ] No secrets in commit history (use `.env.example`, not `.env`)
- [ ] LICENSE file (MIT)

---

## 11. README.md Skeleton (paste into repo at Commit 1)

````markdown
# TriagePilot

> Your labels lie. TriagePilot tells you the truth, every morning at 9 AM.

**Live demo:** https://triagepilot.fly.dev
**Loom walkthrough (5 min):** [link]
**Eval results:** [docs/eval_results.md](docs/eval_results.md)

---

## Problem Definition & Target User

[Fill from Plan Section 2 — keep to 200 words. Anchor on the senior engineer's morning queue.]

## Why This Problem Matters

[3 bullet points or 150 words:
- Cost of mis-prioritization (PR rot, conflicts, slipped releases)
- Why labels fail (stale, politically inflated, lack context)
- Why this is an AI problem, not an automation problem]

## How the Solution Works

[Architecture diagram (paste ASCII from Plan Section 3).
2 paragraphs on the multi-agent flow.
Link to /docs/architecture.md for deep-dive.]

## AI-Native Workflow

**Tools, models, agents:**
- Anthropic Claude Sonnet 4.5 (synthesizer + critic agents)
- Anthropic Claude Haiku 4.5 (per-PR analysis agents)
- GitHub GraphQL API
- Python 3.11 + FastAPI

**Agents:**
1. **Diff Analyst** — reads the unified diff, estimates effort and blast radius
2. **Ticket Context** — reads the linked issue, detects label-vs-reality mismatch
3. **Author Profile** — reads the author's history, scores trust
4. **Synthesizer** — combines all signals, produces ranked queue with reasoning
5. **Critic** — sanity-checks the ranking before output

**AI tools used during development:** [fill from BUILD_LOG]

## Evaluation Method & Results

[Paste numbers from Phase 9 eval runs.
Include the comparison table.
Include at least one chart.]

| Ranker | NDCG@5 (Kubernetes) | NDCG@5 (Next.js) |
|---|---|---|
| Random | 0.XX | 0.XX |
| Label-only | 0.XX | 0.XX |
| Author-only | 0.XX | 0.XX |
| **TriagePilot** | **0.XX** | **0.XX** |

### The Killer Moment

[1-2 screenshots of cases where TriagePilot beat the maintainers' actual review order.]

## Baseline Comparison: Why Not Just Use ChatGPT?

[The experiment described in Plan Section 7.]

## Limitations & Next Iteration Ideas

- **Cold-start problem:** Author trust scores assume history exists. New contributors are scored neutrally.
- **No private repo support yet:** Read-only public-repo focus for the Quest. Linear/Jira adapter exists in `src/ticket_sources/` and is 2 hours from wiring up.
- **Single-reviewer assumption:** Ranking is global, not per-reviewer-expertise.
- **Evening feedback loop:** Stretch goal, not shipped in v1.

## Quick Start

```bash
git clone https://github.com/<you>/triagepilot
cd triagepilot
cp .env.example .env  # add your GITHUB_TOKEN and ANTHROPIC_API_KEY
make install
make eval  # runs the full eval suite
make serve  # launches the web UI at localhost:8000
```

## Architecture

See [docs/architecture.md](docs/architecture.md).

## License

MIT
````

---

## 12. BUILD_LOG.md Template

```markdown
# BUILD_LOG.md

A complete, honest record of the 24-hour build.

## TL;DR

- **Total focused build time:** ~22 hours
- **Final state:** [shipped / partial / pivoted]
- **What worked:** [3 bullets]
- **What didn't:** [3 bullets]
- **What I'd do differently in v2:** [3 bullets]

## Hour-by-Hour

### Hour 0–1: Setup
- What I did
- What AI did well [name the tool: Cursor / Claude Code / etc.]
- What AI got wrong
- What I rejected / improved manually

### Hour 1–4: GitHub Data Pipeline
...

[Repeat per phase]

## Key Decisions

### Decision 1: [Title]
- **Context:** [what was the choice]
- **Options considered:** [list]
- **Chose:** [option]
- **Why:** [reasoning]
- **Cost:** [what I gave up]

[Repeat for 5–8 major decisions]

## Prompts That Worked

[Paste the prompt + the resulting output, with commentary]

## Prompts That Failed

[Paste 2–3 prompts that hallucinated or produced bad output, what I changed]

## AI Tools Used

| Tool | What I used it for | Verdict |
|---|---|---|
| Claude Code | Scaffolding agents, writing GraphQL queries | Excellent for boilerplate |
| Cursor | [if used] | ... |
| Claude Sonnet (API) | Agent reasoning in production | ... |
| Claude Haiku (API) | Per-PR analysis | ... |

## What I Cut and Why (Priority Elimination)

This is the most important section.

- **Cut: Linear/Jira integration** — abstracted behind interface; mentioned as next iteration. Saved ~3 hours.
- **Cut: User auth and per-user Telegram channels** — single hardcoded user for Quest. Saved ~2 hours.
- **Cut: [thing 3]** — saved ~X hours.

## Numbers I'm Proud Of

- N PRs analyzed across eval
- X NDCG@5 vs Y for label-only baseline
- Z seconds end-to-end per repo query

## What I'd Build Next

[5-bullet roadmap]
```

---

## 13. Loom Script (5 minutes, recorded at hour 23)

### 0:00 — 0:30 | The Hook

> "Every morning, senior engineers wake up to 20 open PRs. The labels say High, Medium, Low — but the labels lie. Today I'll show you TriagePilot, an AI that reads what's actually in those PRs and ranks them properly. Built in 24 hours for the MUST Company FDE quest."

### 0:30 — 1:30 | The Demo

- Open live URL on screen
- Paste `kubernetes/kubernetes`
- Wait ~30s, ranking appears
- Walk through top 3 PRs, highlighting reasoning
- Show the "disagreement flag" on a Low-labeled PR that the agent ranked #1

### 1:30 — 3:00 | The Killer Moment

- Show a real historical PR where TriagePilot would have ranked it top-3
- Show that the maintainer actually reviewed it 6 days later
- Show the screenshot of the maintainer comment apologizing for the delay
- "TriagePilot would have flagged this on day one"

### 3:00 — 4:00 | The Architecture

- Show the architecture diagram on screen
- Walk through the 5 agents in 60 seconds
- Highlight: this is multi-agent, with a critic loop, with a real eval methodology

### 4:00 — 4:30 | The Eval

- Show the results table
- Headline number: "0.XX NDCG@5 vs 0.XX for label-only baseline"
- Show generalization to a second repo (Next.js)

### 4:30 — 5:00 | The Honest Close

- "Here's what I cut: Linear integration, per-user auth, evening feedback loop"
- "Here's what's broken: cold-start for new contributors"
- "Here's what I'd ship next: [one sentence]"
- "Code at github.com/[you]/triagepilot — live at triagepilot.fly.dev"

---

## 14. Repo Layout

Single repo, monorepo style. `web/` deploys to Vercel; `server/` deploys to Fly.io.

```
triagepilot/
├── README.md                    # Quest 1 README (all 7 required sections)
├── BUILD_LOG.md                 # 24h journey, prompts, decisions, cuts
├── LICENSE                      # MIT
├── Makefile                     # Top-level commands across both stacks
├── .gitignore
├── docs/
│   ├── architecture.md          # Diagram + agent flow deep-dive
│   └── eval_results.md          # NDCG, Kendall tau, killer-moment screenshots
│
├── web/                         # ▶ Next.js → Vercel
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.mjs
│   ├── components.json          # shadcn/ui config
│   ├── .env.local.example       # NEXT_PUBLIC_API_URL
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx             # Main triage page
│   │   ├── globals.css
│   │   └── api/
│   │       └── rank/route.ts    # (optional) proxy route
│   ├── components/
│   │   ├── PRCard.tsx           # shadcn Card with PR details + reasoning
│   │   ├── RankedQueue.tsx      # SSE consumer rendering the live ranking
│   │   ├── TriageForm.tsx       # Repo input + Triage button
│   │   └── ui/                  # shadcn/ui primitives (card, button, badge, skeleton, input)
│   └── lib/
│       ├── api-client.ts        # Typed fetch + EventSource wrapper
│       └── types.ts             # Shared types mirroring server/Pydantic
│
├── server/                      # ▶ FastAPI → Fly.io
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── Dockerfile               # Single-stage Python 3.11 image
│   ├── fly.toml                 # app = "triagepilot-api", auto_stop=false
│   ├── .dockerignore
│   ├── .env.example             # GITHUB_TOKEN, ANTHROPIC_API_KEY, TELEGRAM_*, ALLOWED_ORIGIN
│   ├── src/
│   │   ├── __init__.py
│   │   ├── api/
│   │   │   └── main.py          # FastAPI app + CORS + /rank + /rank/stream + /health
│   │   ├── github/
│   │   │   ├── client.py        # Async GraphQL client
│   │   │   ├── queries.py
│   │   │   └── cache.py
│   │   ├── features/
│   │   │   └── extractor.py
│   │   ├── agents/
│   │   │   ├── base.py          # Agent abstraction + retry + JSON schema
│   │   │   ├── diff_analyst.py
│   │   │   ├── ticket_context.py
│   │   │   ├── author_profile.py
│   │   │   ├── synthesizer.py
│   │   │   └── critic.py
│   │   ├── pipeline.py          # Orchestrator with asyncio.gather + SSE emission
│   │   ├── eval/
│   │   │   ├── snapshot.py
│   │   │   ├── ground_truth.py
│   │   │   ├── baselines.py
│   │   │   └── metrics.py       # Kendall tau via scipy, custom NDCG
│   │   ├── telegram/
│   │   │   └── bot.py
│   │   └── ticket_sources/      # Abstraction — only GitHub Issues impl for Quest
│   │       └── github_issues.py
│   ├── scripts/
│   │   └── run_eval.py
│   └── tests/
│       └── test_agents.py
│
└── .github/
    └── workflows/
        └── fly-deploy.yml       # (optional) auto-deploy server on push to server/**
```

### Top-level Makefile

```makefile
.PHONY: install dev dev-web dev-server eval deploy-web deploy-server deploy

install:
	cd server && uv sync
	cd web && pnpm install

dev:
	@echo "Web: http://localhost:3000 · Server: http://localhost:8000"
	@$(MAKE) -j 2 dev-server dev-web

dev-server:
	cd server && uv run uvicorn src.api.main:app --reload --port 8000

dev-web:
	cd web && pnpm dev

eval:
	cd server && uv run python scripts/run_eval.py

deploy-server:
	cd server && fly deploy

deploy-web:
	cd web && vercel --prod

deploy: deploy-server deploy-web
```

---

## 15. Sanity Checks Before Submission

30 minutes before submitting, run this checklist:

- [ ] Open repo in incognito — does the README look good without my login?
- [ ] Click `https://triagepilot.vercel.app` in incognito — does it load and produce results?
- [ ] Verify `https://triagepilot-api.fly.dev/health` returns `{"ok": true}`
- [ ] From a fresh clone: `make install && make eval` completes without errors
- [ ] Vercel project Root Directory is still set to `web` (check dashboard)
- [ ] Fly.io app `triagepilot-api` shows `auto_stop_machines = false` (no cold starts during demo)
- [ ] `ALLOWED_ORIGIN` on Fly matches the actual Vercel URL exactly (no trailing slash mismatch)
- [ ] `NEXT_PUBLIC_API_URL` on Vercel matches the actual Fly URL
- [ ] Read BUILD_LOG.md aloud — does it sound honest, specific, and like a real builder wrote it?
- [ ] Check commit history — between 25–30 commits, conventional format, no secrets
- [ ] No `.env` files committed (`git log --all --full-history -- "**/.env"` returns nothing)
- [ ] Loom link works in incognito
- [ ] LICENSE present at root
- [ ] Both tags exist: `v0.1-mvp` and `v1.0-quest-submission`

---

## 16. What This Plan Does NOT Cover (intentionally)

- Per-user authentication (out of scope for Quest)
- A nice marketing landing page (the working URL is the landing page)
- Mobile optimization (works on mobile but not polished)
- Multi-repo dashboard (one repo at a time)
- Real-time webhook updates (poll/refresh on demand only)

These are listed in README "Limitations & Next Iteration Ideas" — that's a feature of the submission, not a bug. *Priority elimination is the skill MUST values most.* Show it.

---

**Next:** open `COMMITS.md` for the 30-commit roadmap.
