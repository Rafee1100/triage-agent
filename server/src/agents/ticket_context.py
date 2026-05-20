from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.agents.base import HAIKU_MODEL, BaseAgent
from src.github.models import PRContext

__all__ = ["TicketContext", "TicketContextAgent"]

LINKED_ISSUE_BODY_MAX = 500
NEUTRAL_URGENCY = 0.5

SYSTEM_PROMPT = """\
ticket_context — decide if stated PR priority matches the linked issue's urgency.

stated_priority: echo as given.

true_urgency_score (0.0-1.0) from issue body content:
- 0.0 = cleanup/docs
- 0.3 = improvement/dev-tool
- 0.6 = regression/customer issue/release blocker
- 1.0 = outage/security/data loss
Signals: "blocking", "production", "customer", "release blocker", "regression", "outage", "security".

label_disagreement: True iff |true_urgency - stated_score| > 0.3 where stated=0.85(high)/0.5(medium)/0.15(low)/0.5(unknown).

disagreement_reason: REQUIRED when disagreement=True. Quote a body phrase.

keywords_extracted: urgency phrases found (max 10).

Output via tool only."""


class TicketContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    stated_priority: str
    true_urgency_score: float = Field(ge=0.0, le=1.0)
    label_disagreement: bool
    disagreement_reason: str | None = None
    keywords_extracted: list[str] = Field(default_factory=list)

    @field_validator("keywords_extracted", mode="before")
    @classmethod
    def _coerce_to_list(cls, v: object) -> object:
        if isinstance(v, str):
            return [v]
        return v

    @model_validator(mode="after")
    def _require_reason_when_disagreeing(self) -> "TicketContext":
        if self.label_disagreement and not (self.disagreement_reason or "").strip():
            raise ValueError(
                "disagreement_reason is required when label_disagreement is True"
            )
        return self


class TicketContextAgent(BaseAgent[TicketContext]):
    name = "ticket_context"
    model = HAIKU_MODEL
    output_schema = TicketContext
    system_prompt = SYSTEM_PROMPT

    @staticmethod
    def format_message(pr: PRContext, stated_priority: str | None) -> str:
        parts = [f"stated_priority: {stated_priority or 'unknown'}"]
        for issue in pr.linked_issues[:2]:
            parts.append(f"\n#{issue.number}: {issue.title[:80]}")
            issue_labels = [lbl.name for lbl in issue.labels]
            if issue_labels:
                parts.append(f"labels: {', '.join(issue_labels[:5])}")
            if issue.body:
                parts.append(f"body:\n{issue.body.strip()[:LINKED_ISSUE_BODY_MAX]}")
        return "\n".join(parts)

    async def analyze(
        self, pr: PRContext, stated_priority: str | None
    ) -> TicketContext:
        if not pr.linked_issues:
            return TicketContext(
                stated_priority="unknown",
                true_urgency_score=NEUTRAL_URGENCY,
                label_disagreement=False,
                disagreement_reason=None,
                keywords_extracted=[],
            )
        return await self.run(self.format_message(pr, stated_priority))
