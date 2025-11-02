Sample natural-language prompts for Griptape (MCP)
=================================================

Use these directly as chat prompts in Griptape Nodes. They map to the current Tier 0 tools and the added stateless helpers. Replace <path> with your file when needed.

Paths
- Absolute: /Users/kyleroche/Documents/Development/usd-mcp/samples/simple.usda
- Normalized variants also work: Users/kyleroche/Documents/Development/usd-mcp/samples/simple.usda

Agent Rules
- Tool selection
  - Prefer stateless tools: summarizeFile, listPrimsFile, primInfoFile, getAttrFile, setAttrFile, createPrimFile, deletePrimFile, getXformFile, setXformFile, getBoundsFile.
  - Avoid persistent stage_id flows unless explicitly requested; if needed, use openStage, listOpenStages, closeStage.
  - Use only alphanumeric tool names (camelCase) as advertised by the server.
- Inputs
  - Provide a flat JSON object for inputs (no nested {"values":{...}} wrapper).
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
  - Verify transforms by calling getXformFile and reading worldMatrix.
- Attributes
  - Use getAttrFile/setAttrFile for reads/writes; use time: "default" unless a timeCode is requested.
- Serialization
  - Return numbers as numbers and vectors/matrices as JSON arrays; avoid tuples or stringified objects.
  - Never use parentheses for arrays (no tuples) – always use [ ... ] for JSON arrays.

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
- "Export <path> flattened to /tmp/flat.usda and export to USDZ /tmp/pack.usdz."

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


