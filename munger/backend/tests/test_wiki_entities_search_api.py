def test_wiki_crud_links_and_related(client, create_wiki_link):
    create_response = client.post(
        "/api/wiki",
        json={
            "title": "First Page",
            "slug": "first-page",
            "content": "alpha beta",
            "page_type": "summary",
        },
    )
    assert create_response.status_code == 201
    page = create_response.json()

    second = client.post(
        "/api/wiki",
        json={
            "title": "Second Page",
            "slug": "second-page",
            "content": "beta gamma",
            "page_type": "concept",
        },
    ).json()

    create_wiki_link(from_page_id=page["id"], to_page_id=second["id"], context="connects")

    list_response = client.get("/api/wiki", params={"search": "alpha"})
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    get_by_id = client.get(f"/api/wiki/{page['id']}")
    assert get_by_id.status_code == 200

    get_by_slug = client.get("/api/wiki/slug/first-page")
    assert get_by_slug.status_code == 200

    update = client.put(f"/api/wiki/{page['id']}", params={"content": "updated content body"})
    assert update.status_code == 200
    assert update.json()["word_count"] == 3

    links = client.get(f"/api/wiki/{page['id']}/links")
    assert links.status_code == 200
    assert links.json()["outgoing"]
    assert links.json()["outgoing"][0]["direction"] == "outgoing"

    related = client.get(f"/api/wiki/{page['id']}/related")
    assert related.status_code == 200
    assert related.json()["page_id"] == page["id"]

    delete = client.delete(f"/api/wiki/{second['id']}")
    assert delete.status_code == 204


def test_wiki_list_pagination(client):
    for i in range(7):
        resp = client.post(
            "/api/wiki",
            json={
                "title": f"Paginated Page {i:02d}",
                "slug": f"paginated-page-{i:02d}",
                "content": f"body number {i}",
                "page_type": "summary",
            },
        )
        assert resp.status_code == 201

    first = client.get("/api/wiki", params={"page": 1, "page_size": 3})
    assert first.status_code == 200
    body = first.json()
    assert body["total"] == 7
    assert body["page"] == 1
    assert body["page_size"] == 3
    assert len(body["items"]) == 3

    second = client.get("/api/wiki", params={"page": 2, "page_size": 3})
    assert len(second.json()["items"]) == 3

    third = client.get("/api/wiki", params={"page": 3, "page_size": 3})
    assert len(third.json()["items"]) == 1

    # No overlap between pages.
    first_ids = {p["id"] for p in body["items"]}
    second_ids = {p["id"] for p in second.json()["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_wiki_search_ranks_title_matches_first(client):
    # "needle" appears in one title, and in the content of a different page.
    titled = client.post(
        "/api/wiki",
        json={
            "title": "Needle In Title",
            "slug": "needle-in-title",
            "content": "unrelated body text",
            "page_type": "summary",
        },
    ).json()
    content_only = client.post(
        "/api/wiki",
        json={
            "title": "Plain Heading",
            "slug": "plain-heading",
            "content": "this body mentions a needle somewhere",
            "page_type": "summary",
        },
    ).json()

    # Both pages match, but the title match must rank first.
    hit = client.get("/api/wiki", params={"search": "needle"})
    assert hit.status_code == 200
    body = hit.json()
    assert body["total"] == 2
    assert [item["id"] for item in body["items"]] == [titled["id"], content_only["id"]]

    # Title ranking survives pagination: the title match is the only first-page result.
    page1 = client.get("/api/wiki", params={"search": "needle", "page": 1, "page_size": 1})
    assert [item["id"] for item in page1.json()["items"]] == [titled["id"]]
    page2 = client.get("/api/wiki", params={"search": "needle", "page": 2, "page_size": 1})
    assert [item["id"] for item in page2.json()["items"]] == [content_only["id"]]

    # Content-only term still matches via full-text search.
    content_hit = client.get("/api/wiki", params={"search": "somewhere"})
    content_body = content_hit.json()
    assert content_body["total"] == 1
    assert content_body["items"][0]["slug"] == "plain-heading"

    # No match anywhere.
    miss = client.get("/api/wiki", params={"search": "zzznomatch"})
    assert miss.json()["total"] == 0


def test_entities_endpoints_cover_list_get_mentions_related_and_update(
    client,
    create_source,
    create_wiki_page,
    create_entity,
    create_entity_mention,
):
    source = create_source()
    page = create_wiki_page(title="Entity Page", slug="entity-page")
    first = create_entity(name="Alpha Concept", entity_type="concept", wiki_page_id=page.id, mention_count=3)
    second = create_entity(name="Beta Concept", entity_type="concept", mention_count=2)
    create_entity_mention(entity_id=first.id, source_id=source.id, wiki_page_id=page.id, context="alpha mention")
    create_entity_mention(entity_id=second.id, source_id=source.id, wiki_page_id=page.id, context="beta mention")

    listed = client.get("/api/entities", params={"search": "Alpha"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    fetched = client.get(f"/api/entities/{first.id}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Alpha Concept"

    mentions = client.get(f"/api/entities/{first.id}/mentions")
    assert mentions.status_code == 200
    mentions_payload = mentions.json()
    assert mentions_payload["entity_name"] == "Alpha Concept"
    assert len(mentions_payload["mentions"]) == 1

    related = client.get(f"/api/entities/{first.id}/related")
    assert related.status_code == 200
    related_payload = related.json()
    assert related_payload["related_entities"][0]["name"] == "Beta Concept"

    update = client.put(
        f"/api/entities/{first.id}",
        json={
            "name": "Alpha Concept Updated",
            "entity_type": "concept",
            "description": "updated description",
            "wiki_page_id": page.id,
            "metadata_json": "{\"origin\":\"test\"}",
        },
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Alpha Concept Updated"


def test_search_and_suggest_cover_multiple_result_types(
    client,
    create_source,
    create_wiki_page,
    create_entity,
):
    create_source(title="Search Source", filename="search.txt", content_text="Alpha evidence")
    create_wiki_page(title="Alpha Page", slug="alpha-page", content="Alpha content body")
    create_entity(name="Alpha Entity", entity_type="concept", description="Alpha concept desc")

    search_response = client.get("/api/search", params={"q": "Alpha"})
    assert search_response.status_code == 200
    result_types = {result["result_type"] for result in search_response.json()["results"]}
    assert {"source", "wiki_page", "entity"} <= result_types

    semantic_response = client.get("/api/search/semantic", params={"q": "Alpha"})
    assert semantic_response.status_code == 200
    assert semantic_response.json()["query"] == "Alpha"

    suggest_response = client.get("/api/search/suggest", params={"q": "Al"})
    assert suggest_response.status_code == 200
    assert suggest_response.json()["suggestions"]
