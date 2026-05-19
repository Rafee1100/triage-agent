import json
from types import SimpleNamespace
from typing import Any

import pytest

from src.agents.author_profile import AuthorProfileAgent
from src.agents.base import AgentError
from src.github.models import AuthorProfile


def _profile(
    *,
    login: str = "alice",
    merged: int = 12,
    revert: float = 0.02,
    reviews: float = 8.0,
) -> AuthorProfile:
    return AuthorProfile(
        login=login,
        merged_pr_count_in_repo=merged,
        revert_rate=revert,
        avg_review_comments_per_pr=reviews,
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
                                name="author_profile_output",
                                arguments=json.dumps(payload),
                            )
                        )
                    ]
                )
            )
        ],
        usage=SimpleNamespace(prompt_tokens=80, completion_tokens=40),
    )


def test_format_message_renders_all_three_numbers() -> None:
    msg = AuthorProfileAgent.format_message(_profile(merged=34, revert=0.015, reviews=12.3))
    assert "@alice" in msg
    assert "merged_90d=34" in msg
    assert "0.015" in msg
    assert "12.3" in msg


async def test_agent_returns_validated_assessment() -> None:
    response = _tool_response(
        {
            "trust_score": 0.82,
            "recommended_review_depth": "skim",
            "rationale": "Author has 34 merged PRs in 90 days and a 0.015 revert rate.",
        }
    )
    agent = AuthorProfileAgent(completion=_fake_completion(response))
    result = await agent.analyze(_profile(merged=34))
    assert result.trust_score == 0.82
    assert result.recommended_review_depth == "skim"


async def test_agent_rejects_invalid_review_depth() -> None:
    bad = _tool_response(
        {
            "trust_score": 0.5,
            "recommended_review_depth": "fast",
            "rationale": "x",
        }
    )
    agent = AuthorProfileAgent(completion=_fake_completion(bad, bad))
    with pytest.raises(AgentError):
        await agent.analyze(_profile())


async def test_agent_rejects_trust_score_out_of_range() -> None:
    bad = _tool_response(
        {
            "trust_score": 1.5,
            "recommended_review_depth": "deep",
            "rationale": "x",
        }
    )
    agent = AuthorProfileAgent(completion=_fake_completion(bad, bad))
    with pytest.raises(AgentError):
        await agent.analyze(_profile())
