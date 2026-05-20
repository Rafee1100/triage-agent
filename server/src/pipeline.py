import asyncio
import logging
import os
from typing import Any, Awaitable, Callable

from pydantic import BaseModel, ConfigDict, Field

from src.agents.author_profile import (
    AuthorAssessment,
    AuthorProfileAgent,
)
from src.agents.critic import CriticAgent, RankingCritique
from src.agents.diff_analyst import DiffAnalysis, DiffAnalystAgent
from src.agents.synthesizer import Ranking, SynthesizerAgent
from src.agents.ticket_context import TicketContext, TicketContextAgent
from src.features.extractor import (
    PRFeatures,
    compute_dependency_depths,
    detect_cross_pr_references,
    extract,
)
from src.github import GitHubClient
from src.github.models import AuthorProfile, FileChange, PRContext

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = int(os.getenv("PIPELINE_LIMIT", "10"))

CompletionFn = Callable[..., Awaitable[Any]]
EventCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


class PRBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    pr: PRContext
    files: list[FileChange] = Field(default_factory=list)
    author: AuthorProfile
    features: PRFeatures
    diff: DiffAnalysis
    ticket: TicketContext
    author_assessment: AuthorAssessment


async def run_pipeline(
    *,
    gh: GitHubClient,
    owner: str,
    name: str,
    limit: int = DEFAULT_LIMIT,
    completion: CompletionFn | None = None,
    on_event: EventCallback | None = None,
) -> Ranking:
    prs = await gh.fetch_open_prs(owner, name, limit=limit)
    return await rank_prs(
        gh=gh, owner=owner, name=name, prs=prs,
        completion=completion, on_event=on_event,
    )


async def rank_prs(
    *,
    gh: GitHubClient,
    owner: str,
    name: str,
    prs: list[PRContext],
    completion: CompletionFn | None = None,
    on_event: EventCallback | None = None,
) -> Ranking:
    if not prs:
        return Ranking(prs=[])

    if on_event:
        await on_event("pipeline_started", {"total_prs": len(prs)})

    files_per_pr, author_lookup = await _fetch_per_pr_context(gh, owner, name, prs)
    cross_refs = detect_cross_pr_references(prs)
    depths = compute_dependency_depths(cross_refs)
    pre_bundles = _build_pre_bundles(prs, files_per_pr, author_lookup, cross_refs, depths)

    diff_agent = DiffAnalystAgent(completion=completion)
    ticket_agent = TicketContextAgent(completion=completion)
    author_agent = AuthorProfileAgent(completion=completion)

    bundles = await _run_per_pr_emitting(
        pre_bundles, diff_agent, ticket_agent, author_agent, on_event
    )

    bundle_by_number = {b.pr.number: b for b in bundles}

    synthesizer = SynthesizerAgent(completion=completion)
    initial = await synthesizer.run(_build_synthesizer_input(bundles))
    initial = _enrich_ranking(initial, bundle_by_number)
    if on_event:
        await on_event(
            "synthesizer_completed",
            {"ranking": [r.model_dump(mode="json") for r in initial.prs]},
        )

    critic = CriticAgent(completion=completion)
    critique = await critic.critique(initial)
    if on_event:
        await on_event(
            "critic_completed",
            {
                "adjustments": [a.model_dump(mode="json") for a in critique.adjustments],
                "overall_assessment": critique.overall_assessment,
            },
        )

    final = apply_critic_adjustments(initial, critique)
    if on_event:
        await on_event(
            "pipeline_done",
            {"final_ranking": [r.model_dump(mode="json") for r in final.prs]},
        )
    return final


def _enrich_ranking(
    ranking: Ranking, bundle_by_number: dict[int, "PRBundle"]
) -> Ranking:
    enriched = []
    for r in ranking.prs:
        bundle = bundle_by_number.get(r.pr_number)
        if bundle is None:
            enriched.append(r)
            continue
        enriched.append(
            r.model_copy(
                update={
                    "title": bundle.pr.title,
                    "author_login": bundle.pr.author.login if bundle.pr.author else None,
                    "url": bundle.pr.url,
                    "ticket_priority_label": bundle.features.ticket_priority_label,
                }
            )
        )
    return Ranking(prs=enriched)


