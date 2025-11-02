from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..errors import error_response
from ..server import _import_pxr
from .tier0 import _ok, _normalize_file_path, _jsonify  # reuse helpers


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
            return error_response("create_failed", f"Could not create prim at {prim_path}")

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
            return error_response("delete_failed", f"Failed to delete prim: {prim_path}")
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

    time_code = Usd.TimeCode.Default() if when == "default" else Usd.TimeCode(float(when))
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
                rows.append([float(row[0]), float(row[1]), float(row[2]), float(row[3])])
            return rows
        # Sequence path (tuple/ list of rows)
        try:
            for r in range(4):
                row = m[r]
                rows.append([float(row[0]), float(row[1]), float(row[2]), float(row[3])])
            return rows
        except Exception:
            # Fallback: identity
            return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]

    return _ok({
        "ops": ops,
        "localMatrix": _m4_to_list(local),
        "worldMatrix": _m4_to_list(world),
    })


def tool_set_xform_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, UsdGeom, _, _ = _import_pxr()
    from pxr import Gf  # type: ignore

    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    when = params.get("time", "default")
    ops: Optional[List[Dict[str, Any]]] = params.get("ops")
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
    time_code = Usd.TimeCode.Default() if when == "default" else Usd.TimeCode(float(when))

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
        # If a transform op exists, edit its matrix directly for robustness
        transform_op = None
        for xop in xformable.GetOrderedXformOps():
            if xop.GetOpType() == UsdGeom.XformOp.TypeTransform:
                transform_op = xop
                break

        def _ensure_transform_op():
            nonlocal transform_op
            if transform_op is None:
                transform_op = xformable.AddXformOp(UsdGeom.XformOp.TypeTransform)
            return transform_op

        for entry in ops:
            op_raw = entry.get("op") or entry.get("opType") or ""
            op = str(op_raw).lower().strip()
            if op.startswith("xformop:"):
                op = op.split(":", 1)[1]
            val = entry.get("value")
            if op in ("translate", "t") and isinstance(val, (list, tuple)):
                to = _ensure_transform_op()
                try:
                    m = to.Get(time_code)
                    if m is None:
                        m = Gf.Matrix4d(1.0)
                except Exception:
                    m = Gf.Matrix4d(1.0)
                m[0][3] = float(val[0])
                m[1][3] = float(val[1])
                m[2][3] = float(val[2])
                to.Set(m, time_code)
            elif op in ("scale", "s") and isinstance(val, (list, tuple)):
                to = _ensure_transform_op()
                try:
                    m = to.Get(time_code)
                    if m is None:
                        m = Gf.Matrix4d(1.0)
                except Exception:
                    m = Gf.Matrix4d(1.0)
                m[0][0] = float(val[0])
                m[1][1] = float(val[1])
                m[2][2] = float(val[2])
                to.Set(m, time_code)
            elif op in ("rotatexyz", "r") and isinstance(val, (list, tuple)):
                to = _ensure_transform_op()
                try:
                    m = to.Get(time_code)
                    if m is None:
                        m = Gf.Matrix4d(1.0)
                except Exception:
                    m = Gf.Matrix4d(1.0)
                rx, ry, rz = [float(v) for v in val]
                Rx = Gf.Rotation(Gf.Vec3d(1, 0, 0), rx).GetMatrix()
                Ry = Gf.Rotation(Gf.Vec3d(0, 1, 0), ry).GetMatrix()
                Rz = Gf.Rotation(Gf.Vec3d(0, 0, 1), rz).GetMatrix()
                R = Rz * Ry * Rx
                # Preserve translation, replace upper-left 3x3
                t = (m[0][3], m[1][3], m[2][3])
                for r in range(3):
                    for c in range(3):
                        m[r][c] = R[r][c]
                m[0][3], m[1][3], m[2][3] = t
                to.Set(m, time_code)
            else:
                return error_response("invalid_params", f"Unsupported xform op: {op}")
    else:
        return error_response("invalid_params", "Provide either 'matrix' or 'ops'")

    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save after set_xform")
    return _ok({"output_path": root.identifier})


