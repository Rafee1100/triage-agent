from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.agents.base import BaseAgent
from src.github.models import PRContext

__all__ = ["TicketContext", "TicketContextAgent"]

LINKED_ISSUE_BODY_MAX = 2000
NEUTRAL_URGENCY = 0.5

SYSTEM_PROMPT = """\
You are ticket_context in TriagePilot. You read a PR's linked issue and decide whether the stated priority label matches the urgency described in the issue body.

For each input you receive:

1. stated_priority: echo the priority label exactly as given (e.g. "high", "medium", "low", or "unknown").

2. true_urgency_score (0.0-1.0): score the URGENCY YOU READ IN THE ISSUE BODY, not the label.
   - 0.0 = no urgency signal (nice-to-have, cleanup, documentation)
   - 0.3 = mild urgency (improvement, dev-tool fix)
   - 0.6 = clear urgency (regression, customer issue, planned release blocker)
   - 1.0 = severe urgency (production outage, security exposure, data loss)
   Signals: "blocking", "production", "customer impact", "release blocker", "regression", "outage", "data loss", "security", "incident".

3. label_disagreement: True iff |true_urgency_score - stated_score| > 0.3
   where stated_score = 0.85 (high), 0.50 (medium), 0.15 (low), 0.50 (unknown).

4. disagreement_reason: REQUIRED when label_disagreement is True. Quote-grounded — cite a phrase from the issue body. Example: 'Body says "blocks Q3 release" but label is Low'.

5. keywords_extracted: the actual urgency-signal phrases you found (max 10).

Output strictly via the ticket_context_output tool."""


class TicketContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    stated_priority: str
    true_urgency_score: float = Field(ge=0.0, le=1.0)
    label_disagreement: bool
    disagreement_reason: str | None = None
    keywords_extracted: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _require_reason_when_disagreeing(self) -> "TicketContext":
        if self.label_disagreement and not (self.disagreement_reason or "").strip():
            raise ValueError(
                "disagreement_reason is required when label_disagreement is True"
            )
        return self


class TicketContextAgent(BaseAgent[TicketContext]):
    name = "ticket_context"
    model = "claude-haiku-4-5-20251001"
    output_schema = TicketContext
    system_prompt = SYSTEM_PROMPT

    @staticmethod
    def format_message(pr: PRContext, stated_priority: str | None) -> str:
        parts = [f"Stated PR priority label: {stated_priority or 'unknown'}"]
        for issue in pr.linked_issues:
            parts.append(f"\nLinked issue #{issue.number}: {issue.title}")
            issue_labels = [lbl.name for lbl in issue.labels]
            if issue_labels:
                parts.append(f"Issue labels: {', '.join(issue_labels)}")
            if issue.body:
                parts.append(
                    f"Issue body:\n{issue.body.strip()[:LINKED_ISSUE_BODY_MAX]}"
                )
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
