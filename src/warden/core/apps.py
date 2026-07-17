"""Application launching, gated by config.allowed_apps.

Launching an app is not treated as destructive (no confirm_token) since it
has no undo-relevant side effect by itself -- the allowlist is the control
here, not a confirmation step. Uses the platform's own "open by name"
resolution (os.startfile on Windows, `open`/`xdg-open` elsewhere) so it
covers anything registered like Start-menu search would, rather than
requiring a full executable path.
"""

from __future__ import annotations

import os
import platform

# A bound `Popen` name (rather than `import subprocess` + `subprocess.Popen`)
# so tests can patch *this module's* reference alone. Patching
# "warden.core.apps.subprocess.Popen" would patch the subprocess module
# itself, process-wide -- catching any unrelated Popen call any other library
# happens to make during the test too, not just this function's.
from subprocess import Popen
from typing import Any

from warden.config import WardenConfig
from warden.safety import check_app_allowed


def launch_app(
    config: WardenConfig, name_or_path: str, args: list[str] | None = None
) -> dict[str, Any]:
    check_app_allowed(name_or_path, config)
    system = platform.system()

    if args:
        # os.startfile has no way to pass arguments, so fall back to a direct launch.
        Popen([name_or_path, *args])
    elif system == "Windows":
        os.startfile(name_or_path)  # noqa: S606 -- name_or_path is allowlist-checked above
    elif system == "Darwin":
        Popen(["open", "-a", name_or_path])
    else:
        Popen(["xdg-open", name_or_path])

    return {"status": "ok", "launched": name_or_path}
