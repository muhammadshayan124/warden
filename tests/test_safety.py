import pytest

from warden.safety import (
    PermissionDenied,
    check_app_allowed,
    check_command_allowed,
    resolve_scoped_path,
)


def test_resolve_scoped_path_allows_paths_inside_root(config, sandbox):
    resolved = resolve_scoped_path(str(sandbox / "existing.txt"), config)
    assert resolved == (sandbox / "existing.txt").resolve()


def test_resolve_scoped_path_allows_the_root_itself(config, sandbox):
    assert resolve_scoped_path(str(sandbox), config) == sandbox.resolve()


def test_resolve_scoped_path_rejects_paths_outside_root(config, tmp_path):
    outside = tmp_path.parent / "definitely-not-allowed.txt"
    with pytest.raises(PermissionDenied):
        resolve_scoped_path(str(outside), config)


def test_resolve_scoped_path_rejects_dotdot_escape(config, sandbox):
    escape_attempt = str(sandbox / "sub" / ".." / ".." / "escaped.txt")
    with pytest.raises(PermissionDenied):
        resolve_scoped_path(escape_attempt, config)


def test_check_command_allowed_passes_for_allowlisted_command(config):
    check_command_allowed("echo", config)  # should not raise


def test_check_command_allowed_rejects_non_allowlisted_command(config):
    with pytest.raises(PermissionDenied):
        check_command_allowed("rm", config)


def test_check_command_allowed_strips_path_and_extension(config):
    # Forward slashes, not backslashes: pathlib.Path only treats backslash as
    # a separator on Windows, so a hardcoded Windows-style path would parse
    # into one giant filename component on Linux/macOS CI runners and this
    # test would fail there for reasons unrelated to the actual behavior
    # being tested. Forward slashes are separators on every platform pathlib
    # supports, which is what makes this test portable across the CI matrix.
    check_command_allowed("/usr/local/bin/echo.exe", config)  # should not raise


def test_check_command_allowed_permits_anything_in_unsafe_shell_mode(config):
    unsafe_config = config.__class__(**{**config.__dict__, "unsafe_shell": True})
    check_command_allowed("literally-anything", unsafe_config)  # should not raise


def test_check_app_allowed_passes_for_allowlisted_app(config):
    check_app_allowed("notepad", config)  # should not raise


def test_check_app_allowed_rejects_non_allowlisted_app(config):
    with pytest.raises(PermissionDenied):
        check_app_allowed("some-random-app", config)
