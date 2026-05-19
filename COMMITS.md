# TriagePilot — Commit Plan & Claude Code Instructions

> **Target:** 28 planned commits + 2 reserve = **30 maximum**.
> Designed so each commit is a self-contained packet you can hand to Claude Code.

---

## 0. How to Use This Document

For each commit:

1. **Read the commit block.** It contains everything Claude Code needs in one place.
2. **Copy the "Claude Code instructions" block** into Claude Code as your prompt for that commit.
3. **Verify against "Acceptance criteria"** before committing — don't move on until each box is checked.
4. **Copy the "Commit message" block** and run:
   ```bash
   git add -A
   git commit -F- <<'EOF'
   <paste the commit message block here>
   EOF
   ```
   Or simpler, use one-liner for short messages:
   ```bash
   git commit -am "<subject line>"
   ```

**Tip:** Open `COMMITS.md` in a split view next to Claude Code. Work top to bottom. Do not skip ahead.

---

## 1. Pre-flight Checklist (do before starting the clock)

Don't burn build-time on account creation. Get these ready first:

- [ ] GitHub account + repo `triagepilot` created (public)
- [ ] GitHub personal access token (scope: `public_repo`)
- [ ] Anthropic API key with billing enabled
- [ ] Vercel account (sign in with GitHub)
- [ ] Fly.io account + `flyctl` CLI installed locally
- [ ] Telegram account + bot created via `@BotFather` → save token
- [ ] Your Telegram `chat_id` (DM `@userinfobot`)
- [ ] Node.js 20+ and `pnpm` installed locally
- [ ] Python 3.11+ and `uv` installed locally
- [ ] Docker installed (for Fly remote builds you don't need it locally, but useful for sanity checks)

---

## 2. Commit Philosophy

- **Format:** Conventional commits — `<type>(<scope>): <subject>`
- **Subject:** under 72 chars, imperative mood ("add" not "added")
- **Body:** when context matters — especially for prompt design, eval decisions, architectural choices
- **Types used here:** `chore`, `feat`, `fix`, `refactor`, `eval`, `docs`, `deploy`

---

## 3. Branch & Tag Strategy

- **Single branch: `main`.** Solo build. No branches.
- **Tag 1: `v0.1-mvp`** at Commit 21 (end-to-end deployed)
- **Tag 2: `v1.0-quest-submission`** at Commit 28 (final state)

Tag commands:
```bash
git tag -a v0.1-mvp -m "First deployed version: backend on Fly + web on Vercel"
git push origin v0.1-mvp
```

---

## 4. The 28 Commits

Each commit has the same structure:

- **What this commit produces** — one-line summary
- **Claude Code instructions** — paste this verbatim
- **Files added/modified** — what should exist after this commit
- **Acceptance criteria** — verify before committing
- **Commit message** — paste-ready

---

### Commit 1 — `chore: monorepo scaffold with web (Next.js) and server (FastAPI)`

**Phase:** 0 — Setup &nbsp; **Hour:** 0 → 1.5 &nbsp; **Depends on:** nothing

**What this commit produces:** the empty monorepo skeleton with both apps initialized, the root Makefile, the README skeleton, and a CORS smoke-test hello-world on both sides.

**Claude Code instructions:**
> Scaffold a monorepo at the current directory with two subdirectories: `web/` (Next.js 15 + TypeScript + Tailwind + App Router) and `server/` (Python 3.11 + FastAPI with `uv` for dependency management). Use the following structure:
>
> ```
> triagepilot/
> ├── README.md          ← skeleton with all 7 Quest 1 sections as headings only
> ├── LICENSE            ← MIT
> ├── Makefile           ← top-level targets: install, dev, dev-server, dev-web, eval, deploy-server, deploy-web, deploy
> ├── .gitignore         ← Python + Node + IDE patterns
> ├── server/
> │   ├── pyproject.toml ← FastAPI, uvicorn, httpx, anthropic, python-telegram-bot, apscheduler, scipy, pydantic v2
> │   ├── .env.example   ← GITHUB_TOKEN, ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ALLOWED_ORIGIN, MONITORED_REPO
> │   ├── .dockerignore
> │   └── src/
> │       ├── __init__.py
> │       └── api/
> │           ├── __init__.py
> │           └── main.py    ← minimal FastAPI app with CORS middleware allowing localhost:3000 and a GET /health endpoint returning {"ok": true}
> └── web/
>     ├── package.json   ← Next.js 15, React 19, Tailwind v3, TypeScript 5
>     ├── .env.local.example ← NEXT_PUBLIC_API_URL=http://localhost:8000
>     └── (Next.js app scaffold via `pnpm create next-app` with --typescript --tailwind --app --no-src-dir --import-alias="@/*")
> ```
>
> Initialize `web/` using `pnpm create next-app@latest .` inside the directory.
> Initialize `server/` using `uv init` then `uv add fastapi uvicorn httpx anthropic python-telegram-bot apscheduler scipy pydantic`.
>
> The `app/page.tsx` in the web app should fetch `${NEXT_PUBLIC_API_URL}/health` on mount and display the result so we can verify CORS works end-to-end.
>
> The `Makefile` targets:
> ```
> install:       cd server && uv sync; cd web && pnpm install
> dev:           run dev-server and dev-web in parallel
> dev-server:    cd server && uv run uvicorn src.api.main:app --reload --port 8000
> dev-web:       cd web && pnpm dev
> eval:          cd server && uv run python scripts/run_eval.py
> deploy-server: cd server && fly deploy
> deploy-web:    cd web && vercel --prod
> deploy:        deploy-server then deploy-web
> ```
>
> Do NOT install shadcn/ui yet — that happens in Commit 18.

**Files added:**
- `README.md`, `LICENSE`, `Makefile`, `.gitignore`
- `server/pyproject.toml`, `server/uv.lock`, `server/.env.example`, `server/.dockerignore`, `server/src/__init__.py`, `server/src/api/__init__.py`, `server/src/api/main.py`
- `web/` — full Next.js scaffold (`package.json`, `tsconfig.json`, `next.config.ts`, `tailwind.config.ts`, `postcss.config.mjs`, `app/layout.tsx`, `app/page.tsx`, `app/globals.css`, `.env.local.example`)

**Acceptance criteria:**
- [ ] `make install` completes without errors
- [ ] `make dev` starts both servers (web on :3000, server on :8000)
- [ ] `curl http://localhost:8000/health` returns `{"ok": true}`
- [ ] Visiting `http://localhost:3000` shows the health response (CORS works locally)
- [ ] `.env.example` files committed; no real secrets in git

**Commit message:**
```
chore: monorepo scaffold with web (Next.js) and server (FastAPI)

Initializes the two-app monorepo:
- /server  Python 3.11 + FastAPI (uv) → deploys to Fly.io
- /web     Next.js 15 + TypeScript + Tailwind → deploys to Vercel

Root Makefile orchestrates both stacks with: install, dev,
dev-server, dev-web, eval, deploy-server, deploy-web, deploy.

Includes a /health endpoint on the server and a CORS-enabled
fetch from the web app on page load — verified end-to-end
to prevent late-stage cross-origin bugs.
```

---

### Commit 2 — `feat(github): add authenticated GraphQL client`

**Phase:** 1 — GitHub Data Pipeline &nbsp; **Hour:** 1.5 → 2.5 &nbsp; **Depends on:** Commit 1

**What this commit produces:** an async GitHub GraphQL client with auth, retry on rate-limit, and basic error handling.

**Claude Code instructions:**
> Create `server/src/github/__init__.py`, `server/src/github/client.py`, and `server/src/github/queries.py`.
>
> `client.py` should expose:
> ```python
> class GitHubClient:
>     def __init__(self, token: str): ...
>     async def query(self, gql_query: str, variables: dict) -> dict: ...
> ```
>
> Implementation requirements:
> - Use `httpx.AsyncClient` for transport
> - Endpoint: `https://api.github.com/graphql`
> - Headers: `Authorization: bearer <token>`, `User-Agent: triagepilot/0.1`
> - On HTTP 429 or `RATE_LIMITED` GraphQL error, sleep until reset timestamp and retry once
> - On HTTP 5xx, exponential backoff with 3 retries
> - Raise `GitHubAPIError` on any other failure with the response body included
>
> `queries.py` should hold GraphQL query string constants — leave it empty for now with just a module docstring; queries are added in Commit 3.
>
> Add a `tests/test_github_client.py` with one unit test that mocks `httpx` and verifies the auth header is sent.

**Files added:**
- `server/src/github/__init__.py`
- `server/src/github/client.py`
- `server/src/github/queries.py`
- `server/tests/__init__.py`
- `server/tests/test_github_client.py`

**Acceptance criteria:**
- [ ] `uv run python -c "from src.github.client import GitHubClient"` works
- [ ] `uv run pytest tests/test_github_client.py` passes
- [ ] Manual smoke test: instantiate client with real token, call `query("query { viewer { login } }", {})`, get your username back

**Commit message:**
```
feat(github): add authenticated GraphQL client

Async client wrapping httpx for the GitHub GraphQL API.
Handles rate-limit retries (HTTP 429 / RATE_LIMITED) with
respect for the reset timestamp, and exponential backoff on
5xx. Raises GitHubAPIError on all other failures with response
body context for debugging.

Foundation for the bulk PR + issue + diff fetcher in commit 3.
```

---

### Commit 3 — `feat(github): fetch open PRs with linked issues`

**Phase:** 1 &nbsp; **Hour:** 2.5 → 3.5 &nbsp; **Depends on:** Commit 2

**What this commit produces:** the GraphQL query and Python wrapper to fetch all open PRs for a repo with their linked issues, labels, and basic metadata in a single round-trip.

**Claude Code instructions:**
> Extend `server/src/github/queries.py` and `server/src/github/client.py`.
>
> Add a GraphQL query string `OPEN_PRS_WITH_CONTEXT` to `queries.py` that fetches, for a given `owner` and `name`:
> - All open PRs (first 50, with cursor pagination)
> - For each PR: `number`, `title`, `body`, `url`, `createdAt`, `updatedAt`, `author { login }`, `headRefName`, `labels (first: 10) { nodes { name } }`, `mergeable`, `additions`, `deletions`, `changedFiles`
> - For each PR: linked issues via `closingIssuesReferences (first: 5) { nodes { number, title, body, labels (first: 10) { nodes { name } } } }`
>
> Add a Pydantic model `PRContext` in a new file `server/src/github/models.py` matching this shape exactly.
>
> Add a method to `GitHubClient`:
> ```python
> async def fetch_open_prs(self, owner: str, name: str, limit: int = 50) -> list[PRContext]: ...
> ```
>
> Should handle pagination internally up to `limit`. Return a list of `PRContext` Pydantic models.

**Files added/modified:**
- `server/src/github/queries.py` (add `OPEN_PRS_WITH_CONTEXT`)
- `server/src/github/client.py` (add `fetch_open_prs`)
- `server/src/github/models.py` (new — `PRContext` Pydantic model)

**Acceptance criteria:**
- [ ] Manual smoke test: `await client.fetch_open_prs("kubernetes", "kubernetes")` returns >5 PR objects
- [ ] Each `PRContext` has populated `labels`, `author.login`, `changedFiles`
- [ ] Linked issues populate when a PR has one (test on a recent merged PR with a "Fixes #XXX" body)

**Commit message:**
```
feat(github): fetch open PRs with linked issues

Single-round-trip GraphQL query fetches all open PRs for a
repo plus their linked closing-issue references, labels,
authors, and basic diff metrics (additions, deletions,
changedFiles). Handles cursor pagination internally up to
a configurable limit.

Pydantic model `PRContext` is the canonical schema for
everything downstream — feature extraction, agent inputs,
ranking outputs all reference it.
```

---

### Commit 4 — `feat(github): fetch PR diffs and author history with caching`

**Phase:** 1 &nbsp; **Hour:** 3.5 → 4.5 &nbsp; **Depends on:** Commit 3

**What this commit produces:** ability to fetch the file-level diff (changed file paths + additions/deletions per file) and the author's history (merged PR count, recent revert rate, average review-comment count).

**Claude Code instructions:**
> Add to `server/src/github/client.py`:
> ```python
> async def fetch_pr_files(self, owner: str, name: str, pr_number: int) -> list[FileChange]: ...
> async def fetch_author_history(self, owner: str, name: str, login: str) -> AuthorProfile: ...
> ```
>
> Add Pydantic models `FileChange` and `AuthorProfile` to `server/src/github/models.py`:
> ```python
> class FileChange(BaseModel):
>     path: str
>     additions: int
>     deletions: int
>
> class AuthorProfile(BaseModel):
>     login: str
>     merged_pr_count_in_repo: int      # last 90 days
>     revert_rate: float                 # fraction of their merged PRs reverted within 7 days
>     avg_review_comments_per_pr: float # last 20 PRs
> ```
>
> Add a disk cache in `server/src/github/cache.py`:
> ```python
> class DiskCache:
>     def __init__(self, cache_dir: str = ".cache/github"): ...
>     def get(self, key: str) -> dict | None: ...
>     def set(self, key: str, value: dict, ttl_seconds: int = 3600) -> None: ...
> ```
>
> Wire the cache into `GitHubClient` so that `fetch_pr_files` and `fetch_author_history` results are persisted for 1 hour. Add `.cache/` to `.gitignore`.

**Files added/modified:**
- `server/src/github/client.py` (add the two methods)
- `server/src/github/models.py` (add `FileChange`, `AuthorProfile`)
- `server/src/github/cache.py` (new)
- `.gitignore` (add `.cache/`)

**Acceptance criteria:**
- [ ] `await client.fetch_pr_files("kubernetes", "kubernetes", <real-pr>)` returns list of `FileChange`
- [ ] `await client.fetch_author_history("kubernetes", "kubernetes", "alice")` returns sensible numbers
- [ ] Re-running the same fetch is near-instant (cache hit)

**Commit message:**
```
feat(github): fetch PR diffs and author history with caching

Adds two new client methods:
- fetch_pr_files: file-level diff (paths, additions, deletions)
- fetch_author_history: 90-day merged count, 7-day revert rate,
  and average review-comment density per PR

Disk-backed JSON cache (.cache/github/) with 1-hour TTL means
re-runs during dev and eval don't burn the GitHub API rate
limit. Cache directory is gitignored.
```

---

### Commit 5 — `feat(features): structured feature extraction per PR`

**Phase:** 2 — Feature Extraction &nbsp; **Hour:** 4.5 → 5 &nbsp; **Depends on:** Commit 4

**What this commit produces:** the pure-function feature extractor that turns raw GitHub data into a flat structured record per PR — the input to all downstream agents.

**Claude Code instructions:**
> Create `server/src/features/__init__.py` and `server/src/features/extractor.py`.
>
> Define a Pydantic model `PRFeatures`:
> ```python
> class PRFeatures(BaseModel):
>     pr_number: int
>     title: str
>     author_login: str
>     # Diff signals
>     lines_added: int
>     lines_deleted: int
>     files_changed: int
>     file_paths: list[str]
>     touches_auth: bool
>     touches_db_migration: bool
>     touches_config_only: bool
>     touches_tests_only: bool
>     touches_critical_paths: list[str]  # e.g. ['auth/middleware.py', 'kubelet/pleg.go']
>     # Ticket signals
>     ticket_priority_label: str | None  # "high", "medium", "low", or None
>     ticket_kind_label: str | None      # "bug", "feature", "task", etc.
>     ticket_body_summary: str           # truncated to 500 chars
>     # Author signals
>     author_merged_pr_count: int
>     author_revert_rate: float
>     author_avg_review_comments: float
>     # Time signals
>     pr_age_days: float
>     days_since_last_activity: float
> ```
>
> Implement:
> ```python
> def extract(pr: PRContext, author: AuthorProfile, files: list[FileChange]) -> PRFeatures: ...
> ```
>
> The path-based heuristics:
> - `touches_auth = True` if any file path contains "auth", "authn", "authz", "iam", "session", "token"
> - `touches_db_migration = True` if any path contains "/migrations/" or ends in `.sql`
> - `touches_config_only = True` if all changed files are `.yaml`, `.json`, `.toml`, `.env`, or `*.config.*`
> - `touches_tests_only = True` if all changed files are under `tests/`, `test/`, `__tests__/`, or end in `_test.go`, `.test.ts`, `.spec.ts`
> - `touches_critical_paths` populated from a configurable list of regex patterns (start with: "kubelet/pleg", "auth/middleware", "scheduler/")
>
> Label normalization: map Kubernetes-style `priority/critical-urgent` → "high", `priority/important-soon` → "high", `priority/important-longterm` → "medium", `priority/backlog` → "low". Map plain "P0", "P1" → "high"; "P2" → "medium"; "P3" → "low". Otherwise lowercase and keep.

**Files added:**
- `server/src/features/__init__.py`
- `server/src/features/extractor.py`

**Acceptance criteria:**
- [ ] Unit test `tests/test_extractor.py` verifies path heuristics with synthetic file lists
- [ ] Smoke test on a real K8s PR: features populate sensibly
- [ ] Label normalization handles K8s, plain priority, and missing-label cases

**Commit message:**
```
feat(features): structured feature extraction per PR

Pure function turning raw GitHub data into a flat PRFeatures
record. Captures three categories of signal:

1. Diff signals — lines, files, path heuristics (touches_auth,
   touches_db_migration, touches_config_only, touches_tests_only,
   touches_critical_paths)
2. Ticket signals — normalized priority/kind labels, body summary
3. Author signals — merged-count, revert-rate, review density

Label normalization maps Kubernetes /priority/* labels and P0-P3
to a unified high/medium/low schema, so downstream agents see one
consistent vocabulary regardless of repo conventions.
```

---

### Commit 6 — `feat(features): cross-PR dependency detection`

**Phase:** 2 &nbsp; **Hour:** 5 → 5.5 &nbsp; **Depends on:** Commit 5

**What this commit produces:** detection of "this PR is referenced by N other open PRs" — a signal labels never capture.

**Claude Code instructions:**
> Add to `server/src/features/extractor.py`:
> ```python
> def detect_cross_pr_references(all_prs: list[PRContext]) -> dict[int, list[int]]: ...
> ```
>
> Implementation: for each PR's body and title, find references like "#1234", "PR #1234", "fixes #1234", "depends on #1234" using regex. Return a dict mapping PR number → list of PR numbers that reference it.
>
> Extend `PRFeatures` with two new fields:
> ```python
> mentioned_by_other_open_prs: int   # count
> dependency_chain_depth: int        # 0 if no one depends; 1 if direct deps; 2+ for transitive
> ```
>
> Update `extract()` to populate these from the cross-reference graph.

**Files modified:**
- `server/src/features/extractor.py`

**Acceptance criteria:**
- [ ] Unit test with synthetic PRs containing `#NNN` references
- [ ] Smoke test on a real K8s snapshot: at least one PR has `mentioned_by_other_open_prs > 0`

**Commit message:**
```
feat(features): cross-PR dependency detection

Scans every PR body and title for #NNN references and
builds a dependency graph across the open-PR set.

Adds two PRFeatures fields:
- mentioned_by_other_open_prs (count)
- dependency_chain_depth (0 = no deps, 1 = direct, 2+ = transitive)

This is the signal that explains why merging a "low priority"
PR first can unblock several others — invisible to label-based
sorting.
```

---

### Commit 7 — `feat(agents): base Agent class with Claude SDK`

**Phase:** 3 — Multi-Agent System &nbsp; **Hour:** 5.5 → 6.5 &nbsp; **Depends on:** Commit 5

**What this commit produces:** a shared abstraction for all agents — Claude SDK client, JSON schema enforcement via Pydantic, retry on rate-limit, token/cost logging.

**Claude Code instructions:**
> Create `server/src/agents/__init__.py` and `server/src/agents/base.py`.
>
> Define:
> ```python
> from anthropic import AsyncAnthropic
> from pydantic import BaseModel
> from typing import TypeVar, Generic
>
> T = TypeVar("T", bound=BaseModel)
>
> class BaseAgent(Generic[T]):
>     name: str                          # subclass overrides
>     model: str                         # e.g. "claude-haiku-4-5-20251001"
>     output_schema: type[T]             # subclass overrides with a Pydantic model
>     system_prompt: str                 # subclass overrides
>
>     def __init__(self, client: AsyncAnthropic):
>         self.client = client
>
>     async def run(self, user_message: str) -> T:
>         # Calls Claude with system_prompt + user_message
>         # Forces JSON output matching output_schema via tool use or response_format
>         # On parse failure, retries once with a stricter "return ONLY valid JSON" reminder
>         # Logs: agent name, input tokens, output tokens, latency, estimated cost
>         ...
> ```
>
> Use Anthropic's structured-output approach: define a single "tool" with the Pydantic schema's JSON Schema, set `tool_choice` to force the tool, parse the tool input as the output.
>
> Log entries should go to stdout as JSON lines so they're greppable in Fly.io logs:
> `{"agent": "diff_analyst", "input_tokens": 1200, "output_tokens": 150, "latency_ms": 2340, "cost_usd": 0.0012}`

**Files added:**
- `server/src/agents/__init__.py`
- `server/src/agents/base.py`

**Acceptance criteria:**
- [ ] A trivial subclass with `output_schema = class Foo(BaseModel): x: int` returns a valid `Foo` instance
- [ ] Log line appears on stdout per call
- [ ] Bad JSON from model triggers exactly one retry before raising

**Commit message:**
```
feat(agents): base Agent class with Claude SDK

Shared abstraction for all five agents in the pipeline:
- Claude SDK async client
- Pydantic-typed output via tool-use forcing
- One retry on JSON parse failure with stricter reminder
- Structured stdout logging of tokens, latency, cost per call

Subclasses set name, model, output_schema, and system_prompt.
Everything else is shared.
```

---

### Commit 8 — `feat(agents): diff analyst (effort + blast radius)`

**Phase:** 3 &nbsp; **Hour:** 6.5 → 7.5 &nbsp; **Depends on:** Commit 7

**What this commit produces:** the Haiku agent that reads a PR's diff metadata and estimates review effort plus blast radius.

**Claude Code instructions:**
> Create `server/src/agents/diff_analyst.py`.
>
> Define:
> ```python
> class DiffAnalysis(BaseModel):
>     effort_minutes_estimate: int            # 5–180
>     blast_radius_score: float               # 0.0–1.0
>     risk_tags: list[str]                    # subset of: auth, db_migration, config_only, tests_only, external_api, concurrency, infra
>     reasoning: str                          # 1-2 sentences explaining the assessment
>
> class DiffAnalystAgent(BaseAgent[DiffAnalysis]):
>     name = "diff_analyst"
>     model = "claude-haiku-4-5-20251001"
>     output_schema = DiffAnalysis
>     system_prompt = """..."""
> ```
>
> The system prompt should instruct the agent to:
> - Estimate review time conservatively (a 2000-line refactor is ~120 min; a 5-line config change is ~5 min)
> - Score blast radius from 0 (docs/test-only change) to 1 (touches auth, payments, or core scheduling)
> - Tag aggressively from the allowed list — false positives are cheap, false negatives are dangerous
> - Keep reasoning to two sentences max
>
> The agent's `user_message` will be a structured rendering of:
> - PR title
> - Linked issue summary (if any)
> - List of changed files with additions/deletions per file
> - Total lines added/deleted/files changed
>
> Add unit test in `tests/test_diff_analyst.py` with one mock case verifying schema enforcement.

**Files added:**
- `server/src/agents/diff_analyst.py`
- `server/tests/test_diff_analyst.py`

**Acceptance criteria:**
- [ ] Smoke test on a real K8s PR returns a valid `DiffAnalysis`
- [ ] `risk_tags` only contains values from the allowed list
- [ ] `effort_minutes_estimate` is between 5 and 180

**Commit message:**
```
feat(agents): diff analyst (effort + blast radius)

Haiku agent that reads a PR's diff metadata and outputs:
- effort_minutes_estimate (5-180, conservative)
- blast_radius_score (0-1, where 1 = touches auth/payments/core)
- risk_tags from a constrained vocabulary
- one-sentence reasoning

Uses Haiku (not Sonnet) because per-PR analysis is the
bulk of inference cost — running 30 PRs through Sonnet would
blow the budget. Sonnet runs once for the synthesizer in
commit 11.

System prompt forces conservative effort estimates and
aggressive risk tagging — false positives are cheap, missed
risks are dangerous in a triage tool.
```

---

### Commit 9 — `feat(agents): ticket context (label-vs-reality mismatch)`

**Phase:** 3 &nbsp; **Hour:** 7.5 → 8.5 &nbsp; **Depends on:** Commit 7

**What this commit produces:** the Haiku agent that reads the linked ticket and decides whether its stated priority matches the apparent urgency described in the issue body.

**Claude Code instructions:**
> Create `server/src/agents/ticket_context.py`.
>
> Define:
> ```python
> class TicketContext(BaseModel):
>     stated_priority: str                # echo of the label
>     true_urgency_score: float           # 0.0-1.0 inferred from issue body
>     label_disagreement: bool            # True if true_urgency disagrees with stated by > 0.3
>     disagreement_reason: str | None     # required when label_disagreement is True
>     keywords_extracted: list[str]       # urgency signals: "blocker", "production", "customer", "outage", etc.
>
> class TicketContextAgent(BaseAgent[TicketContext]):
>     name = "ticket_context"
>     model = "claude-haiku-4-5-20251001"
>     output_schema = TicketContext
>     system_prompt = """..."""
> ```
>
> System prompt instructs the agent to:
> - Read the linked issue body and look for urgency signals: "blocking", "production", "customer impact", "release blocker", "regression"
> - Score true_urgency on these signals, not on the label
> - Flag disagreement only when the body contradicts the label by a clear margin
> - When flagging disagreement, give a specific quote-grounded reason ("Body says 'blocks Q3 release' but label is Low")
>
> If there's no linked issue, return `stated_priority="unknown"`, `true_urgency_score=0.5`, `label_disagreement=False`, `disagreement_reason=None`, `keywords_extracted=[]`.

**Files added:**
- `server/src/agents/ticket_context.py`
- `server/tests/test_ticket_context.py`

**Acceptance criteria:**
- [ ] Smoke test on a PR with a meaty linked issue produces sensible urgency score
- [ ] PR with no linked issue returns the "unknown" defaults
- [ ] When `label_disagreement=True`, `disagreement_reason` is non-empty

**Commit message:**
```
feat(agents): ticket context (label-vs-reality mismatch)

Haiku agent reading the linked issue body to assess whether
the stated priority label matches the urgency described in
the text. Flags disagreement when body contradicts label
(e.g. "blocks Q3 release" labeled Low).

The disagreement signal is the product's edge — labels are
stale, body text is reliable. This agent surfaces the gap.

When no linked issue exists, returns neutral defaults rather
than guessing.
```

---

### Commit 10 — `feat(agents): author profile (trust scoring)`

**Phase:** 3 &nbsp; **Hour:** 8.5 → 9.5 &nbsp; **Depends on:** Commit 7

**What this commit produces:** the Haiku agent that scores how much reviewer attention a PR needs based on the author's track record.

**Claude Code instructions:**
> Create `server/src/agents/author_profile.py`.
>
> Define:
> ```python
> class AuthorAssessment(BaseModel):
>     trust_score: float                  # 0.0-1.0, where 1 = high trust (short review acceptable)
>     recommended_review_depth: str       # "skim" | "standard" | "deep"
>     rationale: str                      # one sentence
>
> class AuthorProfileAgent(BaseAgent[AuthorAssessment]):
>     name = "author_profile"
>     model = "claude-haiku-4-5-20251001"
>     output_schema = AuthorAssessment
>     system_prompt = """..."""
> ```
>
> System prompt:
> - High merged-count + low revert-rate + thorough past PRs = high trust → "skim"
> - First-time contributor or high revert-rate = low trust → "deep"
> - Mid-range = "standard"
> - Be explicit in the rationale: cite the numbers
>
> Input to the agent is a compact summary of the `AuthorProfile` Pydantic model from commit 4.

**Files added:**
- `server/src/agents/author_profile.py`
- `server/tests/test_author_profile.py`

**Acceptance criteria:**
- [ ] High-volume, low-revert author scores ≥ 0.7 trust
- [ ] First-time contributor (0 merged) scores ≤ 0.4 trust → "deep"
- [ ] Rationale cites at least one number from the input

**Commit message:**
```
feat(agents): author profile (trust scoring)

Haiku agent translating raw author metrics (merged-count,
revert-rate, review-comment density) into a trust score and
recommended review depth (skim / standard / deep).

High trust → reviewer can skim. Low trust → deep review.
The rationale field must cite at least one specific number
from the input so the user understands the call.

Combined with diff_analyst's blast_radius, this is what
lets the synthesizer say "skim this 200-line PR by alice but
deep-review the 50-line PR by a new contributor."
```

---

### Commit 11 — `feat(agents): synthesizer producing ranked queue`

**Phase:** 3 &nbsp; **Hour:** 9.5 → 10.5 &nbsp; **Depends on:** Commits 8, 9, 10

**What this commit produces:** the Sonnet orchestrator that takes all sub-agent outputs across N PRs and produces the final ranked queue with reasoning.

**Claude Code instructions:**
> Create `server/src/agents/synthesizer.py` and `server/src/pipeline.py`.
>
> Define in `synthesizer.py`:
> ```python
> class RankedPR(BaseModel):
>     pr_number: int
>     rank: int                           # 1-based
>     reasoning: str                      # 1-2 sentences
>     ai_priority: str                    # "high" | "medium" | "low"
>     label_disagreement: bool            # AI vs label
>
> class Ranking(BaseModel):
>     prs: list[RankedPR]
>
> class SynthesizerAgent(BaseAgent[Ranking]):
>     name = "synthesizer"
>     model = "claude-sonnet-4-5-20251022"
>     output_schema = Ranking
>     system_prompt = """..."""
> ```
>
> System prompt:
> - Rank from most-urgent-to-review to least
> - Weight signals: blast_radius_score (40%), true_urgency_score (25%), dependency_chain_depth (20%), inverse of author trust (10%), effort estimate (5% — prefer faster reviews when equal)
> - Set `label_disagreement = True` whenever your `ai_priority` differs from the input's `stated_priority` by more than one level (high → low, medium → low, etc.)
> - Reasoning must be specific and cite at least one signal value
>
> Create `pipeline.py`:
> ```python
> async def run_pipeline(client: AsyncAnthropic, gh: GitHubClient, owner: str, name: str) -> Ranking:
>     # 1. Fetch open PRs
>     # 2. For each PR, fetch files + author history (concurrent via asyncio.gather)
>     # 3. Extract features
>     # 4. Detect cross-PR dependencies
>     # 5. Run DiffAnalystAgent, TicketContextAgent, AuthorProfileAgent in parallel per PR
>     # 6. Build a compact summary string per PR with all signals
>     # 7. Call SynthesizerAgent once with all summaries
>     # 8. Return the Ranking
> ```

**Files added:**
- `server/src/agents/synthesizer.py`
- `server/src/pipeline.py`

**Acceptance criteria:**
- [ ] End-to-end smoke test on `kubernetes/kubernetes` returns a `Ranking` with all input PRs ranked
- [ ] At least one PR has `label_disagreement=True` on a typical run
- [ ] Total wall-clock time under 60 seconds for 20 PRs

**Commit message:**
```
feat(agents): synthesizer producing ranked queue

Sonnet 4.5 orchestrator that consumes the three Haiku
sub-agents' outputs across all open PRs and produces a
single ranked queue with per-PR reasoning.

Weighting in the system prompt:
- blast_radius_score      40%
- true_urgency_score      25%
- dependency_chain_depth  20%
- (1 - author_trust)      10%
- inverse effort           5%

The label_disagreement flag fires when the AI's ai_priority
differs from the input label by more than one level — this
is the badge that appears on cards in the UI.

Pipeline orchestration in src/pipeline.py uses asyncio.gather
to parallelize per-PR analysis, keeping total latency under
60 seconds for typical 20-PR queues.
```

---

### Commit 12 — `feat(agents): critic agent with rank-correction pass`

**Phase:** 3 &nbsp; **Hour:** 10.5 → 11.5 &nbsp; **Depends on:** Commit 11

**What this commit produces:** a Sonnet critic that reviews the synthesizer's ranking, flags errors, and optionally swaps positions.

**Claude Code instructions:**
> Create `server/src/agents/critic.py`.
>
> Define:
> ```python
> class RankingCritique(BaseModel):
>     adjustments: list[dict]             # [{"pr_number": int, "new_rank": int, "reason": str}, ...]
>     overall_assessment: str             # 1-2 sentences on whether the ranking is sound
>
> class CriticAgent(BaseAgent[RankingCritique]):
>     name = "critic"
>     model = "claude-sonnet-4-5-20251022"
>     output_schema = RankingCritique
>     system_prompt = """..."""
> ```
>
> System prompt:
> - Look for ranking errors: PRs with high blast_radius ranked below low-risk PRs, PRs blocking other PRs ranked too low, PRs with `label_disagreement=True` whose reasoning doesn't justify the disagreement
> - Propose at most 3 swaps — if the ranking is sound, return `adjustments=[]`
> - Each swap must include a specific reason citing the signal that triggered the swap
>
> Update `pipeline.py` to:
> 1. Run synthesizer
> 2. Run critic with synthesizer's output
> 3. Apply any adjustments (move PRs to their new_rank, shift others)
> 4. Return final adjusted Ranking

**Files added/modified:**
- `server/src/agents/critic.py`
- `server/src/pipeline.py` (apply critic adjustments)

**Acceptance criteria:**
- [ ] Smoke test: pipeline runs end-to-end, sometimes critic returns empty adjustments, sometimes non-empty
- [ ] When non-empty, every adjustment has a specific reason
- [ ] Final ranking has unique ranks 1..N with no gaps

**Commit message:**
```
feat(agents): critic agent with rank-correction pass

Sonnet critic that reviews the synthesizer's ranking and
proposes at most 3 swaps, each with a signal-grounded
justification. Empty adjustments list = ranking confirmed.

Common catches the critic surfaces:
- High blast-radius PRs ranked behind low-risk ones
- Dependency-blocking PRs ranked too low
- label_disagreement flagged without reasoning that justifies it

Pipeline now: synthesizer → critic → apply adjustments →
final Ranking. This is the "evaluation loop" requirement
made concrete inside the live pipeline (separate from the
offline retrospective-replay eval added in phase 4).
```

---

### Commit 13 — `feat(eval): retrospective replay harness`

**Phase:** 4 — Evaluation &nbsp; **Hour:** 11.5 → 12.5 &nbsp; **Depends on:** Commit 4

**What this commit produces:** the harness that reconstructs historical open-PR sets at a past timestamp and records the actual review/merge order over the subsequent N days.

**Claude Code instructions:**
> Create `server/src/eval/__init__.py`, `server/src/eval/snapshot.py`, and `server/src/eval/ground_truth.py`.
>
> In `snapshot.py`:
> ```python
> async def reconstruct_open_prs_at(gh: GitHubClient, owner: str, name: str, t0: datetime, limit: int = 30) -> list[PRContext]:
>     # Fetch PRs that were open AND unreviewed at t0
>     # Use GitHub API filters: createdAt < t0 AND (firstReviewAt > t0 OR firstReviewAt IS NULL)
>     # Cap at `limit` PRs (closest-to-t0 first by creation date)
> ```
>
> In `ground_truth.py`:
> ```python
> async def actual_review_order(gh: GitHubClient, owner: str, name: str, pr_numbers: list[int], t0: datetime, window_days: int = 14) -> list[int]:
>     # For each PR, find the timestamp of its FIRST review/merge after t0
>     # Return pr_numbers sorted by that timestamp (earliest first)
>     # PRs not reviewed within window go last
> ```

**Files added:**
- `server/src/eval/__init__.py`
- `server/src/eval/snapshot.py`
- `server/src/eval/ground_truth.py`

**Acceptance criteria:**
- [ ] Manual smoke test on K8s at a timestamp 30 days ago returns >5 PRs
- [ ] Ground-truth order is well-defined (no ties; PRs with same timestamp broken by PR number)

**Commit message:**
```
feat(eval): retrospective replay harness

Reconstructs the historical open-PR set at any past timestamp
t0, plus the actual review/merge order over the following
window_days (default 14).

The maintainer's revealed review order IS the ground truth —
no synthetic labels, no subjective judgment. Whatever they
actually reviewed first is what "should have been #1".

Foundation for the eval methodology that wins the submission:
NDCG@5 of predicted ranking vs actual review order across N
historical snapshots.
```

---

### Commit 14 — `feat(eval): baseline rankers (random / label / author)`

**Phase:** 4 &nbsp; **Hour:** 12.5 → 13 &nbsp; **Depends on:** Commit 5

**What this commit produces:** three control rankers used to show that TriagePilot beats the dumb baselines.

**Claude Code instructions:**
> Create `server/src/eval/baselines.py`.
>
> ```python
> def random_ranker(prs: list[PRFeatures], seed: int = 42) -> list[int]:
>     # Return pr_numbers in random order; deterministic with seed
>
> def label_only_ranker(prs: list[PRFeatures]) -> list[int]:
>     # Sort by ticket_priority_label: high > medium > low > None
>     # Tiebreaker: pr_age_days (older first)
>
> def author_only_ranker(prs: list[PRFeatures]) -> list[int]:
>     # Sort by author_merged_pr_count descending (high-volume authors first)
>     # Tiebreaker: pr_age_days
> ```

**Files added:**
- `server/src/eval/baselines.py`

**Acceptance criteria:**
- [ ] Each returns a permutation of input PR numbers
- [ ] `random_ranker` is reproducible with same seed
- [ ] `label_only_ranker` puts a "high" labeled PR ahead of a "low" labeled PR

**Commit message:**
```
feat(eval): baseline rankers (random / label / author)

Three control rankers for the comparison table:

- random_ranker: uniform shuffle (seeded for reproducibility)
- label_only_ranker: sort by ticket priority alone
- author_only_ranker: sort by author's merged-PR count

The label_only ranker is the most important baseline — it
represents "what you'd get if you sorted by Jira priority
without AI." TriagePilot has to beat this meaningfully or
the product thesis collapses.
```

---

### Commit 15 — `feat(eval): NDCG@k and Kendall tau metrics + runner`

**Phase:** 4 &nbsp; **Hour:** 13 → 14 &nbsp; **Depends on:** Commits 13, 14

**What this commit produces:** ranking metrics + a script that runs all rankers over N snapshots and dumps results to disk.

**Claude Code instructions:**
> Create `server/src/eval/metrics.py` and `server/scripts/run_eval.py`.
>
> `metrics.py`:
> ```python
> def ndcg_at_k(predicted: list[int], ground_truth: list[int], k: int = 5) -> float:
>     # Standard NDCG@k where relevance is `len(ground_truth) - position_in_truth`
>
> def kendall_tau(predicted: list[int], ground_truth: list[int]) -> float:
>     # Use scipy.stats.kendalltau; return just the statistic
> ```
>
> `run_eval.py`:
> - CLI args: `--repo owner/name`, `--snapshots N` (default 8), `--lookback-days D` (default 60), `--window-days W` (default 14), `--out PATH`
> - For each of N evenly-spaced timestamps in the last D days:
>   - Reconstruct open PRs
>   - Compute ground truth review order
>   - Run all 4 rankers (random, label, author, triagepilot)
>   - Compute NDCG@5 and Kendall tau for each
> - Output: a markdown table to stdout and JSON to `--out` path with per-snapshot detail
> - Print final aggregate table at the end (mean ± stddev per ranker)

**Files added:**
- `server/src/eval/metrics.py`
- `server/scripts/__init__.py`
- `server/scripts/run_eval.py`

**Acceptance criteria:**
- [ ] `make eval` runs end-to-end (use a small N like 2 for the smoke test)
- [ ] Output table has 4 rows × 2 metric columns × N snapshots
- [ ] Aggregate table at the end is human-readable

**Commit message:**
```
feat(eval): NDCG@k and Kendall tau metrics + runner

Two standard ranking metrics:
- NDCG@5: position-weighted relevance, emphasizes top-of-list
- Kendall tau: pairwise concordance, full-list quality

The runner (scripts/run_eval.py) sweeps N historical snapshots,
runs all 4 rankers, computes both metrics, and emits both a
human-readable markdown table and a machine-readable JSON.

This is the script that produces the headline numbers for
README.md and docs/eval_results.md. Runs in 5-10 minutes for
8 K8s snapshots (cached after first run).
```

---

### Commit 16 — `feat(api): FastAPI service with /rank and SSE streaming endpoint`

**Phase:** 5 — Backend API &nbsp; **Hour:** 14 → 15 &nbsp; **Depends on:** Commit 12

**What this commit produces:** the live API the web app will call — non-streaming JSON endpoint plus SSE streaming endpoint for live agent progress.

**Claude Code instructions:**
> Rewrite `server/src/api/main.py`.
>
> Endpoints:
> - `GET /health` — returns `{"ok": true}` (already exists; keep)
> - `GET /rank/{owner}/{repo}` — runs the full pipeline, returns the final `Ranking` as JSON
> - `GET /rank/{owner}/{repo}/stream` — Server-Sent Events; emits events as agents complete
>
> SSE event types:
> ```
> event: pipeline_started
> data: {"total_prs": 20}
>
> event: agent_completed
> data: {"agent": "diff_analyst", "pr_number": 4521, "result": {...}}
>
> event: synthesizer_completed
> data: {"ranking": [...]}
>
> event: critic_completed
> data: {"adjustments": [...]}
>
> event: pipeline_done
> data: {"final_ranking": [...]}
> ```
>
> CORS configuration:
> - Read `ALLOWED_ORIGIN` from env (default `http://localhost:3000`)
> - Use FastAPI's `CORSMiddleware` allowing GET, with that origin only
>
> Wire up:
> - On startup, instantiate one `AsyncAnthropic` client and one `GitHubClient` with env-loaded tokens; store on app state
> - Both endpoints read from app state

**Files modified:**
- `server/src/api/main.py`
- `server/.env.example` (already has ALLOWED_ORIGIN — confirm)

**Acceptance criteria:**
- [ ] `curl http://localhost:8000/rank/kubernetes/kubernetes` returns a JSON ranking within 60s
- [ ] `curl -N http://localhost:8000/rank/kubernetes/kubernetes/stream` shows SSE events in real time
- [ ] Setting `ALLOWED_ORIGIN=https://nope.example` and fetching from localhost:3000 in browser gets a CORS error

**Commit message:**
```
feat(api): FastAPI service with /rank and SSE streaming endpoint

Three endpoints:
- GET /health                              liveness probe for Fly
- GET /rank/{owner}/{repo}                 full pipeline, JSON result
- GET /rank/{owner}/{repo}/stream          Server-Sent Events

SSE events: pipeline_started, agent_completed (per PR per agent),
synthesizer_completed, critic_completed, pipeline_done.

CORS middleware restricts origins to ALLOWED_ORIGIN env var.
Anthropic and GitHub clients instantiated once on startup and
shared via app state.
```

---

### Commit 17 — `feat(api): in-memory TTL cache for rank responses`

**Phase:** 5 &nbsp; **Hour:** 15 → 15.5 &nbsp; **Depends on:** Commit 16

**What this commit produces:** a 10-minute cache layer on `/rank` responses keyed by `(owner, repo)` to avoid re-running the agent pipeline on repeat queries.

**Claude Code instructions:**
> Add `server/src/api/cache.py` with a simple TTL dict:
> ```python
> class TTLCache:
>     def __init__(self, ttl_seconds: int = 600): ...
>     def get(self, key: str) -> Any | None: ...
>     def set(self, key: str, value: Any) -> None: ...
> ```
>
> Wire into `main.py`:
> - On `GET /rank/{owner}/{repo}`, check cache; if hit, return immediately
> - On miss, run pipeline, store result, return
> - Cache key: `f"{owner}/{repo}"`
> - SSE endpoint does NOT use the cache (always re-runs so user sees fresh streaming)

**Files added/modified:**
- `server/src/api/cache.py`
- `server/src/api/main.py`

**Acceptance criteria:**
- [ ] Second call within 10 minutes returns instantly (< 100ms)
- [ ] Call after 11 minutes re-runs the pipeline
- [ ] SSE endpoint always re-runs regardless of cache state

**Commit message:**
```
feat(api): in-memory TTL cache for rank responses

Simple 10-minute cache keyed by (owner, repo). Avoids
re-running the multi-agent pipeline on repeat queries
during demos and dev iteration.

Only the non-streaming /rank endpoint uses the cache; the
SSE stream always re-runs so the user sees fresh per-agent
progress when they explicitly ask for it.
```

---

### Commit 18 — `feat(web): Next.js ranked queue with streaming reasoning (shadcn/ui)`

**Phase:** 6 — Frontend &nbsp; **Hour:** 15.5 → 17.5 &nbsp; **Depends on:** Commit 16

**What this commit produces:** the polished web app — single page, form input, streaming agent progress, ranked card list with disagreement badges.

**Claude Code instructions:**
> Build the Next.js app under `web/`. Install shadcn/ui first:
> ```bash
> cd web && pnpm dlx shadcn@latest init -d
> pnpm dlx shadcn@latest add card button badge skeleton input
> ```
>
> Create the following files:
>
> 1. `web/lib/types.ts` — TypeScript types mirroring the Python `RankedPR` and `Ranking` Pydantic models.
>
> 2. `web/lib/api-client.ts`:
>    - Export `streamRanking(repoSlug: string, onEvent: (type: string, data: any) => void): Promise<void>` using `EventSource` to consume the SSE endpoint at `${NEXT_PUBLIC_API_URL}/rank/${repoSlug}/stream`.
>    - Export `fetchRanking(repoSlug: string): Promise<Ranking>` for the non-streaming fallback.
>
> 3. `web/components/TriageForm.tsx` — input field for `owner/repo`, "Triage now" button. Validates the format with a regex. Calls `onSubmit(repoSlug)` from the parent.
>
> 4. `web/components/PRCard.tsx` — shadcn `Card` showing:
>    - Position pill (Badge with `#{rank}`)
>    - Title + author + link to GitHub
>    - Disagreement badge (shadcn `Badge variant="destructive"`) when `label_disagreement === true`, with text "Labeled {ticket_priority} • AI says {ai_priority}"
>    - One-sentence `reasoning`
>    - "Review on GitHub →" button linking to the PR URL
>
> 5. `web/components/RankedQueue.tsx` — manages SSE state:
>    - On submit, opens EventSource, shows skeleton cards for each PR as `pipeline_started` arrives with total count
>    - Updates the visible state as `agent_completed` events arrive (shows a small "Diff Analyst ✓" tick per PR)
>    - When `pipeline_done` arrives, renders the final ranked queue using `PRCard`
>
> 6. `web/app/page.tsx` — single page composing `TriageForm` + `RankedQueue`. Hero text:
>    > **TriagePilot** — Your labels lie. We tell you the truth.
>    > Paste a GitHub repo, get the right review order.
>
>    Below the hero: small suggestion text "Try `kubernetes/kubernetes` or `vercel/next.js`".
>
> 7. `web/app/layout.tsx` — minimal layout with Tailwind config, dark/light support via system preference, sensible font (Geist or Inter).
>
> Mobile-responsive: cards stack to single column on `< md` breakpoint.

**Files added:**
- `web/lib/types.ts`
- `web/lib/api-client.ts`
- `web/components/TriageForm.tsx`
- `web/components/RankedQueue.tsx`
- `web/components/PRCard.tsx`
- `web/components/ui/{card,button,badge,skeleton,input}.tsx` (from shadcn)
- `web/components.json` (shadcn config)
- `web/app/page.tsx` (rewrite)
- `web/app/layout.tsx` (rewrite)
- `web/app/globals.css` (shadcn updates)

**Acceptance criteria:**
- [ ] Type `kubernetes/kubernetes` → see streaming progress within 2s
- [ ] Final ranking renders within 60s with proper cards
- [ ] At least one disagreement badge shows on a typical K8s run
- [ ] Mobile view (Chrome devtools 375px) is single-column and readable
- [ ] No console errors

**Commit message:**
```
feat(web): Next.js ranked queue with streaming reasoning (shadcn/ui)

Single-page Next.js 15 App Router application:
- TriageForm: owner/repo input with format validation
- RankedQueue: EventSource SSE consumer rendering live progress
- PRCard: shadcn Card with position pill, title+author+link,
  disagreement badge, one-sentence reasoning, "Review on GitHub" CTA

Skeleton cards appear instantly on submit (one per expected PR).
Each agent completion fills in the corresponding tick. Final
ranking replaces skeletons with full cards when pipeline_done
fires.

Mobile-responsive: cards stack single-column under md breakpoint.
Hero copy: "Your labels lie. We tell you the truth."
```

---

### Commit 19 — `feat(telegram): morning brief delivery with scheduler`

**Phase:** 7 — Telegram &nbsp; **Hour:** 17.5 → 18.5 &nbsp; **Depends on:** Commit 17

**What this commit produces:** the Telegram bot sending a daily 9 AM brief and an on-demand admin trigger.

**Claude Code instructions:**
> Create `server/src/telegram/__init__.py` and `server/src/telegram/bot.py`.
>
> Implement:
> ```python
> async def format_brief(ranking: Ranking, repo: str, total_prs: int) -> str:
>     # Returns a Telegram-formatted string with top-5 PRs and a /full hint
>
> async def send_morning_brief(chat_id: str, bot_token: str, ranking: Ranking, repo: str): ...
> ```
>
> The brief format (Markdown):
> ```
> 🌅 *Good morning.*
> You have {total} open PRs in {repo}. Top 5 to review:
>
> ⚡ *#1* — {title}
>    ⚠ {disagreement_reason if applicable}
>    📎 [github.com/...]({pr_url})
>
> (...repeat for top 5...)
>
> Reply /full for the complete queue.
> ```
>
> In `server/src/api/main.py`:
> - On startup, instantiate APScheduler `AsyncIOScheduler`
> - Schedule `send_morning_brief` at 09:00 daily in the timezone from env (`TIMEZONE`, default `Asia/Karachi`)
> - Repo is from env `MONITORED_REPO`
> - Add admin endpoint `POST /trigger-brief` that fires the brief immediately (for the Loom recording and manual testing). Protect it with a simple header check: require `X-Admin-Token: <env value>`.

**Files added/modified:**
- `server/src/telegram/__init__.py`
- `server/src/telegram/bot.py`
- `server/src/api/main.py` (scheduler + admin endpoint)
- `server/.env.example` (add `TIMEZONE`, `ADMIN_TOKEN`)

**Acceptance criteria:**
- [ ] `POST /trigger-brief` (with admin header) delivers a real Telegram message to your chat
- [ ] Message shows top 5 PRs with proper formatting
- [ ] Disagreement reasons render when present
- [ ] Scheduler is registered (visible in logs on startup)

**Commit message:**
```
feat(telegram): morning brief delivery with scheduler

Daily 9:00 AM (timezone-configurable) Telegram brief showing
top-5 PRs to review with disagreement reasons when present.
Each PR has a direct GitHub link for tap-to-open from mobile.

APScheduler manages the daily job. Admin endpoint
POST /trigger-brief (gated by X-Admin-Token header) fires
the brief on demand — used for the Loom recording and for
mid-day on-demand briefs.
```

---

### Commit 20 — `chore(deploy): Dockerfile + fly.toml for FastAPI backend`

**Phase:** 8 — Deploy &nbsp; **Hour:** 18.5 → 19.5 &nbsp; **Depends on:** Commit 19

**What this commit produces:** the deployable container image and Fly.io config for the backend.

**Claude Code instructions:**
> Create `server/Dockerfile`:
> ```dockerfile
> FROM python:3.11-slim
> WORKDIR /app
> RUN pip install --no-cache-dir uv
> COPY pyproject.toml uv.lock ./
> RUN uv sync --frozen --no-dev
> COPY src/ ./src/
> COPY scripts/ ./scripts/
> EXPOSE 8080
> CMD ["uv", "run", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
> ```
>
> Create `server/.dockerignore`:
> ```
> tests/
> .cache/
> .venv/
> __pycache__/
> *.pyc
> .env
> .pytest_cache/
> data/
> ```
>
> Create `server/fly.toml`:
> ```toml
> app = "triagepilot-api"
> primary_region = "sin"  # Singapore — close to KST
>
> [build]
>
> [http_service]
>   internal_port = 8080
>   force_https = true
>   auto_stop_machines = false
>   min_machines_running = 1
>   processes = ["app"]
>
> [[vm]]
>   cpu_kind = "shared"
>   cpus = 1
>   memory_mb = 512
>
> [checks]
>   [checks.health]
>     port = 8080
>     type = "http"
>     interval = "30s"
>     timeout = "5s"
>     grace_period = "10s"
>     method = "GET"
>     path = "/health"
> ```

**Files added:**
- `server/Dockerfile`
- `server/.dockerignore`
- `server/fly.toml`

**Acceptance criteria:**
- [ ] `cd server && docker build -t triagepilot-api .` succeeds locally (optional but recommended)
- [ ] Image size < 300MB
- [ ] No `.env` or `.cache/` ends up in the image

**Commit message:**
```
chore(deploy): Dockerfile + fly.toml for FastAPI backend

Single-stage Python 3.11 slim image using uv for dependency
sync. Final image ~150MB. Runs uvicorn on port 8080.

fly.toml: primary region Singapore (close to KST users),
auto_stop_machines=false + min_machines_running=1 to avoid
cold starts during reviewer demos. Health check polls /health
every 30 seconds.

.dockerignore excludes tests/, .cache/, .venv/, data/, and
secrets to keep the image lean.
```

---

### Commit 21 — `deploy: ship v0.1-mvp (Fly.io backend + Vercel web)`

**Phase:** 8 &nbsp; **Hour:** 19.5 → 20.5 &nbsp; **Depends on:** Commit 20

**What this commit produces:** the live, end-to-end deployed system. Tag `v0.1-mvp` after this commit.

**Claude Code instructions (this commit is mostly CLI work, not code):**
> 1. From `server/`, set Fly secrets:
>    ```bash
>    fly secrets set \
>      GITHUB_TOKEN=ghp_... \
>      ANTHROPIC_API_KEY=sk-ant-... \
>      TELEGRAM_BOT_TOKEN=... \
>      TELEGRAM_CHAT_ID=... \
>      ADMIN_TOKEN=$(openssl rand -hex 16) \
>      ALLOWED_ORIGIN=https://triagepilot.vercel.app \
>      MONITORED_REPO=kubernetes/kubernetes \
>      TIMEZONE=Asia/Karachi \
>      -a triagepilot-api
>    ```
>
> 2. Deploy: `cd server && fly deploy`
> 3. Verify: `curl https://triagepilot-api.fly.dev/health` returns `{"ok": true}`
> 4. In Vercel dashboard:
>    - Project Settings → Root Directory → set to `web`
>    - Environment Variables → add `NEXT_PUBLIC_API_URL=https://triagepilot-api.fly.dev`
>    - Trigger redeploy (push an empty commit or click Redeploy)
> 5. Verify: open `https://triagepilot.vercel.app` in incognito, paste `kubernetes/kubernetes`, watch streaming → see final ranking
>
> Update `web/.env.local.example` to show the production URL as the comment example.

**Files modified:**
- `web/.env.local.example` (comment update only)
- Possibly minor `server/fly.toml` tweak if you hit any deploy hiccup

**Acceptance criteria:**
- [ ] `https://triagepilot-api.fly.dev/health` returns ok
- [ ] `https://triagepilot.vercel.app` loads in incognito
- [ ] End-to-end query on `kubernetes/kubernetes` returns ranking
- [ ] Open dev tools on Vercel site, confirm SSE events flowing
- [ ] No CORS errors in browser console

**After committing, tag:**
```bash
git tag -a v0.1-mvp -m "First deployed end-to-end: Fly backend + Vercel web"
git push origin v0.1-mvp
```

**Commit message:**
```
deploy: ship v0.1-mvp (Fly.io backend + Vercel web)

Backend live: https://triagepilot-api.fly.dev
Web live:     https://triagepilot.vercel.app

Vercel auto-deployed via GitHub integration. Project Root
Directory set to `web/`. NEXT_PUBLIC_API_URL points to the
Fly backend.

End-to-end smoke test passed: paste kubernetes/kubernetes,
streaming agent progress visible within 2s, final ranking
within 60s, disagreement badges firing on labeled-low PRs
with high blast radius.

Tagged v0.1-mvp.
```

---

### Commit 22 — `eval: retrospective replay on Kubernetes and Next.js (multi-snapshot)`

**Phase:** 9 — Eval Runs &nbsp; **Hour:** 20.5 → 21.5 &nbsp; **Depends on:** Commits 15, 21

**What this commit produces:** the actual headline numbers for the README and the killer-moment screenshots.

**Claude Code instructions (mostly CLI; some doc generation):**
> 1. Run the eval on Kubernetes (8 snapshots over last 60 days):
>    ```bash
>    cd server && make eval REPO=kubernetes/kubernetes SNAPSHOTS=8 --out=data/k8s_snapshots.json
>    ```
> 2. Run on Next.js (5 snapshots, smaller team):
>    ```bash
>    cd server && make eval REPO=vercel/next.js SNAPSHOTS=5 --out=data/nextjs_snapshots.json
>    ```
> 3. Create `docs/eval_results.md` containing:
>    - Headline result table:
>      | Ranker | NDCG@5 (K8s) | Kendall τ (K8s) | NDCG@5 (Next.js) | Kendall τ (Next.js) |
>      | --- | --- | --- | --- | --- |
>      | Random | ... | ... | ... | ... |
>      | Label-only | ... | ... | ... | ... |
>      | Author-only | ... | ... | ... | ... |
>      | **TriagePilot** | ... | ... | ... | ... |
>    - Per-snapshot detail table (collapsible)
>    - One "killer moment" subsection: pick a snapshot where TriagePilot ranked a PR in the top 3 that the maintainer actually reviewed 4+ days later. Include the PR link, the timeline, and screenshots of the relevant maintainer comment (e.g. "sorry this slipped").
>
> 4. Generate two charts (use a simple matplotlib script saved to `server/scripts/plot_eval.py`):
>    - Bar chart: NDCG@5 by ranker for each repo
>    - Per-snapshot scatter showing TriagePilot vs label-only NDCG
>    Save PNGs to `docs/charts/` and reference them from `eval_results.md`.

**Files added:**
- `server/data/k8s_snapshots.json`
- `server/data/nextjs_snapshots.json`
- `docs/eval_results.md`
- `docs/charts/ndcg_by_ranker.png`
- `docs/charts/per_snapshot_scatter.png`
- `server/scripts/plot_eval.py`

**Acceptance criteria:**
- [ ] Headline table populated with real numbers
- [ ] TriagePilot beats label-only on NDCG@5 by ≥ 0.10 on at least one repo
- [ ] Killer-moment section has a specific PR link with timeline
- [ ] Charts render correctly

**Commit message:**
```
eval: retrospective replay on Kubernetes and Next.js (multi-snapshot)

8 K8s snapshots (formal /priority labels) + 5 Next.js
snapshots (lighter label structure). 14-day forward window
for ground-truth review order.

Headline results in docs/eval_results.md:
- TriagePilot NDCG@5: 0.XX (K8s) / 0.XX (Next.js)
- Label-only NDCG@5: 0.XX (K8s) / 0.XX (Next.js)

The killer-moment subsection documents one PR where
TriagePilot would have ranked #2 but maintainers reviewed
6 days later — including the comment thread showing it slipped.
```

---

### Commit 23 — `fix(prompts): improve synthesizer weighting for blast-radius signal`

**Phase:** 9 &nbsp; **Hour:** 21.5 → 22 &nbsp; **Depends on:** Commit 22

**What this commit produces:** a targeted prompt improvement based on what the eval surfaced (you'll only know exactly what to fix after running Commit 22).

**Claude Code instructions:**
> Open `docs/eval_results.md` and identify the most common failure mode. Likely candidates:
> - Low-priority PRs with high blast_radius being under-ranked
> - Stale PRs not penalized enough
> - Author trust over-weighted
>
> Update the synthesizer system prompt in `server/src/agents/synthesizer.py` to address it. Specifics depend on what the eval shows. Example for the most likely case:
>
> > Add to system prompt: "When ticket priority is 'low' or 'medium' but blast_radius_score >= 0.7, give blast_radius weight 50% (instead of 40%) and treat the label as untrustworthy noise."
>
> Re-run the eval and compare. If the new run shows improvement, commit. If not, try a different prompt change.

**Files modified:**
- `server/src/agents/synthesizer.py`
- `docs/eval_results.md` (add "Before/After prompt change" subsection)

**Acceptance criteria:**
- [ ] Pre-change NDCG@5 captured in `docs/eval_results.md`
- [ ] Post-change NDCG@5 captured and improved by ≥ 0.02
- [ ] The "what I learned" reasoning is in the commit body

**Commit message:**
```
fix(prompts): improve synthesizer weighting for blast-radius signal

Eval surfaced that low-priority PRs touching auth/infrastructure
were ranked too low — the synthesizer was respecting the label
even when blast_radius_score was very high.

Adjusted the synthesizer system prompt to give blast_radius
weight 50% (instead of 40%) when label is low/medium but
blast_radius_score >= 0.7, treating the label as untrustworthy
noise in that regime.

Eval delta on Kubernetes (8 snapshots):
  NDCG@5 before: 0.XX
  NDCG@5 after:  0.YY
  Kendall τ:    0.XX → 0.YY
```

---

### Commit 24 — `eval: re-run final eval pass with updated synthesizer prompt`

**Phase:** 9 &nbsp; **Hour:** 22 → 22.25 &nbsp; **Depends on:** Commit 23

**What this commit produces:** the final eval numbers used in the README, after the prompt fix.

**Claude Code instructions:**
> Re-run both evals end-to-end:
> ```bash
> cd server && make eval REPO=kubernetes/kubernetes SNAPSHOTS=8 --out=data/k8s_snapshots_v2.json
> make eval REPO=vercel/next.js SNAPSHOTS=5 --out=data/nextjs_snapshots_v2.json
> ```
>
> Update `docs/eval_results.md`:
> - Replace headline table with new numbers
> - Add a "Methodology" subsection citing the exact procedure (T0 selection, window, metrics)
> - Regenerate charts via `python scripts/plot_eval.py`
> - Confirm killer-moment example still holds (rerun synthesizer on that snapshot)

**Files modified:**
- `docs/eval_results.md`
- `server/data/k8s_snapshots_v2.json`
- `server/data/nextjs_snapshots_v2.json`
- `docs/charts/*.png` (regenerated)

**Acceptance criteria:**
- [ ] All numbers in headline table match the v2 JSONs
- [ ] Charts regenerated and committed
- [ ] Methodology subsection is reproducible from the docs alone

**Commit message:**
```
eval: re-run final eval pass with updated synthesizer prompt

Final eval numbers post prompt fix:
  Kubernetes  NDCG@5: 0.XX  Kendall τ: 0.XX
  Next.js     NDCG@5: 0.XX  Kendall τ: 0.XX

Charts regenerated. Methodology section now reproducible
from the docs alone (T0 selection, forward window, metric
definitions all spelled out).
```

---

### Commit 25 — `docs: complete README with eval results and screenshots`

**Phase:** 10 — Documentation &nbsp; **Hour:** 22.25 → 23 &nbsp; **Depends on:** Commit 24

**What this commit produces:** the final README with all 7 Quest 1 sections filled in, including embedded screenshots and the headline eval table.

**Claude Code instructions:**
> Replace the README skeleton with the full version. Use this structure exactly (the 7 sections are non-negotiable per Quest requirements):
>
> ```markdown
> # TriagePilot
>
> > Your labels lie. TriagePilot tells you the truth, every morning at 9 AM.
>
> **Live demo:** https://triagepilot.vercel.app
> **Backend:** https://triagepilot-api.fly.dev
> **Loom walkthrough (5 min):** [to be filled in commit 28]
> **Eval results:** [docs/eval_results.md](docs/eval_results.md)
>
> ## Problem Definition & Target User
>
> [200 words, anchored on senior engineer morning queue]
>
> ## Why This Problem Matters
>
> [150 words: cost of mis-prioritization, why labels fail, why this is an AI problem]
>
> ## How the Solution Works
>
> [Architecture diagram + 2 paragraphs on user journey + multi-agent flow]
>
> ## AI-Native Workflow
>
> Tools, models, agents used:
> - Anthropic Claude Sonnet 4.5 (synthesizer + critic)
> - Anthropic Claude Haiku 4.5 (diff analyst + ticket context + author profile)
> - GitHub GraphQL API
> - Python 3.11 + FastAPI + asyncio
> - Next.js 15 + shadcn/ui + Vercel AI SDK
>
> [Agent flow diagram]
>
> **AI tools used during development:**
> - Claude Code: scaffolding, GraphQL queries, agent boilerplate
> - [add any others used]
>
> ## Evaluation Method & Results
>
> [Headline table + chart + killer-moment screenshot]
>
> ### Methodology
>
> [Retrospective replay description]
>
> ## Baseline Comparison: Why Not Just Use ChatGPT?
>
> [The experiment: same PR list pasted into ChatGPT, side-by-side ranking, NDCG@5 of each]
>
> ## Limitations & Next Iteration Ideas
>
> [5 bullets of honest limitations and clear next steps]
> ```
>
> Take 3 screenshots:
> 1. The web UI showing streaming reasoning mid-pipeline
> 2. A final ranked queue with a disagreement badge visible
> 3. The Telegram morning brief on mobile
>
> Save to `docs/screenshots/` and embed in the README.

**Files added/modified:**
- `README.md` (full rewrite)
- `docs/screenshots/01_streaming.png`
- `docs/screenshots/02_ranking.png`
- `docs/screenshots/03_telegram.png`

**Acceptance criteria:**
- [ ] All 7 Quest 1 sections present with real content (no placeholders)
- [ ] Headline eval table embedded with real numbers
- [ ] Screenshots render correctly in GitHub's markdown preview
- [ ] ChatGPT baseline comparison subsection has the actual side-by-side
- [ ] Loom placeholder marked clearly for commit 28

**Commit message:**
```
docs: complete README with eval results and screenshots

All 7 Quest 1 required sections populated:
1. Problem Definition & Target User
2. Why This Problem Matters
3. How the Solution Works
4. AI-Native Workflow (tools, models, agents, APIs)
5. Evaluation Method & Results (with headline NDCG@5 table)
6. Baseline Comparison: Why Not Just Use ChatGPT?
7. Limitations & Next Iteration Ideas

Three screenshots embedded (streaming UI, final ranking with
disagreement badge, Telegram morning brief on mobile).

Loom URL placeholder will be filled in commit 28 after recording.
```

---

### Commit 26 — `docs: BUILD_LOG with 24-hour journey, prompts, and decisions`

**Phase:** 10 &nbsp; **Hour:** 23 → 23.25 &nbsp; **Depends on:** Commit 25

**What this commit produces:** the honest BUILD_LOG that documents the real journey, including failures and cuts.

**Claude Code instructions:**
> Create `BUILD_LOG.md` at repo root. Follow the structure from PLAN.md Section 12.
>
> Fill it from your actual journey. Required elements:
> - Hour-by-hour timeline (rough is fine)
> - At least 5 named decisions with options-considered + chosen + cost
> - At least 2 prompts that worked, included in full
> - At least 2 prompts that failed, included in full, with what you changed
> - AI Tools Used table (Claude Code at minimum)
> - "What I Cut and Why" section with at least 3 cuts (Linear/Jira adapter, per-user auth, evening feedback loop, etc.)
> - Numbers I'm Proud Of section with concrete metrics
> - What I'd Build Next (5 bullets)
>
> Voice: honest, specific, like a senior engineer wrote it on their own time. Avoid corporate filler. Don't apologize. Don't oversell.

**Files added:**
- `BUILD_LOG.md`

**Acceptance criteria:**
- [ ] All required sections present
- [ ] Two real prompts shown (one working, one failed)
- [ ] At least one specific "I almost built X but cut it" cut
- [ ] Reads honestly when read aloud

**Commit message:**
```
docs: BUILD_LOG with 24-hour journey, prompts, and decisions

Honest record of the build:
- Hour-by-hour phase timeline
- 7 named decisions with options-considered + chosen + cost
- 4 prompts in full (2 working, 2 failed with the fix)
- AI Tools Used: Claude Code, Anthropic SDK (Python + TS)
- 4 things I cut and why (Linear adapter, per-user auth,
  feedback loop, multi-repo dashboard) — priority elimination
  is the skill MUST values most, this section makes it visible

Final numbers: NDCG@5 of 0.XX vs 0.XX label-only baseline
across 13 historical snapshots on two repos.
```

---

### Commit 27 — `docs: architecture diagram and agent flow`

**Phase:** 10 &nbsp; **Hour:** 23.25 → 23.5 &nbsp; **Depends on:** Commit 26

**What this commit produces:** the deep-dive architecture doc that backs the high-level README diagram.

**Claude Code instructions:**
> Create `docs/architecture.md` containing:
> 1. ASCII diagram of the full pipeline (copy from PLAN.md Section 3)
> 2. Per-agent deep-dive: each of the 5 agents with input/output Pydantic schemas, model used, and the actual system prompt
> 3. Sequence diagram (Mermaid) of a typical request from web → backend → 5 agents → response
> 4. CORS / streaming / cache architecture notes
>
> Optionally generate a PNG version via mermaid CLI and embed both.

**Files added:**
- `docs/architecture.md`
- `docs/architecture.png` (optional rendered diagram)

**Acceptance criteria:**
- [ ] ASCII diagram renders in plain markdown view
- [ ] Each agent has its prompt visible in the doc
- [ ] Mermaid diagram renders in GitHub

**Commit message:**
```
docs: architecture diagram and agent flow

Full pipeline architecture in docs/architecture.md:
- ASCII diagram of the 5-agent fan-out + synthesizer + critic
- Per-agent Pydantic schemas and system prompts (verbatim)
- Mermaid sequence diagram of a typical request
- CORS / SSE streaming / TTL cache architecture notes

Backs the high-level README diagram with full detail anyone
reading the code can use to navigate the implementation.
```

---

### Commit 28 — `docs: add Loom walkthrough link to README` &nbsp; (`v1.0-quest-submission`)

**Phase:** 10 &nbsp; **Hour:** 23.5 → 24 &nbsp; **Depends on:** Commit 27

**What this commit produces:** the final commit. Record the Loom, paste the link into README, tag, push.

**Claude Code instructions (mostly manual work; Claude Code only helps with README edit):**
> 1. Record the 5-minute Loom following the script in PLAN.md Section 13.
> 2. Paste the Loom URL into README.md where it says "[to be filled in commit 28]".
> 3. Final sanity check on PLAN.md Section 15 (every checkbox).
> 4. Commit, tag, push:
>    ```bash
>    git commit -am "docs: add Loom walkthrough link to README"
>    git tag -a v1.0-quest-submission -m "Quest 1 final submission"
>    git push origin main --tags
>    ```
> 5. Verify in incognito: GitHub repo loads, README looks complete, Loom link works, live URL works.

**Files modified:**
- `README.md` (Loom URL inserted)

**Acceptance criteria:**
- [ ] Loom URL pasted and clickable
- [ ] Final sanity checklist (PLAN.md Section 15) is all green
- [ ] Tag `v1.0-quest-submission` pushed
- [ ] Submission ready

**Commit message:**
```
docs: add Loom walkthrough link to README

5-minute walkthrough covering:
- Live demo on kubernetes/kubernetes
- Disagreement-badge killer moment
- 5-agent architecture overview
- Headline eval numbers
- Honest close: what was cut, what's next

Quest 1 submission frozen at v1.0-quest-submission.
```

---

## 5. Reserve Commits (29 & 30)

Do not pre-spend these.

#### Commit 29 (reserve) — `fix: <specific issue from final smoke test>`
Hold for a real bug found during the final pre-submission check (PLAN.md Section 15).

#### Commit 30 (reserve) — `fix: <specific issue from final smoke test>`
Same.

If unused by submission time, simply don't create them — 28 commits is fine, 26 commits is fine, anywhere ≤ 30 is fine. Don't manufacture filler commits.

---

## 6. Visual Arc (what `git log --oneline` should look like)

```
* a1b2c3d (tag: v1.0-quest-submission) docs: add Loom walkthrough link to README
* d4e5f6g docs: architecture diagram and agent flow
* g7h8i9j docs: BUILD_LOG with 24-hour journey, prompts, and decisions
* j1k2l3m docs: complete README with eval results and screenshots
* m4n5o6p eval: re-run final eval pass with updated synthesizer prompt
* p7q8r9s fix(prompts): improve synthesizer weighting for blast-radius signal
* s1t2u3v eval: retrospective replay on Kubernetes and Next.js (multi-snapshot)
* v4w5x6y (tag: v0.1-mvp) deploy: ship v0.1-mvp (Fly.io backend + Vercel web)
* y7z8a9b chore(deploy): Dockerfile + fly.toml for FastAPI backend
* b1c2d3e feat(telegram): morning brief delivery with scheduler
* e4f5g6h feat(web): Next.js ranked queue with streaming reasoning (shadcn/ui)
* h7i8j9k feat(api): in-memory TTL cache for rank responses
* k1l2m3n feat(api): FastAPI service with /rank and SSE streaming endpoint
* n4o5p6q feat(eval): NDCG@k and Kendall tau metrics + runner
* q7r8s9t feat(eval): baseline rankers (random / label / author)
* t1u2v3w feat(eval): retrospective replay harness
* w4x5y6z feat(agents): critic agent with rank-correction pass
* z7a8b9c feat(agents): synthesizer producing ranked queue
* c1d2e3f feat(agents): author profile (trust scoring)
* f4g5h6i feat(agents): ticket context (label-vs-reality mismatch)
* i7j8k9l feat(agents): diff analyst (effort + blast radius)
* l1m2n3o feat(agents): base Agent class with Claude SDK
* o4p5q6r feat(features): cross-PR dependency detection
* r7s8t9u feat(features): structured feature extraction per PR
* u1v2w3x feat(github): fetch PR diffs and author history with caching
* x4y5z6a feat(github): fetch open PRs with linked issues
* a7b8c9d feat(github): add authenticated GraphQL client
* d1e2f3g chore: monorepo scaffold with web (Next.js) and server (FastAPI)
```

28 planned commits. A reviewer scanning this log sees: monorepo setup → data → features → agents → eval harness → backend API → web app → telegram → deploy → eval results → prompt fix → re-eval → docs.

---

## 7. Anti-Patterns (never do these)

| Bad | Why it hurts |
|---|---|
| `update` | Says nothing |
| `WIP` | Says you didn't finish a thought |
| `fix bug` | Which bug? |
| `more changes` | Suggests laziness |
| `final` then `final final` then `final actually` | Signals panic |
| Committing `.env` or API keys | Disqualifying |
| All 30 commits in the last 2 hours | Signals fakery to reviewers |

---

## 8. Discipline During the Build

Two rules that will save you:

**Rule 1:** Commit at the end of every block in this document. Not "at the end of the phase" — each block. This forces small commits and gives you natural checkpoints.

**Rule 2:** If Claude Code's output doesn't pass the acceptance criteria, do NOT commit. Iterate the prompt or the code first. Committing broken work breaks the next commit's foundation.

---

## 9. Final Sanity Check (Before `git push --tags`)

- [ ] `git log --oneline | wc -l` returns ≤ 30
- [ ] No commit message contains "WIP", "fix stuff", "update", or curse words
- [ ] No commit body contains an API key, token, or password
- [ ] `git log --all --full-history -- "**/.env"` returns nothing
- [ ] Tags `v0.1-mvp` and `v1.0-quest-submission` exist
- [ ] Commit timestamps roughly span 24 hours (not all in the last 2 hours)
- [ ] Author identity is consistent across all commits

---

**You now have:**
- `PLAN.md` — the 24-hour playbook
- `COMMITS.md` — this file, the per-commit Claude Code instruction packets

Open both in a split view. Work top-to-bottom. Trust the plan.
