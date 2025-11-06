from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Dict, List

import anyio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .tools import tier0 as t0
from .tools import tier2 as t2
from .tools import tier3 as t3
from .version import __version__

server = Server("usd-mcp")


def _normalize_args(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    # Coerce list-shaped inputs into a dict when possible
    if isinstance(args, list):
        if len(args) == 1 and isinstance(args[0], dict):
            args = args[0]
        elif all(isinstance(x, dict) for x in args):
            merged: Dict[str, Any] = {}
            for x in args:
                merged.update(x)
            args = merged
        else:
            args = {}

    # Unwrap common wrappers like {"values": {...}} potentially nested
    while (
        isinstance(args, dict)
        and set(args.keys()) == {"values"}
        and isinstance(args.get("values"), dict)
    ):
        args = args["values"]

    def key_fingerprint(key: str) -> str:
        return key.replace("_", "").replace(" ", "").lower()

    synonyms: Dict[str, list[str]] = {
        "path": ["path", "Path"],
        "stage_id": ["stage_id", "stageId", "Stage Id", "stage id", "StageID"],
        "prim_path": ["prim_path", "primPath", "Prim Path"],
        "attr": ["attr", "attribute", "Attr", "Attribute"],
        "output_path": ["output_path", "outputPath", "Output Path"],
        "root": ["root", "Root"],
        "typeFilter": ["typeFilter", "type_filter", "Type Filter", "type"],
        "time": ["time", "Time"],
        "flatten": ["flatten", "Flatten"],
        "clearExisting": ["clearExisting", "clear_existing", "Clear Existing"],
        # Allow common variants for batch items, but DO NOT remap 'ops'
        "items": ["items", "updates", "changes"],
    }

    fingerprint_to_canonical: Dict[str, str] = {}
    for canonical, alts in synonyms.items():
        for alt in alts:
            fingerprint_to_canonical[key_fingerprint(alt)] = canonical

    normalized: Dict[str, Any] = {}
    for k, v in (args or {}).items():
        if isinstance(k, str):
            fp = key_fingerprint(k)
            canonical = fingerprint_to_canonical.get(fp, k)
            normalized[canonical] = v
        else:
            normalized[k] = v

    return normalized


# Define tool registry (name -> (handler, input schema, description))
TOOLS: Dict[str, Any] = {
    "open_stage": (
        t0.tool_open_stage,
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "additionalProperties": True,
        },
        "Open a USD stage from a file path.",
    ),
    # Tier 3 - variants
    "list_variants_in_file": (
        t3.tool_list_variants_in_file,
        {
            "type": "object",
            "properties": {"path": {"type": "string"}, "prim_path": {"type": "string"}},
            "additionalProperties": True,
        },
        "Stateless: list variant sets and selections.",
    ),
    "set_variant_in_file": (
        t3.tool_set_variant_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "prim_path": {"type": "string"},
                "set": {"type": "string"},
                "selection": {},
            },
            "additionalProperties": True,
        },
        "Stateless: set variant selection and save.",
    ),
    # Materials
    "list_materials_in_file": (
        t3.tool_list_materials_in_file,
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "additionalProperties": True,
        },
        "Stateless: list UsdShade.Material prims.",
    ),
    "bind_material_in_file": (
        t3.tool_bind_material_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "prim_path": {"type": "string"},
                "material_path": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "Stateless: bind a material and save.",
    ),
    "unbind_material_in_file": (
        t3.tool_unbind_material_in_file,
        {
            "type": "object",
            "properties": {"path": {"type": "string"}, "prim_path": {"type": "string"}},
            "additionalProperties": True,
        },
        "Stateless: unbind all materials and save.",
    ),
    "get_material_binding_in_file": (
        t3.tool_get_material_binding_in_file,
        {
            "type": "object",
            "properties": {"path": {"type": "string"}, "prim_path": {"type": "string"}},
            "additionalProperties": True,
        },
        "Stateless: get currently bound material (path or null) and binding rel info.",
    ),
    # Cameras
    "list_cameras_in_file": (
        t3.tool_list_cameras_in_file,
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "additionalProperties": True,
        },
        "Stateless: list cameras.",
    ),
    "get_camera_in_file": (
        t3.tool_get_camera_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "camera_path": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "Stateless: get camera parameters.",
    ),
    "set_camera_in_file": (
        t3.tool_set_camera_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "camera_path": {"type": "string"},
                "params": {"type": "object", "additionalProperties": True},
            },
            "additionalProperties": True,
        },
        "Stateless: set camera parameters and save.",
    ),
    # Bounds
    "get_bounds_in_file": (
        t3.tool_get_bounds_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "prim_path": {"type": "string"},
                "time": {"type": ["string", "number"], "default": "default"},
            },
            "additionalProperties": True,
        },
        "Stateless: compute world-space AABB.",
    ),
    # Export / Validate
    "export_usd_file": (
        t3.tool_export_usd_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "output_path": {"type": "string"},
                "flatten": {"type": ["boolean", "null"]},
                "skipIfExists": {"type": ["boolean", "null"]},
            },
            "additionalProperties": True,
        },
        "Export to USD file (optionally flattened). If skipIfExists is true and output exists, returns {skipped:true}.",
    ),
    "export_usdz_file": (
        t3.tool_export_usdz_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "output_path": {"type": "string"},
            },
            "additionalProperties": True,
        },
        "Export to USDZ archive.",
    ),
    "validate_stage_file": (
        t3.tool_validate_stage_file,
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "additionalProperties": True,
        },
        "Validate stage and return issues.",
    ),
    # Composition helpers
    "add_reference_in_file": (
        t3.tool_add_reference_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "prim_path": {"type": "string"},
                "asset_path": {"type": "string"},
                "internal_path": {"type": ["string", "null"]},
            },
            "additionalProperties": True,
        },
        "Add a reference to a prim and save.",
    ),
    "add_sublayer_in_file": (
        t3.tool_add_sublayer_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "sublayer": {"type": "string"},
                "insert_index": {"type": ["integer", "string", "null"]},
            },
            "additionalProperties": True,
        },
        "Append or insert a sublayer into the root layer and save.",
    ),
    "set_default_prim_in_file": (
        t3.tool_set_default_prim_in_file,
        {
            "type": "object",
            "properties": {"path": {"type": "string"}, "prim_path": {"type": "string"}},
            "required": ["path", "prim_path"],
            "additionalProperties": True,
        },
        "Set stage defaultPrim to an existing prim path and save.",
    ),
    "add_references_batch_in_file": (
        t3.tool_add_references_batch_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "prim_path": {"type": "string"},
                            "asset_path": {"type": "string"},
                            "internal_path": {"type": ["string", "null"]},
                        },
                        "required": ["prim_path", "asset_path"],
                        "additionalProperties": True,
                    },
                },
            },
            "required": ["path", "items"],
            "additionalProperties": True,
        },
        "Batch: add multiple references and save once.",
    ),
    "compose_referenced_assembly": (
        t3.tool_compose_referenced_assembly,
        {
            "type": "object",
            "properties": {
                "output_path": {"type": "string"},
                "assets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "asset_path": {"type": "string"},
                            "name": {"type": ["string", "null"]},
                            "internal_path": {"type": ["string", "null"]},
                        },
                        "required": ["asset_path"],
                        "additionalProperties": True,
                    },
                },
                "container_root": {"type": ["string", "null"]},
                "flatten": {"type": ["boolean", "null"]},
                "upAxis": {"type": ["string", "null"]},
                "setDefaultPrim": {"type": ["boolean", "null"]},
                "skipIfExists": {"type": ["boolean", "null"]},
                "clearExisting": {"type": ["boolean", "null"]},
            },
            "required": ["output_path", "assets"],
            "additionalProperties": True,
        },
        "Compose an assembly by ensuring stage and adding references under a container root; resolves defaultPrim for internal paths and optionally flattens USDZ to USDA. Set clearExisting=true to clear all root prims before composing, or false (default) to append to existing stage.",
    ),
    "summarize_file": (
        t0.tool_summarize_file,
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "additionalProperties": True,
        },
        "Open a USD file temporarily and return a summary (no state).",
    ),
    "close_stage": (
        t0.tool_close_stage,
        {
            "type": "object",
            "properties": {"stage_id": {"type": "string"}},
            "required": ["stage_id"],
            "additionalProperties": False,
        },
        "Close a previously opened stage.",
    ),
    "list_open_stages": (
        t0.tool_list_open_stages,
        {"type": "object", "properties": {}, "additionalProperties": True},
        "List open stages maintained by the server.",
    ),
    "get_stage_summary": (
        t0.tool_get_stage_summary,
        {
            "type": "object",
            "properties": {"stage_id": {"type": "string"}},
            "additionalProperties": True,
        },
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
    "list_prims_in_file": (
        t0.tool_list_prims_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "root": {"type": "string", "default": "/"},
                "depth": {"type": "integer", "default": 1},
                "typeFilter": {"type": ["string", "null"]},
            },
            "required": ["path"],
            "additionalProperties": True,
        },
        "Open a USD file and list prim paths (stateless).",
    ),
    "get_prim_info": (
        t0.tool_get_prim_info,
        {
            "type": "object",
            "properties": {
                "stage_id": {"type": "string"},
                "prim_path": {"type": "string"},
            },
            "required": ["stage_id", "prim_path"],
            "additionalProperties": False,
        },
        "Get type, attrs, rels, metadata for a prim.",
    ),
    "get_prim_info_in_file": (
        t0.tool_get_prim_info_in_file,
        {
            "type": "object",
            "properties": {"path": {"type": "string"}, "prim_path": {"type": "string"}},
            "additionalProperties": True,
        },
        "Stateless: get prim info from a file path.",
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
    "get_attribute_value_in_file": (
        t0.tool_get_attribute_value_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "prim_path": {"type": "string"},
                "attr": {"type": "string"},
                "time": {"type": ["string", "number"], "default": "default"},
            },
            "additionalProperties": True,
        },
        "Stateless: read an attribute value from a file path.",
    ),
    "set_attribute_value_in_file": (
        t0.tool_set_attribute_value_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "prim_path": {"type": "string"},
                "attr": {"type": "string"},
                "value": {
                    "type": ["string", "number", "boolean", "array", "object", "null"]
                },
                "time": {"type": ["string", "number"], "default": "default"},
            },
            "additionalProperties": True,
        },
        "Stateless: write an attribute value and save in place.",
    ),
    "batch_set_attributes_in_file": (
        t0.tool_batch_set_attribute_values_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "prim_path": {"type": "string"},
                            "attr": {"type": "string"},
                            "value": {
                                "type": [
                                    "string",
                                    "number",
                                    "boolean",
                                    "array",
                                    "object",
                                    "null",
                                ]
                            },
                            "time": {"type": ["string", "number"]},
                        },
                        "required": ["prim_path", "attr"],
                        "additionalProperties": True,
                    },
                },
            },
            "required": ["path", "items"],
            "additionalProperties": True,
        },
        "Stateless: batch set attribute values and save once.",
    ),
    "set_attribute_value": (
        t0.tool_set_attribute_value,
        {
            "type": "object",
            "properties": {
                "stage_id": {"type": "string"},
                "prim_path": {"type": "string"},
                "attr": {"type": "string"},
                "value": {
                    "type": ["string", "number", "boolean", "array", "object", "null"]
                },
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
    # Tier 2 - stateless authoring & transforms
    "create_prim_in_file": (
        t2.tool_create_prim_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "prim_path": {"type": "string"},
                "type_name": {"type": ["string", "null"]},
                "specifier": {"type": ["string", "null"]},
            },
            "additionalProperties": True,
        },
        "Stateless: create a prim and save.",
    ),
    "delete_prim_in_file": (
        t2.tool_delete_prim_in_file,
        {
            "type": "object",
            "properties": {"path": {"type": "string"}, "prim_path": {"type": "string"}},
            "additionalProperties": True,
        },
        "Stateless: delete a prim and save.",
    ),
    "get_xform_in_file": (
        t2.tool_get_xform_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "prim_path": {"type": "string"},
                "time": {"type": ["string", "number"], "default": "default"},
            },
            "additionalProperties": True,
        },
        "Stateless: get local/world matrices and xformOps.",
    ),
    "set_xform_in_file": (
        t2.tool_set_xform_in_file,
        {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "prim_path": {"type": "string"},
                "time": {"type": ["string", "number"], "default": "default"},
                "ops": {"type": ["array", "null"]},
                "matrix": {
                    "type": ["array", "null"],
                    "items": {"type": "array", "items": {"type": "number"}},
                },
            },
            "additionalProperties": True,
        },
        "Stateless: set xform via ops or 4x4 matrix and save.",
    ),
}


