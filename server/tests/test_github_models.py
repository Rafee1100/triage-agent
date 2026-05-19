from src.github.models import PRContext


def _base_node() -> dict:
    return {
        "number": 12345,
        "title": "Add foo",
        "body": "Description",
        "url": "https://github.com/x/y/pull/12345",
        "createdAt": "2026-05-19T12:00:00Z",
        "updatedAt": "2026-05-19T13:00:00Z",
        "author": {"login": "octocat"},
        "headRefName": "feat/add-foo",
        "mergeable": "MERGEABLE",
        "additions": 10,
        "deletions": 2,
        "changedFiles": 3,
        "labels": {"nodes": [{"name": "bug"}, {"name": "priority/high"}]},
        "closingIssuesReferences": {
            "nodes": [
                {
                    "number": 999,
                    "title": "Foo broken",
                    "body": "Steps to reproduce",
                    "labels": {"nodes": [{"name": "kind/bug"}]},
                }
            ]
        },
    }


def test_pr_context_parses_graphql_node() -> None:
    pr = PRContext.model_validate(_base_node())

    assert pr.number == 12345
    assert pr.author is not None and pr.author.login == "octocat"
    assert [label.name for label in pr.labels] == ["bug", "priority/high"]
    assert pr.changed_files == 3
    assert len(pr.linked_issues) == 1
    assert pr.linked_issues[0].number == 999
    assert pr.linked_issues[0].labels[0].name == "kind/bug"


def test_pr_context_handles_null_author_and_empty_connections() -> None:
    node = _base_node()
    node["author"] = None
    node["mergeable"] = None
    node["labels"] = {"nodes": []}
    node["closingIssuesReferences"] = {"nodes": []}

    pr = PRContext.model_validate(node)

    assert pr.author is None
    assert pr.mergeable == "UNKNOWN"
    assert pr.labels == []
    assert pr.linked_issues == []
