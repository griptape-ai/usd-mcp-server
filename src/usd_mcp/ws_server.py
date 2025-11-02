from __future__ import annotations

import anyio
from types import SimpleNamespace
from .version import __version__
from .mcp_server import server as MCP_SERVER

# Use the official MCP websocket adapter to provide the expected framed message streams
try:
    from mcp.server.websocket import websocket_server  # type: ignore
except Exception as exc:  # pragma: no cover
    websocket_server = None  # defer import error until endpoint use


async def _healthz(_request):
    return PlainTextResponse("ok")


async def _info(_request):
    return JSONResponse({
        "name": "usd-mcp",
        "version": __version__,
        "transports": ["websocket", "stdio"],
    })


async def _asgi_app(scope, receive, send):
    """Minimal ASGI app exposing /ws, /, /healthz without Starlette."""
    if websocket_server is None:
        # Fail fast if adapter missing
        if scope["type"] == "http":
            await send({
                "type": "http.response.start",
                "status": 500,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            })
            await send({"type": "http.response.body", "body": b"websocket adapter missing"})
            return
    path = scope.get("path", "/")
    if scope["type"] == "websocket" and path == "/ws":
        init_opts = SimpleNamespace(
            server_name="usd-mcp",
            server_version=__version__,
            website_url="https://github.com/your-org/usd-mcp",
            icons=[],
            instructions=(
                "Use the listed tools to open, inspect, and modify USD stages."
                " Inputs and outputs are JSON."
            ),
            capabilities={"tools": {}},
        )
        async with websocket_server(scope, receive, send) as (read, write):
            await MCP_SERVER.run(read, write, initialization_options=init_opts)
        return
    if scope["type"] == "http" and path == "/healthz":
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain; charset=utf-8")],
        })
        await send({"type": "http.response.body", "body": b"ok"})
        return
    if scope["type"] == "http" and path == "/":
        body = (
            b"{\n  \"name\": \"usd-mcp\",\n  \"version\": \"" + __version__.encode() + b"\",\n  \"transports\": [\"websocket\", \"stdio\"]\n}\n"
        )
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"application/json; charset=utf-8")],
        })
        await send({"type": "http.response.body", "body": body})
        return
    # 404
    if scope["type"] == "http":
        await send({
            "type": "http.response.start",
            "status": 404,
            "headers": [(b"content-type", b"text/plain; charset=utf-8")],
        })
        await send({"type": "http.response.body", "body": b"not found"})
        return


def serve_ws(host: str = "127.0.0.1", port: int = 8765) -> int:
    import uvicorn
    uvicorn.run(_asgi_app, host=host, port=port)
    return 0


