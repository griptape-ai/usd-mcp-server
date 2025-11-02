import argparse
import json
import sys

from .version import __version__


def _cmd_serve(_: argparse.Namespace) -> int:
    # Lazy import to avoid importing pxr unless actually serving
    from .server import serve

    return serve()


def _cmd_mcp(_: argparse.Namespace) -> int:
    # Start MCP stdio server
    from .mcp_server import main as mcp_main

    return mcp_main()


def _cmd_ws(args: argparse.Namespace) -> int:
    from .ws_server import serve_ws

    return serve_ws(host=args.host, port=args.port)

def _cmd_client(args: argparse.Namespace) -> int:
    # Minimal local client: read a JSON request from stdin or --request
    if args.request:
        try:
            payload = json.loads(args.request)
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"Invalid JSON: {exc}\n")
            return 2
    else:
        try:
            payload = json.loads(sys.stdin.read())
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"Invalid JSON on stdin: {exc}\n")
            return 2

    # For now, just print back the payload (placeholder for future local invocation)
    sys.stdout.write(json.dumps({"echo": payload}, indent=2) + "\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="usd-mcp", description="MCP server for USD")
    parser.add_argument("--version", action="version", version=f"usd-mcp {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    p_serve = sub.add_parser("serve", help="Start the MCP server")
    p_serve.set_defaults(func=_cmd_serve)

    p_mcp = sub.add_parser("mcp-serve", help="Start the MCP stdio server (griptape-compatible)")
    p_mcp.set_defaults(func=_cmd_mcp)

    p_ws = sub.add_parser("ws-serve", help="Start the MCP WebSocket server (ws://)")
    p_ws.add_argument("--host", default="127.0.0.1")
    p_ws.add_argument("--port", default=8765, type=int)
    p_ws.set_defaults(func=_cmd_ws)

    p_client = sub.add_parser("client", help="Minimal local client for quick requests")
    p_client.add_argument("--request", help="Inline JSON request; if omitted, read from stdin")
    p_client.set_defaults(func=_cmd_client)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    return ns.func(ns)


if __name__ == "__main__":
    raise SystemExit(main())


