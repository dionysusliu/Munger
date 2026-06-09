def test_health_endpoint(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["version"] == "0.1.0"
    assert "timestamp" in payload


def test_stats_endpoint_returns_expected_shape(client, create_source, create_wiki_page, create_entity):
    source = create_source(file_type="md")
    page = create_wiki_page(source_id=source.id, page_type="summary")
    create_entity(wiki_page_id=page.id, entity_type="concept")

    response = client.get("/api/stats")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_sources"] == 1
    assert payload["total_wiki_pages"] == 1
    assert payload["total_entities"] == 1
    assert "sources_by_type" in payload
    assert "wiki_pages_by_type" in payload
    assert "entities_by_type" in payload
    assert "recent_activity" in payload


def test_config_endpoints_cover_defaults_and_updates(client):
    get_response = client.get("/api/config")
    assert get_response.status_code == 200

    payload = get_response.json()
    assert payload["total"] > 0
    assert "llm" in payload["configs"]

    put_response = client.put("/api/config/test.harness_mode", json={"value": "deterministic"})
    assert put_response.status_code == 200
    updated = put_response.json()
    assert updated["key"] == "test.harness_mode"
    assert updated["value"] == "deterministic"
