from __future__ import annotations

"""Deterministic Python API over usd_mcp.tools.*

These wrappers call the underlying tool_* functions and return plain dicts.
They raise ValueError on failures instead of returning {ok:false} envelopes.
"""

from typing import Any, Dict, List, Optional

from .tools.tier0 import (
    tool_list_prims_in_file,
    tool_get_prim_info_in_file,
    tool_set_attribute_value_in_file,
    tool_batch_set_attribute_values_in_file,
    tool_summarize_file,
)
from .tools.tier2 import (
    tool_create_prim_in_file,
    tool_delete_prim_in_file,
    tool_get_xform_in_file,
    tool_set_xform_in_file,
)
from .tools.tier3 import (
    tool_get_bounds_in_file,
    tool_list_materials_in_file,
    tool_bind_material_in_file,
    tool_unbind_material_in_file,
    tool_get_material_binding_in_file,
    tool_list_cameras_in_file,
    tool_get_camera_in_file,
    tool_set_camera_in_file,
    tool_export_usd_file,
    tool_export_usdz_file,
    tool_add_references_batch_in_file,
    tool_compose_referenced_assembly,
    tool_set_default_prim_in_file,
)


def _unwrap(resp: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(resp, dict) or "ok" not in resp:
        raise ValueError("invalid response")
    if not resp["ok"]:
        err = resp.get("error")
        raise ValueError(str(err))
    return resp.get("result", {})


# Composition
def compose_referenced_assembly(
    output_path: str,
    assets: List[Dict[str, Any]],
    container_root: str = "/Assets",
    flatten: bool = True,
    upAxis: Optional[str] = "Z",
    setDefaultPrim: bool = True,
    skipIfExists: bool = True,
) -> Dict[str, Any]:
    return _unwrap(
        tool_compose_referenced_assembly(
            {
                "output_path": output_path,
                "assets": assets,
                "container_root": container_root,
                "flatten": flatten,
                "upAxis": upAxis,
                "setDefaultPrim": setDefaultPrim,
                "skipIfExists": skipIfExists,
            }
        )
    )


def add_references_batch(
    path: str, items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    return _unwrap(tool_add_references_batch_in_file({"path": path, "items": items}))


def set_default_prim(path: str, prim_path: str) -> Dict[str, Any]:
    return _unwrap(tool_set_default_prim_in_file({"path": path, "prim_path": prim_path}))


# Export
def export_usd_file(path: str, output_path: str, *, flatten: bool = False, skipIfExists: bool = True) -> Dict[str, Any]:
    return _unwrap(
        tool_export_usd_file({"path": path, "output_path": output_path, "flatten": flatten, "skipIfExists": skipIfExists})
    )


def export_usdz_file(path: str, output_path: str) -> Dict[str, Any]:
    return _unwrap(tool_export_usdz_file({"path": path, "output_path": output_path}))


# Prim authoring
def create_prim_in_file(path: str, prim_path: str, type_name: Optional[str] = None, specifier: Optional[str] = None) -> Dict[str, Any]:
    return _unwrap(
        tool_create_prim_in_file({"path": path, "prim_path": prim_path, "type_name": type_name, "specifier": specifier})
    )


def delete_prim_in_file(path: str, prim_path: str) -> Dict[str, Any]:
    return _unwrap(tool_delete_prim_in_file({"path": path, "prim_path": prim_path}))


# Attributes
def set_attribute_value_in_file(path: str, prim_path: str, attr: str, value: Any, time: Any = "default") -> Dict[str, Any]:
    return _unwrap(
        tool_set_attribute_value_in_file({"path": path, "prim_path": prim_path, "attr": attr, "value": value, "time": time})
    )


def batch_set_attribute_values_in_file(path: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    return _unwrap(tool_batch_set_attribute_values_in_file({"path": path, "items": items}))


# Xforms
def get_xform_in_file(path: str, prim_path: str, time: Any = "default") -> Dict[str, Any]:
    return _unwrap(tool_get_xform_in_file({"path": path, "prim_path": prim_path, "time": time}))


def set_xform_in_file(
    path: str,
    prim_path: str,
    *,
    ops: Optional[List[Dict[str, Any]]] = None,
    matrix: Optional[List[List[float]]] = None,
    time: Any = "default",
) -> Dict[str, Any]:
    return _unwrap(
        tool_set_xform_in_file({"path": path, "prim_path": prim_path, "ops": ops, "matrix": matrix, "time": time})
    )


# Introspection
def list_prims_in_file(path: str, root: str = "/", depth: int = 1, typeFilter: Optional[str] = None) -> Dict[str, Any]:
    return _unwrap(tool_list_prims_in_file({"path": path, "root": root, "depth": depth, "typeFilter": typeFilter}))


def get_prim_info_in_file(path: str, prim_path: str) -> Dict[str, Any]:
    return _unwrap(tool_get_prim_info_in_file({"path": path, "prim_path": prim_path}))


def summarize_file(path: str) -> Dict[str, Any]:
    return _unwrap(tool_summarize_file({"path": path}))


def get_bounds_in_file(path: str, prim_path: str, time: Any = "default") -> Dict[str, Any]:
    return _unwrap(tool_get_bounds_in_file({"path": path, "prim_path": prim_path, "time": time}))


# Materials
def list_materials_in_file(path: str) -> Dict[str, Any]:
    return _unwrap(tool_list_materials_in_file({"path": path}))


def bind_material_in_file(path: str, prim_path: str, material_path: str) -> Dict[str, Any]:
    return _unwrap(tool_bind_material_in_file({"path": path, "prim_path": prim_path, "material_path": material_path}))


def unbind_material_in_file(path: str, prim_path: str) -> Dict[str, Any]:
    return _unwrap(tool_unbind_material_in_file({"path": path, "prim_path": prim_path}))


def get_material_binding_in_file(path: str, prim_path: str) -> Dict[str, Any]:
    return _unwrap(tool_get_material_binding_in_file({"path": path, "prim_path": prim_path}))


# Cameras
def list_cameras_in_file(path: str) -> Dict[str, Any]:
    return _unwrap(tool_list_cameras_in_file({"path": path}))


def get_camera_in_file(path: str, camera_path: str) -> Dict[str, Any]:
    return _unwrap(tool_get_camera_in_file({"path": path, "camera_path": camera_path}))


def set_camera_in_file(path: str, camera_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    return _unwrap(tool_set_camera_in_file({"path": path, "camera_path": camera_path, "params": params}))


