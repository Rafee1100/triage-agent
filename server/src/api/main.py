import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from src.api.cache import TTLCache
from src.github import GitHubClient
from src.pipeline import DEFAULT_LIMIT, rank_prs, run_pipeline
from src.subscriptions import (
    InvalidSubscriptionError,
    Subscription,
    SubscriptionCreate,
    SubscriptionStore,
    to_public,
)
from src.telegram import send_morning_brief

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
    app.state.subs = SubscriptionStore()

    scheduler = AsyncIOScheduler()
    scheduler.start()
    app.state.scheduler = scheduler

    for sub in await app.state.subs.list_all():
        _register_job(app, sub)
    logger.info("scheduler_started", extra={"subscriptions": len(await app.state.subs.list_all())})

    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await gh.aclose()


def _register_job(app: FastAPI, sub: Subscription) -> None:
    scheduler: AsyncIOScheduler = app.state.scheduler
    tz = ZoneInfo(sub.timezone)
    scheduler.add_job(
        _fire_brief,
        CronTrigger(hour=sub.hour, minute=sub.minute, timezone=tz),
        args=[app, sub.id],
        id=f"brief_{sub.id}",
        replace_existing=True,
    )


def _unregister_job(app: FastAPI, sub_id: str) -> None:
    scheduler: AsyncIOScheduler = app.state.scheduler
    job_id = f"brief_{sub_id}"
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass


async def _fire_brief(app: FastAPI, sub_id: str) -> None:
    store: SubscriptionStore = app.state.subs
    sub = await store.get(sub_id)
    if sub is None:
        logger.warning("brief_skipped_missing_sub", extra={"sub_id": sub_id})
        return
    owner, name = sub.repo.split("/", 1)
    gh: GitHubClient = app.state.gh
    ranking = await run_pipeline(gh=gh, owner=owner, name=name)
    await send_morning_brief(sub.chat_id, sub.bot_token, ranking, sub.repo)


app = FastAPI(title="TriagePilot API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
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
    payload = {
        "total_prs": len(prs),
        "ranking": [
            r.model_dump(mode="json")
            for r in sorted(ranking.prs, key=lambda x: x.rank)
        ],
    }
    cache.set(key, payload)
    return payload


@app.get("/rank/{owner}/{repo}/stream")
async def stream_ranking(
    owner: str, repo: str, request: Request
) -> EventSourceResponse:
    gh: GitHubClient = request.app.state.gh
    return EventSourceResponse(_pipeline_event_stream(gh, owner, repo))


@app.get("/subscriptions")
async def list_subscriptions(request: Request) -> dict[str, list[dict[str, Any]]]:
    store: SubscriptionStore = request.app.state.subs
    subs = await store.list_all()
    return {"subscriptions": [to_public(s) for s in subs]}


@app.post("/subscriptions", status_code=201)
async def create_subscription(
    request: Request, payload: dict[str, Any]
) -> dict[str, Any]:
    try:
        spec = SubscriptionCreate.model_validate(payload)
    except (InvalidSubscriptionError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    store: SubscriptionStore = request.app.state.subs
    sub = await store.add(spec)
    _register_job(request.app, sub)
    return to_public(sub)


@app.delete("/subscriptions/{sub_id}", status_code=204)
async def delete_subscription(sub_id: str, request: Request) -> None:
    store: SubscriptionStore = request.app.state.subs
    ok = await store.delete(sub_id)
    if not ok:
        raise HTTPException(status_code=404, detail="subscription not found")
    _unregister_job(request.app, sub_id)


@app.post("/subscriptions/{sub_id}/trigger")
async def trigger_subscription(sub_id: str, request: Request) -> dict[str, Any]:
    store: SubscriptionStore = request.app.state.subs
    sub = await store.get(sub_id)
    if sub is None:
        raise HTTPException(status_code=404, detail="subscription not found")
    await _fire_brief(request.app, sub_id)
    return {"sent": True, "repo": sub.repo}


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
            await emit("pipeline_failed", {"error": f"{type(exc).__name__}: {exc}"})
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
