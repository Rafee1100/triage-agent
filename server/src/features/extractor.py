import re
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field

from src.github.models import AuthorProfile, FileChange, PRContext

__all__ = ["PRFeatures", "extract"]

DEFAULT_CRITICAL_PATTERNS = [
    r"kubelet/pleg",
    r"auth/middleware",
    r"scheduler/",
]

AUTH_TOKENS = ("auth", "authn", "authz", "iam", "session", "token")
DB_MIGRATION_TOKENS = ("/migrations/",)
DB_MIGRATION_SUFFIXES = (".sql",)
CONFIG_SUFFIXES = (".yaml", ".json", ".toml", ".env")
CONFIG_DOTCONFIG = re.compile(r"\.config\.[^/]+$")
TEST_DIR_TOKENS = ("tests/", "test/", "__tests__/")
TEST_SUFFIXES = ("_test.go", ".test.ts", ".spec.ts")
BODY_SUMMARY_MAX = 500

PRIORITY_MAP = {
    "priority/critical-urgent": "high",
    "priority/important-soon": "high",
    "priority/important-longterm": "medium",
    "priority/backlog": "low",
    "p0": "high",
    "p1": "high",
    "p2": "medium",
    "p3": "low",
}

KIND_TOKENS = {
    "bug",
    "feature",
    "task",
    "enhancement",
    "chore",
    "refactor",
    "docs",
    "documentation",
    "test",
    "cleanup",
}


class PRFeatures(BaseModel):
    model_config = ConfigDict(frozen=True)

    pr_number: int
    title: str
    author_login: str

    lines_added: int
    lines_deleted: int
    files_changed: int
    file_paths: list[str] = Field(default_factory=list)
    touches_auth: bool = False
    touches_db_migration: bool = False
    touches_config_only: bool = False
    touches_tests_only: bool = False
    touches_critical_paths: list[str] = Field(default_factory=list)

    ticket_priority_label: str | None = None
    ticket_kind_label: str | None = None
    ticket_body_summary: str = ""

    author_merged_pr_count: int
    author_revert_rate: float
    author_avg_review_comments: float

    pr_age_days: float
    days_since_last_activity: float


def extract(
    pr: PRContext,
    author: AuthorProfile,
    files: list[FileChange],
    *,
    critical_patterns: list[str] | None = None,
    now: datetime | None = None,
) -> PRFeatures:
    patterns = critical_patterns if critical_patterns is not None else DEFAULT_CRITICAL_PATTERNS
    now_ts = now or datetime.now(timezone.utc)

    paths = [fc.path for fc in files]
    label_names = [lbl.name for lbl in pr.labels]

    return PRFeatures(
        pr_number=pr.number,
        title=pr.title,
        author_login=pr.author.login if pr.author else "",
        lines_added=pr.additions,
        lines_deleted=pr.deletions,
        files_changed=pr.changed_files,
        file_paths=paths,
        touches_auth=_touches_auth(paths),
        touches_db_migration=_touches_db_migration(paths),
        touches_config_only=_touches_config_only(paths),
        touches_tests_only=_touches_tests_only(paths),
        touches_critical_paths=_matches_critical(paths, patterns),
        ticket_priority_label=_normalize_priority(label_names),
        ticket_kind_label=_normalize_kind(label_names),
        ticket_body_summary=_summarize_body(pr.body),
        author_merged_pr_count=author.merged_pr_count_in_repo,
        author_revert_rate=author.revert_rate,
        author_avg_review_comments=author.avg_review_comments_per_pr,
        pr_age_days=_days_between(pr.created_at, now_ts),
        days_since_last_activity=_days_between(pr.updated_at, now_ts),
    )


def _touches_auth(paths: list[str]) -> bool:
    return any(any(token in p.lower() for token in AUTH_TOKENS) for p in paths)


def _touches_db_migration(paths: list[str]) -> bool:
    return any(
        any(token in p for token in DB_MIGRATION_TOKENS)
        or p.lower().endswith(DB_MIGRATION_SUFFIXES)
        for p in paths
    )


def _is_config_path(path: str) -> bool:
    lower = path.lower()
    if lower.endswith(CONFIG_SUFFIXES):
        return True
    return bool(CONFIG_DOTCONFIG.search(lower))


def _touches_config_only(paths: list[str]) -> bool:
    return bool(paths) and all(_is_config_path(p) for p in paths)


def _is_test_path(path: str) -> bool:
    lower = path.lower()
    if any(token in lower for token in TEST_DIR_TOKENS):
        return True
    return lower.endswith(TEST_SUFFIXES)


def _touches_tests_only(paths: list[str]) -> bool:
    return bool(paths) and all(_is_test_path(p) for p in paths)


def _matches_critical(paths: list[str], patterns: list[str]) -> list[str]:
    compiled = [re.compile(p) for p in patterns]
    return [p for p in paths if any(c.search(p) for c in compiled)]


def _normalize_priority(label_names: list[str]) -> str | None:
    for name in label_names:
        normalized = name.strip().lower()
        if normalized in PRIORITY_MAP:
            return PRIORITY_MAP[normalized]
        if normalized.startswith("priority/"):
            return normalized.removeprefix("priority/")
    return None


def _normalize_kind(label_names: list[str]) -> str | None:
    for name in label_names:
        normalized = name.strip().lower()
        if normalized.startswith("kind/"):
            return normalized.removeprefix("kind/")
        if normalized in KIND_TOKENS:
            return normalized
    return None


def _summarize_body(body: str | None) -> str:
    if not body:
        return ""
    return body.strip()[:BODY_SUMMARY_MAX]


def _days_between(when: datetime, now: datetime) -> float:
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - when).total_seconds() / 86400.0
