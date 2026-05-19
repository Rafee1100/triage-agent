from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.agents.base import BaseAgent
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

MAX_FILES_IN_PROMPT = 50
LINKED_ISSUE_BODY_PREVIEW = 200

SYSTEM_PROMPT = """\
You are diff_analyst in TriagePilot — a multi-agent PR triage system. You read PR diff metadata and output a structured assessment for a senior reviewer's morning queue.

For each PR you receive:

1. effort_minutes_estimate (5-180, conservative):
   - 2000-line refactor in 3 files ≈ 120 min.
   - 200 lines spread across 30 files ≈ 60 min (file count dominates review cost).
   - 5-line config change ≈ 5 min.
   - Account for linked-issue context: a non-trivial bug fix requires loading issue context too.

2. blast_radius_score (0.0-1.0):
   - 0.0 = docs-only or test-only.
   - 0.3 = isolated feature in non-critical code.
   - 0.6 = touches shared utilities or multiple modules.
   - 1.0 = touches auth, payments, core scheduling, kubelet runtime, or any path where regression = prod outage.
   Use file paths as the primary signal.

3. risk_tags (subset of: auth, db_migration, config_only, tests_only, external_api, concurrency, infra):
   Tag AGGRESSIVELY. False positives are cheap; missed risks are dangerous in a triage tool.
   - auth: authentication, authorization, sessions, tokens, identity.
   - db_migration: schema change, /migrations/ files, .sql files.
   - config_only: ENTIRE change is yaml/json/toml/env/config files.
   - tests_only: ENTIRE change is test files.
   - external_api: adds/modifies calls to external services or third-party SDKs.
   - concurrency: locks, async/await primitives, goroutines, threads, semaphores.
   - infra: Dockerfiles, CI configs, deployment manifests, build tooling.

4. reasoning: 1-2 sentences max. Name the dominant factor in effort and the risks that justify your tags.

Output strictly via the diff_analyst_output tool. Do not output prose."""


class DiffAnalysis(BaseModel):
    model_config = ConfigDict(frozen=True)

    effort_minutes_estimate: int = Field(ge=5, le=180)
    blast_radius_score: float = Field(ge=0.0, le=1.0)
    risk_tags: list[RiskTag] = Field(default_factory=list)
    reasoning: str


class DiffAnalystAgent(BaseAgent[DiffAnalysis]):
    name = "diff_analyst"
    model = "claude-haiku-4-5-20251001"
    output_schema = DiffAnalysis
    system_prompt = SYSTEM_PROMPT

    @staticmethod
    def format_message(pr: PRContext, files: list[FileChange]) -> str:
        parts: list[str] = [f"PR title: {pr.title}"]

        if pr.linked_issues:
            issue_lines: list[str] = []
            for issue in pr.linked_issues:
                line = f"  #{issue.number} — {issue.title}"
                if issue.body:
                    line += f": {issue.body.strip()[:LINKED_ISSUE_BODY_PREVIEW]}"
                issue_lines.append(line)
            parts.append("Linked issues:\n" + "\n".join(issue_lines))

        parts.append(
            f"Totals: +{pr.additions} / -{pr.deletions}, {pr.changed_files} files changed"
        )

        sample = files[:MAX_FILES_IN_PROMPT]
        file_lines = [f"  {fc.path}  +{fc.additions}/-{fc.deletions}" for fc in sample]
        if len(files) > MAX_FILES_IN_PROMPT:
            file_lines.append(f"  ... and {len(files) - MAX_FILES_IN_PROMPT} more files")
        parts.append("Changed files:\n" + "\n".join(file_lines))

        return "\n\n".join(parts)

    async def analyze(self, pr: PRContext, files: list[FileChange]) -> DiffAnalysis:
        return await self.run(self.format_message(pr, files))
