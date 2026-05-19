import json
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from src.agents.base import AgentError, BaseAgent


class Foo(BaseModel):
    x: int


class FooAgent(BaseAgent[Foo]):
    name = "foo"
    model = "groq/llama-3.1-8b-instant"
    output_schema = Foo
    system_prompt = "Return an object with field x of type int."


def _tool_response(name: str, payload: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[
                        SimpleNamespace(
                            function=SimpleNamespace(
                                name=name,
                                arguments=json.dumps(payload),
                            )
                        )
                    ]
                )
            )
        ],
        usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50),
    )


def _ok_response(x: int = 42) -> SimpleNamespace:
    return _tool_response("foo_output", {"x": x})


def _bad_response() -> SimpleNamespace:
    return _tool_response("foo_output", {"x": "not-an-int"})


def _no_tool_response() -> SimpleNamespace:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(tool_calls=None, content="just prose")
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5),
    )


def _fake_completion(*responses: Any) -> Any:
    iterator = iter(responses)

    async def completion(**_kwargs: Any) -> Any:
        return next(iterator)

    return completion


async def test_run_returns_validated_output() -> None:
    agent = FooAgent(completion=_fake_completion(_ok_response(7)))
    result = await agent.run("hi")
    assert isinstance(result, Foo)
    assert result.x == 7


async def test_run_emits_json_log_line_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    agent = FooAgent(completion=_fake_completion(_ok_response()))
    await agent.run("hi")
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "agent_call"
    assert payload["agent"] == "foo"
    assert payload["model"] == "groq/llama-3.1-8b-instant"
    assert payload["tokens_in"] == 100
    assert payload["tokens_out"] == 50
    assert payload["retry"] is False
    assert "duration_ms" in payload
    assert "cost_usd" in payload


async def test_bad_output_triggers_one_retry_then_succeeds(
    capsys: pytest.CaptureFixture[str],
) -> None:
    agent = FooAgent(completion=_fake_completion(_bad_response(), _ok_response(11)))
    result = await agent.run("hi")
    assert result.x == 11

    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["retry"] is False
    assert second["retry"] is True


async def test_bad_output_twice_raises_agent_error() -> None:
    agent = FooAgent(completion=_fake_completion(_bad_response(), _bad_response()))
    with pytest.raises(AgentError):
        await agent.run("hi")


async def test_no_tool_call_triggers_retry() -> None:
    agent = FooAgent(
        completion=_fake_completion(_no_tool_response(), _ok_response(3))
    )
    result = await agent.run("hi")
    assert result.x == 3


