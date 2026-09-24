from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable


def _candidate_repo_roots(start: Path) -> Iterable[Path]:
    current = start.resolve()
    yield current
    yield from current.parents


def find_repo_root(start: Path | None = None) -> Path:
    """Find the repository root without requiring Git to be installed."""
    start = start or Path.cwd()

    for candidate in _candidate_repo_roots(start):
        if (candidate / "pyproject.toml").is_file() and (candidate / "AGENTS.md").is_file():
            return candidate

    # src/trellis_pipeline/config.py -> repository root
    return Path(__file__).resolve().parents[2]


def _load_env_file(path: Path) -> None:
    """Load a small dotenv-compatible subset without adding a dependency."""
    if not path.is_file():
        return

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def _path_from_env(name: str) -> Path | None:
    value = os.environ.get(name, "").strip()
    return Path(value).expanduser() if value else None


def _positive_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default

    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero, got {value}")

    return value


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    env_file: Path
    comfyui_url: str
    comfyui_root: Path | None
    comfyui_start_bat: Path | None
    comfyui_workflows_dir: Path | None
    comfyui_input_dir: Path | None
    comfyui_output_dir: Path | None
    blender_exe: Path | None
    asset_output_dir: Path | None
    comfyui_startup_timeout_seconds: float
    comfyui_health_timeout_seconds: float
    nvidia_smi_exe: str

    @classmethod
    def load(cls, env_file: Path | None = None) -> "Settings":
        repo_root = find_repo_root()
        resolved_env = (env_file or repo_root / ".env").resolve()
        _load_env_file(resolved_env)

        comfyui_url = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").strip().rstrip("/")
        if not comfyui_url:
            comfyui_url = "http://127.0.0.1:8188"

        return cls(
            repo_root=repo_root,
            env_file=resolved_env,
            comfyui_url=comfyui_url,
            comfyui_root=_path_from_env("COMFYUI_ROOT"),
            comfyui_start_bat=_path_from_env("COMFYUI_START_BAT"),
            comfyui_workflows_dir=_path_from_env("COMFYUI_WORKFLOWS_DIR"),
            comfyui_input_dir=_path_from_env("COMFYUI_INPUT_DIR"),
            comfyui_output_dir=_path_from_env("COMFYUI_OUTPUT_DIR"),
            blender_exe=_path_from_env("BLENDER_EXE"),
            asset_output_dir=_path_from_env("ASSET_OUTPUT_DIR"),
            comfyui_startup_timeout_seconds=_positive_float(
                "COMFYUI_STARTUP_TIMEOUT_SECONDS", 120.0
            ),
            comfyui_health_timeout_seconds=_positive_float(
                "COMFYUI_HEALTH_TIMEOUT_SECONDS", 3.0
            ),
            nvidia_smi_exe=os.environ.get("NVIDIA_SMI_EXE", "").strip() or "nvidia-smi",
        )
