from unittest.mock import patch

import pytest

from warden.core import apps
from warden.safety import PermissionDenied


def test_launch_app_rejects_non_allowlisted_app(config):
    with pytest.raises(PermissionDenied):
        apps.launch_app(config, "some-random-app")


def test_launch_app_calls_startfile_on_windows(config):
    # create=True: os.startfile doesn't exist at all on non-Windows Python, but
    # this test deliberately exercises the Windows branch regardless of the
    # host OS actually running the suite (CI runs this on Linux and Windows).
    with (
        patch("warden.core.apps.platform.system", return_value="Windows"),
        patch("warden.core.apps.os.startfile", create=True) as mock_startfile,
    ):
        result = apps.launch_app(config, "notepad")
        mock_startfile.assert_called_once_with("notepad")
        assert result == {"status": "ok", "launched": "notepad"}


def test_launch_app_with_args_uses_popen_instead_of_startfile(config):
    with patch("warden.core.apps.Popen") as mock_popen:
        apps.launch_app(config, "notepad", args=["file.txt"])
        mock_popen.assert_called_once_with(["notepad", "file.txt"])


def test_launch_app_uses_open_on_macos(config):
    with (
        patch("warden.core.apps.platform.system", return_value="Darwin"),
        patch("warden.core.apps.Popen") as mock_popen,
    ):
        apps.launch_app(config, "notepad")
        mock_popen.assert_called_once_with(["open", "-a", "notepad"])
