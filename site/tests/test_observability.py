"""Request logging and route-labelled HTTP metrics."""

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY

from recipes_site import counts
from recipes_site.app import create_app
from recipes_site.config import Settings


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(counts, "bump", lambda *_a, **_k: None)
    return TestClient(create_app(Settings(auth_disabled=True)))


def _count(route: str, status: str) -> float:
    value = REGISTRY.get_sample_value(
        "http_requests_total", {"method": "GET", "route": route, "status": status}
    )
    return value or 0.0


def test_recipe_pages_share_one_route_label(client: TestClient) -> None:
    before = _count("/{slug:path}", "200")
    assert client.get("/breakfast/granola").status_code == 200
    assert client.get("/bread/bread-banana").status_code == 200
    assert _count("/{slug:path}", "200") == before + 2


def test_a_missing_recipe_counts_as_a_404(client: TestClient) -> None:
    before = _count("/{slug:path}", "404")
    client.get("/nope/nope")
    assert _count("/{slug:path}", "404") == before + 1


def test_probes_and_scrapes_are_not_counted(client: TestClient) -> None:
    before = _count("/health", "200")
    client.get("/health")
    assert _count("/health", "200") == before
    assert b"http_requests_total" in client.get("/metrics").content


def test_every_response_carries_a_request_id(client: TestClient) -> None:
    assert len(client.get("/").headers["x-request-id"]) == 32
    echoed = client.get("/", headers={"X-Request-ID": "abc123"})
    assert echoed.headers["x-request-id"] == "abc123"
