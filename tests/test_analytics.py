import json
import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault(
    "PG_DSN", "postgresql://lawcite:changeme@localhost:5432/lawcite_test"
)

from api.main import app  # noqa: E402
from api.main import get_db  # noqa: E402


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ADMIN_METRICS_TOKEN", raising=False)
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            pool = await get_db().connect()
            async with pool.acquire() as conn:
                await conn.execute("TRUNCATE events, chat_messages RESTART IDENTITY")
            yield ac
            async with pool.acquire() as conn:
                await conn.execute("TRUNCATE events, chat_messages RESTART IDENTITY")


@pytest.mark.asyncio
async def test_events_ingest_persists_and_hashes_ip(client):
    resp = await client.post(
        "/api/events",
        headers={"X-Forwarded-For": "203.0.113.9, 10.0.0.1"},
        json={
            "session_id": "sess-alpha",
            "events": [
                {"type": "pageview", "path": "/", "meta": {}},
                {"type": "search", "path": "/", "meta": {"query": "arbitration"}},
            ],
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "recorded": 2}

    pool = await get_db().connect()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM events WHERE session_id = $1 ORDER BY id", "sess-alpha"
        )
        again = await client.post(
            "/api/events",
            headers={"X-Forwarded-For": "203.0.113.9"},
            json={"session_id": "sess-alpha", "events": [{"type": "dwell", "meta": {}}]},
        )
        assert again.status_code == 200
        second = await conn.fetch(
            "SELECT ip_hash FROM events WHERE type = 'dwell' AND session_id = $1",
            "sess-alpha",
        )

    assert len(rows) == 2
    ip_hash = rows[0]["ip_hash"]
    assert ip_hash and len(ip_hash) == 24
    assert "203.0.113.9" not in ip_hash
    assert second and second[0]["ip_hash"] == ip_hash
    assert rows[1]["meta"] and json.loads(rows[1]["meta"])["query"] == "arbitration"
    assert rows[0]["user_agent"]


@pytest.mark.asyncio
async def test_events_rejects_invalid_payloads(client):
    bad_type = await client.post(
        "/api/events",
        json={"session_id": "x", "events": [{"type": "DROP TABLE events"}]},
    )
    assert bad_type.status_code == 422

    empty = await client.post("/api/events", json={"session_id": "x", "events": []})
    assert empty.status_code == 422

    too_many = await client.post(
        "/api/events",
        json={"session_id": "x", "events": [{"type": "ping"}] * 51},
    )
    assert too_many.status_code == 422


@pytest.mark.asyncio
async def test_events_without_session_id_gets_generated(client):
    resp = await client.post("/api/events", json={"events": [{"type": "ping"}]})
    assert resp.status_code == 200
    assert resp.json()["recorded"] == 1

    pool = await get_db().connect()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT session_id FROM events WHERE type = 'ping'"
        )
    assert row and len(row["session_id"]) == 32


@pytest.mark.asyncio
async def test_chat_exchange_is_persisted(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    resp = await client.post(
        "/api/chat",
        headers={"X-Forwarded-For": "198.51.100.7"},
        json={
            "session_id": "sess-chat",
            "mode": "research",
            "messages": [{"role": "user", "content": "What is s.4?"}],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "unconfigured"

    pool = await get_db().connect()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM chat_messages WHERE session_id = $1 ORDER BY id",
            "sess-chat",
        )
    assert [r["role"] for r in rows] == ["user", "assistant"]
    assert rows[0]["content"] == "What is s.4?"
    assert rows[1]["status"] == "unconfigured"
    assert rows[1]["latency_ms"] >= 0
    assert rows[0]["ip_hash"] and "198.51.100.7" not in rows[0]["ip_hash"]


@pytest.mark.asyncio
async def test_metrics_summary_requires_token_and_reports_usage(client, monkeypatch):
    hidden = await client.get("/api/metrics/summary")
    assert hidden.status_code == 404
    wrong = await client.get(
        "/api/metrics/summary", headers={"X-Admin-Token": "nope"}
    )
    assert wrong.status_code == 404

    seeded = await client.post(
        "/api/events",
        json={
            "session_id": "m1",
            "events": [
                {"type": "pageview", "path": "/"},
                {"type": "search", "path": "/", "meta": {"query": "q"}},
                {"type": "dwell", "path": "/", "meta": {"ms": 1500}},
            ],
        },
    )
    assert seeded.status_code == 200

    monkeypatch.setenv("ADMIN_METRICS_TOKEN", "test-token-123")
    resp = await client.get(
        "/api/metrics/summary",
        headers={"X-Admin-Token": "test-token-123"},
        params={"days": 7},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["totals"]["sessions"] == 1
    assert data["totals"]["searches"] == 1
    assert data["totals"]["avg_dwell_ms"] == 1500
    assert data["days"] == 7
    by_type = {r["type"]: r["n"] for r in data["by_type"]}
    assert by_type.get("pageview") == 1
    assert by_type.get("search") == 1
