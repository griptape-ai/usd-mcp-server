Test locally with MCP Inspector
==============================

Prereqs
- Activate your venv and install deps:
  - `python3 -m venv .venv && source .venv/bin/activate`
  - `pip install -U -e .`
  - `pip install "usd-core==25.11"`

Config
- Ensure `mcp.json` exists at the repo root. Example using the `usd-mcp` entrypoint:

```json
{
  "mcpServers": {
    "usd-mcp": {
      "transport": "stdio",
      "command": "/Users/kyleroche/Documents/Development/usd-mcp/.venv/bin/usd-mcp",
      "args": ["mcp-serve"],
      "env": { "PYTHONUNBUFFERED": "1" }
    }
  }
}
```

Alternative (more robust to PATH issues):

```json
{
  "mcpServers": {
    "usd-mcp": {
      "transport": "stdio",
      "command": "/Users/kyleroche/Documents/Development/usd-mcp/.venv/bin/python",
      "args": ["-m", "usd_mcp.mcp_server"],
      "env": { "PYTHONUNBUFFERED": "1" }
    }
  }
}
```

Run Inspector
- From the repo root:
  - `npx -y @modelcontextprotocol/inspector --config ./mcp.json --server usd-mcp`

Try a few calls in Inspector
- Example request lines (stdin JSON):
  - `{"method": "create_stage", "params": {"output_path": "/tmp/inspector_test.usda", "upAxis": "Y", "metersPerUnit": 0.01}}`
  - `{"method": "list_open_stages", "params": {}}`
  - `{"method": "save_stage", "params": {"stage_id": "<id>"}}`

Troubleshooting
- `missing_usd`: install `pip install "usd-core==25.11"` in the same venv.
- PATH issues: prefer the python `-m usd_mcp.mcp_server` config variant with absolute paths.
- Stale code: `pip uninstall -y usd-mcp && pip install -U -e .` then re-run Inspector.

Back: [Docs Index](README.md)


