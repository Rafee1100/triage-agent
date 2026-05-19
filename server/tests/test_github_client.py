import httpx

from src.github.client import GitHubClient


async def test_query_sends_authorization_and_user_agent_headers() -> None:
    captured: dict[str, httpx.Request] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return httpx.Response(
            200,
            json={"data": {"viewer": {"login": "tester"}}},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = GitHubClient(token="ghp_secret", client=http)
        result = await client.query("query { viewer { login } }", {})

    request = captured["request"]
    assert request.headers["authorization"] == "bearer ghp_secret"
    assert request.headers["user-agent"] == "triagepilot/0.1"
    assert str(request.url) == "https://api.github.com/graphql"
    assert result == {"data": {"viewer": {"login": "tester"}}}
