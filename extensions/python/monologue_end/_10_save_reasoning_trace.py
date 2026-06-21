"""PMOVES.Notes extension — save reasoning traces to memory.

Runs at ``monologue_end``. Sources the reasoning text from
``loop_data.last_response`` (the agent's final response for the iteration),
not from a synthetic payload. Persists in a background task so it never blocks
the agent.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from agent import LoopData
from helpers.defer import THREAD_BACKGROUND, DeferredTask
from helpers.extension import Extension
from helpers.print_style import PrintStyle


def _enabled() -> bool:
    return os.getenv("PMOVES_NOTES_ENABLED", "true").lower() == "true"


def _min_length() -> int:
    try:
        return int(os.getenv("PMOVES_NOTES_MIN_REASONING_LENGTH", "100"))
    except (TypeError, ValueError):
        return 100


def _notebook_api_url() -> str:
    return os.getenv("OPEN_NOTEBOOK_API_URL", "http://open-notebook:8000")


def _notebook_token() -> str:
    return os.getenv("OPEN_NOTEBOOK_API_TOKEN", "")


async def _publish_nats_event(subject: str, data: dict[str, Any]) -> None:
    try:
        import nats  # lazy import: optional dependency

        nc = await nats.connect(os.getenv("NATS_URL", "nats://nats:pmoves@nats:4222"))
        try:
            await nc.publish(subject, json.dumps(data).encode())
        finally:
            await nc.close()
    except Exception as exc:  # noqa: BLE001 — best-effort
        PrintStyle(font_color="yellow").print(
            f"[PMOVES.Notes] NATS publish to {subject} failed: {exc}"
        )


async def _save_reasoning_trace(agent_name: str, reasoning: str) -> None:
    stamp = datetime.now(timezone.utc)
    note = {
        "title": f"Reasoning Trace — {agent_name} — {stamp.strftime('%Y-%m-%d %H:%M')}",
        "content": (
            f"# Agent Reasoning Trace\n\n"
            f"**Agent**: {agent_name}\n"
            f"**Timestamp**: {stamp.isoformat()}\n\n"
            f"## Reasoning\n\n{reasoning}\n"
        ),
        "tags": ["reasoning", "trace", agent_name.lower(), "memory"],
        "metadata": {
            "source": "agent-zero-monologue",
            "agent": agent_name,
            "timestamp": stamp.isoformat(),
            "type": "reasoning_trace",
        },
    }

    headers = {"Content-Type": "application/json"}
    token = _notebook_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        import aiohttp  # lazy import

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{_notebook_api_url()}/api/notes",
                json=note,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    detail = await resp.text()
                    PrintStyle(font_color="yellow").print(
                        f"[PMOVES.Notes] reasoning-trace save failed: HTTP {resp.status} — {detail}"
                    )
                    return
                result = await resp.json()
    except Exception as exc:  # noqa: BLE001 — never disturb the agent loop
        PrintStyle(font_color="yellow").print(
            f"[PMOVES.Notes] reasoning-trace error: {exc}"
        )
        return

    await _publish_nats_event(
        "agent.notes.saved.v1",
        {
            "note_id": result.get("id", "unknown"),
            "title": note["title"],
            "tags": ["reasoning", "trace"],
            "timestamp": stamp.isoformat(),
        },
    )


class SaveReasoningTrace(Extension):
    """Save the agent's reasoning trace to Open Notebook after each monologue."""

    async def execute(self, loop_data: LoopData = LoopData(), **kwargs) -> None:
        if not self.agent or not _enabled():
            return

        reasoning = getattr(loop_data, "last_response", "") or ""
        if len(reasoning) < _min_length():
            return

        agent_name = getattr(self.agent, "agent_name", "Agent")
        DeferredTask(thread_name=THREAD_BACKGROUND).start_task(
            _save_reasoning_trace, agent_name, reasoning
        )
