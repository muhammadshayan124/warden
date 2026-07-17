import pytest

from warden.core import filesystem
from warden.safety import PermissionDenied


def test_list_directory_returns_entries_with_metadata(config, sandbox):
    entries = filesystem.list_directory(config, str(sandbox))
    names = {e["name"] for e in entries}
    assert names == {"existing.txt", "sub"}
    file_entry = next(e for e in entries if e["name"] == "existing.txt")
    assert file_entry["is_dir"] is False
    assert file_entry["size_bytes"] == len(b"hello")


def test_read_file_returns_contents(config, sandbox):
    assert filesystem.read_file(config, str(sandbox / "existing.txt")) == "hello"


def test_read_file_rejects_oversized_file(config, sandbox):
    with pytest.raises(ValueError, match="exceeding max_bytes"):
        filesystem.read_file(config, str(sandbox / "existing.txt"), max_bytes=1)


def test_read_file_outside_root_is_denied(config, tmp_path):
    outside = tmp_path.parent / "outside.txt"
    with pytest.raises(PermissionDenied):
        filesystem.read_file(config, str(outside))


def test_search_files_finds_matching_glob(config, sandbox):
    results = filesystem.search_files(config, str(sandbox), glob_pattern="*.py")
    assert [r["path"] for r in results] == [str(sandbox / "sub" / "nested.py")]


def test_search_files_filters_by_content_regex(config, sandbox):
    results = filesystem.search_files(
        config, str(sandbox), glob_pattern="*.py", content_regex="needle"
    )
    assert len(results) == 1
    assert results[0]["matching_lines"][0]["line_number"] == 1


def test_search_files_content_regex_with_no_match_excludes_file(config, sandbox):
    results = filesystem.search_files(
        config, str(sandbox), glob_pattern="*.py", content_regex="nope"
    )
    assert results == []


def test_write_file_creates_new_file_without_confirmation(config, confirmations, sandbox):
    result = filesystem.write_file(config, confirmations, str(sandbox / "new.txt"), "content")
    assert result["status"] == "ok"
    assert (sandbox / "new.txt").read_text() == "content"


def test_write_file_over_existing_requires_confirmation(config, confirmations, sandbox):
    target = sandbox / "existing.txt"
    result = filesystem.write_file(config, confirmations, str(target), "new content")
    assert result["status"] == "confirmation_required"
    assert target.read_text() == "hello"  # unchanged


def test_write_file_over_existing_succeeds_with_valid_token(config, confirmations, sandbox):
    target = sandbox / "existing.txt"
    first = filesystem.write_file(config, confirmations, str(target), "new content")
    second = filesystem.write_file(
        config, confirmations, str(target), "new content", confirm_token=first["confirm_token"]
    )
    assert second["status"] == "ok"
    assert target.read_text() == "new content"


def test_write_file_rejects_bad_confirm_token(config, confirmations, sandbox):
    target = sandbox / "existing.txt"
    with pytest.raises(PermissionError):
        filesystem.write_file(config, confirmations, str(target), "x", confirm_token="bogus")


def test_delete_file_requires_confirmation(config, confirmations, sandbox):
    target = sandbox / "existing.txt"
    result = filesystem.delete_file(config, confirmations, str(target))
    assert result["status"] == "confirmation_required"
    assert target.exists()


def test_delete_file_succeeds_with_valid_token(config, confirmations, sandbox):
    target = sandbox / "existing.txt"
    first = filesystem.delete_file(config, confirmations, str(target))
    second = filesystem.delete_file(
        config, confirmations, str(target), confirm_token=first["confirm_token"]
    )
    assert second["status"] == "ok"
    assert not target.exists()


def test_delete_file_token_cannot_be_reused_for_a_different_file(config, confirmations, sandbox):
    other = sandbox / "other.txt"
    other.write_text("x")
    target = sandbox / "existing.txt"
    token_for_target = filesystem.delete_file(config, confirmations, str(target))["confirm_token"]
    with pytest.raises(PermissionError):
        filesystem.delete_file(config, confirmations, str(other), confirm_token=token_for_target)
    assert other.exists()
