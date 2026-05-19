from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.agents.base import HAIKU_MODEL, BaseAgent
from src.github.models import FileChange, PRContext

__all__ = ["DiffAnalysis", "DiffAnalystAgent", "RiskTag"]

RiskTag = Literal[
    "auth",
    "db_migration",
    "config_only",
    "tests_only",
    "external_api",
    "concurrency",
    "infra",
]

MAX_FILES_IN_PROMPT = 15
LINKED_ISSUE_BODY_PREVIEW = 80

SYSTEM_PROMPT = """\
diff_analyst — assess PR diff metadata for a review queue.

effort_minutes_estimate (5-180, conservative): 2000-line refactor ≈ 120m; 200 lines × 30 files ≈ 60m; 5-line config ≈ 5m.

blast_radius_score (0.0-1.0): 0=docs/tests; 0.3=isolated feature; 0.6=shared utilities; 1.0=auth/payments/scheduling/kubelet/anywhere regression = prod outage.

risk_tags (subset of: auth, db_migration, config_only, tests_only, external_api, concurrency, infra). Tag aggressively. config_only/tests_only require the ENTIRE change to be that category.

reasoning: 1-2 sentences naming the dominant factor.

Output via tool only."""


class DiffAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    effort_minutes_estimate: int = Field(ge=5, le=180)
    blast_radius_score: float = Field(ge=0.0, le=1.0)
    risk_tags: list[RiskTag] = Field(default_factory=list)
    reasoning: str


class DiffAnalystAgent(BaseAgent[DiffAnalysis]):
    name = "diff_analyst"
    model = HAIKU_MODEL
    output_schema = DiffAnalysis
    system_prompt = SYSTEM_PROMPT

    @staticmethod
    def format_message(pr: PRContext, files: list[FileChange]) -> str:
        parts: list[str] = [f"title: {pr.title[:80]}"]
        parts.append(f"totals: +{pr.additions}/-{pr.deletions}, {pr.changed_files}f")

        if pr.linked_issues:
            issue_lines = []
            for issue in pr.linked_issues[:3]:
                line = f"  #{issue.number} {issue.title[:60]}"
                if issue.body:
                    line += f": {issue.body.strip()[:LINKED_ISSUE_BODY_PREVIEW]}"
                issue_lines.append(line)
            parts.append("linked:\n" + "\n".join(issue_lines))

        sample = files[:MAX_FILES_IN_PROMPT]
        file_lines = [f"  {fc.path} +{fc.additions}/-{fc.deletions}" for fc in sample]
        if len(files) > MAX_FILES_IN_PROMPT:
            file_lines.append(f"  ...and {len(files) - MAX_FILES_IN_PROMPT} more files")
        parts.append("files:\n" + "\n".join(file_lines))

        return "\n".join(parts)

    async def analyze(self, pr: PRContext, files: list[FileChange]) -> DiffAnalysis:
        return await self.run(self.format_message(pr, files))
