import subprocess
import sys
import time

import psutil
import pytest

from warden.core import process
from warden.safety import PermissionDenied


def test_list_processes_includes_this_test_run(config):
    processes = process.list_processes()
    assert len(processes) > 0
    assert all({"pid", "name", "memory_mb"} <= set(p.keys()) for p in processes)


def test_run_command_executes_allowlisted_command(config):
    result = process.run_command(config, "python", ["-c", "print('hi')"])
    assert result["status"] == "ok"
    assert result["stdout"].strip() == "hi"
    assert result["returncode"] == 0


def test_run_command_rejects_non_allowlisted_command(config):
    with pytest.raises(PermissionDenied):
        process.run_command(config, "rm", ["-rf", "/"])


def test_run_command_permits_anything_in_unsafe_shell_mode(config):
    unsafe_config = config.__class__(**{**config.__dict__, "unsafe_shell": True})
    result = process.run_command(unsafe_config, "python", ["-c", "print('unsafe ok')"])
    assert result["stdout"].strip() == "unsafe ok"


def test_run_command_reports_nonzero_exit(config):
    result = process.run_command(config, "python", ["-c", "import sys; sys.exit(3)"])
    assert result["status"] == "nonzero_exit"
    assert result["returncode"] == 3


def test_run_command_times_out(config):
    result = process.run_command(
        config, "python", ["-c", "import time; time.sleep(5)"], timeout=0.2
    )
    assert result["status"] == "timeout"


def test_run_command_defaults_cwd_to_first_allowed_root(config, sandbox):
    result = process.run_command(config, "python", ["-c", "import os; print(os.getcwd())"])
    assert result["cwd"] == str(sandbox)


def test_run_command_honors_explicit_cwd_within_allowed_roots(config, sandbox):
    result = process.run_command(
        config, "python", ["-c", "import os; print(os.getcwd())"], cwd=str(sandbox / "sub")
    )
    assert result["cwd"] == str(sandbox / "sub")


def test_run_command_rejects_cwd_outside_allowed_roots(config, tmp_path):
    outside = tmp_path.parent / "outside-cwd"
    outside.mkdir(exist_ok=True)
    with pytest.raises(PermissionDenied):
        process.run_command(config, "python", ["-c", "print('hi')"], cwd=str(outside))


@pytest.fixture
def sleeper_process():
    """A real, harmless child process to exercise kill_process against."""
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    time.sleep(0.3)  # let it fully start
    yield proc
    if psutil.pid_exists(proc.pid):
        proc.kill()
    proc.wait(timeout=5)


def test_kill_process_requires_confirmation(confirmations, sleeper_process):
    result = process.kill_process(confirmations, sleeper_process.pid)
    assert result["status"] == "confirmation_required"
    assert psutil.pid_exists(sleeper_process.pid)


def test_kill_process_succeeds_with_valid_token(confirmations, sleeper_process):
    first = process.kill_process(confirmations, sleeper_process.pid)
    second = process.kill_process(
        confirmations, sleeper_process.pid, confirm_token=first["confirm_token"]
    )
    assert second["status"] == "ok"
    sleeper_process.wait(timeout=5)
    assert not psutil.pid_exists(sleeper_process.pid)


def test_kill_process_token_cannot_target_a_different_pid(confirmations, sleeper_process):
    token_for_real_pid = process.kill_process(confirmations, sleeper_process.pid)["confirm_token"]
    with pytest.raises(PermissionError):
        process.kill_process(
            confirmations, sleeper_process.pid + 1, confirm_token=token_for_real_pid
        )
    assert psutil.pid_exists(sleeper_process.pid)


def test_kill_process_raises_for_unknown_pid(confirmations):
    with pytest.raises(ProcessLookupError):
        process.kill_process(confirmations, pid=999_999_999)
