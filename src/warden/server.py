"""MCP server wiring: thin @mcp.tool() wrappers around warden.core's plain
functions, with a single audit-log call around every one of them.

The core functions in warden/core/*.py contain all the actual logic and are
fully unit-tested without any MCP machinery involved; this module only
exists to expose them over the protocol and record what happened.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from warden.audit import AuditLogger
from warden.config import WardenConfig
from warden.confirmation import ConfirmationStore
from warden.core import apps, filesystem, introspection, process, system

mcp = FastMCP("warden")

_config = WardenConfig.load()
_confirmations = ConfirmationStore(ttl_seconds=_config.confirmation_ttl_seconds)
_audit = AuditLogger(_config.audit_log_path)


def _run(tool_name: str, args: dict[str, Any], fn, *fn_args, **fn_kwargs) -> Any:
    try:
        result = fn(*fn_args, **fn_kwargs)
    except Exception as exc:
        _audit.log(tool_name, args, status="error", detail=str(exc))
        raise
    status = result.get("status", "ok") if isinstance(result, dict) else "ok"
    _audit.log(tool_name, args, status=status)
    return result


@mcp.tool()
def list_directory(path: str) -> list[dict[str, Any]]:
    """List the contents of a directory (name, is_dir, size_bytes). Read-only."""
    return _run("list_directory", {"path": path}, filesystem.list_directory, _config, path)


@mcp.tool()
def read_file(path: str, max_bytes: int = filesystem.MAX_READ_BYTES_DEFAULT) -> str:
    """Read a text file's contents. Read-only."""
    return _run(
        "read_file",
        {"path": path, "max_bytes": max_bytes},
        filesystem.read_file,
        _config,
        path,
        max_bytes,
    )


@mcp.tool()
def search_files(
    root: str,
    glob_pattern: str = "*",
    content_regex: str | None = None,
) -> list[dict[str, Any]]:
    """Find files under `root` matching a glob pattern, optionally filtering to
    files whose contents match a regex (returns matching line numbers/text). Read-only."""
    return _run(
        "search_files",
        {"root": root, "glob_pattern": glob_pattern, "content_regex": content_regex},
        filesystem.search_files,
        _config,
        root,
        glob_pattern,
        content_regex,
    )


@mcp.tool()
def write_file(path: str, content: str, confirm_token: str | None = None) -> dict[str, Any]:
    """Write text to a file. Creating a new file is immediate; overwriting an
    existing one requires calling this twice -- the first call returns a
    confirm_token, which must be passed back to actually overwrite."""
    return _run(
        "write_file",
        {"path": path, "confirm_token": confirm_token},
        filesystem.write_file,
        _config,
        _confirmations,
        path,
        content,
        confirm_token,
    )


@mcp.tool()
def delete_file(path: str, confirm_token: str | None = None) -> dict[str, Any]:
    """Delete a file. Always requires a two-step confirm_token round-trip
    (see write_file's docstring for the pattern)."""
    return _run(
        "delete_file",
        {"path": path, "confirm_token": confirm_token},
        filesystem.delete_file,
        _config,
        _confirmations,
        path,
        confirm_token,
    )


@mcp.tool()
def list_processes() -> list[dict[str, Any]]:
    """List running processes (pid, name, memory_mb). Read-only."""
    return _run("list_processes", {}, process.list_processes)


@mcp.tool()
def run_command(
    command: str,
    args: list[str] | None = None,
    cwd: str | None = None,
    timeout: float = process.DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Run a command and return its stdout/stderr/exit code. Only commands in
    the operator's allowed_commands config may run, unless unsafe_shell is set."""
    return _run(
        "run_command",
        {"command": command, "args": args, "cwd": cwd, "timeout": timeout},
        process.run_command,
        _config,
        command,
        args,
        cwd,
        timeout,
    )


@mcp.tool()
def kill_process(pid: int, confirm_token: str | None = None) -> dict[str, Any]:
    """Terminate a process by pid. Always requires the two-step confirm_token flow."""
    return _run(
        "kill_process",
        {"pid": pid, "confirm_token": confirm_token},
        process.kill_process,
        _confirmations,
        pid,
        confirm_token,
    )


@mcp.tool()
def launch_app(name_or_path: str, args: list[str] | None = None) -> dict[str, Any]:
    """Launch an application. Only apps in the operator's allowed_apps config may run."""
    return _run(
        "launch_app",
        {"name_or_path": name_or_path, "args": args},
        apps.launch_app,
        _config,
        name_or_path,
        args,
    )


@mcp.tool()
def get_system_info() -> dict[str, Any]:
    """Get OS, CPU, memory, and disk usage info. Read-only."""
    return _run("get_system_info", {}, system.get_system_info)


@mcp.tool()
def get_effective_permissions() -> dict[str, Any]:
    """Show the operator's current allowed_roots/allowed_commands/allowed_apps/
    unsafe_shell config -- what this warden instance is actually permitted to
    touch, before attempting something that might be out of scope. Read-only."""
    return _run("get_effective_permissions", {}, introspection.get_effective_permissions, _config)


@mcp.tool()
def get_audit_log(limit: int = 50, tool_filter: str | None = None) -> list[dict[str, Any]]:
    """Show the most recent tool calls this warden instance has made (what,
    when, and whether it succeeded) -- answers "what have you done to my
    machine" from inside the same session, instead of requiring the operator
    to go read the log file by hand. Read-only."""
    return _run(
        "get_audit_log",
        {"limit": limit, "tool_filter": tool_filter},
        introspection.get_audit_log,
        _audit,
        limit,
        tool_filter,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
