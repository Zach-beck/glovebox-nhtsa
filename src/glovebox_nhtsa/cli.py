"""Glovebox CLI: readable vehicle reports without an MCP client."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import anyio

from glovebox_nhtsa.config import Settings
from glovebox_nhtsa.service import build_service


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="glovebox", description="Glovebox vehicle reports and helpers.")
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("report", help="Build a vehicle_report from one VIN.")
    report.add_argument("vin", help="VIN to decode (partial VINs may use *).")
    report.add_argument("--model-year", type=int, default=None, dest="model_year")
    report.add_argument("--html", metavar="PATH", help="Write a self-contained HTML report to PATH.")
    report.add_argument("--json", action="store_true", help="Print vehicle_report JSON on stdout.")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _parser().parse_args(argv)
    if args.command != "report":
        raise SystemExit(f"Unknown command {args.command}")
    settings = Settings.from_env()
    service = build_service(settings)

    async def run_report() -> dict:
        try:
            write_path = Path(args.html).expanduser() if args.html else None
            if write_path is not None:
                return await service.vehicle_report(
                    args.vin,
                    args.model_year,
                    format="html",
                    write_html_path=write_path,
                )
            return await service.vehicle_report(args.vin, args.model_year, format="json")
        finally:
            await service.aclose()

    result = anyio.run(run_report)

    if args.html:
        print(result.get("file_path") or args.html)
        return
    if args.json or not args.html:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return


if __name__ == "__main__":
    main()