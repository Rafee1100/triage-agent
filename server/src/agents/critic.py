from pydantic import BaseModel, ConfigDict, Field

from src.agents.base import BaseAgent
from src.agents.synthesizer import Ranking

__all__ = ["CriticAgent", "RankAdjustment", "RankingCritique"]

MAX_ADJUSTMENTS = 3

SYSTEM_PROMPT = """\
You are critic in TriagePilot. You receive a ranking produced by the synthesizer and review it for errors.

Catch these specifically:
1. PRs with high blast_radius_score (>=0.7) ranked below PRs with low blast_radius (<0.3).
2. PRs that block other PRs (dependency_chain_depth >= 2 or mentioned_by_other_open_prs >= 2) ranked too low.
3. PRs flagged with label_disagreement=True whose reasoning doesn't actually justify the disagreement.

Output:
- adjustments: 0 to 3 swaps. Each is {pr_number, new_rank, reason}. Empty list means "ranking is sound".
- overall_assessment: 1-2 sentences on the ranking's overall quality.

Constraints:
- Each adjustment.reason MUST cite a specific signal value (e.g. "blast_radius=0.85, currently ranked #12").
- new_rank must be within [1, N] where N is the total PR count.
- The synthesizer is usually right; only intervene for clear errors. Do not propose more than 3 adjustments.

Output strictly via the critic_output tool."""


class RankAdjustment(BaseModel):
    model_config = ConfigDict(frozen=True)

    pr_number: int
    new_rank: int = Field(ge=1)
    reason: str


class RankingCritique(BaseModel):
    model_config = ConfigDict(frozen=True)

    adjustments: list[RankAdjustment] = Field(default_factory=list, max_length=MAX_ADJUSTMENTS)
    overall_assessment: str


class CriticAgent(BaseAgent[RankingCritique]):
    name = "critic"
    model = "claude-sonnet-4-5-20251022"
    output_schema = RankingCritique
    system_prompt = SYSTEM_PROMPT

    @staticmethod
    def format_message(ranking: Ranking) -> str:
        parts = [f"Synthesizer's ranking (N={len(ranking.prs)}):", ""]
        for pr in sorted(ranking.prs, key=lambda p: p.rank):
            parts.append(
                f"  #{pr.rank}: PR #{pr.pr_number}  [{pr.ai_priority}]  "
                f"disagreement={pr.label_disagreement}\n"
                f"     reasoning: {pr.reasoning}"
            )
        return "\n".join(parts)

    async def critique(self, ranking: Ranking) -> RankingCritique:
        return await self.run(self.format_message(ranking))
