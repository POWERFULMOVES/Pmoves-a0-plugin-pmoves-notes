"""PMOVES.Notes tool — search notes in Open Notebook.

Conforms to the Agent Zero tool API: subclass ``helpers.tool.Tool`` and
implement ``async def execute(...) -> Response``. Discovered by file name
(``tools/search_notes.py`` -> tool name ``search_notes``).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from helpers.print_style import PrintStyle
from helpers.tool import Response, Tool


def _notebook_api_url() -> str:
    return os.getenv("OPEN_NOTEBOOK_API_URL", "http://open-notebook:8000")


def _notebook_token() -> str:
    return os.getenv("OPEN_NOTEBOOK_API_TOKEN", "")


async def publish_nats_event(subject: str, data: dict[str, Any]) -> None:
    """Best-effort NATS publish; never raises into the caller."""
    try:
        import nats  # lazy import: optional dependency

        nc = await nats.connect(os.getenv("NATS_URL", "nats://nats:pmoves@nats:4222"))
        try:
            await nc.publish(subject, json.dumps(data).encode())
        finally:
            await nc.close()
    except Exception as exc:  # noqa: BLE001 — event publishing is best-effort
        PrintStyle(font_color="yellow").print(
            f"[PMOVES.Notes] NATS publish to {subject} failed: {exc}"
        )


class SearchNotes(Tool):
    """Search PMOVES.AI Open Notebook (persistent knowledge base) for notes."""

    async def execute(
        self,
        query: str = "",
        limit: int = 10,
        tags: list[str] | None = None,
        **kwargs,
    ) -> Response:
        query = query if isinstance(query, str) else str(query)
        if not query.strip():
            return Response(
                message="search_notes error: 'query' is required.", break_loop=False
            )

        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 10
        params: dict[str, object] = {"query": query, "limit": min(max(limit, 1), 50)}
        if isinstance(tags, (list, tuple)) and tags:
            params["tags"] = list(tags)

        headers = {"Content-Type": "application/json"}
        token = _notebook_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            import aiohttp  # lazy import: keeps import errors out of tool discovery

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{_notebook_api_url()}/api/notes/search",
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        detail = await resp.text()
                        return Response(
                            message=f"search_notes failed: HTTP {resp.status} — {detail}",
                            break_loop=False,
                        )
                    results = await resp.json()
        except Exception as exc:  # noqa: BLE001 — surface as tool message, never crash loop
            return Response(message=f"search_notes error: {exc}", break_loop=False)

        notes = results.get("results", []) if isinstance(results, dict) else []
        summary = [
            {
                "id": n.get("id"),
                "title": n.get("title"),
                "snippet": (
                    (n.get("content", "")[:200] + "...")
                    if len(n.get("content", "")) > 200
                    else n.get("content", "")
                ),
                "tags": n.get("tags", []),
                "timestamp": n.get("metadata", {}).get("timestamp"),
            }
            for n in notes
        ]

        await publish_nats_event(
            "agent.notes.searched.v1",
            {
                "query": query,
                "results_count": len(notes),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        body = json.dumps({"query": query, "count": len(notes), "results": summary}, indent=2)
        return Response(message=f"search_notes results:\n{body}", break_loop=False)
