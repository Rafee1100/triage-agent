import json
from types import SimpleNamespace
from typing import Any

import pytest

from src.agents.base import AgentError
from src.agents.ticket_context import TicketContext, TicketContextAgent
from src.github.models import PRContext


def _pr(*, linked: list[dict] | None = None) -> PRContext:
    return PRContext.model_validate(
        {
            "number": 1,
            "title": "Sample",
            "body": None,
            "url": "https://github.com/o/r/pull/1",
            "createdAt": "2026-05-01T00:00:00Z",
            "updatedAt": "2026-05-10T00:00:00Z",
            "author": {"login": "alice"},
            "headRefName": "main",
            "mergeable": "MERGEABLE",
            "additions": 1,
            "deletions": 0,
            "changedFiles": 1,
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
                                name="ticket_context_output",
                                arguments=json.dumps(payload),
                            )
                        )
                    ]
                )
            )
        ],
        usage=SimpleNamespace(prompt_tokens=200, completion_tokens=60),
    )


async def test_analyze_returns_defaults_when_no_linked_issue() -> None:
    agent = TicketContextAgent(completion=_fake_completion())
    result = await agent.analyze(_pr(), stated_priority="high")
    assert result.stated_priority == "unknown"
    assert result.true_urgency_score == 0.5
    assert result.label_disagreement is False
    assert result.disagreement_reason is None
    assert result.keywords_extracted == []


async def test_analyze_calls_llm_when_linked_issue_present() -> None:
    response = _tool_response(
        {
            "stated_priority": "low",
            "true_urgency_score": 0.85,
            "label_disagreement": True,
            "disagreement_reason": 'Body says "blocks Q3 release" but label is low',
            "keywords_extracted": ["blocks", "release"],
        }
    )
    pr = _pr(
        linked=[
            {
                "number": 9,
                "title": "Blocker",
                "body": "This blocks Q3 release.",
                "labels": {"nodes": []},
            }
        ]
    )
    agent = TicketContextAgent(completion=_fake_completion(response))
    result = await agent.analyze(pr, stated_priority="low")
    assert result.label_disagreement is True
    assert "Q3" in (result.disagreement_reason or "")


async def test_disagreement_without_reason_is_rejected() -> None:
    bad = _tool_response(
        {
            "stated_priority": "low",
            "true_urgency_score": 0.85,
            "label_disagreement": True,
            "disagreement_reason": None,
            "keywords_extracted": [],
        }
    )
    pr = _pr(linked=[{"number": 1, "title": "x", "body": "y", "labels": {"nodes": []}}])
    agent = TicketContextAgent(completion=_fake_completion(bad, bad))
    with pytest.raises(AgentError):
        await agent.analyze(pr, stated_priority="low")


def test_format_message_includes_priority_and_issue() -> None:
    pr = _pr(
        linked=[
            {
                "number": 42,
                "title": "Crash on cold start",
                "body": "Production traffic blocked.",
                "labels": {"nodes": [{"name": "kind/bug"}]},
            }
        ]
    )
    msg = TicketContextAgent.format_message(pr, stated_priority="medium")
    assert "stated_priority: medium" in msg
    assert "Crash on cold start" in msg
    assert "Production traffic blocked." in msg
    assert "kind/bug" in msg


def test_ticket_context_validator_accepts_no_disagreement_without_reason() -> None:
    ctx = TicketContext(
        stated_priority="high",
        true_urgency_score=0.8,
        label_disagreement=False,
        disagreement_reason=None,
        keywords_extracted=[],
    )
    assert ctx.label_disagreement is False
