from __future__ import annotations

import json
from typing import Any, Dict, List

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import TextContent, Tool
except Exception as exc:  # pragma: no cover
    raise RuntimeError(
        "Missing 'mcp' package. Install with: pip install mcp"
    ) from exc

import anyio

from .tools import tier0 as t0


server = Server("usd-mcp")


# Define tool registry (name -> (handler, input schema, description))
TOOLS: Dict[str, Any] = {
    "open_stage": (
        t0.tool_open_stage,
        {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False},
        "Open a USD stage from a file path.",
    ),
    "close_stage": (
        t0.tool_close_stage,
        {"type": "object", "properties": {"stage_id": {"type": "string"}}, "required": ["stage_id"], "additionalProperties": False},
        "Close a previously opened stage.",
    ),
    "list_open_stages": (
        t0.tool_list_open_stages,
        {"type": "object", "properties": {}, "additionalProperties": False},
        "List open stages maintained by the server.",
    ),
    "get_stage_summary": (
        t0.tool_get_stage_summary,
        {"type": "object", "properties": {"stage_id": {"type": "string"}}, "required": ["stage_id"], "additionalProperties": False},
        "Summarize layers, roots, timecodes, upAxis, metersPerUnit.",
    ),
    "list_prims": (
        t0.tool_list_prims,
        {
            "type": "object",
            "properties": {
                "stage_id": {"type": "string"},
                "root": {"type": "string", "default": "/"},
                "depth": {"type": "integer", "default": 1},
                "typeFilter": {"type": ["string", "null"]},
            },
            "required": ["stage_id"],
            "additionalProperties": False,
        },
        "List prim paths under a root at limited depth.",
    ),
    "get_prim_info": (
        t0.tool_get_prim_info,
        {
            "type": "object",
            "properties": {"stage_id": {"type": "string"}, "prim_path": {"type": "string"}},
            "required": ["stage_id", "prim_path"],
            "additionalProperties": False,
        },
        "Get type, attrs, rels, metadata for a prim.",
    ),
    "get_attribute_value": (
        t0.tool_get_attribute_value,
        {
            "type": "object",
            "properties": {
                "stage_id": {"type": "string"},
                "prim_path": {"type": "string"},
                "attr": {"type": "string"},
                "time": {"type": ["string", "number"], "default": "default"},
            },
            "required": ["stage_id", "prim_path", "attr"],
            "additionalProperties": False,
        },
        "Read an attribute value at a timeCode or default.",
    ),
    "set_attribute_value": (
        t0.tool_set_attribute_value,
        {
            "type": "object",
            "properties": {
                "stage_id": {"type": "string"},
                "prim_path": {"type": "string"},
                "attr": {"type": "string"},
                "value": {},
                "time": {"type": ["string", "number"], "default": "default"},
            },
            "required": ["stage_id", "prim_path", "attr", "value"],
            "additionalProperties": False,
        },
        "Write an attribute value at a timeCode or default.",
    ),
    "create_stage": (
        t0.tool_create_stage,
        {
            "type": "object",
            "properties": {
                "output_path": {"type": "string"},
                "upAxis": {"type": ["string", "null"]},
                "metersPerUnit": {"type": ["number", "null"]},
            },
            "required": ["output_path"],
            "additionalProperties": False,
        },
        "Create a new USD stage at a path.",
    ),
    "save_stage": (
        t0.tool_save_stage,
        {
            "type": "object",
            "properties": {
                "stage_id": {"type": "string"},
                "output_path": {"type": ["string", "null"]},
                "flatten": {"type": ["boolean", "null"]},
            },
            "required": ["stage_id"],
            "additionalProperties": False,
        },
        "Save the stage (in-place or export to a new file).",
    ),
}


@server.list_tools()
async def _list_tools() -> List[Tool]:
    tools: List[Tool] = []
    for name, (_handler, schema, description) in TOOLS.items():
        tools.append(Tool(name=name, description=description, inputSchema=schema))
    return tools


@server.call_tool()
async def _call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    entry = TOOLS.get(name)
    if not entry:
        return [TextContent(text=json.dumps({"ok": False, "error": {"code": "unknown_tool", "message": name}}))]
    handler = entry[0]
    resp = handler(arguments)
    if not isinstance(resp, dict) or "ok" not in resp:
        return [TextContent(text=json.dumps({"ok": False, "error": {"code": "bad_response", "message": "invalid"}}))]
    if not resp["ok"]:
        return [TextContent(text=json.dumps(resp["error"]))]
    return [TextContent(text=json.dumps(resp.get("result", {})))]


async def _main_async() -> int:
    async with stdio_server() as (read, write):
        await server.run(read, write, initialization_options={})
    return 0


def main() -> int:
    return anyio.run(_main_async)


if __name__ == "__main__":
    raise SystemExit(main())


