from pathlib import Path

import pytest

from warden.config import WardenConfig
from warden.confirmation import ConfirmationStore


@pytest.fixture
def sandbox(tmp_path: Path) -> Path:
    (tmp_path / "existing.txt").write_text("hello")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.py").write_text("print('needle')\nx = 1\n")
    return tmp_path


@pytest.fixture
def config(sandbox: Path) -> WardenConfig:
    return WardenConfig(
        allowed_roots=(sandbox,),
        allowed_commands=("echo", "python"),
        allowed_apps=("notepad",),
        unsafe_shell=False,
        audit_log_path=sandbox / ".audit" / "audit.log",
        confirmation_ttl_seconds=120.0,
    )


@pytest.fixture
def confirmations() -> ConfirmationStore:
    return ConfirmationStore(ttl_seconds=120.0)
