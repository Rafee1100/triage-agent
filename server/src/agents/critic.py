from pydantic import BaseModel, ConfigDict, Field

from src.agents.base import SONNET_MODEL, BaseAgent
from src.agents.synthesizer import Ranking

__all__ = ["CriticAgent", "RankAdjustment", "RankingCritique"]

MAX_ADJUSTMENTS = 3

SYSTEM_PROMPT = """\
critic — review the synthesizer ranking for errors.

Catch:
1. High blast_radius (>=0.7) ranked behind low blast (<0.3).
2. Dep-blockers (depth>=2 or mentioned_by>=2) ranked too low.
3. label_disagreement=True with reasoning that doesn't justify it.

adjustments: 0-3 swaps. Each {pr_number, new_rank, reason}. Empty list = sound.
overall_assessment: 1-2 sentences.

Each reason MUST cite a specific signal value. Synthesizer is usually right.

Output via tool only."""


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
    model = SONNET_MODEL
    output_schema = RankingCritique
    system_prompt = SYSTEM_PROMPT

    @staticmethod
    def format_message(ranking: Ranking) -> str:
        parts = [f"N={len(ranking.prs)}"]
        for pr in sorted(ranking.prs, key=lambda p: p.rank):
            parts.append(
                f"#{pr.rank}: PR{pr.pr_number} [{pr.ai_priority}] td={pr.label_disagreement}"
                f" — {pr.reasoning[:120]}"
            )
        return "\n".join(parts)

    async def critique(self, ranking: Ranking) -> RankingCritique:
        return await self.run(self.format_message(ranking))
