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

Persistent (requires MCP process to persist between actions)
- "Open <path> and give me the stage summary (layers, root prims, timecodes, up axis, meters per unit)."
- "Open <path>, then list prims under / to depth 2."
- "Open <path>, read size on /World/Cube, set it to 1.5, then save the stage."

Robustness and errors
- "Open  <path with extra spaces>  and summarize it."
- "Try to read attribute doesntexist on /World/Cube from <path> and report the error code."
- "Call get stage summary with a random stage id and show the error."

Notes
- If the agent loses the stage_id between steps, prefer the stateless forms ("…in file").
- Keys like Path/Stage Id are tolerated; the server normalizes them.


