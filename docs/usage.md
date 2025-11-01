Usage / Quickstart
==================

Local server
- Start the server (stdin/stdout JSON):
  - `usd-mcp serve`

Calling tools
- The server accepts one JSON object per line on stdin. Example request lines:
  - `{"method": "create_stage", "params": {"output_path": "/tmp/new.usda", "upAxis": "Y", "metersPerUnit": 0.01}}`
  - `{"method": "get_stage_summary", "params": {"stage_id": "<id>"}}`
  - `{"method": "save_stage", "params": {"stage_id": "<id>"}}`

Client helper
- A tiny client is available for echo testing while developing:
  - `echo '{"hello": "world"}' | usd-mcp client`
  - This will be extended to invoke local tools in a future iteration.

Examples
- See `examples/minimal_read.py` and `examples/create_stage.py`.


