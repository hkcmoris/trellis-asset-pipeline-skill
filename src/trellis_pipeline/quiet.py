from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import subprocess
import time
from typing import Sequence


@dataclass(frozen=True)
class QuietRunResult:
    command: tuple[str, ...]
    returncode: int
    duration_seconds: float
    log_path: Path


def default_log_path(repo_root: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return repo_root / "logs" / f"quiet-run-{timestamp}.log"


def tail_log(path: Path, max_lines: int = 40) -> str:
    if not path.is_file():
        return ""

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""

    return "\n".join(lines[-max_lines:]).strip()


def run_quiet(
    command: Sequence[str],
    *,
    log_path: Path,
    cwd: Path | None = None,
) -> QuietRunResult:
    if not command:
        raise ValueError("A command is required.")

    log_path = log_path.resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if cwd is not None:
        cwd = cwd.resolve()
        if not cwd.is_dir():
            raise ValueError(f"Working directory does not exist: {cwd}")

    started = time.monotonic()

    with log_path.open("wb") as log_handle:
        process = subprocess.Popen(
            list(command),
            cwd=str(cwd) if cwd is not None else None,
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
        )

        try:
            returncode = process.wait()
        except KeyboardInterrupt:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            raise

    duration = time.monotonic() - started

    return QuietRunResult(
        command=tuple(command),
        returncode=returncode,
        duration_seconds=duration,
        log_path=log_path,
    )
