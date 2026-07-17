from pathlib import Path

from warden.audit import AuditLogger
from warden.core import introspection


def test_get_effective_permissions_reflects_config(config, sandbox):
    perms = introspection.get_effective_permissions(config)
    assert perms["allowed_roots"] == [str(sandbox)]
    assert perms["allowed_commands"] == list(config.allowed_commands)
    assert perms["allowed_apps"] == list(config.allowed_apps)
    assert perms["unsafe_shell"] is False
    assert perms["confirmation_ttl_seconds"] == 120.0


def test_get_audit_log_returns_recent_entries(tmp_path: Path):
    audit = AuditLogger(tmp_path / "audit.log")
    audit.log("read_file", {"path": "/x"}, status="ok")
    audit.log("delete_file", {"path": "/y"}, status="confirmation_required")

    entries = introspection.get_audit_log(audit, limit=50)
    assert [e["tool"] for e in entries] == ["read_file", "delete_file"]


def test_get_audit_log_respects_limit_and_filter(tmp_path: Path):
    audit = AuditLogger(tmp_path / "audit.log")
    audit.log("read_file", {}, status="ok")
    audit.log("delete_file", {}, status="ok")
    audit.log("read_file", {}, status="error")

    entries = introspection.get_audit_log(audit, limit=50, tool_filter="read_file")
    assert len(entries) == 2
    assert all(e["tool"] == "read_file" for e in entries)
