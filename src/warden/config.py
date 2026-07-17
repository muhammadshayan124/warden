"""Operator-controlled configuration.

Every safety boundary in warden (which directories are touchable, which
commands/apps may run, whether the confirmation gate can be bypassed) is read
from this config -- never from arguments the LLM passes at call time. That
split is the whole safety model: the model can *ask* to do things, but only
the human who wrote the config file decides what's actually reachable.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_PATH_ENV = "WARDEN_CONFIG"

DEFAULT_ALLOWED_COMMANDS = (
    "git",
    "python",
    "python3",
    "pip",
    "node",
    "npm",
    "npx",
    "ls",
    "dir",
    "cat",
    "type",
    "echo",
    "pwd",
)


@dataclass(frozen=True)
class WardenConfig:
    allowed_roots: tuple[Path, ...] = field(default_factory=lambda: (Path.home(),))
    allowed_commands: tuple[str, ...] = DEFAULT_ALLOWED_COMMANDS
    allowed_apps: tuple[str, ...] = ()
    unsafe_shell: bool = False
    audit_log_path: Path = field(default_factory=lambda: Path.home() / ".warden" / "audit.log")
    confirmation_ttl_seconds: float = 120.0

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> WardenConfig:
        path = config_path or os.environ.get(CONFIG_PATH_ENV)
        data = json.loads(Path(path).read_text()) if path and Path(path).exists() else {}

        allowed_roots = data.get("allowed_roots")
        roots = (
            tuple(Path(p).expanduser() for p in allowed_roots) if allowed_roots else (Path.home(),)
        )
        return cls(
            allowed_roots=roots,
            allowed_commands=tuple(data.get("allowed_commands", DEFAULT_ALLOWED_COMMANDS)),
            allowed_apps=tuple(data.get("allowed_apps", ())),
            unsafe_shell=bool(data.get("unsafe_shell", False)),
            audit_log_path=Path(
                data.get("audit_log_path", str(Path.home() / ".warden" / "audit.log"))
            ).expanduser(),
            confirmation_ttl_seconds=float(data.get("confirmation_ttl_seconds", 120.0)),
        )