async def _fetch_per_pr_context(
    gh: GitHubClient,
    owner: str,
    name: str,
    prs: list[PRContext],
) -> tuple[list[list[FileChange]], dict[str, AuthorProfile]]:
    files_tasks = [gh.fetch_pr_files(owner, name, pr.number) for pr in prs]

    author_logins = sorted({pr.author.login for pr in prs if pr.author})
    author_tasks = [
        gh.fetch_author_history(owner, name, login) for login in author_logins
    ]

    files_per_pr, author_profiles = await asyncio.gather(
        asyncio.gather(*files_tasks),
        asyncio.gather(*author_tasks),
    )
    return files_per_pr, {p.login: p for p in author_profiles}


def _build_pre_bundles(
    prs: list[PRContext],
    files_per_pr: list[list[FileChange]],
    author_lookup: dict[str, AuthorProfile],
    cross_refs: dict[int, list[int]],
    depths: dict[int, int],
) -> list[tuple[PRContext, list[FileChange], AuthorProfile, PRFeatures]]:
    result = []
    for pr, files in zip(prs, files_per_pr):
        login = pr.author.login if pr.author else ""
        author = author_lookup.get(login) or AuthorProfile(
            login=login or "(ghost)",
            merged_pr_count_in_repo=0,
            revert_rate=0.0,
            avg_review_comments_per_pr=0.0,
        )
        features = extract(
            pr, author, files,
            cross_pr_references=cross_refs,
            cross_pr_depths=depths,
        )
        result.append((pr, files, author, features))
    return result


async def _run_per_pr_emitting(
    pre_bundles: list[tuple[PRContext, list[FileChange], AuthorProfile, PRFeatures]],
    diff_agent: DiffAnalystAgent,
    ticket_agent: TicketContextAgent,
    author_agent: AuthorProfileAgent,
    on_event: EventCallback | None,
) -> list[PRBundle]:
    async def run_one(
        pr: PRContext,
        files: list[FileChange],
        author: AuthorProfile,
        features: PRFeatures,
    ) -> PRBundle:
        async def wrap(agent_name: str, coro: Awaitable[Any]) -> Any:
            result = await coro
            if on_event:
                await on_event(
                    "agent_completed",
                    {
                        "agent": agent_name,
                        "pr_number": pr.number,
                        "result": result.model_dump(mode="json"),
                    },
                )
            return result

        diff, ticket, author_a = await asyncio.gather(
            wrap("diff_analyst", diff_agent.analyze(pr, files)),
            wrap("ticket_context", ticket_agent.analyze(pr, features.ticket_priority_label)),
            wrap("author_profile", author_agent.analyze(author)),
        )
        return PRBundle(
            pr=pr,
            files=files,
            author=author,
            features=features,
            diff=diff,
            ticket=ticket,
            author_assessment=author_a,
        )

    return await asyncio.gather(*[run_one(*pb) for pb in pre_bundles])


def _build_synthesizer_input(bundles: list[PRBundle]) -> str:
    parts = [f"N={len(bundles)} PRs"]
    for b in bundles:
        parts.append(
            f"\npr_number={b.pr.number} title={b.pr.title[:60]!r}"
            f"\n  +{b.pr.additions}/-{b.pr.deletions}/{b.pr.changed_files}f"
            f" eff={b.diff.effort_minutes_estimate}m"
            f" br={b.diff.blast_radius_score:.2f}"
            f" risks={b.diff.risk_tags}"
            f"\n  sp={b.features.ticket_priority_label or 'unknown'}"
            f" tu={b.ticket.true_urgency_score:.2f}"
            f" td={b.ticket.label_disagreement}"
            f" depth={b.features.dependency_chain_depth}"
            f" mby={b.features.mentioned_by_other_open_prs}"
            f"\n  trust={b.author_assessment.trust_score:.2f}"
            f"({b.author_assessment.recommended_review_depth})"
            f" — {b.diff.reasoning[:80]}"
        )
    return "\n".join(parts)


def apply_critic_adjustments(
    ranking: Ranking, critique: RankingCritique
) -> Ranking:
    if not critique.adjustments:
        return ranking

    by_number = {p.pr_number: p for p in ranking.prs}
    order = sorted(ranking.prs, key=lambda p: p.rank)

    for adj in critique.adjustments[:3]:
        target = by_number.get(adj.pr_number)
        if target is None:
            continue
        if target in order:
            order.remove(target)
        new_pos = max(0, min(len(order), adj.new_rank - 1))
        order.insert(new_pos, target)

    rebuilt = [pr.model_copy(update={"rank": i + 1}) for i, pr in enumerate(order)]
    return Ranking(prs=rebuilt)
