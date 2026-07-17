"""Append-only audit log of every tool call warden executes.

Not just for debugging -- this is the record a user would actually check
after letting an LLM operate their machine unattended for a while: what did
it touch, when, and did it succeed. One JSON object per line, so it's
greppable and diffable without any tooling.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class AuditLogger:
    def __init__(self, path: Path):
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, tool: str, args: dict[str, Any], status: str, detail: str = "") -> None:
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
