import json
from pathlib import Path

from warden.config import WardenConfig


def test_load_with_no_config_file_uses_safe_defaults():
    config = WardenConfig.load(config_path=None)
    assert config.allowed_roots == (Path.home(),)
    assert config.unsafe_shell is False
    assert "git" in config.allowed_commands


def test_load_reads_json_config_file(tmp_path: Path):
    config_file = tmp_path / "warden.json"
    config_file.write_text(
        json.dumps(
            {
                "allowed_roots": [str(tmp_path)],
                "allowed_commands": ["git"],
                "allowed_apps": ["code"],
                "unsafe_shell": True,
                "confirmation_ttl_seconds": 30,
            }
        )
    )
    config = WardenConfig.load(config_path=config_file)
    assert config.allowed_roots == (tmp_path,)
    assert config.allowed_commands == ("git",)
    assert config.allowed_apps == ("code",)
    assert config.unsafe_shell is True
    assert config.confirmation_ttl_seconds == 30.0


def test_load_with_nonexistent_config_path_falls_back_to_defaults(tmp_path: Path):
    config = WardenConfig.load(config_path=tmp_path / "does-not-exist.json")
    assert config.allowed_roots == (Path.home(),)
