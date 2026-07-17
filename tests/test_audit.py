import json
from pathlib import Path

from warden.audit import AuditLogger


def test_log_appends_jsonl_entry(tmp_path: Path):
    logger = AuditLogger(tmp_path / "audit.log")
    logger.log("read_file", {"path": "/x"}, status="ok")
    entries = logger.read_all()
    assert len(entries) == 1
    assert entries[0]["tool"] == "read_file"
    assert entries[0]["args"] == {"path": "/x"}
    assert entries[0]["status"] == "ok"
    assert "ts" in entries[0]


def test_log_creates_parent_directory(tmp_path: Path):
    logger = AuditLogger(tmp_path / "nested" / "dir" / "audit.log")
    logger.log("get_system_info", {}, status="ok")
    assert (tmp_path / "nested" / "dir" / "audit.log").exists()


def test_multiple_entries_are_appended_in_order(tmp_path: Path):
    logger = AuditLogger(tmp_path / "audit.log")
    logger.log("tool_a", {}, status="ok")
    logger.log("tool_b", {}, status="error", detail="boom")
    entries = logger.read_all()
    assert [e["tool"] for e in entries] == ["tool_a", "tool_b"]
    assert entries[1]["detail"] == "boom"


def test_read_all_returns_empty_list_when_no_log_yet(tmp_path: Path):
    logger = AuditLogger(tmp_path / "never-written.log")
    assert logger.read_all() == []


def test_read_recent_respects_limit(tmp_path: Path):
    logger = AuditLogger(tmp_path / "audit.log")
    for i in range(5):
        logger.log(f"tool_{i}", {}, status="ok")
    recent = logger.read_recent(limit=2)
    assert [e["tool"] for e in recent] == ["tool_3", "tool_4"]


def test_read_recent_filters_by_tool(tmp_path: Path):
    logger = AuditLogger(tmp_path / "audit.log")
    logger.log("read_file", {}, status="ok")
    logger.log("delete_file", {}, status="ok")
    logger.log("read_file", {}, status="error")
    recent = logger.read_recent(limit=50, tool_filter="read_file")
    assert [e["status"] for e in recent] == ["ok", "error"]


def test_log_rotates_once_max_bytes_is_exceeded(tmp_path: Path):
    log_path = tmp_path / "audit.log"
    logger = AuditLogger(log_path, max_bytes=200)
    for _ in range(20):
        logger.log("some_tool", {"note": "padding to grow the file"}, status="ok")

    backup_path = log_path.with_suffix(".log.1")
    assert backup_path.exists()
    # The live log should only hold entries written since the last rotation.
    assert len(logger.read_all()) < 20


def test_rotation_preserves_older_entries_in_the_backup_file(tmp_path: Path):
    log_path = tmp_path / "audit.log"
    logger = AuditLogger(log_path, max_bytes=1)  # rotate on every single write
    logger.log("tool_a", {}, status="ok")
    logger.log("tool_b", {}, status="ok")

    backup_path = log_path.with_suffix(".log.1")
    backup_entries = [
        json.loads(line)
        for line in backup_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert backup_entries[0]["tool"] == "tool_a"
