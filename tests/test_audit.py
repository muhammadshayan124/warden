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
