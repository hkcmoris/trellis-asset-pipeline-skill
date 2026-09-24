from __future__ import annotations

import argparse
import json
import sys

from .comfy import ComfyUIError, ensure_running, is_running, start, system_stats
from .config import Settings
from .doctor import exit_code, run_doctor


def _settings() -> Settings:
    try:
        return Settings.load()
    except ValueError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc


def _print_checks(checks: list) -> None:
    width = max((len(check.name) for check in checks), default=0)

    for check in checks:
        print(f"{check.level:<5} {check.name:<{width}}  {check.detail}")


def _doctor(args: argparse.Namespace) -> int:
    settings = _settings()
    checks = run_doctor(settings, start_comfyui=args.start_comfyui)
    _print_checks(checks)
    return exit_code(checks)


def _comfy_status(_: argparse.Namespace) -> int:
    settings = _settings()

    if not is_running(settings):
        print(f"OFFLINE  {settings.comfyui_url}")
        return 1

    stats = system_stats(settings)
    print(f"ONLINE   {settings.comfyui_url}")
    print(json.dumps(stats, indent=2))
    return 0


def _comfy_ensure(_: argparse.Namespace) -> int:
    settings = _settings()

    try:
        state, _ = ensure_running(settings)
    except ComfyUIError as exc:
        print(f"ERROR    {exc}", file=sys.stderr)
        return 1

    print(f"OK       ComfyUI {state} at {settings.comfyui_url}")
    return 0


def _comfy_start(_: argparse.Namespace) -> int:
    settings = _settings()

    if is_running(settings):
        print(f"ERROR    ComfyUI is already running at {settings.comfyui_url}", file=sys.stderr)
        return 1

    try:
        process = start(settings)
    except ComfyUIError as exc:
        print(f"ERROR    {exc}", file=sys.stderr)
        return 1

    print(f"STARTED  launcher PID {process.pid}")
    print("         Use 'trellis-pipeline comfy status' to check readiness.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trellis-pipeline",
        description="Local tooling for the TRELLIS asset pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser(
        "doctor", help="Check local pipeline configuration and dependencies."
    )
    doctor_parser.add_argument(
        "--start-comfyui",
        action="store_true",
        help="Start ComfyUI if it is offline, then wait for the API.",
    )
    doctor_parser.set_defaults(handler=_doctor)

    comfy_parser = subparsers.add_parser("comfy", help="Manage the local ComfyUI process.")
    comfy_subparsers = comfy_parser.add_subparsers(dest="comfy_command", required=True)

    status_parser = comfy_subparsers.add_parser("status", help="Check ComfyUI API status.")
    status_parser.set_defaults(handler=_comfy_status)

    ensure_parser = comfy_subparsers.add_parser(
        "ensure", help="Start ComfyUI only if needed and wait until it is ready."
    )
    ensure_parser.set_defaults(handler=_comfy_ensure)

    start_parser = comfy_subparsers.add_parser(
        "start", help="Launch the configured batch file without waiting for readiness."
    )
    start_parser.set_defaults(handler=_comfy_start)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))
