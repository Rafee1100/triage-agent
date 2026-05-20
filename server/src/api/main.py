import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from src.api.cache import TTLCache
from src.github import GitHubClient
from src.pipeline import DEFAULT_LIMIT, rank_prs

logger = logging.getLogger(__name__)

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://localhost:3000")
RANK_CACHE_TTL_S = 600


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN env var is required")
    gh = GitHubClient(token)
    app.state.gh = gh
    app.state.rank_cache = TTLCache(ttl_seconds=RANK_CACHE_TTL_S)
    try:
        yield
    finally:
        await gh.aclose()


app = FastAPI(title="TriagePilot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/rank/{owner}/{repo}")
async def get_ranking(owner: str, repo: str, request: Request) -> dict[str, Any]:
    gh: GitHubClient = request.app.state.gh
    cache: TTLCache = request.app.state.rank_cache
    key = f"{owner}/{repo}"

    cached = cache.get(key)
    if cached is not None:
        return cached

    prs = await gh.fetch_open_prs(owner, repo, limit=DEFAULT_LIMIT)
    if not prs:
        payload = {"total_prs": 0, "ranking": []}
        cache.set(key, payload)
        return payload

    ranking = await rank_prs(gh=gh, owner=owner, name=repo, prs=prs)
    pr_by_number = {pr.number: pr for pr in prs}
    enriched_ranking = []
    for r in sorted(ranking.prs, key=lambda x: x.rank):
        item = r.model_dump(mode="json")
        pr = pr_by_number.get(r.pr_number)
        if pr:
            item["title"] = pr.title
            item["author_login"] = pr.author.login if pr.author else None
            item["url"] = pr.url
        enriched_ranking.append(item)
    payload = {"total_prs": len(prs), "ranking": enriched_ranking}
    cache.set(key, payload)
    return payload


@app.get("/rank/{owner}/{repo}/stream")
async def stream_ranking(
    owner: str, repo: str, request: Request
) -> EventSourceResponse:
    gh: GitHubClient = request.app.state.gh
    return EventSourceResponse(_pipeline_event_stream(gh, owner, repo))


async def _pipeline_event_stream(
    gh: GitHubClient, owner: str, repo: str
) -> AsyncIterator[dict[str, Any]]:
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event_type: str, data: dict[str, Any]) -> None:
        await queue.put({"event": event_type, "data": json.dumps(data)})

    async def run() -> None:
        try:
            prs = await gh.fetch_open_prs(owner, repo, limit=DEFAULT_LIMIT)
            if not prs:
                await emit("pipeline_done", {"final_ranking": []})
                return
            await rank_prs(gh=gh, owner=owner, name=repo, prs=prs, on_event=emit)
        except Exception as exc:
            logger.exception("pipeline_failed")
            await emit("error", {"error": str(exc)})
        finally:
            await queue.put(None)

    task = asyncio.create_task(run())
    try:
        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
    finally:
        if not task.done():
            task.cancel()
