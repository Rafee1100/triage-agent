import asyncio
from datetime import datetime, timezone
from typing import Any

from src.github import GitHubClient
from src.github.models import PRContext
from src.github.queries import OPEN_PRS_AT_SNAPSHOT

MAX_PAGE = 100


async def reconstruct_open_prs_at(
    gh: GitHubClient,
    owner: str,
    name: str,
    t0: datetime,
    limit: int = 30,
) -> list[PRContext]:
    if limit <= 0:
        return []

    t0 = _ensure_aware(t0)
    t0_str = t0.strftime("%Y-%m-%dT%H:%M:%SZ")
    repo = f"{owner}/{name}"

    q_still_open = f"repo:{repo} is:pr is:open created:<{t0_str}"
    q_closed_after = (
        f"repo:{repo} is:pr is:closed created:<{t0_str} closed:>{t0_str}"
    )

    page_size = min(MAX_PAGE, limit * 3)

    nodes_open, nodes_closed = await asyncio.gather(
        _search_prs(gh, q_still_open, page_size),
        _search_prs(gh, q_closed_after, page_size),
    )

    seen: set[int] = set()
    eligible: list[dict[str, Any]] = []
    for node in nodes_open + nodes_closed:
        number = node.get("number")
        if number in seen:
            continue
        if not _was_unreviewed_at(node, t0):
            continue
        seen.add(number)
        eligible.append(node)

    eligible.sort(key=lambda n: n["createdAt"], reverse=True)
    return [PRContext.model_validate(n) for n in eligible[:limit]]


async def _search_prs(gh: GitHubClient, query: str, first: int) -> list[dict[str, Any]]:
    response = await gh.query(OPEN_PRS_AT_SNAPSHOT, {"q": query, "first": first})
    search = (response.get("data") or {}).get("search") or {}
    nodes = search.get("nodes") or []
    return [n for n in nodes if n]


def _was_unreviewed_at(node: dict[str, Any], t0: datetime) -> bool:
    first = _earliest_review_at(node)
    return first is None or first > t0


def _earliest_review_at(node: dict[str, Any]) -> datetime | None:
    nodes = (node.get("reviews") or {}).get("nodes") or []
    timestamps = [datetime.fromisoformat(r["submittedAt"]) for r in nodes if r.get("submittedAt")]
    return min(timestamps) if timestamps else None


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
