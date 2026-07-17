"""Shared enforcement: path scoping and command/app allowlisting.

These are the boundaries every tool call must pass through before touching
anything real. Nothing here is configurable by a tool argument -- only by
the operator's WardenConfig.
"""

from __future__ import annotations

from pathlib import Path

from warden.config import WardenConfig


class PermissionDenied(Exception):
    """Raised when a requested path/command/app falls outside the configured allowlist."""


def resolve_scoped_path(path: str, config: WardenConfig) -> Path:
    """Resolve `path` and confirm it falls inside one of config.allowed_roots.

    Resolves symlinks and `..` segments first so a request can't escape its
    root by indirection -- the check is against the real, final location on
    disk, not the string the caller passed in.
    """
    candidate = Path(path).expanduser().resolve()
    for root in config.allowed_roots:
        root_resolved = root.expanduser().resolve()
        if candidate == root_resolved or root_resolved in candidate.parents:
            return candidate
    roots_display = ", ".join(str(r) for r in config.allowed_roots)
    raise PermissionDenied(f"'{candidate}' is outside all allowed_roots ({roots_display})")


def check_command_allowed(command: str, config: WardenConfig) -> None:
    if config.unsafe_shell:
        return
    executable_name = Path(command).stem.lower()
    allowed = {c.lower() for c in config.allowed_commands}
    if executable_name not in allowed:
        raise PermissionDenied(
            f"'{command}' is not in allowed_commands (unsafe_shell is off). "
            f"Allowed: {sorted(allowed)}"
        )


def check_app_allowed(name_or_path: str, config: WardenConfig) -> None:
    key = Path(name_or_path).stem.lower()
    allowed = {Path(a).stem.lower() for a in config.allowed_apps}
    if key not in allowed:
        raise PermissionDenied(
            f"'{name_or_path}' is not in allowed_apps. Allowed: {sorted(allowed)}"
        )
