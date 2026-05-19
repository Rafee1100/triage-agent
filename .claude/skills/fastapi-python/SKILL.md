---
name: fastapi-python
description: Use when writing or modifying any Python/FastAPI code under `server/`. Enforces async-first I/O, Pydantic v2 validation, RORO inputs/outputs, functional style, and early-return error handling. Encodes TriagePilot-specific pins for the Anthropic SDK, agent prompts, SSE streaming, caching, logging, CORS, and storage. Trigger on edits to `server/**/*.py`, new route handlers, Pydantic schemas, agent prompts, dependencies, or background tasks.
---

# FastAPI + Python

You are an expert in FastAPI and Python backend development. The rules below apply to every change inside `server/`. The **TriagePilot Project Decisions** section at the bottom encodes choices that are non-negotiable for this codebase — do not re-litigate them per-commit.

## Key Principles

- Write concise, technical responses with accurate Python examples.
- Favor functional, declarative programming over class-based approaches.
- Prioritize modularization to eliminate code duplication.
- Use descriptive variable names with auxiliary verbs (e.g., `is_active`, `has_permission`).
- Use lowercase-with-underscores for file/directory names (e.g., `routers/user_routes.py`).
- Export routes and utilities explicitly via `__all__` or by re-exporting from the package `__init__.py`.
- Follow the RORO pattern — **R**eceive an **O**bject, **R**eturn an **O**bject.

## Python / FastAPI Standards

- Use `def` for pure functions; `async def` for anything that performs I/O.
- Type-hint every function signature. Prefer Pydantic models over raw `dict`s.
- Module structure order: exported router → sub-routers → utilities → static content → types (models, schemas).
- Prefer concise one-line conditional expressions where they aid readability (e.g., `value = a if cond else b`).
- Use guard clauses; do not nest happy-path logic inside `else`.

## Error Handling

- Handle edge cases at function entry points.
- Use early returns for error conditions; the happy path lives at the bottom of the function.
- Avoid unnecessary `else` branches — prefer `if cond: return ...` patterns.
- Use guard clauses for preconditions.
- Raise `HTTPException` for expected errors and model them as specific HTTP responses.
- Provide structured logging and user-friendly error messages (never leak stack traces to clients).

## FastAPI-Specific Guidelines

- Use functional components (plain functions) plus Pydantic models for input validation — not class-based views.
- Declare every route with an explicit `response_model` and return-type annotation.
- Manage startup/shutdown with the `lifespan` context manager, not deprecated `@app.on_event(...)`.
- Use middleware for logging and CORS.
- Apply Pydantic v2 `BaseModel` consistently for request/response validation.
- Rely on FastAPI's dependency injection (`Depends(...)`) for shared resources (HTTP clients, settings, caches).

## Performance

- Minimize blocking I/O; every database and HTTP call must be `async`.
- Use `asyncio.gather` to parallelize independent I/O — especially across per-PR agent fan-out.
- Cache hot reads (in-memory TTL is the default for this project).
- Optimize Pydantic serialization — use `model_dump(mode="json")` only when crossing process boundaries.
- Lazy-load large datasets; stream where possible.

## Conventions

- Public route handlers stay thin — push logic into utilities/services that are independently testable.
- Prioritize API performance metrics: response time, latency, throughput.
- One logical change per commit; agents land one at a time.

---

## TriagePilot Project Decisions

These choices are pinned for the lifetime of this project. Do not re-litigate them per-commit.

### Stack & Approved Dependencies

- **Web:** FastAPI, Starlette, `sse-starlette` for streaming.
- **Validation:** Pydantic v2.
- **HTTP client:** `httpx.AsyncClient` (shared via DI).
- **LLM:** `anthropic.AsyncAnthropic` (official SDK).
- **GitHub API:** plain `httpx` POSTs to `https://api.github.com/graphql` — **do not** introduce the `gql` library.
- **Background work:** APScheduler (in-process), `asyncio.gather` for fan-out.
- **Storage:** stdlib `sqlite3` and JSON-on-disk only. **No** SQLAlchemy, **no** asyncpg, **no** Redis.
- **Logging:** stdlib `logging` with a JSON formatter (no `structlog`).
- **Tests:** `pytest`, `pytest-asyncio` (`asyncio_mode = "auto"`).

