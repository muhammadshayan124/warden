"""Process listing, command execution, and process termination.

run_command is allowlist-gated by config.allowed_commands unless the
operator has explicitly set unsafe_shell=True. Its working directory is
always resolved against allowed_roots too -- an allowlisted command run
from an arbitrary cwd could otherwise read/write anywhere on disk, which
would quietly undermine the whole point of allowed_roots. This does not
(and cannot, short of real sandboxing) stop an allowlisted general-purpose
interpreter like `python` from touching paths outside allowed_roots via its
own arguments -- see the README's Limitations section.

kill_process always requires the two-step confirmation flow -- there is no
config flag that skips it, since killing the wrong process has no undo.
"""

from __future__ import annotations

import shlex
import subprocess
from typing import Any

import psutil

from warden.config import WardenConfig
from warden.confirmation import ConfirmationStore
from warden.safety import check_command_allowed, resolve_scoped_path

DEFAULT_COMMAND_TIMEOUT_SECONDS = 30.0


def list_processes() -> list[dict[str, Any]]:
    processes = []
    for proc in psutil.process_iter(["pid", "name", "memory_info"]):
        try:
            info = proc.info
            memory_mb = (
                round(info["memory_info"].rss / (1024 * 1024), 1) if info["memory_info"] else None
            )
            processes.append({"pid": info["pid"], "name": info["name"], "memory_mb": memory_mb})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return processes


def run_command(
    config: WardenConfig,
    command: str,
    args: list[str] | None = None,
    cwd: str | None = None,
    timeout: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    check_command_allowed(command, config)
    argv = [command, *(args or [])]

    # A cwd outside allowed_roots would let an allowlisted command read/write
    # anywhere via relative paths, quietly defeating the filesystem scoping.
    # No cwd given defaults to the first allowed root rather than whatever
    # directory the warden process itself happens to be running from.
    resolved_cwd = resolve_scoped_path(cwd, config) if cwd else config.allowed_roots[0]

    try:
        result = subprocess.run(
            argv,
            cwd=str(resolved_cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "timeout",
            "command": shlex.join(argv),
            "timeout_seconds": timeout,
            "partial_stdout": (exc.stdout or "")[-2000:] if exc.stdout else "",
        }
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"'{command}' was not found on PATH") from exc

    return {
        "status": "ok" if result.returncode == 0 else "nonzero_exit",
        "command": shlex.join(argv),
        "cwd": str(resolved_cwd),
        "returncode": result.returncode,
        "stdout": result.stdout[-10_000:],
        "stderr": result.stderr[-10_000:],
    }


def kill_process(
    confirmations: ConfirmationStore,
    pid: int,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    try:
        proc = psutil.Process(pid)
        name = proc.name()
    except psutil.NoSuchProcess as exc:
        raise ProcessLookupError(f"No process with pid {pid}") from exc

    fingerprint = f"kill:{pid}:{name}"
    if not confirm_token:
        token = confirmations.create("kill_process", fingerprint)
        return {
            "status": "confirmation_required",
            "confirm_token": token,
            "summary": f"This will terminate pid {pid} ({name}). "
            f"Call kill_process again with this confirm_token to proceed.",
        }

    if not confirmations.verify(confirm_token, "kill_process", fingerprint):
        raise PermissionError("Invalid, expired, or already-used confirm_token for kill_process")

    proc.terminate()
    return {"status": "ok", "pid": pid, "name": name}
