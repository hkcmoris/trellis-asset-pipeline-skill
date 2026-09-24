from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

from .comfy import ComfyUIError, ensure_running, is_running
from .config import Settings


@dataclass(frozen=True)
class Check:
    name: str
    level: str
    detail: str


def _path_check(name: str, path: Path | None, kind: str) -> Check:
    if path is None:
        return Check(name, "WARN", "not configured")

    exists = path.is_file() if kind == "file" else path.is_dir()
    return Check(name, "OK" if exists else "ERROR", str(path))


def _blender_check(settings: Settings) -> Check:
    if settings.blender_exe is None:
        return Check("Blender", "WARN", "BLENDER_EXE is not configured")

    if not settings.blender_exe.is_file():
        return Check("Blender", "ERROR", f"not found: {settings.blender_exe}")

    try:
        completed = subprocess.run(
            [str(settings.blender_exe), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return Check("Blender", "ERROR", f"{settings.blender_exe}: {exc}")

    first_line = (completed.stdout or completed.stderr).splitlines()
    version = first_line[0].strip() if first_line else "executable found"
    return Check("Blender", "OK", version)


def _gpu_check(settings: Settings) -> Check:
    executable = settings.nvidia_smi_exe
    resolved = shutil.which(executable) if not Path(executable).is_file() else executable

    if not resolved:
        return Check("NVIDIA GPU", "WARN", f"{executable!r} not found")

    try:
        completed = subprocess.run(
            [
                str(resolved),
                "--query-gpu=name,memory.total",
                "--format=csv,noheader",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return Check("NVIDIA GPU", "WARN", str(exc))

    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip() or "nvidia-smi failed"
        return Check("NVIDIA GPU", "WARN", detail)

    detail = "; ".join(line.strip() for line in completed.stdout.splitlines() if line.strip())
    return Check("NVIDIA GPU", "OK", detail or "detected")


def run_doctor(settings: Settings, start_comfyui: bool = False) -> list[Check]:
    checks: list[Check] = []

    checks.append(
        Check(
            ".env",
            "OK" if settings.env_file.is_file() else "WARN",
            str(settings.env_file)
            if settings.env_file.is_file()
            else f"not found: {settings.env_file}",
        )
    )

    running = is_running(settings)

    if not running and start_comfyui:
        try:
            state, _ = ensure_running(settings)
            running = True
            checks.append(Check("ComfyUI startup", "OK", state))
        except ComfyUIError as exc:
            checks.append(Check("ComfyUI startup", "ERROR", str(exc)))

    checks.append(
        Check(
            "ComfyUI API",
            "OK" if running else "WARN",
            f"{settings.comfyui_url} ({'online' if running else 'offline'})",
        )
    )

    checks.extend(
        [
            _path_check("ComfyUI root", settings.comfyui_root, "dir"),
            _path_check("ComfyUI startup", settings.comfyui_start_bat, "file"),
            _path_check("ComfyUI workflows", settings.comfyui_workflows_dir, "dir"),
            _path_check("ComfyUI input", settings.comfyui_input_dir, "dir"),
            _path_check("ComfyUI output", settings.comfyui_output_dir, "dir"),
            _blender_check(settings),
            _gpu_check(settings),
        ]
    )

    if settings.asset_output_dir is None:
        checks.append(Check("Asset output", "WARN", "ASSET_OUTPUT_DIR is not configured"))
    elif settings.asset_output_dir.is_dir():
        checks.append(Check("Asset output", "OK", str(settings.asset_output_dir)))
    else:
        checks.append(
            Check(
                "Asset output",
                "WARN",
                f"configured but does not exist yet: {settings.asset_output_dir}",
            )
        )

    return checks


def exit_code(checks: list[Check]) -> int:
    return 1 if any(check.level == "ERROR" for check in checks) else 0
