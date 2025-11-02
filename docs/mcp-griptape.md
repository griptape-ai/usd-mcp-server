MCP with Griptape Nodes (Local stdio)
=====================================

Prereqs
- In your venv: `pip install -e .` and `pip install "usd-core==25.11"`
- Also install MCP SDK (installed via project deps): `pip show mcp`

Start command
- Use the dedicated MCP entry: `usd-mcp mcp-serve`

WebSocket server (persistent sessions)
- Start: `usd-mcp ws-serve --host 127.0.0.1 --port 8765`
- Griptape configuration (WebSocket):

```json
{
  "transport": "websocket",
  "url": "ws://127.0.0.1:8765/ws"
}
```

SSE (optional, if your stack expects SSE)
- This server focuses on WebSocket and stdio; SSE may be added later.

Griptape configuration (JSON)
Paste this in the New MCP Server modal (Connection Type: Local Process (stdio)):

```json
{
  "transport": "stdio",
  "command": "/Users/kyleroche/Documents/Development/usd-mcp/.venv/bin/usd-mcp",
  "args": ["mcp-serve"],
  "env": {
    "PYTHONUNBUFFERED": "1"
  },
  "encoding": "utf-8",
  "encoding_error_handler": "strict"
}
```

Alternative (more robust to PATH issues):

```json
{
  "transport": "stdio",
  "command": "/Users/kyleroche/Documents/Development/usd-mcp/.venv/bin/python",
  "args": ["-m", "usd_mcp.mcp_server"],
  "env": {
    "PYTHONUNBUFFERED": "1"
  },
  "encoding": "utf-8",
  "encoding_error_handler": "strict"
}
```

Notes
- The server exposes Tier 0 tools: open/close/list stages, stage summary, list prims, prim info, get/set attribute, create/save stage.
- Ensure the absolute paths match your machine/venv.
- If pxr is missing the server will respond with a `missing_usd` error; install `usd-core` in the same venv.


Back: [Docs Index](README.md)

