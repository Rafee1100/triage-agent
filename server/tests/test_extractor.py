from datetime import datetime, timezone

from src.features.extractor import extract
from src.github.models import AuthorProfile, FileChange, PRContext

NOW = datetime(2026, 5, 19, tzinfo=timezone.utc)


def _pr(*, labels: list[str] | None = None, body: str | None = "Hello") -> PRContext:
    return PRContext.model_validate(
        {
            "number": 1,
            "title": "Sample",
            "body": body,
            "url": "https://github.com/o/r/pull/1",
            "createdAt": "2026-05-01T00:00:00Z",
            "updatedAt": "2026-05-10T00:00:00Z",
            "author": {"login": "alice"},
            "headRefName": "main",
            "mergeable": "MERGEABLE",
            "additions": 10,
            "deletions": 5,
            "changedFiles": 3,
            "labels": {"nodes": [{"name": n} for n in (labels or [])]},
            "closingIssuesReferences": {"nodes": []},
        }
    )


def _profile() -> AuthorProfile:
    return AuthorProfile(
        login="alice",
        merged_pr_count_in_repo=12,
        revert_rate=0.0,
        avg_review_comments_per_pr=5.0,
    )


def _files(paths: list[str]) -> list[FileChange]:
    return [FileChange(path=p, additions=1, deletions=0) for p in paths]


def _extract(paths: list[str], *, labels: list[str] | None = None, body: str = "Hello"):
    return extract(_pr(labels=labels, body=body), _profile(), _files(paths), now=NOW)


def test_touches_auth_when_path_contains_auth_token() -> None:
    assert _extract(["auth/middleware.go", "main.go"]).touches_auth is True


def test_touches_auth_matches_iam_session_token_substrings() -> None:
    for path in ("iam/role.go", "session/manager.ts", "token/refresh.py"):
        assert _extract([path]).touches_auth is True


def test_touches_auth_false_when_no_auth_paths() -> None:
    assert _extract(["pkg/scheduler/main.go"]).touches_auth is False


def test_touches_db_migration_on_migrations_dir_or_sql_suffix() -> None:
    assert _extract(["db/migrations/001_init.sql"]).touches_db_migration is True
    assert _extract(["src/x/0042_add_column.sql"]).touches_db_migration is True
    assert _extract(["src/app.go"]).touches_db_migration is False


def test_touches_config_only_requires_all_paths_to_match() -> None:
    assert _extract(["x.yaml", "y.json", "z.toml"]).touches_config_only is True
    assert _extract([".env", "webpack.config.js"]).touches_config_only is True
    assert _extract(["x.yaml", "main.go"]).touches_config_only is False


def test_touches_config_only_false_for_empty_files() -> None:
    assert _extract([]).touches_config_only is False


def test_touches_tests_only_recognizes_dirs_and_suffixes() -> None:
    assert _extract(["pkg/auth/main_test.go"]).touches_tests_only is True
    assert _extract(["tests/foo.py"]).touches_tests_only is True
    assert _extract(["src/components/__tests__/x.spec.ts"]).touches_tests_only is True
    assert _extract(["src/main.ts"]).touches_tests_only is False


def test_touches_critical_paths_returns_matched_paths_only() -> None:
    features = _extract(
        ["pkg/kubelet/pleg/generic.go", "pkg/scheduler/foo.go", "main.go"]
    )
    assert features.touches_critical_paths == [
        "pkg/kubelet/pleg/generic.go",
        "pkg/scheduler/foo.go",
    ]


def test_priority_label_normalizes_kubernetes_styles() -> None:
    assert _extract(["main.go"], labels=["priority/critical-urgent"]).ticket_priority_label == "high"
    assert _extract(["main.go"], labels=["priority/important-soon"]).ticket_priority_label == "high"
    assert _extract(["main.go"], labels=["priority/important-longterm"]).ticket_priority_label == "medium"
    assert _extract(["main.go"], labels=["priority/backlog"]).ticket_priority_label == "low"


def test_priority_label_normalizes_p_levels() -> None:
    assert _extract(["main.go"], labels=["P0"]).ticket_priority_label == "high"
    assert _extract(["main.go"], labels=["P1"]).ticket_priority_label == "high"
    assert _extract(["main.go"], labels=["P2"]).ticket_priority_label == "medium"
    assert _extract(["main.go"], labels=["P3"]).ticket_priority_label == "low"


def test_priority_label_falls_back_to_lowercased_priority_suffix() -> None:
    assert _extract(["main.go"], labels=["priority/Foo"]).ticket_priority_label == "foo"


def test_priority_label_none_when_no_priority_label() -> None:
    assert _extract(["main.go"], labels=["kind/bug", "area/scheduler"]).ticket_priority_label is None


def test_kind_label_normalizes_kubernetes_style_and_plain_tokens() -> None:
    assert _extract(["main.go"], labels=["kind/feature"]).ticket_kind_label == "feature"
    assert _extract(["main.go"], labels=["bug"]).ticket_kind_label == "bug"
    assert _extract(["main.go"], labels=["area/scheduler"]).ticket_kind_label is None


def test_body_summary_truncated_to_500_chars() -> None:
    features = _extract(["main.go"], body="x" * 600)
    assert len(features.ticket_body_summary) == 500


def test_body_summary_empty_for_none_or_blank() -> None:
    assert _extract(["main.go"], body="").ticket_body_summary == ""
    assert _extract(["main.go"], body="   \n  ").ticket_body_summary == ""


def test_age_and_activity_days_match_created_and_updated() -> None:
    features = _extract(["main.go"])
    assert abs(features.pr_age_days - 18.0) < 0.5
    assert abs(features.days_since_last_activity - 9.0) < 0.5