# Provide camelCase aliases for clients that restrict tool names to letters/numbers
def _to_camel(name: str) -> str:
    parts = name.split("_")
    if not parts:
        return name
    head, tail = parts[0], parts[1:]
    return head + "".join(p[:1].upper() + p[1:] for p in tail)


_aliases: Dict[str, Any] = {}
for _name, _entry in list(TOOLS.items()):
    if "_" in _name:
        _camel = _to_camel(_name)
        if _camel not in TOOLS:
            _handler, _schema, _desc = _entry
            _aliases[_camel] = (_handler, _schema, f"{_desc} (alias)")

if _aliases:
    TOOLS.update(_aliases)

# Add short, alphanumeric-friendly aliases to guide clients
_short_aliases = {
    "open_stage": ["open"],
    "close_stage": ["close"],
    "list_open_stages": ["listStages"],
    "get_stage_summary": ["stageSummary"],
    "list_prims": ["listPrims"],
    "get_prim_info": ["primInfo"],
    "get_attribute_value": ["getAttr"],
    "set_attribute_value": ["setAttr"],
    "create_stage": ["create"],
    "save_stage": ["save"],
    "summarize_file": ["summarizeFile"],
    "list_prims_in_file": ["listPrimsFile"],
    "get_prim_info_in_file": ["primInfoFile"],
    "get_attribute_value_in_file": ["getAttrFile"],
    "set_attribute_value_in_file": ["setAttrFile"],
    "batch_set_attributes_in_file": ["setAttrsFile", "batchSetAttrsFile"],
    "create_prim_in_file": ["createPrimFile"],
    "delete_prim_in_file": ["deletePrimFile"],
    "get_xform_in_file": ["getXformFile"],
    "set_xform_in_file": ["setXformFile"],
    "list_variants_in_file": ["listVariantsFile"],
    "set_variant_in_file": ["setVariantFile"],
    "list_materials_in_file": ["listMaterialsFile"],
    "bind_material_in_file": ["bindMaterialFile"],
    "unbind_material_in_file": ["unbindMaterialFile"],
    "list_cameras_in_file": ["listCamerasFile"],
    "get_camera_in_file": ["getCameraFile"],
    "set_camera_in_file": ["setCameraFile"],
    "get_bounds_in_file": ["getBoundsFile"],
    "export_usd_file": ["exportUsdFile"],
    "export_usdz_file": ["exportUsdzFile"],
    "validate_stage_file": ["validateStageFile"],
    "add_reference_in_file": ["addReferenceInFile"],
    "add_sublayer_in_file": ["addSublayerInFile"],
    "set_default_prim_in_file": ["setDefaultPrimFile"],
    "add_references_batch_in_file": ["addReferencesBatchInFile"],
    "compose_referenced_assembly": ["composeReferencedAssembly"],
}

