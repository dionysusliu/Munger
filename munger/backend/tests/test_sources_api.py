def test_source_upload_list_get_status_and_delete_flow(client):
    upload = client.post(
        "/api/sources/upload",
        files={"file": ("note.txt", b"source body for upload", "text/plain")},
        data={"title": "Uploaded Note"},
    )
    assert upload.status_code == 201
    created = upload.json()
    source_id = created["id"]

    list_response = client.get("/api/sources")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["title"] == "Uploaded Note"

    get_response = client.get(f"/api/sources/{source_id}")
    assert get_response.status_code == 200
    assert get_response.json()["filename"] == "note.txt"

    trigger_response = client.post(f"/api/sources/{source_id}/ingest")
    assert trigger_response.status_code == 202
    trigger_payload = trigger_response.json()
    assert trigger_payload["job_id"] is not None

    status_response = client.get(f"/api/sources/{source_id}/status")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["source_id"] == source_id
    assert "events" in status_payload
    assert status_payload["events"] == []

    delete_response = client.delete(f"/api/sources/{source_id}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/sources/{source_id}")
    assert missing_response.status_code == 404


def test_duplicate_source_upload_returns_conflict(client):
    files = {"file": ("dup.txt", b"same payload", "text/plain")}
    first = client.post("/api/sources/upload", files=files, data={"title": "Dup 1"})
    second = client.post("/api/sources/upload", files=files, data={"title": "Dup 2"})

    assert first.status_code == 201
    assert second.status_code == 409
    assert "identical content" in second.json()["detail"]
