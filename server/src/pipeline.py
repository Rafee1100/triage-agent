import asyncio
import logging

from anthropic import AsyncAnthropic
from pydantic import BaseModel, ConfigDict, Field

from src.agents.author_profile import AuthorAssessment, AuthorProfileAgent
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

DEFAULT_LIMIT = 30


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
    client: AsyncAnthropic,
    gh: GitHubClient,
    owner: str,
    name: str,
    limit: int = DEFAULT_LIMIT,
) -> Ranking:
    prs = await gh.fetch_open_prs(owner, name, limit=limit)
    if not prs:
        return Ranking(prs=[])

    files_per_pr, author_lookup = await _fetch_per_pr_context(gh, owner, name, prs)
    cross_refs = detect_cross_pr_references(prs)
    depths = compute_dependency_depths(cross_refs)

    pre_bundles = _build_pre_bundles(prs, files_per_pr, author_lookup, cross_refs, depths)

    diff_agent = DiffAnalystAgent(client)
    ticket_agent = TicketContextAgent(client)
    author_agent = AuthorProfileAgent(client)

    per_pr_results = await asyncio.gather(
        *[
            _run_per_pr_agents(
                diff_agent, ticket_agent, author_agent, pr, files, author, features
            )
            for pr, files, author, features in pre_bundles
        ]
    )

    bundles: list[PRBundle] = [
        PRBundle(
            pr=pr,
            files=files,
            author=author,
            features=features,
            diff=diff_a,
            ticket=ticket_c,
            author_assessment=author_a,
        )
        for (pr, files, author, features), (diff_a, ticket_c, author_a) in zip(
            pre_bundles, per_pr_results
        )
    ]

    synthesizer = SynthesizerAgent(client)
    initial = await synthesizer.run(_build_synthesizer_input(bundles))

    critic = CriticAgent(client)
    critique = await critic.critique(initial)

    return apply_critic_adjustments(initial, critique)


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
            pr,
            author,
            files,
            cross_pr_references=cross_refs,
            cross_pr_depths=depths,
        )
        result.append((pr, files, author, features))
    return result


async def _run_per_pr_agents(
    diff_agent: DiffAnalystAgent,
    ticket_agent: TicketContextAgent,
    author_agent: AuthorProfileAgent,
    pr: PRContext,
    files: list[FileChange],
    author: AuthorProfile,
    features: PRFeatures,
) -> tuple[DiffAnalysis, TicketContext, AuthorAssessment]:
    return await asyncio.gather(
        diff_agent.analyze(pr, files),
        ticket_agent.analyze(pr, features.ticket_priority_label),
        author_agent.analyze(author),
    )


def _build_synthesizer_input(bundles: list[PRBundle]) -> str:
    parts = [f"Open PRs to rank (N={len(bundles)}):", ""]
    for b in bundles:
        author_login = b.pr.author.login if b.pr.author else "(ghost)"
        parts.append(
            f"PR #{b.pr.number} — {b.pr.title[:80]}\n"
            f"  author: @{author_login}  trust={b.author_assessment.trust_score:.2f} "
            f"(review={b.author_assessment.recommended_review_depth})\n"
            f"  size: +{b.pr.additions}/-{b.pr.deletions}, {b.pr.changed_files} files  "
            f"effort={b.diff.effort_minutes_estimate}min\n"
            f"  blast_radius={b.diff.blast_radius_score:.2f}  risk_tags={b.diff.risk_tags}\n"
            f"  stated_priority={b.features.ticket_priority_label or 'unknown'}  "
            f"true_urgency={b.ticket.true_urgency_score:.2f}  "
            f"ticket_disagreement={b.ticket.label_disagreement}\n"
            f"  dependency_chain_depth={b.features.dependency_chain_depth}  "
            f"mentioned_by={b.features.mentioned_by_other_open_prs}\n"
            f"  diff_reasoning: {b.diff.reasoning}"
        )
        parts.append("")
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
