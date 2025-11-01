ADR 0002: Error envelope for MCP tool responses
===============================================

Status: accepted

Context
- LLM orchestration benefits from consistent error shapes and stable codes.

Decision
- All tool responses use `{ ok: bool, result?: any, error?: { code, message, details? } }`.
- Error codes are short, kebab/snake: `missing_usd`, `invalid_params`, `stage_not_found`, `not_found`, `open_failed`, `save_failed`, `export_failed`, `internal_error`.

Consequences
- Callers can branch on `ok` and `error.code` reliably.
- Details can include `path`, `stage_id`, or other contextual hints.


