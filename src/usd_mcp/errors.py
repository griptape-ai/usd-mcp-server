from typing import Any, Dict, Optional


class UsdMcpError(Exception):
    """Base exception for usd-mcp errors."""


class MissingUsdError(UsdMcpError):
    """Raised when pxr/USD is not available on the host."""


class StageNotFoundError(UsdMcpError):
    """Raised when a referenced stage_id does not exist."""


def error_response(code: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }


