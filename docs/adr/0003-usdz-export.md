ADR 0003: USDZ export strategy
==============================

Status: accepted (planned for Tier 4)

Context
- Users want compressed `.usdz` packages for portability.
- USD provides APIs/utilities to package layers and optional assets.

Decision
- Provide a tool `export_usdz(stage_id, output_path, packTextures?: bool)` in Tier 4.
- Prefer Python API when available (e.g., `UsdUtils.CreateNewUsdzPackage`) or fall back to invoking `usdzip` if present on PATH.
- Validate `output_path` ends with `.usdz` and is writable.

Details
- If `packTextures` is true, include external image assets referenced by the stage.
- Flattening: export will use a referenced layer stack; full flatten will remain a separate option in `export_usd`.
- Error codes: `export_failed`, `io_error`, `unsupported_version` (if USD lacks needed APIs).

Consequences
- Keeps Tier 0 simple; adds value when moving to distribution/hand-off stages.
- Requires USD build with utilities; provide graceful errors if unsupported.


