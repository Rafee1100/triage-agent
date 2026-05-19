import json
from types import SimpleNamespace
from typing import Any

import pytest

from src.agents.base import AgentError
from src.agents.synthesizer import Ranking, SynthesizerAgent


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
                                name="synthesizer_output",
                                arguments=json.dumps(payload),
                            )
                        )
                    ]
                )
            )
        ],
        usage=SimpleNamespace(prompt_tokens=2000, completion_tokens=400),
    )


async def test_synthesizer_returns_valid_ranking() -> None:
    response = _tool_response(
        {
            "prs": [
                {
                    "pr_number": 101,
                    "rank": 1,
                    "reasoning": "blast_radius=0.9 and true_urgency=0.85 push it to the top.",
                    "ai_priority": "high",
                    "label_disagreement": False,
                },
                {
                    "pr_number": 102,
                    "rank": 2,
                    "reasoning": "Doc-only change with blast_radius=0.05.",
                    "ai_priority": "low",
                    "label_disagreement": True,
                },
            ]
        }
    )
    agent = SynthesizerAgent(completion=_fake_completion(response))
    ranking: Ranking = await agent.run("input batch")
    assert len(ranking.prs) == 2
    assert ranking.prs[0].rank == 1
    assert ranking.prs[1].ai_priority == "low"


async def test_synthesizer_rejects_invalid_priority() -> None:
    bad = _tool_response(
        {
            "prs": [
                {
                    "pr_number": 1,
                    "rank": 1,
                    "reasoning": "x",
                    "ai_priority": "URGENT",
                    "label_disagreement": False,
                }
            ]
        }
    )
    agent = SynthesizerAgent(completion=_fake_completion(bad, bad))
    with pytest.raises(AgentError):
        await agent.run("input")
