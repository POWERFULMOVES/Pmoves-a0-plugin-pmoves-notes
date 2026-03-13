# a0-plugin-pmoves-notes

**Persistent note-taking integration for Agent Zero with PMOVES.AI Open Notebook.**

## Overview

This plugin enables Agent Zero to automatically save conversation summaries and reasoning traces to PMOVES.AI's persistent knowledge base (Open Notebook / SurrealDB). It provides tools for manual note management and publishes events to NATS for coordination with other services.

## Features

- **Auto-save conversation summaries** after each message loop
- **Save reasoning traces** from agent monologues to persistent memory
- **Manual note tools** (`save_note`, `search_notes`) for agent-controlled notes
- **NATS event publishing** for note operations
- **Tag-based categorization** for easy retrieval
- **Full PMOVES.AI integration** (TensorZero, NATS, Open Notebook)

## Installation

### Via PMOVES-a0-plugins Index

1. Ensure the plugin is indexed in `PMOVES-a0-plugins/plugins/pmoves-notes-integration/`
2. Agent Zero will automatically discover and install it

### Manual Installation

```bash
# Clone this repository
git clone https://github.com/POWERFULMOVES/a0-plugin-pmoves-notes.git

# Copy to Agent Zero extensions directory
cp -r a0-plugin-pmoves-notes/extensions/* PMOVES-Agent-Zero/python/extensions/
cp -r a0-plugin-pmoves-notes/tools/* PMOVES-Agent-Zero/python/tools/
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|-----------|---------|-------------|
| `OPEN_NOTEBOOK_API_URL` | No | `http://open-notebook:8000` | Open Notebook API endpoint |
| `OPEN_NOTEBOOK_API_TOKEN` | No | | API token for authentication |
| `NATS_URL` | No | `nats://nats:pmoves@nats:4222` | NATS connection URL |
| `PMOVES_NOTES_ENABLED` | No | `true` | Enable/disable plugin |
| `PMOVES_NOTES_MIN_REASONING_LENGTH` | No | `100` | Min reasoning length to save |

### Docker Compose Example

```yaml
services:
  agent-zero:
    image: ghcr.io/powerfulmoves/pmoves-agent-zero:pmoves-latest
    environment:
      - OPEN_NOTEBOOK_API_URL=http://open-notebook:8000
      - OPEN_NOTEBOOK_API_TOKEN=${OPEN_NOTEBOOK_TOKEN}
      - NATS_URL=nats://nats:pmoves@nats:4222
      - PMOVES_NOTES_ENABLED=true
    depends_on:
      - open-notebook
      - nats
```

## Extension Points

### message_loop_end (Priority: 10)

Automatically saves conversation summaries after each message loop.

**Captures:**
- Recent messages (last 10)
- Agent name
- Conversation context

**Tags applied:** `conversation`, `auto-saved`, `<agent_name>`

### monologue_end (Priority: 10)

Saves agent reasoning traces to persistent memory.

**Captures:**
- Monologue/reasoning text
- Agent name
- Tool usage
- Input context

**Tags applied:** `reasoning`, `trace`, `<agent_name>`, `memory`

## Tools

### save_note

Manually save a note to Open Notebook.

```python
{
  "content": "Important finding from research...",
  "title": "Research Notes 2026-03-13",
  "tags": ["research", "findings"]
}
```

**Parameters:**
- `content` (required): Note content
- `title` (optional): Note title
- `tags` (optional): List of tags

**Returns:** Note ID and confirmation

### search_notes

Search the knowledge base for relevant notes.

```python
{
  "query": "Agent Zero integration patterns",
  "limit": 10,
  "tags": ["documentation"]
}
```

**Parameters:**
- `query` (required): Search query
- `limit` (optional): Max results (default: 10)
- `tags` (optional): Filter by tags

**Returns:** List of matching notes with snippets

## NATS Events

### agent.notes.saved.v1

Published when a note is created or updated.

```json
{
  "note_id": "uuid",
  "title": "Note Title",
  "tags": ["tag1", "tag2"],
  "timestamp": "2026-03-13T14:00:00Z"
}
```

### agent.notes.searched.v1

Published when a note search is performed.

```json
{
  "query": "search term",
  "results_count": 5,
  "timestamp": "2026-03-13T14:00:00Z"
}
```

## PMOVES.AI Integration

This plugin follows PMOVES.AI integration patterns:

1. **TensorZero**: Uses TensorZero format for any LLM calls (if added)
2. **NATS**: Authenticated NATS URL (`nats://nats:pmoves@nats:4222`)
3. **Open Notebook**: Connects to SurrealDB knowledge base at port 8000
4. **Security**: No hardcoded credentials; uses environment variables
5. **Observability**: Publishes events for service mesh monitoring

## Usage Example

```python
# In Agent Zero, the plugin automatically saves conversations

# User: "Research PMOVES.AI integration patterns"
# Agent: [Reasoning...] [Saves reasoning trace via monologue_end extension]
# Agent: [Provides answer]
# [Message loop ends → Auto-saves conversation summary via message_loop_end extension]

# Agent can also manually save notes
# Agent: Let me save that important finding to my notes.
# [Calls save_note tool]

# Agent can search existing knowledge
# Agent: Let me check what I know about TensorZero integration.
# [Calls search_notes tool]
```

## Development

### Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run with coverage
pytest --cov=extensions --cov=tools
```

### Docker Build

```bash
# Build the plugin image
docker build -t a0-plugin-pmoves-notes:test .

# Test with Agent Zero
docker run --rm -v $(pwd):/plugin \
  -e OPEN_NOTEBOOK_API_URL=http://host.docker.internal:8000 \
  a0-plugin-pmoves-notes:test
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow PMOVES.AI security patterns
4. Add tests for new features
5. Submit a PR

## License

MIT License - see LICENSE file for details

## Author

POWERFULMOVES

## See Also

- [PMOVES.AI Documentation](https://github.com/POWERFULMOVES/PMOVES.AI)
- [Agent Zero Documentation](https://github.com/POWERFULMOVES/PMOVES-Agent-Zero)
- [PMOVES-a0-plugins Index](https://github.com/POWERFULMOVES/PMOVES-a0-plugins)
- [Open Notebook](https://github.com/POWERFULMOVES/PMOVES-Open-Notebook)
