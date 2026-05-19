import asyncio
import logging
import time
from typing import Any

import httpx

from src.github.models import PRContext
from src.github.queries import OPEN_PRS_WITH_CONTEXT

logger = logging.getLogger(__name__)

GITHUB_GRAPHQL_URL = "https://api.github.com/graphql"
USER_AGENT = "triagepilot/0.1"
DEFAULT_TIMEOUT_S = 30.0
MAX_SERVER_ERROR_RETRIES = 3
BASE_BACKOFF_S = 1.0
RATE_LIMIT_WAIT_CAP_S = 60.0
GITHUB_MAX_PAGE_SIZE = 100


class GitHubAPIError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class GitHubClient:
    def __init__(
        self,
        token: str,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not token:
            raise ValueError("token must be a non-empty string")
        self._token = token
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S)

    async def query(self, gql_query: str, variables: dict[str, Any]) -> dict[str, Any]:
        payload = {"query": gql_query, "variables": variables}
        headers = {
            "Authorization": f"bearer {self._token}",
            "User-Agent": USER_AGENT,
        }

        rate_limit_retried = False
        server_error_attempts = 0

        while True:
            try:
                response = await self._client.post(
                    GITHUB_GRAPHQL_URL,
                    json=payload,
                    headers=headers,
                )
            except httpx.HTTPError as exc:
                if server_error_attempts < MAX_SERVER_ERROR_RETRIES:
                    delay = BASE_BACKOFF_S * (2**server_error_attempts)
                    logger.warning(
                        "github_transport_retry",
                        extra={
                            "attempt": server_error_attempts + 1,
                            "delay_s": delay,
                            "error": str(exc),
                        },
                    )
                    await asyncio.sleep(delay)
                    server_error_attempts += 1
                    continue
                raise GitHubAPIError(f"Transport error after retries: {exc}") from exc

            if response.status_code == 429:
                if rate_limit_retried:
                    raise GitHubAPIError(
                        "Rate limited again after waiting for reset",
                        status_code=429,
                        body=response.text,
                    )
                await self._sleep_until_rate_limit_reset(response)
                rate_limit_retried = True
                continue

            if 500 <= response.status_code < 600:
                if server_error_attempts < MAX_SERVER_ERROR_RETRIES:
                    delay = BASE_BACKOFF_S * (2**server_error_attempts)
                    logger.warning(
                        "github_server_error_retry",
                        extra={
                            "attempt": server_error_attempts + 1,
                            "delay_s": delay,
                            "status_code": response.status_code,
                        },
                    )
                    await asyncio.sleep(delay)
                    server_error_attempts += 1
                    continue
                raise GitHubAPIError(
                    f"Server error {response.status_code} after retries",
                    status_code=response.status_code,
                    body=response.text,
                )

            if response.status_code >= 400:
                raise GitHubAPIError(
                    f"HTTP {response.status_code}",
                    status_code=response.status_code,
                    body=response.text,
                )

            try:
                data: dict[str, Any] = response.json()
            except ValueError as exc:
                raise GitHubAPIError(
                    "Non-JSON response from GitHub",
                    status_code=response.status_code,
                    body=response.text,
                ) from exc

            errors = data.get("errors") or []
            if errors and any(self._is_rate_limited_error(err) for err in errors):
                if rate_limit_retried:
                    raise GitHubAPIError(
                        "GraphQL RATE_LIMITED again after waiting for reset",
                        status_code=response.status_code,
                        body=response.text,
                    )
                await self._sleep_until_rate_limit_reset(response)
                rate_limit_retried = True
                continue

            if errors and data.get("data") is None:
                raise GitHubAPIError(
                    f"GraphQL errors: {errors}",
                    status_code=response.status_code,
                    body=response.text,
                )

            return data

    async def fetch_open_prs(
        self,
        owner: str,
        name: str,
        limit: int = 50,
    ) -> list[PRContext]:
        if limit <= 0:
            return []

        collected: list[PRContext] = []
        cursor: str | None = None

        while len(collected) < limit:
            page_size = min(GITHUB_MAX_PAGE_SIZE, limit - len(collected))
            variables: dict[str, Any] = {
                "owner": owner,
                "name": name,
                "first": page_size,
                "after": cursor,
            }
            response = await self.query(OPEN_PRS_WITH_CONTEXT, variables)

            repository = (response.get("data") or {}).get("repository")
            if not repository:
                raise GitHubAPIError(
                    f"Repository {owner}/{name} not found or not accessible",
                    body=str(response),
                )

            pulls = repository.get("pullRequests") or {}
            for node in pulls.get("nodes") or []:
                collected.append(PRContext.model_validate(node))

            page_info = pulls.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                break
            cursor = page_info.get("endCursor")
            if not cursor:
                break

        return collected[:limit]

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "GitHubClient":
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()

    @staticmethod
    def _is_rate_limited_error(err: dict[str, Any]) -> bool:
        return err.get("type") == "RATE_LIMITED"

    @staticmethod
    async def _sleep_until_rate_limit_reset(response: httpx.Response) -> None:
        reset_header = response.headers.get("X-RateLimit-Reset")
        delay = BASE_BACKOFF_S
        if reset_header:
            try:
                reset_at = float(reset_header)
                delay = max(BASE_BACKOFF_S, reset_at - time.time())
            except ValueError:
                pass
        delay = min(delay, RATE_LIMIT_WAIT_CAP_S)
        logger.warning("github_rate_limited", extra={"delay_s": delay})
        await asyncio.sleep(delay)
