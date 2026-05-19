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
    model = "claude-haiku-4-5"
    output_schema = Foo
    system_prompt = "Return an object with field x of type int."


def _ok_response(x: int = 42) -> SimpleNamespace:
    return SimpleNamespace(
        content=[
            SimpleNamespace(type="tool_use", name="foo_output", input={"x": x}),
        ],
        usage=SimpleNamespace(input_tokens=100, output_tokens=50),
    )


def _bad_response() -> SimpleNamespace:
    return SimpleNamespace(
        content=[
            SimpleNamespace(
                type="tool_use", name="foo_output", input={"x": "not-an-int"}
            ),
        ],
        usage=SimpleNamespace(input_tokens=100, output_tokens=50),
    )


def _fake_client(*responses: Any) -> SimpleNamespace:
    iterator = iter(responses)

    async def create(**_kwargs: Any) -> Any:
        return next(iterator)

    return SimpleNamespace(messages=SimpleNamespace(create=create))


async def test_run_returns_validated_output() -> None:
    agent = FooAgent(_fake_client(_ok_response(7)))  # type: ignore[arg-type]
    result = await agent.run("hi")
    assert isinstance(result, Foo)
    assert result.x == 7


async def test_run_emits_json_log_line_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    agent = FooAgent(_fake_client(_ok_response()))  # type: ignore[arg-type]
    await agent.run("hi")
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "agent_call"
    assert payload["agent"] == "foo"
    assert payload["model"] == "claude-haiku-4-5"
    assert payload["tokens_in"] == 100
    assert payload["tokens_out"] == 50
    assert payload["retry"] is False
    assert "duration_ms" in payload
    assert "cost_usd" in payload


async def test_bad_output_triggers_one_retry_then_succeeds(
    capsys: pytest.CaptureFixture[str],
) -> None:
    agent = FooAgent(_fake_client(_bad_response(), _ok_response(11)))  # type: ignore[arg-type]
    result = await agent.run("hi")
    assert result.x == 11

    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    second = json.loads(lines[1])
    assert first["retry"] is False
    assert second["retry"] is True


async def test_bad_output_twice_raises_agent_error() -> None:
    agent = FooAgent(_fake_client(_bad_response(), _bad_response()))  # type: ignore[arg-type]
    with pytest.raises(AgentError):
        await agent.run("hi")


async def test_no_tool_use_block_triggers_retry() -> None:
    no_tool = SimpleNamespace(
        content=[SimpleNamespace(type="text", text="just prose")],
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )
    agent = FooAgent(_fake_client(no_tool, _ok_response(3)))  # type: ignore[arg-type]
    result = await agent.run("hi")
    assert result.x == 3
