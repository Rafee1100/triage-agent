import json
from types import SimpleNamespace
from typing import Any

import pytest

from src.agents.base import AgentError
from src.agents.critic import CriticAgent
from src.agents.synthesizer import Ranking, RankedPR


def _ranking(n: int = 3) -> Ranking:
    return Ranking(
        prs=[
            RankedPR(
                pr_number=100 + i,
                rank=i + 1,
                reasoning=f"reasoning for #{100+i}",
                ai_priority="medium",
                label_disagreement=False,
            )
            for i in range(n)
        ]
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
                                name="critic_output",
                                arguments=json.dumps(payload),
                            )
                        )
                    ]
                )
            )
        ],
        usage=SimpleNamespace(prompt_tokens=500, completion_tokens=150),
    )


def test_format_message_lists_ranking_in_order() -> None:
    msg = CriticAgent.format_message(_ranking())
    lines = msg.splitlines()
    assert lines[0] == "N=3"
    assert "rank=1 pr_number=100" in msg
    assert "rank=3 pr_number=102" in msg


async def test_critic_returns_empty_adjustments_for_sound_ranking() -> None:
    response = _tool_response(
        {
            "adjustments": [],
            "overall_assessment": "Ranking is sound — top PRs align with blast_radius.",
        }
    )
    agent = CriticAgent(completion=_fake_completion(response))
    critique = await agent.critique(_ranking())
    assert critique.adjustments == []
    assert "sound" in critique.overall_assessment.lower()


async def test_critic_returns_typed_adjustments() -> None:
    response = _tool_response(
        {
            "adjustments": [
                {
                    "pr_number": 102,
                    "new_rank": 1,
                    "reason": "blast_radius=0.9 but currently ranked #3",
                }
            ],
            "overall_assessment": "Top-3 needs reorder.",
        }
    )
    agent = CriticAgent(completion=_fake_completion(response))
    critique = await agent.critique(_ranking())
    assert len(critique.adjustments) == 1
    assert critique.adjustments[0].pr_number == 102
    assert critique.adjustments[0].new_rank == 1


async def test_critic_rejects_more_than_three_adjustments() -> None:
    too_many = _tool_response(
        {
            "adjustments": [
                {"pr_number": 100 + i, "new_rank": i + 1, "reason": "x"}
                for i in range(4)
            ],
            "overall_assessment": "x",
        }
    )
    agent = CriticAgent(completion=_fake_completion(too_many, too_many))
    with pytest.raises(AgentError):
        await agent.critique(_ranking(4))
