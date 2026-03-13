"""
PMOVES.Notes Extension - Save reasoning traces to memory.

This extension runs at monologue_end to save agent reasoning traces
to persistent memory via Open Notebook.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict


def get_notebook_api_url() -> str:
    """Get Open Notebook API URL from environment."""
    return os.getenv("OPEN_NOTEBOOK_API_URL", "http://open-notebook:8000")


def get_notebook_token() -> str:
    """Get Open Notebook API token from environment."""
    token = os.getenv("OPEN_NOTEBOOK_API_TOKEN", "")
    return token if token else ""


async def save_reasoning_trace(
    agent_name: str,
    reasoning: str,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Save reasoning trace to Open Notebook memory."""
    import aiohttp

    api_url = get_notebook_api_url()
    token = get_notebook_token()

    # Create a structured note for the reasoning trace
    note = {
        "title": f"Reasoning Trace - {agent_name} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
        "content": f"""# Agent Reasoning Trace

**Agent**: {agent_name}
**Timestamp**: {datetime.utcnow().isoformat()}

## Reasoning

{reasoning}

## Context

{json.dumps(context or {}, indent=2)}
""",
        "tags": ["reasoning", "trace", agent_name.lower(), "memory"],
        "metadata": {
            "source": "agent-zero-monologue",
            "agent": agent_name,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "reasoning_trace"
        }
    }

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{api_url}/api/notes",
            json=note,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as response:
            if response.status == 200:
                result = await response.json()
                print(f"[PMOVES.Notes] Saved reasoning trace for {agent_name}")
                return result
            else:
                error_text = await response.text()
                print(f"[PMOVES.Notes] Failed to save reasoning trace: {response.status} - {error_text}")
                return {"error": error_text}


class Extension:
    """PMOVES.Notes extension for saving reasoning traces."""

    def __init__(self):
        self.enabled = os.getenv("PMOVES_NOTES_ENABLED", "true").lower() == "true"
        self.min_length = int(os.getenv("PMOVES_NOTES_MIN_REASONING_LENGTH", "100"))

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the extension at monologue_end.

        Expected input_data keys:
        - monologue: The reasoning/monologue text
        - agent_name: Name of the current agent
        - context: Additional context about the reasoning
        """
        if not self.enabled:
            return input_data

        try:
            monologue = input_data.get("monologue", "")
            agent_name = input_data.get("agent_name", "Agent")

            # Only save if monologue is substantial enough
            if len(monologue) < self.min_length:
                return input_data

            # Save reasoning trace
            result = await save_reasoning_trace(
                agent_name=agent_name,
                reasoning=monologue,
                context={
                    "input": input_data.get("input", ""),
                    "tools_used": input_data.get("tools_used", []),
                    "step_count": input_data.get("step_count", 0)
                }
            )

        except Exception as e:
            # Don't fail the monologue on error
            print(f"[PMOVES.Notes] Reasoning trace error: {e}")

        return input_data
