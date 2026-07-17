"""Integration tests that go through the real MCP protocol layer (mcp.call_tool),
not just the plain functions in warden.core -- this is what actually proves the
FastMCP wiring, the module-level config/confirmation/audit singletons, and the
audit-logging wrapper in _run() all work together, not just each piece alone.
"""

from __future__ import annotations

import pytest
from mcp.server.fastmcp.exceptions import ToolError

import warden.server as server_module
from warden.audit import AuditLogger


@pytest.fixture(autouse=True)
def _patch_server_globals(config, confirmations, monkeypatch, tmp_path):
    """Point the server's module-level singletons at a sandboxed config for
    every test in this file, instead of whatever real config/home directory
    the process happened to load at import time."""
    monkeypatch.setattr(server_module, "_config", config)
    monkeypatch.setattr(server_module, "_confirmations", confirmations)
    monkeypatch.setattr(server_module, "_audit", AuditLogger(tmp_path / "audit.log"))


def _text(result):
    """FastMCP's call_tool returns (content_blocks, structured_result); the
    structured result is what we actually want to assert on."""
    return result[1]


async def test_get_system_info_round_trips_through_mcp(sandbox):
    result = await server_module.mcp.call_tool("get_system_info", {})
    data = _text(result)
    assert data["os"]
    assert data["cpu_count"] >= 1


async def test_list_directory_enforces_allowed_roots(sandbox):
    result = await server_module.mcp.call_tool("list_directory", {"path": str(sandbox)})
    # FastMCP wraps a bare list return in {"result": [...]} since structured
    # output requires a top-level object.
    entries = _text(result)["result"]
    names = {entry["name"] for entry in entries}
    assert names == {"existing.txt", "sub"}


async def test_list_directory_outside_allowed_roots_raises(tmp_path):
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    with pytest.raises(ToolError, match="outside all allowed_roots"):
        await server_module.mcp.call_tool("list_directory", {"path": str(outside)})


async def test_delete_file_confirmation_round_trip_through_mcp(sandbox):
    target = sandbox / "existing.txt"

    first = _text(await server_module.mcp.call_tool("delete_file", {"path": str(target)}))
    assert first["status"] == "confirmation_required"
    assert target.exists()

    second = _text(
        await server_module.mcp.call_tool(
            "delete_file", {"path": str(target), "confirm_token": first["confirm_token"]}
        )
    )
    assert second["status"] == "ok"
    assert not target.exists()


async def test_run_command_rejects_non_allowlisted_command_through_mcp(sandbox):
    with pytest.raises(ToolError, match="not in allowed_commands"):
        await server_module.mcp.call_tool("run_command", {"command": "rm", "args": ["-rf", "."]})


async def test_every_call_is_recorded_in_the_audit_log(sandbox):
    await server_module.mcp.call_tool("get_system_info", {})
    entries = server_module._audit.read_all()
    assert any(e["tool"] == "get_system_info" and e["status"] == "ok" for e in entries)


async def test_failed_call_is_recorded_in_the_audit_log_too(sandbox):
    with pytest.raises(ToolError):
        await server_module.mcp.call_tool("read_file", {"path": "/definitely/not/allowed.txt"})
    entries = server_module._audit.read_all()
    assert any(e["tool"] == "read_file" and e["status"] == "error" for e in entries)