for _name, _alts in _short_aliases.items():
    if _name in TOOLS:
        _handler, _schema, _desc = TOOLS[_name]
        for _alias in _alts:
            if _alias not in TOOLS:
                TOOLS[_alias] = (_handler, _schema, f"{_desc} (alias)")

# Optionally disable older composition tools to reduce agent confusion
_DISABLED_NAMES = {
    "add_reference_in_file",
    "addReferenceInFile",
    "add_sublayer_in_file",
    "addSublayerInFile",
}
for _n in list(TOOLS.keys()):
    if _n in _DISABLED_NAMES:
        TOOLS.pop(_n, None)


@server.list_tools()
async def _list_tools() -> List[Tool]:
    tools: List[Tool] = []
    for name, (_handler, schema, description) in TOOLS.items():
        # Some clients require tool names to be strictly alphanumeric
        if not name.isalnum():
            continue
        tools.append(Tool(name=name, description=description, inputSchema=schema))
    return tools


@server.call_tool()
async def _call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    entry = TOOLS.get(name)
    if not entry:
        return [
            TextContent.model_validate(
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "ok": False,
                            "error": {"code": "unknown_tool", "message": name},
                        }
                    ),
                }
            )
        ]
    handler = entry[0]
    try:
        arguments = _normalize_args(name, arguments)
        if not isinstance(arguments, dict):
            arguments = {}
        resp = handler(arguments)
    except Exception as exc:
        return [
            TextContent.model_validate(
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "ok": False,
                            "error": {"code": "call_failed", "message": str(exc)},
                        }
                    ),
                }
            )
        ]
    if not isinstance(resp, dict) or "ok" not in resp:
        return [
            TextContent.model_validate(
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "ok": False,
                            "error": {"code": "bad_response", "message": "invalid"},
                        }
                    ),
                }
            )
        ]
    if not resp["ok"]:
        payload = (
            json.dumps(resp["error"])
            if not isinstance(resp["error"], str)
            else resp["error"]
        )
        return [TextContent.model_validate({"type": "text", "text": payload})]
    # Explicitly construct a dict and validate into TextContent to satisfy strict clients
    return [
        TextContent.model_validate(
            {"type": "text", "text": json.dumps(resp.get("result", {}))}
        )
    ]


async def _main_async() -> int:
    async with stdio_server() as (read, write):
        init_opts = SimpleNamespace(
            server_name="usd-mcp",
            server_version=__version__,
            website_url="https://github.com/your-org/usd-mcp",
            icons=[],
            instructions="Use the listed tools to open, inspect, and modify USD stages. Inputs and outputs are JSON.",
            capabilities={"tools": {}},
        )
        await server.run(read, write, initialization_options=init_opts)
    return 0


def main() -> int:
    return anyio.run(_main_async)


if __name__ == "__main__":
    raise SystemExit(main())
