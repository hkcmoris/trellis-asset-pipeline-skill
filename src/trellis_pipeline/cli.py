from __future__ import annotations

import argparse
import json
import sys

from .comfy import ComfyUIError, ensure_running, is_running, start, system_stats
from .config import Settings
from .doctor import exit_code, run_doctor
from .workflows import (
    SOURCE_LABELS,
    WorkflowError,
    class_counts,
    clone_workflow_to_user,
    discover_workflows,
    format_scalar,
    inspect_workflow,
    resolve_workflow,
    suspicious_nodes,
)


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


def _workflows_list(args: argparse.Namespace) -> int:
    settings = _settings()
    discovered = discover_workflows(settings)
    selected_sources = [args.source] if args.source else list(SOURCE_LABELS)

    total = 0
    for source in selected_sources:
        label = SOURCE_LABELS[source]
        workflows = discovered[source]
        total += len(workflows)

        print(label)
        if not workflows:
            print("  (none found)")
        else:
            for workflow in workflows:
                print(f"  {workflow.relative_path}")
        print()

    return 0 if total else 1


def _print_node(node, *, indent: str = "  ") -> None:
    title = f' "{node.title}"' if node.title else ""
    print(f"{indent}[{node.node_id}] {node.class_type}{title}")

    for name, value in sorted(node.scalar_inputs.items()):
        print(f"{indent}    {name}: {format_scalar(value)}")


def _workflows_inspect(args: argparse.Namespace) -> int:
    settings = _settings()

    try:
        workflow = resolve_workflow(settings, args.workflow, source=args.source)
        inspection = inspect_workflow(workflow)
    except WorkflowError as exc:
        print(f"ERROR    {exc}", file=sys.stderr)
        return 1

    print(f"Source:   {SOURCE_LABELS[workflow.source]}")
    print(f"File:     {workflow.path}")
    print(f"Format:   {inspection.format}")
    print(f"Nodes:    {len(inspection.nodes)}")

    if inspection.format == "unknown":
        keys = ", ".join(inspection.top_level_keys) or "(none)"
        print(f"Top keys: {keys}")
        print()
        print("Could not recognize this as a standard ComfyUI UI or API workflow.")
        return 1

    print()
    print("NODE CLASSES")
    for class_type, count in class_counts(inspection.nodes):
        print(f"  {count:>3}  {class_type}")

    flagged = suspicious_nodes(inspection.nodes)
    print()
    print("TRELLIS / PERFORMANCE-RELEVANT NODES")
    if not flagged:
        print("  (none matched by name)")
    else:
        for node in flagged:
            _print_node(node)

    if args.all_nodes:
        print()
        print("ALL NODES")
        for node in inspection.nodes:
            _print_node(node)

    if inspection.format == "ui":
        print()
        print(
            "NOTE: UI workflow widget values are positional, so inspect shows them as "
            "widget[index] rather than guessing parameter names."
        )

    return 0


def _workflows_clone(args: argparse.Namespace) -> int:
    settings = _settings()

    try:
        result = clone_workflow_to_user(
            settings,
            args.workflow,
            source=args.source,
            name=args.name,
            overwrite=args.overwrite,
        )
    except WorkflowError as exc:
        print(f"ERROR    {exc}", file=sys.stderr)
        return 1

    action = "OVERWROTE" if result.overwritten else "COPIED"
    print(action)
    print(f"Source:      [{result.source.source}] {result.source.path}")
    print(f"Destination: {result.destination}")
    print(f"Format:      {result.format}")
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

    workflows_parser = subparsers.add_parser(
        "workflows",
        help="Discover, inspect, and copy ComfyUI/TRELLIS workflow JSON.",
    )
    workflows_subparsers = workflows_parser.add_subparsers(
        dest="workflows_command",
        required=True,
    )

    list_parser = workflows_subparsers.add_parser(
        "list",
        help="List workflow JSON from examples, user workflows, and this repository.",
    )
    list_parser.add_argument(
        "--source",
        choices=tuple(SOURCE_LABELS),
        help="Show only one workflow source.",
    )
    list_parser.set_defaults(handler=_workflows_list)

    inspect_parser = workflows_subparsers.add_parser(
        "inspect",
        help="Inspect a workflow without modifying it.",
    )
    inspect_parser.add_argument(
        "workflow",
        help="Filename, stem, or relative path of the workflow to inspect.",
    )
    inspect_parser.add_argument(
        "--source",
        choices=tuple(SOURCE_LABELS),
        help="Resolve the workflow only from this source.",
    )
    inspect_parser.add_argument(
        "--all-nodes",
        action="store_true",
        help="Print every node in addition to performance-relevant nodes.",
    )
    inspect_parser.set_defaults(handler=_workflows_inspect)

    clone_parser = workflows_subparsers.add_parser(
        "clone",
        help="Copy a workflow into the configured user workflow directory.",
    )
    clone_parser.add_argument(
        "workflow",
        help="Filename, stem, or relative path of the source workflow.",
    )
    clone_parser.add_argument(
        "--source",
        choices=tuple(SOURCE_LABELS),
        required=True,
        help="Source to copy from. Examples should normally use --source examples.",
    )
    clone_parser.add_argument(
        "--name",
        required=True,
        help="New filename in COMFYUI_WORKFLOWS_DIR. .json is added automatically.",
    )
    clone_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Explicitly allow replacing an existing destination file.",
    )
    clone_parser.set_defaults(handler=_workflows_clone)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))
