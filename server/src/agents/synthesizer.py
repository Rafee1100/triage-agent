from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.agents.base import SONNET_MODEL, BaseAgent

__all__ = ["AIPriority", "RankedPR", "Ranking", "SynthesizerAgent"]

AIPriority = Literal["high", "medium", "low"]

SYSTEM_PROMPT = """\
synthesizer — rank N open PRs by review urgency, 1=highest.

Score per PR:
  0.40 * blast_radius_score
+ 0.25 * true_urgency_score
+ 0.20 * (depth / max_depth_in_batch, else 0)
+ 0.10 * (1 - trust_score)
+ 0.05 * (1 - effort_min/180)

ai_priority: "high" if score>0.65; "medium" if 0.35-0.65; "low" if <0.35.
label_disagreement: True iff ai_priority differs from stated_priority by >1 level (high vs low; high vs medium; medium vs low). stated="unknown" => False.
reasoning: 1-2 sentences citing >=1 signal value.

Output exactly N PRs with contiguous ranks 1..N via tool only."""


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
    model = SONNET_MODEL
    output_schema = Ranking
    system_prompt = SYSTEM_PROMPT
