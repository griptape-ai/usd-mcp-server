from __future__ import annotations

import anyio
from types import SimpleNamespace
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket

from .version import __version__
from .mcp_server import server as MCP_SERVER


async def _healthz(_request):
    return PlainTextResponse("ok")


async def _info(_request):
    return JSONResponse({
        "name": "usd-mcp",
        "version": __version__,
        "transports": ["websocket", "stdio"],
    })


async def _ws_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def read():
        message = await websocket.receive_text()
        return message

    async def write(message: str):
        await websocket.send_text(message)

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

    await MCP_SERVER.run(read, write, initialization_options=init_opts)


def create_app() -> Starlette:
    return Starlette(
        routes=[
            Route("/healthz", _healthz),
            Route("/", _info),
            WebSocketRoute("/ws", _ws_endpoint),
        ]
    )


def serve_ws(host: str = "127.0.0.1", port: int = 8765) -> int:
    import uvicorn

    app = create_app()
    uvicorn.run(app, host=host, port=port)
    return 0


