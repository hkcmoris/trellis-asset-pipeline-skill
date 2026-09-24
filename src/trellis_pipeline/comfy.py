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
    command = f'call "{batch_file}"'
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    log_path = _startup_log_path(settings)

    log_handle = log_path.open("ab", buffering=0)
    try:
        process = subprocess.Popen(
            [comspec, "/d", "/s", "/c", command],
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            creationflags=creationflags,
        )
    finally:
        log_handle.close()

    return process


def wait_until_ready(settings: Settings) -> dict[str, Any]:
    deadline = time.monotonic() + settings.comfyui_startup_timeout_seconds
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        try:
            return system_stats(settings)
        except ComfyUIError as exc:
            last_error = exc
            time.sleep(2.0)

    detail = f" Last error: {last_error}" if last_error else ""
    raise ComfyUIError(
        "ComfyUI did not become ready within "
        f"{settings.comfyui_startup_timeout_seconds:g} seconds.{detail}"
    )


def ensure_running(settings: Settings) -> tuple[str, dict[str, Any]]:
    try:
        stats = system_stats(settings)
        return "already-running", stats
    except ComfyUIError:
        start(settings)
        stats = wait_until_ready(settings)
        return "started", stats
