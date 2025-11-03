from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import os

from ..errors import error_response
from ..server import _import_pxr
from .tier0 import _ok, _normalize_file_path, _jsonify


# Variants
def tool_list_variants_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    if not path or not prim_path:
        return error_response("invalid_params", "'path' and 'prim_path' are required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")
    sets = {}
    vsets = prim.GetVariantSets()
    for name in vsets.GetNames():
        sel = vsets.GetVariantSet(name).GetVariantSelection()
        sets[name] = sel or None
    return _ok({"variantSets": sets})


def tool_set_variant_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    set_name: str = params.get("set")
    selection: str = params.get("selection")
    if not path or not prim_path or not set_name or selection is None:
        return error_response("invalid_params", "'path','prim_path','set','selection' required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")
    vs = prim.GetVariantSets().GetVariantSet(set_name)
    try:
        ok = vs.SetVariantSelection(selection)
    except Exception as exc:
        return error_response("set_failed", str(exc))
    if not ok:
        return error_response("set_failed", f"Failed to set variant {set_name}={selection}")
    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save after set variant")
    return _ok({"variantSets": {set_name: selection}})


# Materials
def tool_list_materials_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    try:
        from pxr import UsdShade  # type: ignore
    except Exception as exc:  # pragma: no cover
        return error_response("missing_usd", "UsdShade not available")
    path = _normalize_file_path(params.get("path"))
    if not path:
        return error_response("invalid_params", "'path' is required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    mats: List[str] = []
    for prim in stage.Traverse():
        mat = UsdShade.Material(prim)
        if mat and mat.GetPrim().IsValid():
            mats.append(prim.GetPath().pathString)
    return _ok({"materials": mats})


def tool_bind_material_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    try:
        from pxr import UsdShade  # type: ignore
    except Exception as exc:
        return error_response("missing_usd", "UsdShade not available")
    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    material_path: str = params.get("material_path")
    if not path or not prim_path or not material_path:
        return error_response("invalid_params", "'path','prim_path','material_path' required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    mat_prim = stage.GetPrimAtPath(material_path)
    if not prim or not mat_prim:
        return error_response("not_found", "prim or material not found")
    mat = UsdShade.Material(mat_prim)
    if not mat:
        return error_response("invalid_params", f"Not a UsdShade.Material: {material_path}")
    UsdShade.MaterialBindingAPI(prim).Bind(mat)
    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save after bind")
    return _ok({"bound": True})


def tool_unbind_material_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    try:
        from pxr import UsdShade  # type: ignore
    except Exception as exc:
        return error_response("missing_usd", "UsdShade not available")
    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    if not path or not prim_path:
        return error_response("invalid_params", "'path','prim_path' required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", "prim not found")
    UsdShade.MaterialBindingAPI(prim).UnbindAllBindings()
    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save after unbind")
    return _ok({"unbound": True})


def tool_get_material_binding_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    try:
        from pxr import UsdShade  # type: ignore
    except Exception:
        return error_response("missing_usd", "UsdShade not available")
    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    if not path or not prim_path:
        return error_response("invalid_params", "'path','prim_path' required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", "prim not found")
    mat = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
    if mat and mat.GetPrim().IsValid():
        return _ok({"material_path": mat.GetPath().pathString})
    # Also report if a binding relationship spec still exists but has no targets
    rel = UsdShade.MaterialBindingAPI(prim).GetDirectBindingRel()
    rel_exists = bool(rel) and rel.IsValid()
    targets: List[str] = []
    try:
        if rel_exists:
            tmp: List[Any] = []
            rel.GetTargets(tmp)
            targets = [t.pathString for t in tmp]
    except Exception:
        targets = []
    return _ok({"material_path": None, "bindingRelExists": bool(rel_exists), "bindingTargets": targets})


# Cameras
def tool_list_cameras_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, UsdGeom, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    if not path:
        return error_response("invalid_params", "'path' is required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    cams: List[str] = []
    for prim in stage.Traverse():
        if prim.GetTypeName() == "Camera":
            cams.append(prim.GetPath().pathString)
    return _ok({"cameras": cams})


def tool_get_camera_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, UsdGeom, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    camera_path: str = params.get("camera_path")
    if not path or not camera_path:
        return error_response("invalid_params", "'path' and 'camera_path' required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    cam_prim = stage.GetPrimAtPath(camera_path)
    if not cam_prim:
        return error_response("not_found", f"Camera not found: {camera_path}")
    cam = UsdGeom.Camera(cam_prim)
    data = {
        "focalLength": _jsonify(cam.GetFocalLengthAttr().Get()),
        "horizontalAperture": _jsonify(cam.GetHorizontalApertureAttr().Get()),
        "verticalAperture": _jsonify(cam.GetVerticalApertureAttr().Get()),
        "clippingRange": _jsonify(cam.GetClippingRangeAttr().Get()),
        "projection": _jsonify(cam.GetProjectionAttr().Get()),
    }
    return _ok({"camera": data})


def tool_set_camera_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, UsdGeom, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    camera_path: str = params.get("camera_path")
    params_in: Dict[str, Any] = params.get("params") or {}
    if not path or not camera_path:
        return error_response("invalid_params", "'path' and 'camera_path' required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    cam_prim = stage.GetPrimAtPath(camera_path)
    if not cam_prim:
        # create camera
        cam_prim = stage.DefinePrim(camera_path, "Camera")
    cam = UsdGeom.Camera(cam_prim)
    if "focalLength" in params_in:
        cam.GetFocalLengthAttr().Set(float(params_in["focalLength"]))
    if "horizontalAperture" in params_in:
        cam.GetHorizontalApertureAttr().Set(float(params_in["horizontalAperture"]))
    if "verticalAperture" in params_in:
        cam.GetVerticalApertureAttr().Set(float(params_in["verticalAperture"]))
    if "clippingRange" in params_in and isinstance(params_in["clippingRange"], (list, tuple)):
        rng = params_in["clippingRange"]
        if len(rng) == 2:
            cam.GetClippingRangeAttr().Set(tuple(float(v) for v in rng))
    if "projection" in params_in:
        cam.GetProjectionAttr().Set(params_in["projection"])  # string token ok
    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save camera params")
    return _ok({"camera_path": camera_path})


# Bounds
def tool_get_bounds_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, UsdGeom, _, _ = _import_pxr()
    try:
        from pxr import Gf  # type: ignore
    except Exception:
        Gf = None  # type: ignore
    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    when = params.get("time", "default")
    if not path or not prim_path:
        return error_response("invalid_params", "'path' and 'prim_path' required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")
    time_code = Usd.TimeCode.Default() if when == "default" else Usd.TimeCode(float(when))
    cache = UsdGeom.BBoxCache(time_code, [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy])
    # Try world bound first
    bbox_world = cache.ComputeWorldBound(prim)
    box_world = bbox_world.GetBox()
    mn = [float(x) for x in box_world.GetMin()]
    mx = [float(x) for x in box_world.GetMax()]

    # Fallback translation fix for older USD builds: if parent translation is not applied, add it
    def _is_identity3(m) -> bool:
        try:
            for r in range(3):
                for c in range(3):
                    exp = 1.0 if r == c else 0.0
                    if abs(float(m[r][c]) - exp) > 1e-12:
                        return False
            return True
        except Exception:
            return True

    # Try to compute authored world matrix via XformCache first
    xf_cache = UsdGeom.XformCache(time_code)
    world_m = xf_cache.GetLocalToWorldTransform(prim)
    if Gf is not None and _is_identity3(world_m):
        # Accumulate transform ops up the chain similar to get_xform_in_file fallback
        def _authored_tm(p):
            xp = UsdGeom.Xformable(p)
            for op in xp.GetOrderedXformOps():
                if op.GetOpType() == UsdGeom.XformOp.TypeTransform:
                    try:
                        return op.Get(time_code)
                    except Exception:
                        return None
            return None

        acc = Gf.Matrix4d(1.0)
        cur = prim
        non_id = False
        chain = []
        while cur and cur.IsValid() and str(cur.GetPath()) != "/":
            chain.append(cur)
            cur = cur.GetParent()
        chain.reverse()
        for p in chain:
            m = _authored_tm(p)
            if m is not None:
                acc = acc * m
                if not _is_identity3(m):
                    non_id = True
        if non_id:
            world_m = acc

    # Compute a transformed-local fallback world box using the authored/composed world matrix
    try:
        bbox_local = cache.ComputeLocalBound(prim)
        if Gf is not None:
            bbox_local = bbox_local.Transform(world_m)
            lb = bbox_local.GetBox()
            mn_alt = [float(x) for x in lb.GetMin()]
            mx_alt = [float(x) for x in lb.GetMax()]
        else:
            mn_alt = mn
            mx_alt = mx
    except Exception:
        mn_alt, mx_alt = mn, mx

    # If the world box looks centered at origin but world_m has translation, prefer the transformed-local box
    try:
        t = [float(world_m[0][3]), float(world_m[1][3]), float(world_m[2][3])] if Gf is not None else [0.0, 0.0, 0.0]
    except Exception:
        t = [0.0, 0.0, 0.0]
    center = [(mn[i] + mx[i]) * 0.5 for i in range(3)]
    if any(abs(v) > 1e-12 for v in t) and all(abs(center[i]) < 1e-9 for i in range(3)):
        mn, mx = mn_alt, mx_alt

    return _ok({"min": mn, "max": mx})


# Export / Validate
def tool_export_usd_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    output_path: str = params.get("output_path")
    flatten: bool = bool(params.get("flatten", False))
    skip_if_exists: bool = bool(params.get("skipIfExists", True))
    if not path or not output_path:
        return error_response("invalid_params", "'path' and 'output_path' required")
    # Idempotent: skip when output exists and caller allows it
    try:
        if skip_if_exists and isinstance(output_path, str) and os.path.exists(output_path):
            return _ok({"output_path": output_path, "skipped": True})
    except Exception:
        pass
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    try:
        if flatten and hasattr(stage, "Export"):
            ok = stage.Export(output_path)
        else:
            ok = stage.GetRootLayer().Export(output_path)
    except Exception as exc:
        return error_response("export_failed", str(exc))
    if not ok:
        return error_response("export_failed", f"Failed to export to {output_path}")
    return _ok({"output_path": output_path})


def tool_export_usdz_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    try:
        from pxr import UsdUtils  # type: ignore
    except Exception:
        return error_response("missing_usd", "UsdUtils not available for USDZ export")
    path = _normalize_file_path(params.get("path"))
    output_path: str = params.get("output_path")
    if not path or not output_path:
        return error_response("invalid_params", "'path' and 'output_path' required")
    try:
        ok = UsdUtils.CreateNewUsdzPackage(path, output_path)
    except Exception as exc:
        return error_response("export_failed", str(exc))
    if not ok:
        return error_response("export_failed", f"Failed to create USDZ {output_path}")
    return _ok({"output_path": output_path})


def tool_validate_stage_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    if not path:
        return error_response("invalid_params", "'path' is required")
    try:
        stage = Usd.Stage.Open(path)
        if stage is None:
            return error_response("open_failed", f"Failed to open stage: {path}")
        # Placeholder: return basic info as no issues
        return _ok({"issues": []})
    except Exception as exc:
        return error_response("validate_failed", str(exc))


def tool_add_reference_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """Add a reference to a prim in a USD file and save.

    Inputs:
      - path: path to the target USD file (stage to modify)
      - prim_path: prim on that stage that will receive the reference
      - asset_path: path to the referenced USD/USDZ/USDA
      - internal_path: optional prim path inside the referenced asset (default: use asset's defaultPrim if present)
    """
    Usd, _, _, _ = _import_pxr()
    path: str = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path") or ""
    asset_path: str = _normalize_file_path(params.get("asset_path"))
    internal_path_in = params.get("internal_path")
    internal_path: str = (internal_path_in or "").strip()
    # Treat '/' as empty; we'll resolve to defaultPrim if possible
    if internal_path == "/":
        internal_path = ""
    if not path or not prim_path or not asset_path:
        return error_response("invalid_params", "'path', 'prim_path', 'asset_path' are required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")
    # If no internal prim path provided, try the asset's defaultPrim
    if internal_path == "":
        try:
            ref_stage = Usd.Stage.Open(asset_path)
            if ref_stage:
                dp = ref_stage.GetDefaultPrim()
                if dp and dp.IsValid():
                    internal_path = dp.GetPath().pathString
        except Exception:
            # fallback: keep empty
            internal_path = ""
    try:
        if internal_path:
            prim.GetReferences().AddReference(asset_path, internal_path)
        else:
            prim.GetReferences().AddReference(asset_path)
    except Exception as exc:
        return error_response("reference_failed", str(exc))
    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save after add_reference")
    return _ok({"prim_path": prim_path, "asset_path": asset_path, "internal_path": internal_path or None})


def tool_add_sublayer_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """Add a sublayer to the root layer of a USD file and save.

    Inputs:
      - path: target USD file
      - sublayer: path to a USD layer to append in subLayerPaths
      - insert_index: optional index to insert at (append by default)
    """
    Usd, _, _, _ = _import_pxr()
    path: str = _normalize_file_path(params.get("path"))
    sublayer: str = _normalize_file_path(params.get("sublayer"))
    insert_index = params.get("insert_index")
    if not path or not sublayer:
        return error_response("invalid_params", "'path' and 'sublayer' are required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    root = stage.GetRootLayer()
    try:
        if insert_index is None or insert_index == "append":
            if sublayer not in root.subLayerPaths:
                root.subLayerPaths.append(sublayer)
        else:
            idx = int(insert_index)
            if sublayer not in root.subLayerPaths:
                root.subLayerPaths.insert(idx, sublayer)
    except Exception as exc:
        return error_response("sublayer_failed", str(exc))
    if not root.Save():
        return error_response("save_failed", "Failed to save after add_sublayer")
    return _ok({"sublayers": list(root.subLayerPaths)})


def tool_set_default_prim_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """Set the stage defaultPrim to the given prim path and save.

    Inputs:
      - path: target USD file
      - prim_path: absolute prim path to set as defaultPrim (must exist)
    """
    Usd, _, _, _ = _import_pxr()
    path: str = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path") or ""
    if not path or not prim_path:
        return error_response("invalid_params", "'path' and 'prim_path' are required")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")
    try:
        stage.SetDefaultPrim(prim)
    except Exception as exc:
        return error_response("set_failed", str(exc))
    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save after set_default_prim")
    return _ok({"defaultPrim": prim_path})


# Batch: add many references in one call
def tool_add_references_batch_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """Add multiple references to a USD file in one save.

    Inputs:
      - path: target USD file
      - items: array of { prim_path, asset_path, internal_path? }
        - if internal_path omitted/empty or '/', resolve via referenced stage defaultPrim
    """
    Usd, _, _, _ = _import_pxr()
    path: str = _normalize_file_path(params.get("path"))
    items: List[Dict[str, Any]] = params.get("items") or []
    if not path:
        return error_response("invalid_params", "'path' is required")
    if not isinstance(items, list) or not items:
        return error_response("invalid_params", "'items' must be a non-empty array")
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")

    results: List[Dict[str, Any]] = []
    for it in items:
        prim_path = (it.get("prim_path") or "").strip()
        asset_path = _normalize_file_path(it.get("asset_path"))
        internal_path = (it.get("internal_path") or "").strip()
        if internal_path == "/":
            internal_path = ""
        if not prim_path or not asset_path:
            results.append({"prim_path": prim_path, "ok": False, "error": "missing prim_path or asset_path"})
            continue
        prim = stage.GetPrimAtPath(prim_path)
        if not prim:
            prim = stage.DefinePrim(prim_path, "Xform")
        # resolve defaultPrim when internal_path is empty
        if internal_path == "":
            try:
                ref_stage = Usd.Stage.Open(asset_path)
                if ref_stage:
                    dp = ref_stage.GetDefaultPrim()
                    if dp and dp.IsValid():
                        internal_path = dp.GetPath().pathString
            except Exception:
                internal_path = ""
        try:
            if internal_path:
                prim.GetReferences().AddReference(asset_path, internal_path)
            else:
                prim.GetReferences().AddReference(asset_path)
            results.append({"prim_path": prim_path, "asset_path": asset_path, "internal_path": internal_path or None, "ok": True})
        except Exception as exc:
            results.append({"prim_path": prim_path, "asset_path": asset_path, "ok": False, "error": str(exc)})

    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save after batch add references")
    return _ok({"results": results})


# One-shot assembly: export (optional), ensure stage/containers, add references, set defaultPrim
def tool_compose_referenced_assembly(params: Dict[str, Any]) -> Dict[str, Any]:
    """Compose an assembly stage by referencing a list of assets.

    Inputs:
      - output_path: path to the assembly .usd/.usda to write
      - assets: [{ asset_path, name?, internal_path? }]
      - container_root: where to place containers (default '/Assets')
      - flatten: bool, when asset_path is .usdz, export to sibling .usda first
      - upAxis: 'Z' or 'Y' (default 'Z' on create)
      - setDefaultPrim: bool (default true) — set to container_root
      - skipIfExists: bool (default true) for intermediate exports
    """
    Usd, UsdGeom, _, _ = _import_pxr()
    output_path: str = _normalize_file_path(params.get("output_path"))
    assets: List[Dict[str, Any]] = params.get("assets") or []
    container_root: str = params.get("container_root", "/Assets") or "/Assets"
    flatten: bool = bool(params.get("flatten", True))
    up_axis: Optional[str] = params.get("upAxis")
    set_default: bool = bool(params.get("setDefaultPrim", True))
    skip_if_exists: bool = bool(params.get("skipIfExists", True))
    if not output_path:
        return error_response("invalid_params", "'output_path' is required")
    if not isinstance(assets, list) or not assets:
        return error_response("invalid_params", "'assets' must be a non-empty array")

    # Open-or-create stage
    stage = None
    if os.path.exists(output_path):
        stage = Usd.Stage.Open(output_path)
    else:
        stage = Usd.Stage.CreateNew(output_path)
        # default Z when not specified
        if up_axis is None or str(up_axis).upper().startswith("Z"):
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        else:
            UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

    # Ensure container root
    stage.DefinePrim(container_root, "Xform")

    def _basename_noext(p: str) -> str:
        base = os.path.basename(p)
        name, _ = os.path.splitext(base)
        return name

    referenced = 0
    for a in assets:
        src_path = _normalize_file_path(a.get("asset_path"))
        if not src_path:
            continue
        name = (a.get("name") or _basename_noext(src_path)).strip() or _basename_noext(src_path)
        internal_path = (a.get("internal_path") or "").strip()

        # Optionally export USDZ -> USDA sibling
        ref_path = src_path
        try:
            if flatten and str(src_path).lower().endswith(".usdz"):
                target = os.path.splitext(src_path)[0] + ".usda"
                if not (skip_if_exists and os.path.exists(target)):
                    st = Usd.Stage.Open(src_path)
                    if st is None:
                        return error_response("open_failed", f"Failed to open asset: {src_path}")
                    ok = st.Export(target)
                    if not ok:
                        return error_response("export_failed", f"Failed to export {target}")
                ref_path = target
        except Exception as exc:
            return error_response("export_failed", str(exc))

        # Resolve defaultPrim if internal_path empty
        if internal_path == "" or internal_path == "/":
            try:
                rstage = Usd.Stage.Open(ref_path)
                if rstage:
                    dp = rstage.GetDefaultPrim()
                    if dp and dp.IsValid():
                        internal_path = dp.GetPath().pathString
                    else:
                        internal_path = ""
            except Exception:
                internal_path = ""

        container = container_root.rstrip("/") + "/" + name
        prim = stage.GetPrimAtPath(container)
        if not prim:
            prim = stage.DefinePrim(container, "Xform")
        try:
            if internal_path:
                prim.GetReferences().AddReference(ref_path, internal_path)
            else:
                prim.GetReferences().AddReference(ref_path)
            referenced += 1
        except Exception as exc:
            return error_response("reference_failed", str(exc))

    if set_default:
        try:
            prim = stage.GetPrimAtPath(container_root)
            if prim:
                stage.SetDefaultPrim(prim)
        except Exception:
            pass

    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save compose")
    return _ok({"combined_path": output_path, "referenced": referenced})

