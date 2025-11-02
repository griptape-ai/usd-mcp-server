from __future__ import annotations

from typing import Any, Dict, List, Optional
import os

from ..errors import error_response
from ..server import STAGES, _import_pxr


def _ok(result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"ok": True}
    if result is not None:
        payload["result"] = result
    return payload


def _jsonify(value: Any) -> Any:
    """Convert USD/Tf/Sdf objects to JSON-safe structures.

    - Scalars pass through
    - Sequences map element-wise
    - Dicts stringify keys and convert values
    - Objects fall back to str(value)
    """
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple, set)):
        return [_jsonify(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    # Common USD types
    # Sdf.Path-like
    path_str = getattr(value, "pathString", None)
    if isinstance(path_str, str):
        return path_str
    # TfToken-like
    try:
        from pxr import Tf, Gf, Vt  # type: ignore

        if isinstance(value, getattr(Tf, "Token", ())):
            return str(value)
        # Common vectors
        if isinstance(value, (getattr(Gf, "Vec3d", ()), getattr(Gf, "Vec3f", ()))):
            return [float(value[0]), float(value[1]), float(value[2])]
        # Token arrays and other Vt arrays
        if isinstance(value, getattr(Vt, "Array", ())):
            try:
                return [_jsonify(v) for v in value]
            except Exception:
                return [str(v) for v in value]
    except Exception:
        pass
    # Enums and others
    return str(value)


def _normalize_file_path(raw: Optional[str]) -> Optional[str]:
    if not isinstance(raw, str):
        return raw
    p = raw.strip()
    if not p:
        return p
    # expand ~ and env vars
    p = os.path.expandvars(os.path.expanduser(p))
    # Fix common macOS-style missing leading slash (e.g., "Users/...")
    if not os.path.isabs(p) and os.path.exists("/" + p):
        p = "/" + p
    return p


def tool_open_stage(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    if not path:
        return error_response("invalid_params", "'path' is required")
    if not os.path.exists(path):
        return error_response("not_found", f"File does not exist: {path}")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    stage_id = STAGES.add(stage)
    return _ok({"stage_id": stage_id})


def tool_close_stage(params: Dict[str, Any]) -> Dict[str, Any]:
    stage_id = params.get("stage_id")
    if not stage_id:
        return error_response("invalid_params", "'stage_id' is required")
    STAGES.remove(stage_id)
    return _ok({})


def tool_list_open_stages(_: Dict[str, Any]) -> Dict[str, Any]:
    _, _, Sdf, _ = _import_pxr()
    stages = []
    for sid, stage in STAGES.items():
        root_layer = stage.GetRootLayer()
        stages.append(
            {
                "stage_id": sid,
                "root_layer": {
                    "identifier": root_layer.identifier,
                    "realPath": getattr(root_layer, "realPath", None),
                },
                "dirty": root_layer.dirty if isinstance(root_layer, Sdf.Layer) else None,
            }
        )
    return _ok({"stages": stages})


def tool_get_stage_summary(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, UsdGeom, _, _ = _import_pxr()
    stage_id = params.get("stage_id")
    if not stage_id:
        return error_response("invalid_params", "'stage_id' is required")
    stage = STAGES.get(stage_id)

    layers = []
    for layer in stage.GetLayerStack():
        layers.append(
            {
                "identifier": layer.identifier,
                "realPath": getattr(layer, "realPath", None),
            }
        )

    root_prims = [p.GetPath().pathString for p in stage.GetPseudoRoot().GetChildren()]
    up_axis = str(UsdGeom.GetStageUpAxis(stage))
    # Use UsdGeom API for wide USD version compatibility
    meters_per_unit = float(UsdGeom.GetStageMetersPerUnit(stage))
    start = stage.GetStartTimeCode()
    end = stage.GetEndTimeCode()

    return _ok(
        {
            "layers": layers,
            "root_prims": root_prims,
            "timeCodes": {"start": start, "end": end},
            "upAxis": up_axis,
            "metersPerUnit": meters_per_unit,
        }
    )


def tool_summarize_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """Stateless summary helper: open a file, summarize, and return without keeping state."""
    Usd, UsdGeom, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    if not path:
        return error_response("invalid_params", "'path' is required")
    if not os.path.exists(path):
        return error_response("not_found", f"File does not exist: {path}")

    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")

    layers = []
    for layer in stage.GetLayerStack():
        layers.append(
            {
                "identifier": layer.identifier,
                "realPath": getattr(layer, "realPath", None),
            }
        )

    root_prims = [p.GetPath().pathString for p in stage.GetPseudoRoot().GetChildren()]
    up_axis = str(UsdGeom.GetStageUpAxis(stage))
    meters_per_unit = float(UsdGeom.GetStageMetersPerUnit(stage))
    start = stage.GetStartTimeCode()
    end = stage.GetEndTimeCode()

    return _ok(
        {
            "layers": layers,
            "root_prims": root_prims,
            "timeCodes": {"start": start, "end": end},
            "upAxis": up_axis,
            "metersPerUnit": meters_per_unit,
        }
    )


def tool_list_prims(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    stage_id = params.get("stage_id")
    root: str = params.get("root", "/")
    if isinstance(root, str):
        root = root.strip() or "/"
    depth: int = int(params.get("depth", 1))
    type_filter: Optional[str] = params.get("typeFilter")

    if not stage_id:
        return error_response("invalid_params", "'stage_id' is required")
    stage = STAGES.get(stage_id)
    root_prim = stage.GetPrimAtPath(root)
    if not root_prim:
        return error_response("not_found", f"Root prim not found: {root}")

    results: List[str] = []

    def visit(prim, d: int) -> None:
        if d < 0:
            return
        if prim and prim.IsValid():
            if type_filter is None or prim.GetTypeName() == type_filter:
                results.append(prim.GetPath().pathString)
            if d > 0:
                for child in prim.GetChildren():
                    visit(child, d - 1)

    visit(root_prim, depth)
    return _ok({"prim_paths": results})


def tool_list_prims_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """Stateless listing helper: open a file, list prims, close."""
    Usd, _, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    if not path:
        return error_response("invalid_params", "'path' is required")
    if not os.path.exists(path):
        return error_response("not_found", f"File does not exist: {path}")

    root: str = params.get("root", "/")
    if isinstance(root, str):
        root = root.strip() or "/"
    depth: int = int(params.get("depth", 1))
    type_filter: Optional[str] = params.get("typeFilter")

    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")

    root_prim = stage.GetPrimAtPath(root)
    if not root_prim:
        return error_response("not_found", f"Root prim not found: {root}")

    results: List[str] = []

    def visit(prim, d: int) -> None:
        if d < 0:
            return
        if prim and prim.IsValid():
            if type_filter is None or prim.GetTypeName() == type_filter:
                results.append(prim.GetPath().pathString)
            if d > 0:
                for child in prim.GetChildren():
                    visit(child, d - 1)

    visit(root_prim, depth)
    return _ok({"prim_paths": results})

def tool_get_prim_info(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    stage_id = params.get("stage_id")
    prim_path: str = params.get("prim_path")
    if isinstance(prim_path, str):
        prim_path = prim_path.strip()
    if not stage_id or not prim_path:
        return error_response("invalid_params", "'stage_id' and 'prim_path' are required")

    stage = STAGES.get(stage_id)
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")

    attrs = [a.GetName() for a in prim.GetAttributes()]
    rels = [r.GetName() for r in prim.GetRelationships()]
    metadata = _jsonify(prim.GetAllMetadata())
    return _ok(
        {
            "type": prim.GetTypeName(),
            "attrs": attrs,
            "rels": rels,
            "metadata": metadata,
        }
    )


def tool_get_attribute_value(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    stage_id = params.get("stage_id")
    prim_path: str = params.get("prim_path")
    attr_name: str = params.get("attr")
    if isinstance(prim_path, str):
        prim_path = prim_path.strip()
    if isinstance(attr_name, str):
        attr_name = attr_name.strip()
    when = params.get("time", "default")
    if not stage_id or not prim_path or not attr_name:
        return error_response("invalid_params", "'stage_id', 'prim_path', 'attr' are required")
    stage = STAGES.get(stage_id)
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")
    attr = prim.GetAttribute(attr_name)
    if not attr:
        return error_response("not_found", f"Attribute not found: {attr_name}")
    value = attr.Get() if when == "default" else attr.Get(float(when))
    return _ok({"value": _jsonify(value)})


def tool_set_attribute_value(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    stage_id = params.get("stage_id")
    prim_path: str = params.get("prim_path")
    attr_name: str = params.get("attr")
    value = params.get("value")
    when = params.get("time", "default")
    if isinstance(prim_path, str):
        prim_path = prim_path.strip()
    if isinstance(attr_name, str):
        attr_name = attr_name.strip()
    if not stage_id or not prim_path or not attr_name:
        return error_response("invalid_params", "'stage_id', 'prim_path', 'attr' are required")
    stage = STAGES.get(stage_id)
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")
    attr = prim.GetAttribute(attr_name)
    if not attr:
        return error_response("not_found", f"Attribute not found: {attr_name}")
    ok = attr.Set(value) if when == "default" else attr.Set(value, float(when))
    if not ok:
        return error_response("set_failed", f"Failed to set attribute: {attr_name}")
    return _ok({})


def tool_get_prim_info_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    if isinstance(prim_path, str):
        prim_path = prim_path.strip()
    if not path or not prim_path:
        return error_response("invalid_params", "'path' and 'prim_path' are required")
    if not os.path.exists(path):
        return error_response("not_found", f"File does not exist: {path}")

    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")
    attrs = [a.GetName() for a in prim.GetAttributes()]
    rels = [r.GetName() for r in prim.GetRelationships()]
    metadata = _jsonify(prim.GetAllMetadata())
    return _ok({"type": prim.GetTypeName(), "attrs": attrs, "rels": rels, "metadata": metadata})


def tool_get_attribute_value_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    attr_name: str = params.get("attr")
    when = params.get("time", "default")
    if isinstance(prim_path, str):
        prim_path = prim_path.strip()
    if isinstance(attr_name, str):
        attr_name = attr_name.strip()
    if not path or not prim_path or not attr_name:
        return error_response("invalid_params", "'path', 'prim_path', 'attr' are required")
    if not os.path.exists(path):
        return error_response("not_found", f"File does not exist: {path}")

    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")
    attr = prim.GetAttribute(attr_name)
    if not attr:
        return error_response("not_found", f"Attribute not found: {attr_name}")
    value = attr.Get() if when == "default" else attr.Get(float(when))
    return _ok({"value": _jsonify(value)})


def tool_set_attribute_value_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    attr_name: str = params.get("attr")
    value = params.get("value")
    when = params.get("time", "default")
    if isinstance(prim_path, str):
        prim_path = prim_path.strip()
    if isinstance(attr_name, str):
        attr_name = attr_name.strip()
    if not path or not prim_path or not attr_name:
        return error_response("invalid_params", "'path', 'prim_path', 'attr' are required")
    if not os.path.exists(path):
        return error_response("not_found", f"File does not exist: {path}")

    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")
    attr = prim.GetAttribute(attr_name)
    if not attr:
        return error_response("not_found", f"Attribute not found: {attr_name}")
    ok = attr.Set(value) if when == "default" else attr.Set(value, float(when))
    if not ok:
        return error_response("set_failed", f"Failed to set attribute: {attr_name}")
    # Save in place
    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save after set")
    return _ok({"output_path": root.identifier})


def tool_create_stage(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, UsdGeom, _, _ = _import_pxr()
    output_path: str = params.get("output_path")
    if isinstance(output_path, str):
        output_path = output_path.strip()
    if not output_path:
        return error_response("invalid_params", "'output_path' is required")
    up_axis = params.get("upAxis")
    meters_per_unit = params.get("metersPerUnit")

    stage = Usd.Stage.CreateNew(output_path)
    if up_axis:
        # Accept "Y" or "Z"
        if str(up_axis).upper().startswith("Z"):
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        else:
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    if meters_per_unit:
        UsdGeom.SetStageMetersPerUnit(stage, float(meters_per_unit))

    stage_id = STAGES.add(stage)
    return _ok({"stage_id": stage_id})


def tool_save_stage(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, Sdf, _ = _import_pxr()
    stage_id = params.get("stage_id")
    output_path: Optional[str] = params.get("output_path")
    if isinstance(output_path, str):
        output_path = output_path.strip()
    flatten: bool = bool(params.get("flatten", False))
    if not stage_id:
        return error_response("invalid_params", "'stage_id' is required")

    stage = STAGES.get(stage_id)
    root = stage.GetRootLayer()
    if output_path:
        # Minimal export; flatten currently not implemented in Tier 0
        ok = root.Export(output_path)
        if not ok:
            return error_response("export_failed", f"Failed to export to {output_path}")
        return _ok({"output_path": output_path})
    else:
        # Save in-place
        ok = root.Save()
        if not ok:
            return error_response("save_failed", "Failed to save root layer")
        return _ok({"output_path": root.identifier})


