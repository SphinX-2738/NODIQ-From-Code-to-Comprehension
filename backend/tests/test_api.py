from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    """Health endpoint should always return ok."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_unknown_repo():
    """Chatting about a repo that hasn't been ingested should return 404."""
    response = client.post("/api/v1/chat", json={
        "repo_id": "nonexistent-repo",
        "question": "how does login work?"
    })
    assert response.status_code == 404


def test_graph_unknown_repo():
    """Getting graph for unknown repo should return 404."""
    response = client.get("/api/v1/graph/nonexistent-repo")
    assert response.status_code == 404


def test_ingest_invalid_github_url():
    """An invalid GitHub URL should return 400."""
    response = client.post("/api/v1/ingest/github", json={
        "github_url": "https://not-a-real-url.com/bad/repo",
        "repo_id": "test-repo"
    })
    assert response.status_code == 400