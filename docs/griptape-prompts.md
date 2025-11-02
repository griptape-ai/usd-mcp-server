Sample natural-language prompts for Griptape (MCP)
=================================================

Use these directly as chat prompts in Griptape Nodes. They map to the current Tier 0 tools and the added stateless helpers. Replace <path> with your file when needed.

Paths
- Absolute: /Users/kyleroche/Documents/Development/usd-mcp/samples/simple.usda
- Normalized variants also work: Users/kyleroche/Documents/Development/usd-mcp/samples/simple.usda

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

Transforms (Tier 2)
- Translate via ops: "Translate /World/Cube to [2, 0, 0] in <path>, save, then get the transform and show worldMatrix."
- Rotate via ops (degrees XYZ): "Rotate /World/Cube by [0, 45, 0] (degrees XYZ) in <path>, save, then get the transform and show worldMatrix."
- Combined ops: "Translate /World/Cube to [2, 0, 0] and rotate [0, 45, 0] (degrees XYZ) in <path>, save, then get the transform and show worldMatrix."
- Matrix fallback (robust): "Set /World/Cube transform matrix in <path> to [[1,0,0,0],[0,0.70710678,-0.70710678,0],[0,0.70710678,0.70710678,0],[0,0,0,1]], save, then getXformFile and show worldMatrix."

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


