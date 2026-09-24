from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from .config import Settings


SOURCE_LABELS = {
    "examples": "TRELLIS EXAMPLES",
    "user": "USER WORKFLOWS",
    "repo": "REPO WORKFLOWS",
}

SUSPICIOUS_TERMS = (
    "cascade",
    "reconstruct",
    "remesh",
    "quad",
    "texture",
    "decode",
    "simplif",
    "sparse",
    "shape",
)


class WorkflowError(RuntimeError):
    """Raised when workflow discovery or inspection cannot continue."""


@dataclass(frozen=True)
class WorkflowFile:
    source: str
    root: Path
    path: Path

    @property
    def relative_path(self) -> Path:
        try:
            return self.path.relative_to(self.root)
        except ValueError:
            return Path(self.path.name)


@dataclass(frozen=True)
class NodeSummary:
    node_id: str
    class_type: str
    title: str | None
    scalar_inputs: dict[str, Any]


@dataclass(frozen=True)
class WorkflowInspection:
    workflow: WorkflowFile
    format: str
    nodes: list[NodeSummary]
    top_level_keys: list[str]


def workflow_roots(settings: Settings) -> dict[str, Path | None]:
    return {
        "examples": settings.trellis_example_workflows_dir,
        "user": settings.comfyui_workflows_dir,
        "repo": settings.repo_root / "workflows",
    }


def _json_files(root: Path | None) -> list[Path]:
    if root is None or not root.is_dir():
        return []

    return sorted(
        (path for path in root.rglob("*.json") if path.is_file()),
        key=lambda path: str(path).lower(),
    )


def discover_workflows(settings: Settings) -> dict[str, list[WorkflowFile]]:
    discovered: dict[str, list[WorkflowFile]] = {}

    for source, root in workflow_roots(settings).items():
        if root is None:
            discovered[source] = []
            continue

        discovered[source] = [
            WorkflowFile(source=source, root=root, path=path)
            for path in _json_files(root)
        ]

    return discovered


def _normalized_lookup(value: str) -> str:
    return value.replace("\\", "/").strip().lower()


def resolve_workflow(
    settings: Settings,
    query: str,
    source: str | None = None,
) -> WorkflowFile:
    discovered = discover_workflows(settings)
    candidates: list[WorkflowFile] = []

    sources = [source] if source else list(SOURCE_LABELS)
    wanted = _normalized_lookup(query)

    for current_source in sources:
        for workflow in discovered.get(current_source, []):
            rel = _normalized_lookup(str(workflow.relative_path))
            name = workflow.path.name.lower()
            stem = workflow.path.stem.lower()

            if wanted in {rel, name, stem}:
                candidates.append(workflow)

    if not candidates:
        # Fall back to a conservative substring search if no exact match exists.
        for current_source in sources:
            for workflow in discovered.get(current_source, []):
                rel = _normalized_lookup(str(workflow.relative_path))
                if wanted in rel:
                    candidates.append(workflow)

    if not candidates:
        source_text = f" in source {source!r}" if source else ""
        raise WorkflowError(f"No workflow matched {query!r}{source_text}.")

    if len(candidates) > 1:
        matches = "\n".join(
            f"  [{item.source}] {item.relative_path}" for item in candidates
        )
        raise WorkflowError(
            f"Workflow name {query!r} is ambiguous. Use --source or a relative path:\n{matches}"
        )

    return candidates[0]


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        raise WorkflowError(f"Could not read workflow: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(
            f"Workflow is not valid JSON: {path} (line {exc.lineno}, column {exc.colno})"
        ) from exc


