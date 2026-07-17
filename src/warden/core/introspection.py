"""Tools that answer "what is warden actually allowed to do, and what has
it done" -- turning the safety model and the audit log from static
config/log files into things the LLM itself can query mid-session, rather
than something only the operator can see by reading files by hand.
"""

from __future__ import annotations

from typing import Any

from warden.audit import AuditLogger
from warden.config import WardenConfig


def get_effective_permissions(config: WardenConfig) -> dict[str, Any]:
    return {
        "allowed_roots": [str(p) for p in config.allowed_roots],
        "allowed_commands": list(config.allowed_commands),
        "allowed_apps": list(config.allowed_apps),
        "unsafe_shell": config.unsafe_shell,
        "confirmation_ttl_seconds": config.confirmation_ttl_seconds,
    }


def get_audit_log(
    audit: AuditLogger, limit: int = 50, tool_filter: str | None = None
) -> list[dict[str, Any]]:
    return audit.read_recent(limit=limit, tool_filter=tool_filter)
