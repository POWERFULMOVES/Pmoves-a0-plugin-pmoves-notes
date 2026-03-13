"""
PMOVES.Notes Tool - Search notes in Open Notebook.

This tool allows agents to search the persistent knowledge base.
"""

import os
from typing import Any


def get_notebook_api_url() -> str:
    """Get Open Notebook API URL from environment."""
    return os.getenv("OPEN_NOTEBOOK_API_URL", "http://open-notebook:8000")


def get_notebook_token() -> str:
    """Get Open Notebook API token from environment."""
    token = os.getenv("OPEN_NOTEBOOK_API_TOKEN", "")
    return token if token else ""


class Tool:
    """Tool for searching notes in Open Notebook."""

    @property
    def definition(self):
        return {
            "name": "search_notes",
            "description": "Search PMOVES.AI Open Notebook (persistent knowledge base) for notes",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant notes"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 10
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional filter by tags (e.g., ['research', 'conversation'])"
                    }
                },
                "required": ["query"]
            }
        }

    async def execute(self, **kwargs):
        """Execute the tool - search notes in Open Notebook."""
        import aiohttp

        query = kwargs.get("query", "")
        limit = kwargs.get("limit", 10)
        tags = kwargs.get("tags", [])

        if not query:
            return {
                "success": False,
                "error": "Query is required"
            }

        api_url = get_notebook_api_url()
        token = get_notebook_token()

        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Build search request
        search_params = {
            "query": query,
            "limit": min(limit, 50)  # Cap at 50
        }

        if tags:
            search_params["tags"] = tags

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{api_url}/api/notes/search",
                    params=search_params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        results = await response.json()
                        notes = results.get("results", [])

                        # Publish NATS event
                        try:
                            import nats
                            from datetime import datetime
                            nc = await nats.connect(os.getenv("NATS_URL", "nats://nats:pmoves@nats:4222"))
                            await nc.publish("agent.notes.searched.v1", json.dumps({
                                "query": query,
                                "results_count": len(notes),
                                "timestamp": datetime.utcnow().isoformat()
                            }).encode())
                            await nc.close()
                        except Exception as e:
                            print(f"[PMOVES.Notes] Failed to publish NATS event: {e}")

                        return {
                            "success": True,
                            "query": query,
                            "count": len(notes),
                            "results": [
                                {
                                    "id": note.get("id"),
                                    "title": note.get("title"),
                                    "snippet": note.get("content", "")[:200] + "..." if len(note.get("content", "")) > 200 else note.get("content", ""),
                                    "tags": note.get("tags", []),
                                    "timestamp": note.get("metadata", {}).get("timestamp")
                                }
                                for note in notes
                            ]
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Search failed: {response.status} - {error_text}"
                        }
        except Exception as e:
            return {
                "success": False,
                "error": f"Exception occurred: {str(e)}"
            }
