"""
PMOVES.Notes Extension - Auto-save conversation summaries.

This extension runs at message_loop_end to automatically save conversation
summaries to Open Notebook (SurrealDB knowledge base).
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
    if not token:
        # For development, allow empty token
        return ""
    return token


async def publish_nats_event(subject: str, data: Dict[str, Any]) -> None:
    """Publish event to NATS."""
    try:
        import nats
        nc = await nats.connect(os.getenv("NATS_URL", "nats://nats:pmoves@nats:4222"))
        await nc.publish(subject, json.dumps(data).encode())
        await nc.close()
    except Exception as e:
        # Log but don't fail the extension
        print(f"[PMOVES.Notes] Failed to publish NATS event: {e}")


async def save_conversation_summary(
    title: str,
    content: str,
    tags: list = None,
    metadata: dict = None
) -> Dict[str, Any]:
    """Save conversation summary to Open Notebook."""
    import aiohttp

    api_url = get_notebook_api_url()
    token = get_notebook_token()

    # Prepare the note payload
    note = {
        "title": title,
        "content": content,
        "tags": tags or ["conversation", "auto-saved"],
        "metadata": {
            **(metadata or {}),
            "source": "agent-zero",
            "timestamp": datetime.utcnow().isoformat(),
            "agent": "pmoves-notes-plugin"
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
                print(f"[PMOVES.Notes] Saved conversation summary: {title}")
                return result
            else:
                error_text = await response.text()
                print(f"[PMOVES.Notes] Failed to save note: {response.status} - {error_text}")
                return {"error": error_text}


class Extension:
    """PMOVES.Notes extension for auto-saving conversation summaries."""

    def __init__(self):
        self.enabled = os.getenv("PMOVES_NOTES_ENABLED", "true").lower() == "true"

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the extension at message_loop_end.

        Expected input_data keys:
        - messages: List of conversation messages
        - agent_name: Name of the current agent
        - user_input: Latest user message
        - assistant_response: Latest assistant response
        """
        if not self.enabled:
            return input_data

        try:
            messages = input_data.get("messages", [])
            agent_name = input_data.get("agent_name", "Agent")

            if not messages:
                return input_data

            # Generate summary from recent messages
            recent_messages = messages[-10:] if len(messages) > 10 else messages

            # Create title from first user message or agent name
            title = None
            for msg in recent_messages:
                if msg.get("role") == "user":
                    title = msg.get("content", "")[:60] + "..." if len(msg.get("content", "")) > 60 else msg.get("content", "")
                    break

            if not title:
                title = f"Conversation with {agent_name}"

            # Build content from conversation
            content_parts = []
            for msg in recent_messages:
                role = msg.get("role", "unknown").capitalize()
                content = msg.get("content", "")
                content_parts.append(f"**{role}**: {content}")

            content = "\n\n".join(content_parts)

            # Extract any reasoning traces (monologue) if present
            metadata = {
                "message_count": len(messages),
                "agent_name": agent_name
            }

            # Save to Open Notebook
            result = await save_conversation_summary(
                title=title,
                content=content,
                tags=["conversation", "auto-saved", agent_name.lower()],
                metadata=metadata
            )

            # Publish NATS event
            if "error" not in result:
                await publish_nats_event("agent.notes.saved.v1", {
                    "note_id": result.get("id", "unknown"),
                    "title": title,
                    "tags": ["conversation", "auto-saved"],
                    "timestamp": datetime.utcnow().isoformat()
                })

        except Exception as e:
            # Don't fail the message loop on error
            print(f"[PMOVES.Notes] Extension error: {e}")

        return input_data
