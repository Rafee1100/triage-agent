import asyncio
import json
import logging
import re
import time
from typing import Any, Generic, TypeVar

import anthropic
from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

MAX_TOKENS = 4096
ANTHROPIC_RETRY_ATTEMPTS = 3
BASE_BACKOFF_S = 1.0

PRICING_PER_M = {
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.0},
}

RETRY_REMINDER = (
    "IMPORTANT: Return ONLY valid JSON matching the tool's input_schema. "
    "No prose, no markdown, no commentary."
)


class AgentError(Exception):
    pass


class BaseAgent(Generic[T]):
    name: str = ""
    model: str = ""
    output_schema: type[T]
    system_prompt: str = ""

    def __init__(self, client: AsyncAnthropic) -> None:
        self.client = client

    async def run(self, user_message: str) -> T:
        tool_schema = self._build_tool_schema()

        result, err = await self._call_and_parse(user_message, tool_schema, is_retry=False)
        if err is None and result is not None:
            return result

        retry_message = f"{user_message}\n\n{RETRY_REMINDER}"
        result, err = await self._call_and_parse(retry_message, tool_schema, is_retry=True)
        if err is None and result is not None:
            return result
        raise AgentError(
            f"agent {self.name!r} failed to produce valid output after retry: {err}"
        )

    async def _call_and_parse(
        self,
        user_message: str,
        tool_schema: dict[str, Any],
        is_retry: bool,
    ) -> tuple[T | None, str | None]:
        t0 = time.perf_counter()
        response = await self._messages_create_with_retries(user_message, tool_schema)
        duration_ms = int((time.perf_counter() - t0) * 1000)

        tool_use_input: dict[str, Any] | None = None
        for block in response.content:
            if (
                getattr(block, "type", None) == "tool_use"
                and getattr(block, "name", None) == self._tool_name()
            ):
                tool_use_input = getattr(block, "input", None)
                break

        usage = getattr(response, "usage", None)
        tokens_in = int(getattr(usage, "input_tokens", 0) or 0)
        tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
        cost = _estimate_cost(self.model, tokens_in, tokens_out)

        _emit_log(
            {
                "event": "agent_call",
                "agent": self.name,
                "model": self.model,
                "duration_ms": duration_ms,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_usd": round(cost, 6),
                "retry": is_retry,
            }
        )

        if tool_use_input is None:
            return None, "no tool_use block in response"

        try:
            return self.output_schema.model_validate(tool_use_input), None
        except ValidationError as exc:
            return None, str(exc)

    async def _messages_create_with_retries(
        self,
        user_message: str,
        tool_schema: dict[str, Any],
    ) -> Any:
        attempts = 0
        while True:
            try:
                return await self.client.messages.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    system=self.system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                    tools=[tool_schema],
                    tool_choice={"type": "tool", "name": self._tool_name()},
                )
            except (anthropic.RateLimitError, anthropic.APIConnectionError) as exc:
                attempts += 1
                if attempts >= ANTHROPIC_RETRY_ATTEMPTS:
                    raise
                delay = BASE_BACKOFF_S * (2 ** (attempts - 1))
                logger.warning(
                    "anthropic_retry",
                    extra={
                        "agent": self.name,
                        "attempt": attempts,
                        "delay_s": delay,
                        "error": type(exc).__name__,
                    },
                )
                await asyncio.sleep(delay)

    def _tool_name(self) -> str:
        return f"{self.name}_output"

    def _build_tool_schema(self) -> dict[str, Any]:
        return {
            "name": self._tool_name(),
            "description": f"Structured output for the {self.name} agent.",
            "input_schema": self.output_schema.model_json_schema(),
        }


def _estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    base = re.sub(r"-\d{8}$", "", model)
    rates = PRICING_PER_M.get(base)
    if not rates:
        return 0.0
    return (tokens_in * rates["input"] + tokens_out * rates["output"]) / 1_000_000


def _emit_log(payload: dict[str, Any]) -> None:
    print(json.dumps(payload), flush=True)
