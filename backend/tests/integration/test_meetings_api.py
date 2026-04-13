from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_meeting_lifecycle():
    created = client.post("/api/meetings", json={"title": "Integration test"})
    assert created.status_code == 200
    meeting = created.json()
    meeting_id = meeting["id"]

    listed = client.get("/api/meetings")
    assert listed.status_code == 200
    assert any(item["id"] == meeting_id for item in listed.json())

    fetched = client.get(f"/api/meetings/{meeting_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == meeting_id

    deleted = client.delete(f"/api/meetings/{meeting_id}")
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True

