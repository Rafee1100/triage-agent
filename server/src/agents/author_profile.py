from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.agents.base import HAIKU_MODEL, BaseAgent
from src.github.models import AuthorProfile as AuthorProfileData

__all__ = ["AuthorAssessment", "AuthorProfileAgent", "ReviewDepth"]

ReviewDepth = Literal["skim", "standard", "deep"]

SYSTEM_PROMPT = """\
author_profile — map metrics to trust + review depth.

Input: merged 90d, revert rate, avg review comments/PR.

trust_score (0.0-1.0):
- 0.0 = first-time (merged=0) OR revert>0.15
- 0.4 = mid-volume
- 0.7 = 10+ merged, revert<=0.05
- 1.0 = senior (30+ merged, near-zero revert, dense reviews)

recommended_review_depth:
- "skim" if merged>=10, revert<=0.05, avg_reviews>=8
- "deep" if merged==0 OR revert>0.15
- "standard" otherwise

rationale: ONE sentence citing at least one input number.

Output via tool only."""


class AuthorAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    trust_score: float = Field(ge=0.0, le=1.0)
    recommended_review_depth: ReviewDepth
    rationale: str


class AuthorProfileAgent(BaseAgent[AuthorAssessment]):
    name = "author_profile"
    model = HAIKU_MODEL
    output_schema = AuthorAssessment
    system_prompt = SYSTEM_PROMPT

    @staticmethod
    def format_message(profile: AuthorProfileData) -> str:
        return (
            f"@{profile.login}\n"
            f"merged_90d={profile.merged_pr_count_in_repo}\n"
            f"revert_rate={profile.revert_rate:.3f}\n"
            f"avg_reviews={profile.avg_review_comments_per_pr:.1f}"
        )

    async def analyze(self, profile: AuthorProfileData) -> AuthorAssessment:
        return await self.run(self.format_message(profile))
