from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import Settings


class ComfyUIError(RuntimeError):
    """Raised when ComfyUI cannot be reached or started."""


def system_stats(settings: Settings) -> dict[str, Any]:
    url = f"{settings.comfyui_url}/system_stats"
    request = Request(url, headers={"Accept": "application/json"})

    try:
        with urlopen(request, timeout=settings.comfyui_health_timeout_seconds) as response:
            payload = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise ComfyUIError(f"ComfyUI is not reachable at {settings.comfyui_url}: {exc}") from exc

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ComfyUIError("ComfyUI /system_stats returned invalid JSON") from exc

    if not isinstance(parsed, dict):
        raise ComfyUIError("ComfyUI /system_stats returned an unexpected payload")

    return parsed


def is_running(settings: Settings) -> bool:
    try:
        system_stats(settings)
        return True
    except ComfyUIError:
        return False


def _startup_log_path(settings: Settings) -> Path:
    path = settings.repo_root / "logs" / "comfyui-startup.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _startup_log_tail(settings: Settings, max_lines: int = 30) -> str:
    path = _startup_log_path(settings)
    if not path.is_file():
        return ""

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""

    return "\n".join(lines[-max_lines:]).strip()


def start(settings: Settings) -> subprocess.Popen[bytes]:
    if settings.comfyui_start_bat is None:
        raise ComfyUIError(
            "COMFYUI_START_BAT is not configured. Copy .env.example to .env and set it."
        )

    batch_file = settings.comfyui_start_bat
    if not batch_file.is_file():
        raise ComfyUIError(f"ComfyUI startup batch file does not exist: {batch_file}")

    cwd = settings.comfyui_root or batch_file.parent
    if not cwd.is_dir():
        raise ComfyUIError(f"ComfyUI working directory does not exist: {cwd}")

    if os.name != "nt":
        raise ComfyUIError(
            "COMFYUI_START_BAT is a Windows batch file; automatic startup currently requires Windows."
        )

    comspec = os.environ.get("COMSPEC", "cmd.exe")
    # Pass a raw Windows command line instead of a list here. Python's Windows
    # list-to-command-line quoting escapes nested quotes with backslashes,
    # which cmd.exe does not interpret as quote escapes. The classic doubled
    # quote form is required for a quoted batch-file path after /c.
    command_line = f'"{comspec}" /d /s /c ""{batch_file}""'
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    log_path = _startup_log_path(settings)

    log_handle = log_path.open("ab", buffering=0)
    try:
        process = subprocess.Popen(
            command_line,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
    finally:
        log_handle.close()

    return process


def wait_until_ready(
    settings: Settings,
    process: subprocess.Popen[bytes] | None = None,
) -> dict[str, Any]:
    deadline = time.monotonic() + settings.comfyui_startup_timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            return system_stats(settings)
        except ComfyUIError as exc:
            last_error = exc

        if process is not None:
            return_code = process.poll()
            if return_code not in (None, 0):
                tail = _startup_log_tail(settings)
                detail = f"\n\nStartup log tail:\n{tail}" if tail else ""
                raise ComfyUIError(
                    f"ComfyUI startup process exited with code {return_code}.{detail}"
                )

        time.sleep(2.0)

    detail = f" Last error: {last_error}" if last_error else ""
    tail = _startup_log_tail(settings)
    log_detail = f"\n\nStartup log tail:\n{tail}" if tail else ""
    raise ComfyUIError(
        "ComfyUI did not become ready within "
        f"{settings.comfyui_startup_timeout_seconds:g} seconds.{detail}{log_detail}"
    )


def ensure_running(settings: Settings) -> tuple[str, dict[str, Any]]:
    try:
        stats = system_stats(settings)
        return "already-running", stats
    except ComfyUIError:
        process = start(settings)
        stats = wait_until_ready(settings, process=process)
        return "started", stats
