import json
import sys
import uuid
from typing import Any, Callable, Dict, Optional

from .errors import MissingUsdError, StageNotFoundError, error_response


class StageRegistry:
    def __init__(self) -> None:
        self._stages: Dict[str, Any] = {}

    def new_id(self) -> str:
        return uuid.uuid4().hex[:8]

    def add(self, stage: Any) -> str:
        stage_id = self.new_id()
        self._stages[stage_id] = stage
        return stage_id

    def get(self, stage_id: str) -> Any:
        if stage_id not in self._stages:
            raise StageNotFoundError(f"Unknown stage_id: {stage_id}")
        return self._stages[stage_id]

    def remove(self, stage_id: str) -> None:
        if stage_id in self._stages:
            del self._stages[stage_id]

    def items(self):
        return self._stages.items()


STAGES = StageRegistry()


def _import_pxr():
    try:
        # Import lazily so environments without USD can still install/inspect
        from pxr import Usd, UsdGeom, Sdf, Tf  # type: ignore

        return Usd, UsdGeom, Sdf, Tf
    except Exception as exc:  # pragma: no cover - message clarity matters
        raise MissingUsdError(
            "USD (pxr) not available. Install a USD build and ensure 'from pxr import Usd' works."
        ) from exc


def _register_tools() -> Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]]:
    # Import here to avoid pxr import during CLI help, etc.
    from .tools.tier0 import (
        tool_open_stage,
        tool_close_stage,
        tool_list_open_stages,
        tool_get_stage_summary,
        tool_list_prims,
        tool_get_prim_info,
        tool_get_attribute_value,
        tool_set_attribute_value,
        tool_create_stage,
        tool_save_stage,
    )

    return {
        "open_stage": tool_open_stage,
        "close_stage": tool_close_stage,
        "list_open_stages": tool_list_open_stages,
        "get_stage_summary": tool_get_stage_summary,
        "list_prims": tool_list_prims,
        "get_prim_info": tool_get_prim_info,
        "get_attribute_value": tool_get_attribute_value,
        "set_attribute_value": tool_set_attribute_value,
        "create_stage": tool_create_stage,
        "save_stage": tool_save_stage,
    }


def serve() -> int:
    """Very small JSON-RPC-like loop over stdin/stdout.

    Request format:
        {"method": "open_stage", "params": { ... }}

    Response format: ResponseEnvelope dict.
    """
    tools = _register_tools()

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method")
            params = req.get("params") or {}
        except Exception as exc:
            sys.stdout.write(json.dumps(error_response("bad_request", f"Invalid JSON: {exc}")) + "\n")
            sys.stdout.flush()
            continue

        handler = tools.get(method)
        if handler is None:
            sys.stdout.write(json.dumps(error_response("unknown_method", f"Unknown method: {method}")) + "\n")
            sys.stdout.flush()
            continue

        try:
            resp = handler(params)
        except MissingUsdError as exc:
            resp = error_response("missing_usd", str(exc))
        except StageNotFoundError as exc:
            resp = error_response("stage_not_found", str(exc))
        except Exception as exc:  # pragmatic safety
            resp = error_response("internal_error", str(exc))

        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()

    return 0


