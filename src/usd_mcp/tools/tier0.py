from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..errors import error_response
from ..server import STAGES, _import_pxr


def _ok(result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"ok": True}
    if result is not None:
        payload["result"] = result
    return payload


def tool_open_stage(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    path = params.get("path")
    if not path:
        return error_response("invalid_params", "'path' is required")
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
    meters_per_unit = stage.GetMetersPerUnit()
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


def tool_get_prim_info(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    stage_id = params.get("stage_id")
    prim_path: str = params.get("prim_path")
    if not stage_id or not prim_path:
        return error_response("invalid_params", "'stage_id' and 'prim_path' are required")

    stage = STAGES.get(stage_id)
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")

    attrs = [a.GetName() for a in prim.GetAttributes()]
    rels = [r.GetName() for r in prim.GetRelationships()]
    metadata = prim.GetAllMetadata()
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
    return _ok({"value": value})


def tool_set_attribute_value(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    stage_id = params.get("stage_id")
    prim_path: str = params.get("prim_path")
    attr_name: str = params.get("attr")
    value = params.get("value")
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
    ok = attr.Set(value) if when == "default" else attr.Set(value, float(when))
    if not ok:
        return error_response("set_failed", f"Failed to set attribute: {attr_name}")
    return _ok({})


def tool_create_stage(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, UsdGeom, _, _ = _import_pxr()
    output_path: str = params.get("output_path")
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
        stage.SetMetersPerUnit(float(meters_per_unit))

    stage_id = STAGES.add(stage)
    return _ok({"stage_id": stage_id})


def tool_save_stage(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, Sdf, _ = _import_pxr()
    stage_id = params.get("stage_id")
    output_path: Optional[str] = params.get("output_path")
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


