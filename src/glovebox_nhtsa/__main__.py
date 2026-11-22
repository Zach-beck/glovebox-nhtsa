"""Run Glovebox over stdio, or over Streamable HTTP on localhost."""

from __future__ import annotations

import argparse
import logging
import sys

import uvicorn
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from glovebox_nhtsa import __version__
from glovebox_nhtsa.config import Settings
from glovebox_nhtsa.server import create_server


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="glovebox-nhtsa", description="Local NHTSA vehicle data for MCP clients.")
    parser.add_argument("--transport", choices=("stdio", "http"), default=None)
    parser.add_argument("--version", action="store_true")
    return parser


class _TokenGate:
    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope.get("headers", [])}
            if headers.get("authorization") != f"Bearer {self.token}":
                response = JSONResponse({"error": "unauthorized"}, status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.version:
        print(__version__)
        return
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s")
    settings = Settings.from_env()
    if args.transport:
        settings = Settings(
            transport=args.transport,
            http_host=settings.http_host,
            http_port=settings.http_port,
            http_token=settings.http_token,
            cache_dir=settings.cache_dir,
            data_dir=settings.data_dir,
            offline=settings.offline,
            fixtures_dir=settings.fixtures_dir,
            investigations_file=settings.investigations_file,
            request_gap_seconds=settings.request_gap_seconds,
            request_timeout_seconds=settings.request_timeout_seconds,
        )
    server = create_server(settings)
    if settings.transport == "http":
        app = server.streamable_http_app(
            streamable_http_path="/mcp",
            stateless_http=True,
            host=settings.http_host,
        )
        if settings.http_token:
            app = _TokenGate(app, settings.http_token)
        uvicorn.run(app, host=settings.http_host, port=settings.http_port, log_level="info")
        return
    if settings.transport != "stdio":
        raise SystemExit(f"Unknown transport {settings.transport}")
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
