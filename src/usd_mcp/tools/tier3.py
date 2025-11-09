from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from ..errors import error_response
from ..server import _import_pxr
from .tier0 import _jsonify, _normalize_file_path, _ok


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
        return error_response(
            "invalid_params", "'path','prim_path','set','selection' required"
        )
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
        return error_response(
            "set_failed", f"Failed to set variant {set_name}={selection}"
        )
    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save after set variant")
    return _ok({"variantSets": {set_name: selection}})


def tool_author_variants_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """Author variant sets and variants on a prim in a USD file.

    Supports both single variant (simple API) and batch operations (flexible).
    Can create variants with references (model variants), material bindings (material variants),
    transforms (size variants), and other attributes.

    Inputs:
      - path: USD file path
      - prim_path: prim to add variant set to
      - set: variant set name (e.g., "modelVariant", "material", "size")
      - variant: variant name (for single variant addition - simple API)
      - asset_path: optional, for model variants (creates reference)
      - internal_path: optional, for referenced asset (defaults to asset's defaultPrim if not provided)
      - material_path: optional, for material variants (creates binding)
      - xform: optional, transform matrix or ops for size/transform variants
      - attributes: optional dict of attribute values
      - variants: optional array of variant definitions (for batch operations), each with same structure as above
      - select: optional, variant name to select after creation
      - clear_local: optional bool (default true), clear local opinions on attributes that will be variantized
    """
    Usd, UsdGeom, _, _ = _import_pxr()
    try:
        from pxr import Gf, UsdShade  # type: ignore
    except Exception:
        UsdShade = None  # type: ignore
        Gf = None  # type: ignore

    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    set_name: str = params.get("set")
    variant_name: Optional[str] = params.get("variant")
    variants_array: Optional[List[Dict[str, Any]]] = params.get("variants")
    clear_local: bool = bool(params.get("clear_local", True))
    select: Optional[str] = params.get("select")

    if not path or not prim_path or not set_name:
        return error_response(
            "invalid_params", "'path', 'prim_path', and 'set' are required"
        )

    # Must provide either single variant or variants array
    if not variant_name and not variants_array:
        return error_response(
            "invalid_params", "Either 'variant' or 'variants' array must be provided"
        )
    if variant_name and variants_array:
        return error_response(
            "invalid_params", "Cannot provide both 'variant' and 'variants' array"
        )

    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")

    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return error_response("not_found", f"Prim not found: {prim_path}")

    # Capture existing reference if it exists (to preserve it in a default variant)
    existing_refs = []
    refs = prim.GetReferences()
    if refs:
        # Get existing references from the authored layer
        # Try multiple methods to ensure we capture the references
        try:
            # Method 1: GetAddedOrExplicitItems (preferred)
            ref_list = refs.GetAddedOrExplicitItems()
            for ref_item in ref_list:
                try:
                    # Sdf.Reference has assetPath and primPath properties
                    asset_path_str = (
                        str(ref_item.assetPath) if ref_item.assetPath else None
                    )
                    prim_path_str = None
                    if ref_item.primPath:
                        prim_path_str = (
                            str(ref_item.primPath)
                            if hasattr(ref_item.primPath, "__str__")
                            else ref_item.primPath.pathString
                            if hasattr(ref_item.primPath, "pathString")
                            else None
                        )
                    if asset_path_str:
                        existing_refs.append(
                            {
                                "asset_path": asset_path_str,
                                "internal_path": prim_path_str,
                            }
                        )
                except Exception:
                    continue
        except Exception:
            # Method 2: Try to get from the layer directly
            try:
                prim_spec = stage.GetRootLayer().GetPrimAtPath(prim.GetPath())
                if prim_spec and prim_spec.referenceList:
                    for ref_item in (
                        prim_spec.referenceList.prependedItems
                        + prim_spec.referenceList.explicitItems
                    ):
                        try:
                            asset_path_str = (
                                str(ref_item.assetPath) if ref_item.assetPath else None
                            )
                            prim_path_str = None
                            if ref_item.primPath:
                                prim_path_str = str(ref_item.primPath)
                            if asset_path_str:
                                existing_refs.append(
                                    {
                                        "asset_path": asset_path_str,
                                        "internal_path": prim_path_str,
                                    }
                                )
                        except Exception:
                            continue
            except Exception:
                # If we can't get existing refs, that's ok - we'll still create default variant
                pass

    # Get or create variant set (idempotent)
    vsets = prim.GetVariantSets()
    try:
        vset = vsets.GetVariantSet(set_name)
    except Exception:
        # Variant set doesn't exist, create it
        vset = vsets.AddVariantSet(set_name)

    # Normalize to list of variants to process
    variants_to_process: List[Dict[str, Any]] = []
    if variants_array:
        variants_to_process = variants_array
    elif variant_name:
        # Single variant mode - extract params for this variant
        variant_def: Dict[str, Any] = {"name": variant_name}
        if "asset_path" in params:
            variant_def["asset_path"] = params.get("asset_path")
        if "internal_path" in params:
            variant_def["internal_path"] = params.get("internal_path")
        if "material_path" in params:
            variant_def["material_path"] = params.get("material_path")
        if "xform" in params:
            variant_def["xform"] = params.get("xform")
        if "attributes" in params:
            variant_def["attributes"] = params.get("attributes")
        variants_to_process = [variant_def]

    # Check if variant set is new (doesn't have variants yet)
    # If it's new and we're creating variants with asset_path, we should create a "default" variant
    # to preserve the existing reference (if any)
    is_new_variant_set = False
    try:
        existing_variant_names = vset.GetVariantNames()
        is_new_variant_set = len(existing_variant_names) == 0
    except Exception:
        is_new_variant_set = True

    # If this is a new variant set and we're creating variants with asset_path,
    # we should always create a "default" variant to preserve existing references
    # BUT: Only if "default" is not already in the variants array
    has_default_in_array = any(
        (v.get("name") or v.get("variant") or "") == "default"
        for v in variants_to_process
    )
    should_create_default = (
        is_new_variant_set
        and any(v.get("asset_path") for v in variants_to_process)
        and not has_default_in_array
    )

    # Clear local opinions once before processing variants (per OpenUSD best practice)
    # Local opinions must be cleared outside variant context
    # BUT: Don't clear references yet if we're creating a default variant - we'll move them there first
    if clear_local:
        # Determine what needs to be cleared by checking all variants
        has_asset_path = any(v.get("asset_path") for v in variants_to_process)
        has_material_path = any(v.get("material_path") for v in variants_to_process)
        has_xform = any(v.get("xform") for v in variants_to_process)
        has_attributes = any(v.get("attributes") for v in variants_to_process)

        # Clear references if any variant will author asset_path
        # BUT: If we're creating a default variant, we'll move references there first, then clear
        # So we'll clear references AFTER creating the default variant
        # (We'll handle this after the default variant is created)

        # Clear material binding if any variant will author material_path
        if has_material_path and UsdShade:
            try:
                UsdShade.MaterialBindingAPI(prim).UnbindAllBindings()
            except Exception:
                pass

        # Clear transform ops if any variant will author xform
        if has_xform:
            xformable = UsdGeom.Xformable(prim)
            if xformable:
                xformable.ClearXformOpOrder()

        # Clear attributes if any variant will author them
        if has_attributes:
            all_attr_names = set()
            for v in variants_to_process:
                attrs = v.get("attributes")
                if attrs and isinstance(attrs, dict):
                    all_attr_names.update(attrs.keys())
            for attr_name in all_attr_names:
                attr = prim.GetAttribute(attr_name)
                if attr:
                    attr.Clear()

        # Clear references AFTER creating default variant (if we're not creating default)
        # If we ARE creating default, we'll clear references after moving them to default variant
        if has_asset_path and not should_create_default:
            refs = prim.GetReferences()
            if refs:
                refs.ClearReferences()

    # If this is a new variant set and user didn't provide "default" explicitly,
    # create a "default" variant to preserve existing references (if any)
    if should_create_default:
        default_variant_name = "default"
        try:
            vset.AddVariant(default_variant_name)
        except Exception:
            pass  # Already exists

        try:
            vset.SetVariantSelection(default_variant_name)
        except Exception as exc:
            return error_response(
                "set_failed", f"Failed to set default variant selection: {exc}"
            )

        try:
            with vset.GetVariantEditContext():
                # Add existing references to default variant (if any)
                if existing_refs:
                    for ref_info in existing_refs:
                        try:
                            if ref_info["internal_path"]:
                                prim.GetReferences().AddReference(
                                    ref_info["asset_path"], ref_info["internal_path"]
                                )
                            else:
                                prim.GetReferences().AddReference(
                                    ref_info["asset_path"]
                                )
                        except Exception as exc:
                            return error_response(
                                "reference_failed",
                                f"Failed to preserve existing reference in default variant: {exc}",
                            )
                # If no existing references, the default variant will be empty
                # This is fine - it represents the "original" state before variants
        except Exception as exc:
            return error_response(
                "variant_failed", f"Failed to author default variant: {exc}"
            )

        # After creating default variant, clear local references if they were moved
        # This is critical: we've moved the references to the default variant, so clear local ones
        if existing_refs and clear_local:
            refs = prim.GetReferences()
            if refs:
                # Clear local references - they're now in the default variant
                refs.ClearReferences()

    # If user provided "default" explicitly in variants array, we still need to clear local refs
    # (they'll be using the asset_path they provided, not the existing reference)
    elif has_default_in_array and existing_refs and clear_local:
        # User provided "default" explicitly, so clear local references
        # They'll use their own asset_path for the default variant
        refs = prim.GetReferences()
        if refs:
            refs.ClearReferences()

    # Process each variant
    created_variants: List[str] = []
    for variant_def in variants_to_process:
        # Support both "name" and "variant" as keys for variant name
        var_name: str = variant_def.get("name") or variant_def.get("variant") or ""
        if not var_name:
            continue

        # Add variant if not exists (idempotent)
        try:
            vset.AddVariant(var_name)
        except Exception:
            # Variant already exists, that's ok
            pass

        # Set variant selection to enter edit context
        try:
            vset.SetVariantSelection(var_name)
        except Exception as exc:
            return error_response(
                "set_failed", f"Failed to set variant selection: {exc}"
            )

        # Enter variant edit context
        # Following Pixar pattern: AddVariant -> SetVariantSelection -> GetVariantEditContext
        try:
            with vset.GetVariantEditContext():
                # Author reference if asset_path provided
                # Support both formats:
                # 1. Direct: {"name": "bitten", "asset_path": "./path.usda"}
                # 2. Nested: {"name": "bitten", "references": [{"asset_path": "./path.usda"}]}
                asset_path = variant_def.get("asset_path")
                internal_path_from_variant = variant_def.get("internal_path")

                # If asset_path not found, check references array
                if not asset_path:
                    references = variant_def.get("references")
                    if (
                        references
                        and isinstance(references, list)
                        and len(references) > 0
                    ):
                        # Take first reference from array
                        ref_obj = references[0]
                        if isinstance(ref_obj, dict):
                            asset_path = ref_obj.get("asset_path")
                            if not internal_path_from_variant:
                                internal_path_from_variant = ref_obj.get(
                                    "internal_path"
                                )

                if asset_path:
                    # Normalize the asset path (resolve relative paths)
                    asset_path = _normalize_file_path(asset_path)
                    if not asset_path:
                        return error_response(
                            "invalid_params",
                            f"Failed to normalize asset_path for variant '{var_name}'",
                        )
                    internal_path: str = (internal_path_from_variant or "").strip()
                    if internal_path == "/":
                        internal_path = ""

                    # Resolve internal_path from asset's defaultPrim if not provided
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
                        # Add reference inside variant context
                        # Note: We're inside GetVariantEditContext(), so this will be authored in the variant
                        if internal_path:
                            prim.GetReferences().AddReference(asset_path, internal_path)
                        else:
                            prim.GetReferences().AddReference(asset_path)
                        # Verify the reference was added (for debugging)
                        # Note: This check happens after the context exits, so we can't verify here
                    except Exception as exc:
                        # Provide more detailed error message
                        error_msg = (
                            f"Failed to add reference to variant '{var_name}': {exc}"
                        )
                        if asset_path:
                            error_msg += f" (asset_path: {asset_path}, internal_path: {internal_path or 'none'})"
                        return error_response("reference_failed", error_msg)

                # Author material binding if material_path provided
                material_path = variant_def.get("material_path")
                if material_path and UsdShade:
                    mat_prim = stage.GetPrimAtPath(material_path)
                    if not mat_prim:
                        return error_response(
                            "not_found", f"Material not found: {material_path}"
                        )
                    mat = UsdShade.Material(mat_prim)
                    if not mat:
                        return error_response(
                            "invalid_params",
                            f"Not a UsdShade.Material: {material_path}",
                        )
                    try:
                        UsdShade.MaterialBindingAPI(prim).Bind(mat)
                    except Exception as exc:
                        return error_response(
                            "bind_failed", f"Failed to bind material: {exc}"
                        )

                # Author transform if xform provided
                xform = variant_def.get("xform")
                if xform:
                    xformable = UsdGeom.Xformable(prim)
                    if not xformable:
                        return error_response(
                            "invalid_params", f"Prim is not Xformable: {prim_path}"
                        )

                    time_code = Usd.TimeCode.Default()

                    # Handle matrix format
                    if isinstance(xform, (list, tuple)) and len(xform) == 4:
                        # Check if it's a matrix (list of 4 lists)
                        if all(
                            isinstance(row, (list, tuple)) and len(row) == 4
                            for row in xform
                        ):
                            if Gf:
                                try:
                                    m = Gf.Matrix4d(xform)
                                    xf_op = xformable.AddXformOp(
                                        UsdGeom.XformOp.TypeTransform
                                    )
                                    xf_op.Set(m, time_code)
                                except Exception as exc:
                                    return error_response(
                                        "xform_failed", f"Failed to set matrix: {exc}"
                                    )
                            else:
                                return error_response(
                                    "missing_usd",
                                    "Gf not available for matrix transforms",
                                )
                        else:
                            # Treat as ops array
                            ops = xform
                    elif isinstance(xform, dict):
                        # Single op dict
                        ops = [xform]
                    else:
                        # Assume it's an ops array
                        ops = xform if isinstance(xform, list) else [xform]

                    # Handle ops format
                    if isinstance(ops, list):
                        xapi = UsdGeom.XformCommonAPI(prim)
                        translate_val = None
                        scale_val = None
                        rotate_val = None

                        for entry in ops:
                            if isinstance(entry, dict):
                                op_raw = entry.get("op") or entry.get("opType") or ""
                                op = str(op_raw).lower().strip()
                                if op.startswith("xformop:"):
                                    op = op.split(":", 1)[1]
                                val = entry.get("value")
                                if op in ("translate", "t") and isinstance(
                                    val, (list, tuple)
                                ):
                                    translate_val = [
                                        float(val[0]),
                                        float(val[1]),
                                        float(val[2]),
                                    ]
                                elif op in ("scale", "s") and isinstance(
                                    val, (list, tuple)
                                ):
                                    scale_val = [
                                        float(val[0]),
                                        float(val[1]),
                                        float(val[2]),
                                    ]
                                elif op in ("rotatexyz", "r") and isinstance(
                                    val, (list, tuple)
                                ):
                                    rotate_val = [
                                        float(val[0]),
                                        float(val[1]),
                                        float(val[2]),
                                    ]

                        if Gf:
                            if translate_val is not None:
                                xapi.SetTranslate(Gf.Vec3d(*translate_val), time_code)
                            if rotate_val is not None:
                                try:
                                    xapi.SetRotate(
                                        Gf.Vec3f(*rotate_val),
                                        UsdGeom.XformCommonAPI.RotationOrderXYZ,
                                        time_code,
                                    )
                                except Exception:
                                    try:
                                        xapi.SetRotate(Gf.Vec3f(*rotate_val))
                                    except Exception:
                                        pass
                            if scale_val is not None:
                                xapi.SetScale(Gf.Vec3f(*scale_val), time_code)

                # Author other attributes if provided
                attributes = variant_def.get("attributes")
                if attributes and isinstance(attributes, dict):
                    for attr_name, attr_value in attributes.items():
                        try:
                            attr = prim.GetAttribute(attr_name)
                            if not attr:
                                # Create attribute if it doesn't exist
                                attr = prim.CreateAttribute(attr_name, type(attr_value))
                            attr.Set(attr_value)
                        except Exception as exc:
                            return error_response(
                                "attr_failed",
                                f"Failed to set attribute {attr_name}: {exc}",
                            )

                created_variants.append(var_name)

        except Exception as exc:
            # Don't return error immediately - collect errors and continue processing
            # This allows us to process all variants even if one fails
            error_msg = f"Failed to author variant '{var_name}': {exc}"
            # For now, we'll still return error to surface issues, but log which variant failed
            return error_response("variant_failed", error_msg)

    # Set final variant selection if provided
    # If no selection provided and we created a default variant, use "default"
    # Otherwise, use the last created variant or the provided selection
    final_selection = select
    if not final_selection and should_create_default:
        final_selection = "default"
    elif not final_selection and created_variants:
        final_selection = created_variants[-1]

    if final_selection:
        try:
            vset.SetVariantSelection(final_selection)
        except Exception as exc:
            return error_response("set_failed", f"Failed to set final selection: {exc}")

    # Save
    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save after authoring variants")

    # Include default variant in the list if it was created
    all_variants = created_variants.copy()
    if should_create_default and "default" not in all_variants:
        all_variants.insert(0, "default")

    return _ok(
        {
            "prim_path": prim_path,
            "set": set_name,
            "variants": all_variants,
            "selection": final_selection or None,
        }
    )


