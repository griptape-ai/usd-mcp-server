Tier 0 Tools
============

All responses follow `{ ok: bool, result?, error? }`.

open_stage
- Params: `{ path: string }`
- Result: `{ stage_id: string }`

close_stage
- Params: `{ stage_id: string }`
- Result: `{}`

list_open_stages
- Params: `{}`
- Result: `{ stages: [{ stage_id, root_layer: { identifier, realPath }, dirty }] }`

get_stage_summary
- Params: `{ stage_id: string }`
- Result: `{ layers: [{identifier, realPath}], root_prims: string[], timeCodes: {start, end}, upAxis: string, metersPerUnit: number }`

list_prims
- Params: `{ stage_id: string, root?: string = "/", depth?: number = 1, typeFilter?: string }`
- Result: `{ prim_paths: string[] }`

get_prim_info
- Params: `{ stage_id: string, prim_path: string }`
- Result: `{ type: string, attrs: string[], rels: string[], metadata: object }`

get_attribute_value
- Params: `{ stage_id: string, prim_path: string, attr: string, time?: number|"default" }`
- Result: `{ value: any }`

set_attribute_value
- Params: `{ stage_id: string, prim_path: string, attr: string, value: any, time?: number|"default" }`
- Result: `{}`

create_stage
- Params: `{ output_path: string, upAxis?: "Y"|"Z", metersPerUnit?: number }`
- Result: `{ stage_id: string }`

save_stage
- Params: `{ stage_id: string, output_path?: string, flatten?: boolean }`
- Result: `{ output_path: string }`

Failure cases
- `missing_usd`: Host lacks `pxr`.
- `stage_not_found`: Unknown `stage_id`.
- `invalid_params`: Missing or invalid inputs.
- `not_found`: Prim or attribute not found.
- `open_failed` / `save_failed` / `export_failed`: I/O errors.


Back: [Tool Docs](README.md) · [Docs Index](../README.md)

