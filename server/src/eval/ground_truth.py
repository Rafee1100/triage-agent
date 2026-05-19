import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

from src.github import GitHubClient
from src.github.queries import PR_REVIEW_TIMELINE


async def actual_review_order(
    gh: GitHubClient,
    owner: str,
    name: str,
    pr_numbers: list[int],
    t0: datetime,
    window_days: int = 14,
) -> list[int]:
    if not pr_numbers:
        return []

    t0 = _ensure_aware(t0)
    t_end = t0 + timedelta(days=window_days)

    async def fetch_one(num: int) -> tuple[int, datetime | None]:
        response = await gh.query(
            PR_REVIEW_TIMELINE,
            {"owner": owner, "name": name, "number": num},
        )
        pr = ((response.get("data") or {}).get("repository") or {}).get("pullRequest")
        if not pr:
            return num, None
        return num, _first_action_within(pr, t0, t_end)

    results = await asyncio.gather(*[fetch_one(n) for n in pr_numbers])
    return _sort_by_action(results)


def _first_action_within(
    pr_node: dict[str, Any], t0: datetime, t_end: datetime
) -> datetime | None:
    candidates: list[datetime] = []

    nodes = (pr_node.get("reviews") or {}).get("nodes") or []
    for review in nodes:
        submitted = review.get("submittedAt")
        if not submitted:
            continue
        dt = datetime.fromisoformat(submitted)
        if t0 < dt < t_end:
            candidates.append(dt)

    merged = pr_node.get("mergedAt")
    if merged:
        dt = datetime.fromisoformat(merged)
        if t0 < dt < t_end:
            candidates.append(dt)

    return min(candidates) if candidates else None


def _sort_by_action(results: list[tuple[int, datetime | None]]) -> list[int]:
    def key(item: tuple[int, datetime | None]) -> tuple[int, datetime]:
        num, ts = item
        if ts is None:
            return (1, datetime.max.replace(tzinfo=timezone.utc))
        return (0, ts)

    return [num for num, _ in sorted(results, key=key)]


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
