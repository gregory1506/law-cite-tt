from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

MAX_META_CHARS = 8192
MAX_PATH_CHARS = 512
MAX_UA_CHARS = 512


def events_hash_key() -> str:
    return os.environ.get("EVENTS_HASH_KEY") or "lawcite-dev"


def admin_metrics_token() -> str:
    return os.environ.get("ADMIN_METRICS_TOKEN", "")


def retention_days() -> int:
    try:
        days = int(os.environ.get("ANALYTICS_RETENTION_DAYS", "400"))
    except ValueError:
        days = 400
    return max(1, days)


def hash_ip(ip: str) -> str:
    """One-way, key-salted fingerprint of a client IP. Raw IPs are never stored."""
    if not ip:
        return ""
    digest = hmac.new(
        events_hash_key().encode("utf-8"), ip.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return digest[:24]


def client_ip(
    x_forwarded_for: str | None, x_real_ip: str | None, fallback: str | None
) -> str:
    """First hop of X-Forwarded-For (Traefik) with graceful fallbacks."""
    if x_forwarded_for:
        first = x_forwarded_for.split(",")[0].strip()
        if first:
            return first
    if x_real_ip and x_real_ip.strip():
        return x_real_ip.strip()
    return (fallback or "").strip()


def user_agent(header: str | None) -> str:
    return (header or "")[:MAX_UA_CHARS]


def _meta_json(meta: dict[str, Any]) -> str:
    try:
        text = json.dumps(meta, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        return '{"_unserializable":true}'
    if len(text) > MAX_META_CHARS:
        return json.dumps({"_truncated": True, "keys": list(meta)[:20]})
    return text


async def record_events(pool, *, session_id: str, ip_hash: str, ua: str, events) -> int:
    rows = [
        (
            session_id,
            ev.type,
            (ev.path or "")[:MAX_PATH_CHARS],
            _meta_json(ev.meta),
            ip_hash,
            ua,
        )
        for ev in events
    ]
    async with pool.acquire() as conn:
        await conn.executemany(
            "INSERT INTO events (session_id, type, path, meta, ip_hash, user_agent) "
            "VALUES ($1, $2, $3, $4::jsonb, $5, $6)",
            rows,
        )
    return len(rows)


async def record_chat_exchange(
    pool,
    *,
    session_id: str,
    ip_hash: str,
    ua: str,
    mode: str,
    user_content: str,
    answer: str,
    status: str,
    sources: list,
    latency_ms: int,
) -> None:
    sources_json = json.dumps(sources or [], separators=(",", ":"), default=str)
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_messages "
            "(session_id, role, content, status, sources, mode, latency_ms, ip_hash, user_agent) "
            "VALUES ($1, 'user', $2, '', '[]'::jsonb, $3, 0, $4, $5)",
            session_id,
            user_content,
            mode,
            ip_hash,
            ua,
        )
        await conn.execute(
            "INSERT INTO chat_messages "
            "(session_id, role, content, status, sources, mode, latency_ms, ip_hash, user_agent) "
            "VALUES ($1, 'assistant', $2, $3, $4::jsonb, $5, $6, $7, $8)",
            session_id,
            answer,
            status,
            sources_json,
            mode,
            latency_ms,
            ip_hash,
            ua,
        )


async def purge_old_events(pool, days: int) -> dict:
    """Delete analytics rows older than `days` (retention policy). Returns counts."""
    async with pool.acquire() as conn:
        ev = await conn.execute(
            "DELETE FROM events WHERE created_at < now() - make_interval(days => $1)",
            days,
        )
        cm = await conn.execute(
            "DELETE FROM chat_messages WHERE created_at < now() - make_interval(days => $1)",
            days,
        )
    return {
        "events": int(ev.split()[-1]) if ev else 0,
        "chat_messages": int(cm.split()[-1]) if cm else 0,
    }


async def summarize_usage(pool, days: int) -> dict:
    """Aggregate beta metrics: sessions, feature usage, funnel, chat throughput."""
    async with pool.acquire() as conn:
        daily = await conn.fetch(
            "SELECT to_char(date_trunc('day', created_at), 'YYYY-MM-DD') AS day, "
            "count(*) AS events, count(DISTINCT session_id) AS sessions "
            "FROM events WHERE created_at > now() - make_interval(days => $1) "
            "GROUP BY 1 ORDER BY 1",
            days,
        )
        by_type = await conn.fetch(
            "SELECT type, count(*) AS n FROM events "
            "WHERE created_at > now() - make_interval(days => $1) "
            "GROUP BY 1 ORDER BY n DESC LIMIT 30",
            days,
        )
        top_paths = await conn.fetch(
            "SELECT path, count(*) AS n FROM events "
            "WHERE type = 'pageview' AND created_at > now() - make_interval(days => $1) "
            "GROUP BY 1 ORDER BY n DESC LIMIT 20",
            days,
        )
        totals = await conn.fetchrow(
            "SELECT count(DISTINCT session_id) AS sessions, count(*) AS events, "
            "count(*) FILTER (WHERE type = 'search') AS searches, "
            "count(*) FILTER (WHERE type = 'cite_validate') AS cite_validations, "
            "count(*) FILTER (WHERE type = 'cite_copy') AS cite_copies, "
            "count(*) FILTER (WHERE type = 'atlas_open') AS atlas_opens, "
            "count(*) FILTER (WHERE type = 'dwell') AS dwells, "
            "coalesce(avg((meta->>'ms')::bigint) FILTER (WHERE type = 'dwell'), 0) AS avg_dwell_ms "
            "FROM events WHERE created_at > now() - make_interval(days => $1)",
            days,
        )
        chat = await conn.fetchrow(
            "SELECT count(*) FILTER (WHERE role = 'assistant') AS turns, "
            "count(DISTINCT session_id) AS sessions, "
            "count(*) FILTER (WHERE role = 'assistant' AND status = 'refused') AS refused, "
            "coalesce(avg(latency_ms) FILTER (WHERE role = 'assistant'), 0) AS avg_latency_ms "
            "FROM chat_messages WHERE created_at > now() - make_interval(days => $1)",
            days,
        )
    return {
        "days": days,
        "totals": dict(totals) if totals else {},
        "chat": dict(chat) if chat else {},
        "daily": [dict(r) for r in daily],
        "by_type": [dict(r) for r in by_type],
        "top_paths": [dict(r) for r in top_paths],
    }
