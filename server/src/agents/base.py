import asyncio
import json
import logging
import os
import time
from typing import Any, Awaitable, Callable, Generic, TypeVar

os.environ.setdefault("LITELLM_LOG", "ERROR")

import litellm
from pydantic import BaseModel, ValidationError

litellm.suppress_debug_info = True
litellm.set_verbose = False

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

HAIKU_MODEL = os.getenv("HAIKU_MODEL", "groq/llama-3.3-70b-versatile")
SONNET_MODEL = os.getenv("SONNET_MODEL", "groq/llama-3.3-70b-versatile")

MAX_TOKENS = 1024
RETRY_ATTEMPTS = 6
BASE_BACKOFF_S = 2.0
MAX_BACKOFF_S = 60.0

RETRY_REMINDER = "Return ONLY valid JSON for the tool. No prose."

CompletionFn = Callable[..., Awaitable[Any]]


class AgentError(Exception):
    pass


class BaseAgent(Generic[T]):
    name: str = ""
    model: str = ""
    output_schema: type[T]
    system_prompt: str = ""

    def __init__(self, completion: CompletionFn | None = None) -> None:
        self._completion = completion or litellm.acompletion

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
        try:
            response = await self._completion_with_retries(user_message, tool_schema)
        except litellm.BadRequestError as exc:
            duration_ms = int((time.perf_counter() - t0) * 1000)
            _emit_log(
                {
                    "event": "agent_call",
                    "agent": self.name,
                    "model": self.model,
                    "duration_ms": duration_ms,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "cost_usd": 0.0,
                    "retry": is_retry,
                    "error": "bad_request",
                }
            )
            return None, f"bad_request: {exc}"
        duration_ms = int((time.perf_counter() - t0) * 1000)

        tool_input = self._extract_tool_input(response)
        tokens_in, tokens_out = self._extract_usage(response)
        cost = self._estimate_cost(response)

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

        if tool_input is None:
            return None, "no tool_call in response"

        try:
            return self.output_schema.model_validate(tool_input), None
        except ValidationError as exc:
            return None, str(exc)

    async def _completion_with_retries(
        self,
        user_message: str,
        tool_schema: dict[str, Any],
    ) -> Any:
        attempts = 0
        while True:
            try:
                return await self._completion(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    tools=[{"type": "function", "function": tool_schema}],
                    tool_choice={
                        "type": "function",
                        "function": {"name": self._tool_name()},
                    },
                )
            except (litellm.RateLimitError, litellm.APIConnectionError) as exc:
                attempts += 1
                if attempts >= RETRY_ATTEMPTS:
                    raise
                delay = min(BASE_BACKOFF_S * (2 ** (attempts - 1)), MAX_BACKOFF_S)
                logger.warning(
                    "llm_retry",
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
            "description": f"{self.name} output",
            "parameters": _compact_schema(self.output_schema.model_json_schema()),
        }

    def _extract_tool_input(self, response: Any) -> dict[str, Any] | None:
        try:
            choices = getattr(response, "choices", None) or []
            if not choices:
                return None
            message = getattr(choices[0], "message", None)
            tool_calls = getattr(message, "tool_calls", None) or []
            for call in tool_calls:
                fn = getattr(call, "function", None)
                if fn is None:
                    continue
                if getattr(fn, "name", None) != self._tool_name():
                    continue
                args = getattr(fn, "arguments", None)
                if isinstance(args, str):
                    return json.loads(args)
                if isinstance(args, dict):
                    return args
            return None
        except (json.JSONDecodeError, AttributeError):
            return None

    @staticmethod
    def _extract_usage(response: Any) -> tuple[int, int]:
        usage = getattr(response, "usage", None)
        return (
            int(getattr(usage, "prompt_tokens", 0) or 0),
            int(getattr(usage, "completion_tokens", 0) or 0),
        )

    @staticmethod
    def _estimate_cost(response: Any) -> float:
        try:
            return float(litellm.completion_cost(completion_response=response) or 0.0)
        except Exception:
            return 0.0


def _compact_schema(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _compact_schema(v) for k, v in node.items() if k != "title"}
    if isinstance(node, list):
        return [_compact_schema(v) for v in node]
    return node


def _emit_log(payload: dict[str, Any]) -> None:
    print(json.dumps(payload), flush=True)