def detect_format(data: Any) -> str:
    if not isinstance(data, dict):
        return "unknown"

    nodes = data.get("nodes")
    if isinstance(nodes, list):
        return "ui"

    if data and all(
        isinstance(value, dict) and isinstance(value.get("class_type"), str)
        for value in data.values()
    ):
        return "api"

    prompt = data.get("prompt")
    if isinstance(prompt, dict) and prompt and all(
        isinstance(value, dict) and isinstance(value.get("class_type"), str)
        for value in prompt.values()
    ):
        return "api-wrapper"

    return "unknown"


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _api_nodes(data: dict[str, Any], wrapped: bool = False) -> list[NodeSummary]:
    prompt = data["prompt"] if wrapped else data
    nodes: list[NodeSummary] = []

    for node_id, node in prompt.items():
        if not isinstance(node, dict):
            continue

        inputs = node.get("inputs")
        scalar_inputs = {}
        if isinstance(inputs, dict):
            scalar_inputs = {
                str(key): value
                for key, value in inputs.items()
                if _is_scalar(value)
            }

        meta = node.get("_meta")
        title = meta.get("title") if isinstance(meta, dict) and isinstance(meta.get("title"), str) else None

        nodes.append(
            NodeSummary(
                node_id=str(node_id),
                class_type=str(node.get("class_type", "<unknown>")),
                title=title,
                scalar_inputs=scalar_inputs,
            )
        )

    return nodes


def _ui_nodes(data: dict[str, Any]) -> list[NodeSummary]:
    nodes: list[NodeSummary] = []

    for index, node in enumerate(data.get("nodes", [])):
        if not isinstance(node, dict):
            continue

        node_id = str(node.get("id", index))
        class_type = str(node.get("type", node.get("class_type", "<unknown>")))
        title = node.get("title") if isinstance(node.get("title"), str) else None

        scalar_inputs: dict[str, Any] = {}

        # UI workflows often store editable widget values positionally. They are
        # still useful for inspection, but we deliberately avoid guessing names.
        widgets = node.get("widgets_values")
        if isinstance(widgets, list):
            for widget_index, value in enumerate(widgets):
                if _is_scalar(value):
                    scalar_inputs[f"widget[{widget_index}]"] = value
        elif isinstance(widgets, dict):
            scalar_inputs.update(
                {
                    str(key): value
                    for key, value in widgets.items()
                    if _is_scalar(value)
                }
            )

        properties = node.get("properties")
        if isinstance(properties, dict):
            for key, value in properties.items():
                if _is_scalar(value) and key not in scalar_inputs:
                    scalar_inputs[f"property.{key}"] = value

        nodes.append(
            NodeSummary(
                node_id=node_id,
                class_type=class_type,
                title=title,
                scalar_inputs=scalar_inputs,
            )
        )

    return nodes


def inspect_workflow(workflow: WorkflowFile) -> WorkflowInspection:
    data = _load_json(workflow.path)
    workflow_format = detect_format(data)

    if not isinstance(data, dict):
        nodes: list[NodeSummary] = []
        keys: list[str] = []
    else:
        keys = sorted(str(key) for key in data.keys())
        if workflow_format == "api":
            nodes = _api_nodes(data)
        elif workflow_format == "api-wrapper":
            nodes = _api_nodes(data, wrapped=True)
        elif workflow_format == "ui":
            nodes = _ui_nodes(data)
        else:
            nodes = []

    return WorkflowInspection(
        workflow=workflow,
        format=workflow_format,
        nodes=nodes,
        top_level_keys=keys,
    )


def class_counts(nodes: Iterable[NodeSummary]) -> list[tuple[str, int]]:
    counts = Counter(node.class_type for node in nodes)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))


def suspicious_nodes(nodes: Iterable[NodeSummary]) -> list[NodeSummary]:
    results = []

    for node in nodes:
        haystack = f"{node.class_type} {node.title or ''}".lower()
        if any(term in haystack for term in SUSPICIOUS_TERMS):
            results.append(node)

    return results


def format_scalar(value: Any, max_length: int = 120) -> str:
    rendered = json.dumps(value, ensure_ascii=False) if isinstance(value, str) else repr(value)
    if len(rendered) > max_length:
        return rendered[: max_length - 3] + "..."
    return rendered
