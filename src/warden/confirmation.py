"""Two-step confirmation for destructive actions.

A destructive tool call (delete a file, kill a process, overwrite existing
content) never executes on its first call. It returns a confirm_token that
identifies exactly that action against exactly that target. The caller must
invoke the same tool again with that token to actually execute -- which
means an irreversible action always shows up as two distinct, inspectable
tool calls rather than one, giving a human (or an MCP client's own approval
UI) a real chance to see it coming.

Tokens are single-use and expire after `ttl_seconds`, and are bound to a
fingerprint of the target (e.g. the resolved file path) so a token issued
for deleting file A can't be replayed against file B.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass


@dataclass
class _PendingConfirmation:
    action: str
    fingerprint: str
    expires_at: float


class ConfirmationStore:
    def __init__(self, ttl_seconds: float = 120.0):
        self._ttl_seconds = ttl_seconds
        self._pending: dict[str, _PendingConfirmation] = {}

    def create(self, action: str, fingerprint: str) -> str:
        token = uuid.uuid4().hex
        self._pending[token] = _PendingConfirmation(
            action=action,
            fingerprint=fingerprint,
            expires_at=time.monotonic() + self._ttl_seconds,
        )
        return token

    def verify(self, token: str, action: str, fingerprint: str) -> bool:
        """Check and consume a token. Returns False (without raising) on any mismatch."""
        entry = self._pending.get(token)
        if entry is None:
            return False
        del self._pending[token]  # one-time use, regardless of outcome below
        if time.monotonic() > entry.expires_at:
            return False
        return entry.action == action and entry.fingerprint == fingerprint