Do not add new top-level dependencies without flagging it explicitly in the response.

### Project Structure

Anchored to PLAN.md Section 14:

```
server/src/
├── api/main.py             # FastAPI app + routes + CORS
├── github/{client,queries,cache}.py
├── features/extractor.py
├── agents/{base,diff_analyst,ticket_context,author_profile,synthesizer,critic}.py
├── pipeline.py             # async orchestrator with asyncio.gather + SSE emission
├── eval/{snapshot,ground_truth,baselines,metrics}.py
└── telegram/bot.py
```

Tests live under `server/tests/`, mirroring the `src/` layout. Fixtures under `server/tests/fixtures/`.

### Anthropic SDK

- Use `anthropic.AsyncAnthropic`. One shared client created in the `lifespan` context manager, injected via `Depends`.
- Wrap every `messages.create()` call in a retry helper that handles `anthropic.RateLimitError` and `anthropic.APIConnectionError` with exponential backoff (capped at 3 attempts).
- All agent outputs must be Pydantic-validated. Use the tool_use API with a single tool whose `input_schema` matches the agent's Pydantic model.
- Log per call: `agent`, `model`, `duration_ms`, `tokens_in`, `tokens_out`.
- Model selection is project-pinned: **synthesizer + critic** → `claude-sonnet-4-5`; **diff_analyst + ticket_context + author_profile** → `claude-haiku-4-5`. Do not override per-call.

### Agent Prompts

- Each agent's system prompt lives as a module-level constant `SYSTEM_PROMPT: str = """..."""` inside its `agents/*.py` file.
- No external prompt files, no f-strings inside the prompt body — inject variables only at call time via the user message.
- Treat the prompt as the agent's contract: editing it counts as a behavior change and warrants its own commit.

### SSE Streaming

- Use `sse_starlette.sse.EventSourceResponse`.
- Every emitted event has a typed Pydantic model (`AgentStartedEvent`, `AgentCompletedEvent`, `PRRankedEvent`, `FinalRankingEvent`).
- Serialize via `model.model_dump_json()` into the `data` field. Set the `event` field to the snake_case event name.
- Never emit raw dicts.

### Caching

- One module-level async TTL cache: `dict[tuple[str, str], tuple[float, T]]`, keyed by `(owner, repo)`, value is `(expires_at_unix, payload)`, **TTL 10 minutes**.
- No external cache library.
- GitHub responses cache to disk as JSON under `server/data/cache/<owner>__<repo>__<query_hash>.json`.

### Logging

- Configure stdlib `logging` at app startup (inside `lifespan`).
- JSON formatter; one log record per line.
- Required fields when logging agent activity: `pr_number`, `agent`, `duration_ms`, `tokens_in`, `tokens_out`, `repo`.
- Never log secrets, full PR diffs, or raw Anthropic response bodies.

### CORS

- Read `ALLOWED_ORIGIN` from env — single exact origin string, no wildcards, no trailing slash.
- Validate at app startup: if `ALLOWED_ORIGIN` is unset or `"*"`, fail fast with a clear error.
- `allow_credentials=True` and explicit `allow_methods` / `allow_headers` — never `["*"]` for both at once.

### Testing

- `pytest` with `pytest-asyncio` in `auto` mode.
- Anthropic calls are mocked by default. Set `ANTHROPIC_LIVE=1` to opt into live calls (used only by the eval harness).
- GitHub responses load from `tests/fixtures/<repo>/<query>.json` snapshots.
- Each agent has at least one happy-path test and one schema-violation test.

### Storage

- SQLite via stdlib `sqlite3` (sync); wrap in `asyncio.to_thread` only when blocking the event loop matters.
- JSON-on-disk cache lives under `server/data/cache/`; never commit `data/cache/` contents (already in `.gitignore`).
- No ORM. Hand-write SQL when needed (rare for this project — most state is in-memory or on-disk JSON).
