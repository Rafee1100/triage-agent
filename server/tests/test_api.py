import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    with patch.dict(os.environ, {"GITHUB_TOKEN": "ghp_test"}, clear=False):
        from src.api.main import app

        with TestClient(app) as test_client:
            yield test_client


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_cors_headers_present_on_allowed_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
