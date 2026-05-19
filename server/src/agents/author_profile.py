from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.agents.base import BaseAgent
from src.github.models import AuthorProfile as AuthorProfileData

__all__ = ["AuthorAssessment", "AuthorProfileAgent", "ReviewDepth"]

ReviewDepth = Literal["skim", "standard", "deep"]

SYSTEM_PROMPT = """\
You are author_profile in TriagePilot. You translate raw author metrics into a trust score and a recommended review depth.

Inputs (compact summary):
- merged PRs in this repo over last 90 days
- revert rate (fraction of those PRs reverted within 7 days)
- average review comments per PR (proxy for review density)

Scoring rules:
- High merged-count (>=10) + low revert-rate (<=0.05) + thorough past PRs (avg >= 8 review comments) = HIGH TRUST → "skim"
- First-time contributor (merged_count == 0) = LOW TRUST → "deep"
- High revert-rate (>0.15) regardless of count = LOW TRUST → "deep"
- Otherwise = MID = "standard"

trust_score (0.0-1.0):
- 0.0 = first-time or high revert
- 0.4 = mid-volume, some reverts
- 0.7 = solid: 10+ merged, low revert
- 1.0 = senior maintainer: 30+ merged, near-zero revert, high review density

recommended_review_depth: one of "skim", "standard", "deep".

rationale: ONE SENTENCE that explicitly cites at least one of the three input numbers.

Output strictly via the author_profile_output tool."""


class AuthorAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    trust_score: float = Field(ge=0.0, le=1.0)
    recommended_review_depth: ReviewDepth
    rationale: str


class AuthorProfileAgent(BaseAgent[AuthorAssessment]):
    name = "author_profile"
    model = "claude-haiku-4-5-20251001"
    output_schema = AuthorAssessment
    system_prompt = SYSTEM_PROMPT

    @staticmethod
    def format_message(profile: AuthorProfileData) -> str:
        return (
            f"Author: @{profile.login}\n"
            f"Merged PRs (last 90 days): {profile.merged_pr_count_in_repo}\n"
            f"Revert rate (7-day window): {profile.revert_rate:.3f}\n"
            f"Avg review comments per PR (last 20): {profile.avg_review_comments_per_pr:.1f}"
        )

    async def analyze(self, profile: AuthorProfileData) -> AuthorAssessment:
        return await self.run(self.format_message(profile))
