from fastapi.testclient import TestClient

from server.main import app, settings

client = TestClient(app)


def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert set(body) == {"ok", "db", "agent_version"}  # matches docs/specs/api-contract.md


def test_cors_allows_our_web_origin():
    r = client.get("/api/health", headers={"Origin": settings.web_origin})
    assert r.headers.get("access-control-allow-origin") == settings.web_origin


def test_cors_does_not_allow_other_origins():
    r = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers
