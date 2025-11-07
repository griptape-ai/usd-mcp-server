Sample natural-language prompts for Griptape (MCP)

**Key Workflow for Maya Compatibility:**
1. **Asset Assemblies from USDZ files**: Use `flatten: true` and `upAxis: "Y"` - this creates a flattened USDA file with Y-up automatically and applies a -90 degree X rotation to correct orientation when converting from Z-up to Y-up
2. **Layout Files**: Use `flatten: false` and `upAxis: "Y"` - references the Y-up asset assemblies
3. **Transforms**: Use `setXformFile` (NOT `batchSetAttributesInFile`) - scale from referenced files is automatically preserved
4. **Internal Paths**: Set `internal_path: null` to reference the root of asset files without an internal path
=================================================

Use these directly as chat prompts in Griptape Nodes. They map to the current Tier 0 tools and the added stateless helpers. Replace <path> with your file when needed.

Paths
- Absolute: /Users/kyleroche/Documents/Development/usd-mcp/samples/simple.usda
- Normalized variants also work: Users/kyleroche/Documents/Development/usd-mcp/samples/simple.usda

Agent Rules
- Tool selection
  - Prefer stateless tools: summarizeFile, listPrimsFile, primInfoFile, getAttrFile, setAttrFile, createPrimFile, deletePrimFile, getXformFile, setXformFile, getBoundsFile.
  - For composition/assembly, prefer composeReferencedAssembly (single call) or addReferencesBatchInFile.
  - The older per-reference tools may be hidden; do not rely on addReferenceInFile/addSublayerInFile.
  - Avoid persistent stage_id flows unless explicitly requested; if needed, use openStage, listOpenStages, closeStage.
  - Use only alphanumeric tool names (camelCase) as advertised by the server.
- Inputs
  - The MCP server automatically handles Griptape's `{"values":{...}}` wrapper, so you can provide inputs either way.
  - Use canonical keys: path, prim_path, root, depth, attr, value, time, ops, matrix.
  - Trim whitespace in all path-like strings; prefer absolute paths when available.
- Outputs
  - If asked for strict JSON, final message must be exactly the tool’s JSON result (no prose, no code fences, no extra keys).
  - When an Output Schema is present, conform exactly to it; consider single-object outputs like {"worldMatrix": [...]}, {"min": [...], "max": [...]}, etc.
- Recovery
  - On validation errors about missing fields, retry with canonical flat inputs.
  - If a stage_id becomes unknown, switch to stateless tools (…File variants) instead of reopening stateful sessions.
  - On “Tool name can only contain letters and numbers”, ensure tool names are camelCase without symbols.
- Transforms
  - For setXformFile, prefer ops (translate, rotateXYZ in degrees, scale). Fallback to a 4×4 matrix when necessary.
  - Ops input MUST be an array of entries: [{"op":"translate","value":[x,y,z]}]. Do not use a single dict.
  - **IMPORTANT**: Always use setXformFile to set transforms, NOT batchSetAttributesInFile. xformOps must be created properly using setXformFile.
  - When setting transforms on prims that reference other files, the transforms in the referenced files are preserved automatically by USD composition. The transforms you set on the referencing prim are separate and additive. **Scale from referenced files is automatically preserved** - if you only set translate and rotate, the scale from the referenced file will still be included in the xformOpOrder.
  - Verify transforms by calling getXformFile and reading worldMatrix.
- Attributes
  - Use getAttrFile/setAttrFile for single reads/writes; use time: "default" unless a timeCode is requested.
  - When setting many attributes, prefer the batched writer setAttrsFile to stay under tool-call limits.
- Serialization
  - Return numbers as numbers and vectors/matrices as JSON arrays; avoid tuples or stringified objects.
  - Never use parentheses for arrays (no tuples) – always use [ ... ] for JSON arrays.

Composition (preferred)
- One‑shot compose with optional USDZ→USDA flatten, container root, and defaultPrim:
  - "Execute one action and print only the tool's JSON result. No prose. Call composeReferencedAssembly with: {\"output_path\":\"<assembly.usda>\",\"assets\":[{\"asset_path\":\"<a.usdz>\",\"name\":\"a\",\"internal_path\":\"/root/model\"},{\"asset_path\":\"<b.usdz>\",\"name\":\"b\",\"internal_path\":\"/root/model\"}],\"container_root\":\"/Assets\",\"flatten\":true,\"upAxis\":\"Z\",\"setDefaultPrim\":true,\"skipIfExists\":true}."
- Notes:
  - internal_path can be omitted; the server resolves it from the asset's defaultPrim. Supplying "/root/model" explicitly makes viewers resolve predictably.
  - composeReferencedAssembly is idempotent: it opens or creates stages, ensures container root, and sets defaultPrim when requested.
  - **container_root**: If omitted or set to `/Assets`, automatically derives from output_path filename (e.g., `/path/to/blue_shoe_asset.usda` → `/blue_shoe_asset`). If explicitly provided, uses that value.
  - **flatten**: Set `flatten: false` to keep USDZ files as references (don't convert to USDA). Default is `true`. **IMPORTANT FOR MAYA**: When creating asset assemblies from Z-up USDZ files for Maya, set `flatten: true` and `upAxis: "Y"` - this will create a flattened USDA file with Y-up in the same directory as the original USDZ (e.g., `apple.usdz` → `apple.usda`). The flattened file will have the correct upAxis set automatically, and if converting from Z-up to Y-up, a -90 degree X rotation will be applied to the root prims to correct the orientation.
  - **clearExisting**: Set `clearExisting: true` to clear all root prims before composing. Default is `false`.
  - **upAxis**: Set to `"Y"` for Maya compatibility (default is `"Z"`). **CRITICAL FOR MAYA**: Maya expects Y-up by default. **Always use `upAxis: "Y"` for both asset assemblies and layout files that will be used in Maya**. **IMPORTANT**: If the original USDZ files are Z-up, set `flatten: true` and `upAxis: "Y"` when creating asset assemblies - this will flatten the USDZ to USDA, set the upAxis to Y on the flattened file automatically, and apply a -90 degree X rotation to the root prims to correct the orientation when converting from Z-up to Y-up. USD does NOT automatically convert transforms when referencing files with different upAxis values - the transforms in the referenced file are still in the original upAxis space, but they're being interpreted in the referencing file's upAxis space, which causes orientation issues. The upAxis is updated even when opening existing files if explicitly provided. If you have existing flattened files with `upAxis = "Z"`, they will be updated to Y-up when you call `composeReferencedAssembly` with `upAxis: "Y"` and `flatten: true` (even if the file already exists).
  - **Relative paths**: Use relative paths like `"./model/asset.usdz"` for asset_path - they resolve relative to the output file's directory.
  - **internal_path**: In asset objects, controls which prim in the referenced file to reference:
    - If omitted or empty string: automatically resolves the referenced file's defaultPrim
    - If explicitly set to `null`: references the root of the file without an internal_path (e.g., `@./apple/apple_asset.usda@` instead of `@./apple/apple_asset.usda@</apple_asset>`)
    - If set to a specific path: uses that path (e.g., `"/root/model"`)
    - When user says "reference the root" or "without internal_path", set `internal_path: null` for each asset
- Example for single asset assembly (from USDZ for Maya):
  - "Create an assembly by referencing ./model/blue_shoe.usdz as blue_shoe_asset. Use composeReferencedAssembly with: {\"output_path\":\"/path/to/blue_shoe_asset.usda\",\"assets\":[{\"asset_path\":\"./model/blue_shoe.usdz\",\"name\":\"blue_shoe_asset\"}],\"flatten\":true,\"clearExisting\":true,\"upAxis\":\"Y\"}. Note: container_root is automatically derived from output_path filename (/blue_shoe_asset), so it can be omitted. For Maya compatibility, use flatten: true and upAxis: \"Y\" - this will create a flattened USDA file (blue_shoe.usda) with Y-up in the same directory as the original USDZ."
- Example for layout assembly (multiple assets):
  - "Create a layout assembly by referencing multiple asset files. Use composeReferencedAssembly with: {\"output_path\":\"/path/to/layout.usda\",\"assets\":[{\"asset_path\":\"./apple/apple_asset.usda\",\"name\":\"apple\",\"internal_path\":null},{\"asset_path\":\"./blue_shoe/blue_shoe_asset.usda\",\"name\":\"blue_shoe\",\"internal_path\":null}],\"container_root\":\"/World\",\"flatten\":false,\"clearExisting\":true,\"upAxis\":\"Y\"}. When user says 'reference the root' or 'without internal_path', set internal_path: null for each asset. IMPORTANT: Always set upAxis: \"Y\" for layout files and asset assemblies that will be used in Maya. Note: Transforms in the referenced asset files (like -90 X rotation and scale) are preserved and combined with layout transforms. Scale from referenced files is automatically preserved when setting transforms."

Composition (fallback batch)
- If composeReferencedAssembly is unavailable:
  - exportUsdFile for each USDZ → USDA with { flatten:true, skipIfExists:true }
  - createStage { upAxis:"Z" }
  - addReferencesBatchInFile with items: [{ prim_path:"/Assets/<name>", asset_path:"<asset.usda>", internal_path:"/root/model" }, …]
  - setDefaultPrimFile { prim_path:"/Assets" }

Two‑agent flow (Describe → Build)
- Container pattern: Represent each visible object with a container Xform and a geometry child named Geom. Apply translate/rotate on the container; apply size/scale on Geom. Children attach to the container (not to Geom).
- Dimensions vs scale (use dimensions in Describe):
  - Sphere: diameter
  - Cube: edge (uniform)
  - Cone: baseDiameter and height
  - Platform/Base: dimensions [width, depth, height]
- Build mapping (how the builder should convert dimensions → USD):
  - Sphere.diameter → /Sphere/Geom.radius = diameter/2
  - Cube.edge → /Cube/Geom.size = edge (if you only have a 3-array, use xformOp:scale = array/2 on Geom)
  - Cone.baseDiameter,height → /Cone/Geom.radius = baseDiameter/2; /Cone/Geom.height = height
  - Platform.dimensions [W,D,H] → /Floor/Geom xformOp:scale = [W/2, D/2, H/2]; /Floor translate.z = H/2
- Resting and spacing:
  - Z-up world. platformTopZ = platform.height/2. For each object: centerZ = platformTopZ + (objectHeight/2).
  - Side-by-side without overlap: along X, separate centers by (widthA/2 + widthB/2 + margin), margin = 0.5.
- Colors:
  - Use primvars:displayColor on Geom. Provide [r,g,b]. Server accepts displayColor or primvars:displayColor and coerces [r,g,b] → [[r,g,b]].

Describe output contract (consumed by Build)
```json
{
  "platform": { "name": "Floor", "dimensions": [10, 10, 1], "color": [1,1,1] },
  "objects": [
    { "name": "Sphere", "type": "Sphere", "diameter": 3, "translate": [-5, 0, 2.5], "color": [1,0.2,0.2] },
    { "name": "Cube",   "type": "Cube",   "edge": 3,     "translate": [ 0, 0, 2.5], "color": [0.4,0.6,1] },
    { "name": "Cone",   "type": "Cone",   "baseDiameter": 2, "height": 4, "translate": [ 5, 0, 3], "color": [1,0.6,0.3] }
  ]
}
```

Layout (Describe → Build handoff)
- Assume Z-up unless specified. If platform thickness is unknown, assume thickness = 2.0 so platform top Z = +1.0.
- Report sizes as geometry (not transform scale): Sphere uses diameter; Cube uses edge length; Cone uses base diameter and height.
- Ensure no overlaps: along X, separate centers by (widthA/2 + widthB/2 + margin) with margin = 0.5.
- Rest on platform: set Z center = platformTop + (objectHeight/2).
- Emit a machine-readable layout block the build agent can consume:
```json
{
  "layout": {
    "upAxis": "Z",
    "platform": { "path": "/Floor/Platform", "thickness": 2.0, "topZ": 1.0 },
    "margin": 0.5,
    "objects": [
      { "name": "Sphere", "type": "Sphere", "size": { "diameter": 3.0 }, "translate": [-5.0, 0.0, 2.5] },
      { "name": "Cube",   "type": "Cube",   "size": { "edge": 3.0 },     "translate": [ 0.0, 0.0, 2.5] },
      { "name": "Cone",   "type": "Cone",   "size": { "baseDiameter": 2.0, "height": 4.0 }, "translate": [ 5.0, 0.0, 3.0] }
    ]
  }
}
```

Stateless (recommended for reliability)
- "Summarize this USD file: <path>"
- "List prims in file at <path> to depth 1."
- "Give me detailed info for /World/Cube in <path>."
- "What is the value of size on /World/Cube in <path>?"
- "Create a Cube at /World/MyCube in <path> and save, then list prims under /World."
- "Delete /World/MyCube in <path> and save, then list prims under /World."
- "Get the local and world transform for /World/Cube in <path>."
- "Set /World/Cube translate to [1, 2, 3] in <path>, save, then get the transform again."

Stage lifecycle (persistent session)
- "Open <path> and list open stages."
- "Close the previously opened stage, then list open stages again."

Attribute reads/writes (stateless write path available)
- "Set /World/Cube.size to 1.5 in <path>, save, then read back /World/Cube.size."
- "Set /World/Cube.visibility to invisible in <path>, save, then read back /World/Cube.visibility."
 - Colors (strict JSON final):
   - "Return only a single JSON object with key displayColor. No prose, no code fences, no extra keys. Steps: 1) Call setAttrFile with {\"path\":\"<path>\",\"prim_path\":\"/World/Cube\",\"attr\":\"primvars:displayColor\",\"value\":[[1,0,0]],\"time\":\"default\"}. 2) Call getAttrFile with {\"path\":\"<path>\",\"prim_path\":\"/World/Cube\",\"attr\":\"primvars:displayColor\",\"time\":\"default\"}. 3) Output exactly {\"displayColor\": <value from step 2>} only."

Batch attribute writes (preferred when >2 writes)
- "Batch set these colors in <path> and save in a single call: /Floor=[1,1,1], /Floor/Sphere=[1,0,0], /Floor/Cube=[0.678,0.847,0.902], /Floor/Cone=[1,0.647,0]. Use setAttrsFile with items array, then return output_path and per-item status."
- Example input (copy/paste into a tool block if needed):
```json
{
  "path": "/Users/kyleroche/Documents/Development/usd-mcp/scene.usda",
  "items": [
    {"prim_path": "/Floor",        "attr": "primvars:displayColor", "value": [1,1,1]},
    {"prim_path": "/Floor/Sphere", "attr": "primvars:displayColor", "value": [1,0,0]},
    {"prim_path": "/Floor/Cube",   "attr": "primvars:displayColor", "value": [0.678,0.847,0.902]},
    {"prim_path": "/Floor/Cone",   "attr": "primvars:displayColor", "value": [1,0.647,0]}
  ]
}
```
Notes:
- Provide [r,g,b] for displayColor; the server coerces to [[r,g,b]].
- You can mix different attrs in the same items array.

Transforms (Tier 2)
- Translate via ops: "Translate /World/Cube to [2, 0, 0] in <path>, save, then get the transform and show worldMatrix."
- Rotate via ops (degrees XYZ): "Rotate /World/Cube by [0, 45, 0] (degrees XYZ) in <path>, save, then get the transform and show worldMatrix."
- Combined ops: "Translate /World/Cube to [2, 0, 0] and rotate [0, 45, 0] (degrees XYZ) in <path>, save, then get the transform and show worldMatrix."
- Matrix fallback (robust): "Set /World/Cube transform matrix in <path> to [[1,0,0,0],[0,0.70710678,-0.70710678,0],[0,0.70710678,0.70710678,0],[0,0,0,1]], save, then getXformFile and show worldMatrix."

Tier 3 (variants, materials, cameras, bounds)
- "List variant sets and selections for /World/Cube in <path>."
- "If a variant set named modelVariant exists on /World/Cube, set its selection to 'high' and save; report the new selection."
- "List materials in <path>, then bind the first material to /World/Cube and save; report /World/Cube's material binding."
- "Unbind any materials on /World/Cube in <path> and save, then confirm binding is removed."
 - Binding check (strict JSON final):
   - "Return only a single JSON object with key material_path. No prose, no code fences, no extra keys. Steps: 1) Call getMaterialBindingFile with {\"path\":\"<path>\",\"prim_path\":\"/World/Cube\"}. 2) Output exactly {\"material_path\": <value from step 1.material_path>} only."
- "List cameras in <path>. If none, create /World/Camera1 with focalLength=50 and horizontalAperture=36, save, then read its parameters."
- "Compute the world-space bounding box for /World/Cube in <path> and return min/max."
- Bounds (strict JSON final):
  - "Return only a single JSON object with keys min and max. No prose, no code fences, no extra keys. Steps: 1) Call getBoundsFile with {\"path\":\"<path>\",\"prim_path\":\"/World/Cube\"}. 2) Output exactly the tool’s JSON result as the final message. Do not wrap or reformat it."
  - Example (copy/paste):
    - "Return only a single JSON object with keys min and max. No prose, no code fences, no extra keys. Steps: 1) Call getBoundsFile with {\"path\":\"/Users/kyleroche/Documents/Development/usd-mcp/samples/simple.usda\",\"prim_path\":\"/World/Cube\"}. 2) Output exactly the tool’s JSON result as the final message. Do not wrap or reformat it."
  - Note: On some USD builds, BBoxCache may return centered world bounds under hierarchy. The server applies fallbacks; if bounds still appear centered, treat them as local-space extents and use getXformFile.worldMatrix for truth.
- "Export <path> flattened to /tmp/flat.usda and export to USDZ /tmp/pack.usdz."

Variants (authoring and selection)
- Use authorVariantsInFile for creation/update in one call (flat JSON only). Do NOT write variantSets directly and do NOT loop setVariantFile to create variants.
- After authoring, select with setVariantFile. You can have multiple variant sets on the same prim (e.g., asset, size, look, lod).
- Prefer referencing USDZs without flattening to keep packaged textures intact.

Quick NL prompt (asset swap)
- “Create/overwrite <mop_variants.usda> (Z-up). Ensure Xform /World/Mop. Author variants on /World/Mop in ONE call: set ‘asset’ with
  - asset.mop: reference </abs/path/mop.usdz> using asset defaultPrim (no flatten)
  - asset.broom: reference </abs/path/broom.usdz> using asset defaultPrim (no flatten)
  Select asset=mop. Save and export to </abs/path/mop_combined.usdz>. Flat JSON only; don’t write ‘variantSets’.”

Quick NL prompt (two sets: asset + size)
- “Create/overwrite <stage.usda> (Z-up). Ensure Xform /World/Item. Author variants in two calls:
  1) authorVariantsInFile set=‘asset’: mop → </…/mop.usdz>, broom → </…/broom.usdz>
  2) authorVariantsInFile set=‘size’: full → identity, small → xformOp:transform = diag([0.3,0.3,0.3,1])
  Select asset=mop and size=small. Export to </…/combined.usdz>. Flat JSON only.”

authorVariantsInFile (explicit JSON example)
```json
{
  "path": "/abs/mop_variants.usda",
  "prim_path": "/World/Mop",
  "set": "model",
  "variants": [
    { "name": "mop", "asset_path": "/abs/mop.usdz" },
    { "name": "mop_small", "asset_path": "/abs/mop_small.usdz",
      "xform": { "matrix": [[0.3,0,0,0],[0,0.3,0,0],[0,0,0.3,0],[0,0,0,1]] } }
  ],
  "select": "mop"
}
```

Selecting a variant (stateless)
```json
{ "path": "/abs/mop_variants.usda", "prim_path": "/World/Mop", "set": "model", "selection": "mop" }
```

Verifying variants
```json
{ "path": "/abs/mop_variants.usda", "prim_path": "/World/Mop" }
```

Batch fallback (only if authorVariantsInFile unavailable)
- Supported variant-context suffix: use dot+colon on prim_path to enter a variant edit context: 
  - "/World/Mop.model:mop" and "/World/Mop.model:mop_small"
- Example items array:
```json
{
  "path": "/abs/mop_variants.usda",
  "items": [
    { "prim_path": "/World/Mop.model:mop", "attr": "references",
      "value": [{ "asset_path": "/abs/mop.usdz" }] },
    { "prim_path": "/World/Mop.model:mop_small", "attr": "references",
      "value": [{ "asset_path": "/abs/mop_small.usdz" }] },
    { "prim_path": "/World/Mop.model:mop_small", "attr": "xformOp:transform",
      "value": [[0.3,0,0,0],[0,0.3,0,0],[0,0,0.3,0],[0,0,0,1]] }
  ]
}
```
- Notes:
  - Direct writes to ‘variantSets’ or ‘*:variantSelection’ are rejected; use authorVariantsInFile or setVariantFile.
  - Do not use braces in prim paths; use dot+colon (set:variant) context only.

Naming guidance
- Choose set names by intent: ‘asset’ (swap models), ‘size’ (scale), ‘look’ (materials), ‘lod’ (levels of detail), ‘state’ (poses/config).
- Keep tokens lowercase, consistent across assets; e.g., asset=mop|broom, size=full|small.

Path robustness
- "Summarize  <path with extra spaces>  ."
- "Summarize Users/…/simple.usda." (no leading slash)
- "Summarize ~/Documents/…/simple.usda." (tilde expansion)
- "Summarize ${HOME}/Documents/…/simple.usda." (env var)

Persistent (requires MCP process to persist between actions)
- "Open <path> and give me the stage summary (layers, root prims, timecodes, up axis, meters per unit)."
- "Open <path>, then list prims under / to depth 2."
- "Open <path>, read size on /World/Cube, set it to 1.5, then save the stage."

Diagnostics and error handling
- "Try to read attribute doesNotExist on /World/Cube in <path> and report the error code."
- "Call get stage summary with a random stage id and show the error only."
- "Open /does/not/exist.usda and report the error code only."

Robustness and errors
- "Open  <path with extra spaces>  and summarize it."
- "Try to read attribute doesntexist on /World/Cube from <path> and report the error code."
- "Call get stage summary with a random stage id and show the error."

Notes
- If the agent loses the stage_id between steps, prefer the stateless forms ("…in file").
- Keys like Path/Stage Id are tolerated; the server normalizes them.
- Tools are advertised with alphanumeric names (e.g., summarizeFile, listPrimsFile, primInfoFile, getAttrFile, setAttrFile, createPrimFile, deletePrimFile, getXformFile, setXformFile); clients that require letters/numbers only are supported.

Strict JSON finals (Griptape)
- If you enable an Output Schema that expects JSON, add a system rule for the task: "Final message must be exactly the tool’s JSON result, no prose, no code fences, no extra keys." Consider disabling streaming for that task to avoid partial JSON deltas.

Output Schema snippets (copy/paste)
- Bounds (min/max):
```json
{
  "type": "object",
  "properties": {
    "min": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 },
    "max": { "type": "array", "items": { "type": "number" }, "minItems": 3, "maxItems": 3 }
  },
  "required": ["min", "max"],
  "additionalProperties": false
}
```
- Transform (worldMatrix only):
```json
{
  "type": "object",
  "properties": {
    "worldMatrix": {
      "type": "array",
      "items": {
        "type": "array",
        "items": { "type": "number" },
        "minItems": 4,
        "maxItems": 4
      },
      "minItems": 4,
      "maxItems": 4
    }
  },
  "required": ["worldMatrix"],
  "additionalProperties": false
}
```
- List prims (prim_paths):
```json
{
  "type": "object",
  "properties": {
    "prim_paths": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["prim_paths"],
  "additionalProperties": false
}
```