# Materials
def tool_list_materials_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
    Usd, _, _, _ = _import_pxr()
    try:
        from pxr import UsdShade  # type: ignore
    except Exception:  # pragma: no cover
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
    except Exception:
        return error_response("missing_usd", "UsdShade not available")
    path = _normalize_file_path(params.get("path"))
    prim_path: str = params.get("prim_path")
    material_path: str = params.get("material_path")
    if not path or not prim_path or not material_path:
        return error_response(
            "invalid_params", "'path','prim_path','material_path' required"
        )
    stage = Usd.Stage.Open(path)
    if stage is None:
        return error_response("open_failed", f"Failed to open stage: {path}")
    prim = stage.GetPrimAtPath(prim_path)
    mat_prim = stage.GetPrimAtPath(material_path)
    if not prim or not mat_prim:
        return error_response("not_found", "prim or material not found")
    mat = UsdShade.Material(mat_prim)
    if not mat:
        return error_response(
            "invalid_params", f"Not a UsdShade.Material: {material_path}"
        )
    UsdShade.MaterialBindingAPI(prim).Bind(mat)
    root = stage.GetRootLayer()
    if not root.Save():
        return error_response("save_failed", "Failed to save after bind")
    return _ok({"bound": True})


def tool_unbind_material_in_file(params: Dict[str, Any]) -> Dict[str, Any]:
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
    return _ok(
        {
            "material_path": None,
            "bindingRelExists": bool(rel_exists),
            "bindingTargets": targets,
        }
    )


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
    if "clippingRange" in params_in and isinstance(
        params_in["clippingRange"], (list, tuple)
    ):
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
    time_code = (
        Usd.TimeCode.Default() if when == "default" else Usd.TimeCode(float(when))
    )
    cache = UsdGeom.BBoxCache(
        time_code,
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
    )
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
        t = (
            [float(world_m[0][3]), float(world_m[1][3]), float(world_m[2][3])]
            if Gf is not None
            else [0.0, 0.0, 0.0]
        )
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
        if (
            skip_if_exists
            and isinstance(output_path, str)
            and os.path.exists(output_path)
        ):
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
        return error_response(
            "invalid_params", "'path', 'prim_path', 'asset_path' are required"
        )
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
    return _ok(
        {
            "prim_path": prim_path,
            "asset_path": asset_path,
            "internal_path": internal_path or None,
        }
    )


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
            results.append(
                {
                    "prim_path": prim_path,
                    "ok": False,
                    "error": "missing prim_path or asset_path",
                }
            )
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
            results.append(
                {
                    "prim_path": prim_path,
                    "asset_path": asset_path,
                    "internal_path": internal_path or None,
                    "ok": True,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "prim_path": prim_path,
                    "asset_path": asset_path,
                    "ok": False,
                    "error": str(exc),
                }
            )

    root = stage.GetRootLayer()
    if not root.Save():
        return error_response(
            "save_failed", "Failed to save after batch add references"
        )
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
      - clearExisting: bool (default false) — if true, clear all root prims before composing
    """
    Usd, UsdGeom, _, _ = _import_pxr()
    output_path: str = _normalize_file_path(params.get("output_path"))
    assets: List[Dict[str, Any]] = params.get("assets") or []
    container_root_param = params.get("container_root")
    flatten: bool = bool(params.get("flatten", True))
    up_axis: Optional[str] = params.get("upAxis")
    set_default: bool = bool(params.get("setDefaultPrim", True))
    skip_if_exists: bool = bool(params.get("skipIfExists", True))
    clear_existing: bool = bool(params.get("clearExisting", False))
    if not output_path:
        return error_response("invalid_params", "'output_path' is required")
    if not isinstance(assets, list) or not assets:
        return error_response("invalid_params", "'assets' must be a non-empty array")

    # Auto-derive container_root from output_path if not explicitly provided
    if not container_root_param or container_root_param == "/Assets":
        # Extract filename without extension from output_path
        output_basename = os.path.basename(output_path)
        output_name, _ = os.path.splitext(output_basename)
        if output_name:
            container_root = "/" + output_name
        else:
            container_root = "/Assets"
    else:
        container_root = container_root_param

    # Open-or-create stage
    stage = None
    if os.path.exists(output_path):
        stage = Usd.Stage.Open(output_path)
        # Optionally clear all existing root-level prims
        # This ensures a clean composition when requested
        if clear_existing:
            root_prims = list(stage.GetPseudoRoot().GetChildren())
            for prim in root_prims:
                try:
                    stage.RemovePrim(prim.GetPath())
                except Exception:
                    pass
        # Update upAxis if explicitly provided
        if up_axis is not None:
            if str(up_axis).upper().startswith("Z"):
                UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
            else:
                UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
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
    # Get output directory for resolving relative paths
    output_dir = os.path.dirname(os.path.abspath(output_path))

    for a in assets:
        src_path_raw = a.get("asset_path")
        if not src_path_raw:
            continue
        src_path = _normalize_file_path(src_path_raw)
        if not src_path:
            continue

        # Resolve relative paths relative to output file's directory
        # Keep original relative path for the reference, but resolve for opening
        if not os.path.isabs(src_path):
            # Resolve relative to output file's directory
            resolved_src_path = os.path.normpath(os.path.join(output_dir, src_path))
        else:
            resolved_src_path = src_path

        name = (a.get("name") or _basename_noext(src_path)).strip() or _basename_noext(
            src_path
        )
        # Check if internal_path was explicitly set to null (reference root)
        internal_path_raw = a.get("internal_path")
        if "internal_path" in a and internal_path_raw is None:
            # Explicitly null - reference root without internal_path
            internal_path = None
        elif internal_path_raw:
            internal_path = str(internal_path_raw).strip()
        else:
            # Not provided or empty - will resolve defaultPrim
            internal_path = ""

        # Optionally export USDZ -> USDA sibling
        # Use resolved path for opening, but keep original for reference
        ref_path_for_open = resolved_src_path
        ref_path_for_ref = src_path  # Keep original relative path for reference

        try:
            # Check if we should flatten - check both original and resolved paths
            is_usdz = str(src_path).lower().endswith(".usdz") or str(
                resolved_src_path
            ).lower().endswith(".usdz")
            if flatten and is_usdz:
                # For flattened target, resolve relative to original src_path location
                if not os.path.isabs(src_path):
                    target = os.path.splitext(resolved_src_path)[0] + ".usda"
                else:
                    target = os.path.splitext(src_path)[0] + ".usda"

                # Check if we need to recreate (always recreate if converting from Z-up to Y-up)
                should_recreate = False
                if not (skip_if_exists and os.path.exists(target)):
                    # File doesn't exist or skip_if_exists is False - need to create
                    should_recreate = True
                elif up_axis is not None:
                    # File exists - check if we're converting from Z-up to Y-up - always recreate in this case
                    st_check = Usd.Stage.Open(ref_path_for_open)
                    if st_check is not None:
                        original_up_axis = UsdGeom.GetStageUpAxis(st_check)
                        if original_up_axis == UsdGeom.Tokens.z and str(
                            up_axis
                        ).upper().startswith("Y"):
                            should_recreate = True

                # If file exists and we're not recreating, we still need to update paths to point to target
                if not should_recreate and os.path.exists(target):
                    # File exists and we're not recreating - just update upAxis if needed
                    if up_axis is not None:
                        st = Usd.Stage.Open(target)
                        if st is not None:
                            if str(up_axis).upper().startswith("Z"):
                                UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
                            else:
                                UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.y)
                            # Save the updated upAxis
                            root = st.GetRootLayer()
                            root.Save()
                    # Update paths to point to target
                    if not os.path.isabs(src_path):
                        try:
                            ref_path_for_ref = os.path.relpath(target, output_dir)
                        except ValueError:
                            ref_path_for_ref = target
                    else:
                        ref_path_for_ref = target
                    ref_path_for_open = target
                elif should_recreate:
                    st = Usd.Stage.Open(ref_path_for_open)
                    if st is None:
                        return error_response(
                            "open_failed", f"Failed to open asset: {ref_path_for_open}"
                        )
                    # Check original upAxis
                    original_up_axis = UsdGeom.GetStageUpAxis(st)
                    # Set upAxis on the flattened file if specified
                    if up_axis is not None:
                        if str(up_axis).upper().startswith("Z"):
                            UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.z)
                        else:
                            UsdGeom.SetStageUpAxis(st, UsdGeom.Tokens.y)
                        # If converting from Z-up to Y-up, rotate -90 degrees around X
                        if original_up_axis == UsdGeom.Tokens.z and str(
                            up_axis
                        ).upper().startswith("Y"):
                            from pxr import Gf  # type: ignore

                            # Apply rotation to all prims recursively
                            # First, try to find a "model" prim (common in Blender exports)
                            # If found, apply rotation there; otherwise apply to root prims
                            def apply_rotation_to_prim(prim):
                                xformable = UsdGeom.Xformable(prim)
                                if xformable:
                                    xapi = UsdGeom.XformCommonAPI(prim)
                                    # Get existing rotation from xformOps if present
                                    existing_rotate = None
                                    for op in xformable.GetOrderedXformOps():
                                        op_name = op.GetOpName()
                                        if op_name.startswith("xformOp:rotate"):
                                            try:
                                                rot_val = op.Get(Usd.TimeCode.Default())
                                                if rot_val is not None:
                                                    existing_rotate = rot_val
                                                    break
                                            except Exception:
                                                pass

                                    if existing_rotate is not None:
                                        # Combine with -90 X rotation
                                        new_rotate = (
                                            existing_rotate[0] - 90.0,
                                            existing_rotate[1],
                                            existing_rotate[2],
                                        )
                                    else:
                                        new_rotate = (-90.0, 0.0, 0.0)
                                    xapi.SetRotate(
                                        Gf.Vec3f(*new_rotate),
                                        UsdGeom.XformCommonAPI.RotationOrderXYZ,
                                    )

                            # Look for "model" prim first (common in Blender exports)
                            model_prim = None
                            root_prims = st.GetPseudoRoot().GetChildren()
                            for root_prim in root_prims:
                                # Check if this prim is named "model"
                                if root_prim.GetName() == "model":
                                    model_prim = root_prim
                                    break
                                # Check children for "model" prim
                                for child in root_prim.GetChildren():
                                    if child.GetName() == "model":
                                        model_prim = child
                                        break
                                if model_prim:
                                    break

                            if model_prim:
                                # Apply rotation to model prim
                                apply_rotation_to_prim(model_prim)
                            else:
                                # Apply rotation to all root prims
                                for root_prim in root_prims:
                                    apply_rotation_to_prim(root_prim)
                    ok = st.Export(target)
                    if not ok:
                        return error_response(
                            "export_failed", f"Failed to export {target}"
                        )
                    # Update paths to point to target after creation
                    if not os.path.isabs(src_path):
                        try:
                            ref_path_for_ref = os.path.relpath(target, output_dir)
                        except ValueError:
                            ref_path_for_ref = target
                    else:
                        ref_path_for_ref = target
                    ref_path_for_open = target
        except Exception as exc:
            return error_response("export_failed", str(exc))

        # Resolve defaultPrim only if internal_path is empty string (not explicitly None)
        if internal_path == "" or internal_path == "/":
            try:
                rstage = Usd.Stage.Open(ref_path_for_open)
                if rstage:
                    dp = rstage.GetDefaultPrim()
                    if dp and dp.IsValid():
                        internal_path = dp.GetPath().pathString
                    else:
                        internal_path = ""
            except Exception:
                internal_path = ""

        # For layout files (multiple assets), create wrapper Xform structure to preserve asset transforms
        # Structure: /container/name (wrapper for layout transforms) -> /container/name/asset_name (reference preserves asset transforms)
        # For single asset assemblies, keep reference directly on the prim
        is_layout = len(assets) > 1

        container_root_leaf = container_root.rstrip("/").split("/")[-1]
        if name == container_root_leaf:
            wrapper_path = container_root
        else:
            wrapper_path = container_root.rstrip("/") + "/" + name

        if is_layout:
            # Layout file: create wrapper Xform for layout transforms
            wrapper_prim = stage.GetPrimAtPath(wrapper_path)
            if not wrapper_prim:
                wrapper_prim = stage.DefinePrim(wrapper_path, "Xform")

            # Get asset's defaultPrim name for the reference prim
            ref_prim_name = None
            try:
                rstage = Usd.Stage.Open(ref_path_for_open)
                if rstage:
                    dp = rstage.GetDefaultPrim()
                    if dp and dp.IsValid():
                        ref_prim_name = dp.GetName()
            except Exception:
                pass
            if not ref_prim_name:
                # Fallback to asset filename
                ref_prim_name = _basename_noext(ref_path_for_ref) or "asset"

            # Create child Xform for the reference (preserves asset transforms)
            ref_prim_path = wrapper_path.rstrip("/") + "/" + ref_prim_name
            ref_prim = stage.GetPrimAtPath(ref_prim_path)
            if not ref_prim:
                ref_prim = stage.DefinePrim(ref_prim_path, "Xform")

            # Put reference on child prim
            prim = ref_prim
        else:
            # Single asset assembly: reference directly on the prim (existing behavior)
            prim = stage.GetPrimAtPath(wrapper_path)
            if not prim:
                prim = stage.DefinePrim(wrapper_path, "Xform")

        try:
            if internal_path is None:
                # Explicitly null - reference root without internal_path
                prim.GetReferences().AddReference(ref_path_for_ref)
            elif internal_path:
                # Has internal_path - use it
                prim.GetReferences().AddReference(ref_path_for_ref, internal_path)
            else:
                # Empty after resolution attempt - reference root
                prim.GetReferences().AddReference(ref_path_for_ref)
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
