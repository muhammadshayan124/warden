"""Append-only audit log of every tool call warden executes.

Not just for debugging -- this is the record a user would actually check
after letting an LLM operate their machine unattended for a while: what did
it touch, when, and did it succeed. One JSON object per line, so it's
greppable and diffable without any tooling, and it's exposed back to the
LLM itself as the get_audit_log tool, so "what have you done to my machine"
is a question the model can just answer from inside the same session.

Rotates to a single `.1` backup once the log exceeds max_bytes, so an
unattended long-running session can't grow this file without bound.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10MB


class AuditLogger:
    def __init__(self, path: Path, max_bytes: int = DEFAULT_MAX_BYTES):
        self._path = path
        self._max_bytes = max_bytes
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _rotate_if_needed(self) -> None:
        if self._path.exists() and self._path.stat().st_size >= self._max_bytes:
            backup = self._path.with_suffix(self._path.suffix + ".1")
            backup.unlink(missing_ok=True)
            self._path.rename(backup)

    def log(self, tool: str, args: dict[str, Any], status: str, detail: str = "") -> None:
        self._rotate_if_needed()
        entry = {
            "ts": time.time(),
            "tool": tool,
            "args": args,
            "status": status,
            "detail": detail,
        }
        with open(self._path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line.strip()]

    def read_recent(self, limit: int = 50, tool_filter: str | None = None) -> list[dict[str, Any]]:
        entries = self.read_all()
        if tool_filter:
            entries = [e for e in entries if e["tool"] == tool_filter]
        return entries[-limit:]
