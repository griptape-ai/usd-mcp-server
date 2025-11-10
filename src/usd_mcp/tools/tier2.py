from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..errors import error_response
from ..server import _import_pxr
from .tier0 import _jsonify, _normalize_file_path, _ok  # reuse helpers


def tool_create_prim_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, UsdGeom, Sdf, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    type_name: Optional[str] = params.get("type_name")
    specifier: str = str(params.get("specifier", "def")).lower()
    if isinstance(prim_path, str):
        prim_path = prim_path.strip()
    if not path or not prim_path:
        return error_response("invalid_params", "'path' and 'prim_path' are required")

    try:
        stage = Usd.Stage.Open(path)
        if stage is None:
            return error_response("open_failed", f"Failed to open stage: {path}")

        sdf_path = Sdf.Path(prim_path)
        # Ensure parent exists
        parent = stage.GetPrimAtPath(sdf_path.GetParentPath())
        if not parent:
            stage.DefinePrim(sdf_path.GetParentPath())

        prim = None
        if specifier == "over":
            prim = stage.OverridePrim(sdf_path)
            if type_name:
                prim.SetTypeName(type_name)
        elif specifier == "class":
            prim = stage.CreateClassPrim(sdf_path)
            if type_name:
                prim.SetTypeName(type_name)
        else:  # def
            prim = stage.DefinePrim(sdf_path, type_name or "")

        if not prim:
            return error_response(
                "create_failed", f"Could not create prim at {prim_path}"
            )

        root = stage.GetRootLayer()
        if not root.Save():
            return error_response("save_failed", "Failed to save after create")
        return _ok({"created": prim_path, "output_path": root.identifier})
    except Exception as exc:
        return error_response("create_failed", str(exc))


def tool_delete_prim_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, Sdf, _ = _import_pxr()
    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    if isinstance(prim_path, str):
        prim_path = prim_path.strip()
    if not path or not prim_path:
        return error_response("invalid_params", "'path' and 'prim_path' are required")

    try:
        stage = Usd.Stage.Open(path)
        if stage is None:
            return error_response("open_failed", f"Failed to open stage: {path}")
        if not stage.GetPrimAtPath(prim_path):
            return error_response("not_found", f"Prim not found: {prim_path}")
        if not stage.RemovePrim(Sdf.Path(prim_path)):
            return error_response(
                "delete_failed", f"Failed to delete prim: {prim_path}"
            )
        root = stage.GetRootLayer()
        if not root.Save():
            return error_response("save_failed", "Failed to save after delete")
        return _ok({"deleted": prim_path, "output_path": root.identifier})
    except Exception as exc:
        return error_response("delete_failed", str(exc))


def tool_get_xform_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, UsdGeom, _, _ = _import_pxr()
    from pxr import Gf  # type: ignore

    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    when = params.get("time", "default")
    if isinstance(prim_path, str):
        prim_path = prim_path.strip()
    if not path or not prim_path:
        return error_response("invalid_params", "'path' and 'prim_path' are required")

    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")

    time_code = (
        Usd.TimeCode.Default() if when == "default" else Usd.TimeCode(float(when))
    )
    # Ensure prim is Xform-typed if it's untyped, so xform ops can be authored
    try:
        if not prim.GetTypeName():
            prim.SetTypeName("Xform")
    except Exception:
        pass
    xformable = UsdGeom.Xformable(prim)
    ops = []
    for op in xformable.GetOrderedXformOps():
        try:
            val = op.Get(time_code)
            if op.GetOpType() == UsdGeom.XformOp.TypeTransform:
                val = _m4_to_list(val)
            else:
                val = _jsonify(val)
            ops.append({"op": op.GetOpName(), "value": val})
        except Exception:
            ops.append({"op": op.GetOpName(), "value": None})

    cache = UsdGeom.XformCache(time_code)
    world = cache.GetLocalToWorldTransform(prim)
    local = cache.GetLocalTransformation(prim)

    # Fallback: if world is identity but a transform op exists with a non-identity matrix,
    # use that matrix as world (helps with edge cases in some USD builds)
    def _is_identity(m) -> bool:
        try:
            for r in range(4):
                for c in range(4):
                    expected = 1.0 if r == c else 0.0
                    if abs(float(m[r][c]) - expected) > 1e-12:
                        return False
            return True
        except Exception:
            return False

    if _is_identity(world):
        for op in xformable.GetOrderedXformOps():
            if op.GetOpType() == UsdGeom.XformOp.TypeTransform:
                try:
                    tm = op.Get(time_code)
                    if not _is_identity(tm):
                        world = tm
                        break
                except Exception:
                    pass

    # Second fallback: accumulate authored transform ops up the ancestor chain
    if _is_identity(world):
        try:
            from pxr import Gf  # type: ignore
        except Exception:
            Gf = None  # type: ignore

        def _authored_transform_matrix(p):
            xp = UsdGeom.Xformable(p)
            for op in xp.GetOrderedXformOps():
                if op.GetOpType() == UsdGeom.XformOp.TypeTransform:
                    try:
                        return op.Get(time_code)
                    except Exception:
                        return None
            return None

        chain: list = []
        cur = prim
        # Collect from root->...->prim
        while cur and cur.IsValid() and str(cur.GetPath()) != "/":
            chain.append(cur)
            cur = cur.GetParent()
        chain.reverse()

        # Multiply parent-first: World = M_parent * ... * M_child
        if Gf is not None:
            acc = Gf.Matrix4d(1.0)
            any_non_identity = False
            for p in chain:
                m = _authored_transform_matrix(p)
                if m is not None:
                    acc = acc * m
                    if not _is_identity(m):
                        any_non_identity = True
            if any_non_identity:
                world = acc

    def _m4_to_list(m) -> List[List[float]]:
        rows: List[List[float]] = []
        # Gf.Matrix4d path
        if hasattr(m, "GetRow"):
            for r in range(4):
                row = m.GetRow(r)
                rows.append(
                    [float(row[0]), float(row[1]), float(row[2]), float(row[3])]
                )
            return rows
        # Sequence path (tuple/ list of rows)
        try:
            for r in range(4):
                row = m[r]
                rows.append(
                    [float(row[0]), float(row[1]), float(row[2]), float(row[3])]
                )
            return rows
        except Exception:
            # Fallback: identity
            return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]

    return _ok(
        {
            "ops": ops,
            "localMatrix": _m4_to_list(local),
            "worldMatrix": _m4_to_list(world),
        }
    )


