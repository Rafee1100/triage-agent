import json
from types import SimpleNamespace
from typing import Any

import pytest

from src.agents.base import AgentError
from src.agents.diff_analyst import DiffAnalystAgent
from src.github.models import FileChange, PRContext


def _pr(*, title: str = "Sample", linked: list[dict] | None = None) -> PRContext:
    return PRContext.model_validate(
        {
            "number": 1,
            "title": title,
            "body": None,
            "url": "https://github.com/o/r/pull/1",
            "createdAt": "2026-05-01T00:00:00Z",
            "updatedAt": "2026-05-10T00:00:00Z",
            "author": {"login": "alice"},
            "headRefName": "main",
            "mergeable": "MERGEABLE",
            "additions": 30,
            "deletions": 5,
            "changedFiles": 2,
            "labels": {"nodes": []},
            "closingIssuesReferences": {"nodes": linked or []},
        }
    )


def _fake_completion(*responses: Any) -> Any:
    iterator = iter(responses)

    async def completion(**_kwargs: Any) -> Any:
        return next(iterator)

    return completion


def _tool_response(payload: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[
                        SimpleNamespace(
                            function=SimpleNamespace(
                                name="diff_analyst_output",
                                arguments=json.dumps(payload),
                            )
                        )
                    ]
                )
            )
        ],
        usage=SimpleNamespace(prompt_tokens=300, completion_tokens=80),
    )


def test_format_message_renders_title_totals_and_files() -> None:
    pr = _pr(title="Fix auth bug")
    files = [
        FileChange(path="pkg/auth/middleware.go", additions=20, deletions=5),
        FileChange(path="pkg/auth/middleware_test.go", additions=10, deletions=0),
    ]
    msg = DiffAnalystAgent.format_message(pr, files)
    assert "title: Fix auth bug" in msg
    assert "pkg/auth/middleware.go" in msg
    assert "+20/-5" in msg
    assert "totals: +30/-5, 2f" in msg


def test_format_message_includes_linked_issue_summary() -> None:
    pr = _pr(
        linked=[
            {
                "number": 99,
                "title": "Auth fails on cold start",
                "body": "Steps to reproduce: hit /login after 5min idle.",
                "labels": {"nodes": []},
            }
        ]
    )
    msg = DiffAnalystAgent.format_message(pr, [])
    assert "#99" in msg
    assert "Auth fails on cold start" in msg
    assert "Steps to reproduce" in msg


def test_format_message_truncates_large_file_lists() -> None:
    pr = _pr()
    files = [FileChange(path=f"f{i}.go", additions=1, deletions=0) for i in range(25)]
    msg = DiffAnalystAgent.format_message(pr, files)
    assert "and 10 more files" in msg
    assert "f20.go" not in msg


async def test_agent_returns_validated_diff_analysis() -> None:
    response = _tool_response(
        {
            "effort_minutes_estimate": 45,
            "blast_radius_score": 0.7,
            "risk_tags": ["auth", "concurrency"],
            "reasoning": "Touches auth middleware with goroutine usage.",
        }
    )
    agent = DiffAnalystAgent(completion=_fake_completion(response))
    result = await agent.run("test")
    assert result.effort_minutes_estimate == 45
    assert result.blast_radius_score == 0.7
    assert result.risk_tags == ["auth", "concurrency"]


async def test_agent_rejects_effort_out_of_bounds() -> None:
    bad = _tool_response(
        {
            "effort_minutes_estimate": 500,
            "blast_radius_score": 0.5,
            "risk_tags": [],
            "reasoning": "x",
        }
    )
    agent = DiffAnalystAgent(completion=_fake_completion(bad, bad))
    with pytest.raises(AgentError):
        await agent.run("test")


async def test_agent_rejects_unknown_risk_tag() -> None:
    bad = _tool_response(
        {
            "effort_minutes_estimate": 30,
            "blast_radius_score": 0.5,
            "risk_tags": ["security"],
            "reasoning": "x",
        }
    )
    agent = DiffAnalystAgent(completion=_fake_completion(bad, bad))
    with pytest.raises(AgentError):
        await agent.run("test")


async def test_agent_rejects_blast_radius_above_one() -> None:
    bad = _tool_response(
        {
            "effort_minutes_estimate": 30,
            "blast_radius_score": 1.5,
            "risk_tags": [],
            "reasoning": "x",
        }
    )
    agent = DiffAnalystAgent(completion=_fake_completion(bad, bad))
    with pytest.raises(AgentError):
        await agent.run("test")
