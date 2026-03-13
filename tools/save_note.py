"""
PMOVES.Notes Tool - Save a note to Open Notebook.

This tool allows agents to manually save notes to the persistent knowledge base.
"""

import json
import os
from datetime import datetime
from typing import Any


def get_notebook_api_url() -> str:
    """Get Open Notebook API URL from environment."""
    return os.getenv("OPEN_NOTEBOOK_API_URL", "http://open-notebook:8000")


def get_notebook_token() -> str:
    """Get Open Notebook API token from environment."""
    token = os.getenv("OPEN_NOTEBOOK_API_TOKEN", "")
    return token if token else ""


class Tool:
    """Tool for saving notes to Open Notebook."""

    @property
    def definition(self):
        return {
            "name": "save_note",
            "description": "Save a note to PMOVES.AI Open Notebook (persistent knowledge base)",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The note content to save"
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional title for the note (defaults to first line of content)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional tags for categorization (e.g., ['research', 'todo'])"
                    }
                },
                "required": ["content"]
            }
        }

    async def execute(self, **kwargs):
        """Execute the tool - save note to Open Notebook."""
        import aiohttp

        content = kwargs.get("content", "")
        title = kwargs.get("title", "")
        tags = kwargs.get("tags", [])

        if not content:
            return {
                "success": False,
                "error": "Content is required"
            }

        # Generate title from content if not provided
        if not title:
            first_line = content.split("\n")[0]
            title = first_line[:60] + "..." if len(first_line) > 60 else first_line

        api_url = get_notebook_api_url()
        token = get_notebook_token()

        note = {
            "title": title,
            "content": content,
            "tags": tags + ["agent-created"],
            "metadata": {
                "source": "agent-zero-tool",
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{api_url}/api/notes",
                    json=note,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        # Publish NATS event
                        try:
                            import nats
                            nc = await nats.connect(os.getenv("NATS_URL", "nats://nats:pmoves@nats:4222"))
                            await nc.publish("agent.notes.saved.v1", json.dumps({
                                "note_id": result.get("id", "unknown"),
                                "title": title,
                                "tags": tags,
                                "timestamp": datetime.utcnow().isoformat()
                            }).encode())
                            await nc.close()
                        except Exception as e:
                            print(f"[PMOVES.Notes] Failed to publish NATS event: {e}")

                        return {
                            "success": True,
                            "note_id": result.get("id"),
                            "title": title,
                            "message": f"Note saved successfully with ID: {result.get('id')}"
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Failed to save note: {response.status} - {error_text}"
                        }
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception occurred: {str(e)}"
            }
