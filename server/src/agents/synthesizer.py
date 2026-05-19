from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.agents.base import BaseAgent

__all__ = ["AIPriority", "RankedPR", "Ranking", "SynthesizerAgent"]

AIPriority = Literal["high", "medium", "low"]

SYSTEM_PROMPT = """\
You are synthesizer in TriagePilot. You receive a compact list of N open PRs with all their signals from upstream agents and produce a single ranked queue from most-urgent-to-review to least.

Weighting (combine into one score per PR):
- blast_radius_score             40%
- true_urgency_score             25%
- dependency_chain_depth         20%   (normalize: divide by max depth in batch, fall back to 0 if all zero)
- (1.0 - author_trust_score)     10%
- (1.0 - normalized_effort)       5%   (normalize effort_minutes to 0-1 by dividing by 180)

For each PR output:
- pr_number: from input
- rank: 1-based, where 1 = review first
- ai_priority: "high" if combined score > 0.65; "medium" if 0.35-0.65; "low" if < 0.35
- label_disagreement: True iff ai_priority differs from the input's stated_priority by more than one level (high vs low; high vs medium; medium vs low). If stated_priority=="unknown" set label_disagreement=False.
- reasoning: 1-2 sentences citing AT LEAST ONE specific signal value. Example: "Touches auth/middleware with blast_radius=0.9; trust_score=0.4 on a recent contributor argues for deep review."

Constraints:
- Exactly N PRs in output (one per input).
- Ranks 1..N with no gaps and no duplicates.
- Lower rank number = higher urgency.

Output strictly via the synthesizer_output tool."""


class RankedPR(BaseModel):
    model_config = ConfigDict(frozen=True)

    pr_number: int
    rank: int = Field(ge=1)
    reasoning: str
    ai_priority: AIPriority
    label_disagreement: bool


class Ranking(BaseModel):
    model_config = ConfigDict(frozen=True)

    prs: list[RankedPR] = Field(default_factory=list)


class SynthesizerAgent(BaseAgent[Ranking]):
    name = "synthesizer"
    model = "claude-sonnet-4-5-20251022"
    output_schema = Ranking
    system_prompt = SYSTEM_PROMPT