def tool_set_xform_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, UsdGeom, Sdf, _ = _import_pxr()
    from pxr import Gf  # type: ignore

    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    when = params.get("time", "default")
    # Accept both 'ops' (preferred) and 'items' (fallback from some callers)
    ops: Optional[List[Dict[str, Any]]] = params.get("ops") or params.get("items")
    matrix = params.get("matrix")
    if isinstance(prim_path, str):
        prim_path = prim_path.strip()
    if not path or not prim_path:
        return error_response("invalid_params", "'path' and 'prim_path' are required")

    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")

    xformable = UsdGeom.Xformable(prim)
    time_code = (
        Usd.TimeCode.Default() if when == "default" else Usd.TimeCode(float(when))
    )

    # Set transform matrix without removing existing ops
    if matrix is not None:
        # Reuse existing transform op if present, otherwise add one
        xf_op = None
        for op in xformable.GetOrderedXformOps():
            if op.GetOpType() == UsdGeom.XformOp.TypeTransform:
                xf_op = op
                break
        if xf_op is None:
            xf_op = xformable.AddXformOp(UsdGeom.XformOp.TypeTransform)

        try:
            m = Gf.Matrix4d(matrix)
        except Exception:
            # Fallback if matrix is list[list]
            m = Gf.Matrix4d(1.0)
            for r in range(min(4, len(matrix))):
                for c in range(min(4, len(matrix[r]))):
                    m[r][c] = float(matrix[r][c])
        xf_op.Set(m, time_code)
    elif ops:
        # Prefer XformCommonAPI to author translate/rotate/scale ops explicitly,
        # and ensure xformOpOrder excludes stale TypeTransform entries.
        xapi = UsdGeom.XformCommonAPI(prim)

        translate_val = None
        scale_val = None
        rotate_val = None

        for entry in ops:
            op_raw = entry.get("op") or entry.get("opType") or ""
            op = str(op_raw).lower().strip()
            if op.startswith("xformop:"):
                op = op.split(":", 1)[1]
            val = entry.get("value")
            if op in ("translate", "t") and isinstance(val, (list, tuple)):
                translate_val = [float(val[0]), float(val[1]), float(val[2])]
            elif op in ("scale", "s") and isinstance(val, (list, tuple)):
                scale_val = [float(val[0]), float(val[1]), float(val[2])]
            elif op in ("rotatexyz", "r") and isinstance(val, (list, tuple)):
                rotate_val = [float(val[0]), float(val[1]), float(val[2])]
            else:
                return error_response("invalid_params", f"Unsupported xform op: {op}")

        # If authoring gprims, interpret scale as geometric size rather than xform scale.
        prim_type = prim.GetTypeName() or ""
        # Keep Cube as xform scale to support non-uniform scales (e.g., [10,10,1])
        if scale_val is not None and prim_type in ("Sphere", "Cone"):
            try:
                if prim_type == "Sphere":
                    # UsdGeom.Sphere uses 'radius'; interpret scale.x as diameter
                    radius_attr = prim.GetAttribute("radius")
                    if radius_attr:
                        radius_attr.Set(float(scale_val[0]) * 0.5, time_code)
                    scale_val = None
                elif prim_type == "Cone":
                    # UsdGeom.Cone uses 'height' and 'radius'; map scale.z -> height, scale.x -> diameter
                    height_attr = prim.GetAttribute("height")
                    radius_attr = prim.GetAttribute("radius")
                    if height_attr:
                        height_attr.Set(float(scale_val[2]), time_code)
                    if radius_attr:
                        radius_attr.Set(float(scale_val[0]) * 0.5, time_code)
                    scale_val = None
            except Exception:
                # Fall back to xform scale if size authoring fails
                pass

        # Keep transforms authored on the target prim; do not reroute to children.

        # Apply via CommonAPI - only set what's provided (overrides, not preserves)
        if translate_val is not None:
            xapi.SetTranslate(Gf.Vec3d(*translate_val), time_code)
        if rotate_val is not None:
            # Degrees, XYZ order
            try:
                from pxr import UsdGeom as _UG  # type: ignore

                xapi.SetRotate(
                    Gf.Vec3f(*rotate_val),
                    _UG.XformCommonAPI.RotationOrderXYZ,
                    time_code,
                )
            except Exception:
                # Fallback without explicit order arg
                try:
                    xapi.SetRotate(Gf.Vec3f(*rotate_val))
                except Exception:
                    pass
        if scale_val is not None:
            xapi.SetScale(Gf.Vec3f(*scale_val), time_code)

        # Rebuild op order: include ops that were explicitly set, plus any scale from referenced files
        # This ensures we only override what's provided, but preserve scale from references
        current_ops = []
        all_ops = xformable.GetOrderedXformOps()

        # Track which ops we've explicitly set
        set_translate = translate_val is not None
        set_rotate = rotate_val is not None
        set_scale = scale_val is not None

        # Check if prim has references - if so, we need to preserve scale from references
        has_references = prim.HasAuthoredReferences()

        # Check if scale exists in composition (from references) even if not authored on this prim
        scale_from_refs = False
        if has_references and not set_scale:
            try:
                # Check if scale attribute exists when composed (from references)
                scale_attr = prim.GetAttribute("xformOp:scale")
                if scale_attr:
                    # Try to get the composed value
                    scale_val_composed = scale_attr.Get(time_code)
                    if scale_val_composed is not None:
                        scale_from_refs = True
            except Exception:
                pass

        # Build op order in standard order: translate, rotate, scale
        # Include ops that were explicitly set, plus scale if it exists (from references)
        for op in all_ops:
            op_type = op.GetOpType()
            op_name = op.GetName()
            # Skip TypeTransform ops
            if op_type == UsdGeom.XformOp.TypeTransform:
                continue
            # Include translate if explicitly set
            if op_name == "xformOp:translate" and set_translate:
                current_ops.append(op)
            # Include rotate if explicitly set
            elif op_name.startswith("xformOp:rotate") and set_rotate:
                current_ops.append(op)
            # Include scale if explicitly set OR if it exists from references
            elif op_name == "xformOp:scale":
                if set_scale:
                    # Explicitly set scale - include it
                    current_ops.append(op)
                elif scale_from_refs:
                    # Scale exists from references - preserve it in op order
                    current_ops.append(op)
                else:
                    # Check if scale op has a value (not from references)
                    try:
                        if op.Get(time_code) is not None:
                            current_ops.append(op)
                    except Exception:
                        pass

        # If scale exists from references but wasn't in all_ops, we need to add it
        if scale_from_refs and not set_scale:
            # Check if we already have a scale op in current_ops
            has_scale_op = any(op.GetName() == "xformOp:scale" for op in current_ops)
            if not has_scale_op:
                # Scale exists from references but no op was found - create one to preserve it
                try:
                    scale_op = xformable.AddXformOp(
                        UsdGeom.XformOp.TypeScale, UsdGeom.XformOp.PrecisionFloat
                    )
                    current_ops.append(scale_op)
                except Exception:
                    pass

        # Set the op order - what was explicitly provided plus preserved scale
        if current_ops:
            xformable.SetXformOpOrder(current_ops)
    else:
        return error_response("invalid_params", "Provide either 'matrix' or 'ops'")

    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save after set_xform")
    return _ok({"output_path": root.identifier})
