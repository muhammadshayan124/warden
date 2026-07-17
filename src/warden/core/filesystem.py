"""File operations, scoped to config.allowed_roots.

Reads and directory listings are always safe (no confirmation needed).
Writing over an *existing* file and deleting a file are destructive and go
through the ConfirmationStore two-step flow; creating a brand new file does
not, since nothing is lost by it.
"""

from __future__ import annotations

import fnmatch
import re
from typing import Any

from warden.config import WardenConfig
from warden.confirmation import ConfirmationStore
from warden.safety import resolve_scoped_path

MAX_READ_BYTES_DEFAULT = 200_000
MAX_SEARCH_RESULTS_DEFAULT = 200


def list_directory(config: WardenConfig, path: str) -> list[dict[str, Any]]:
    target = resolve_scoped_path(path, config)
    if not target.is_dir():
        raise NotADirectoryError(f"'{target}' is not a directory")
    entries = []
    for child in sorted(target.iterdir()):
        stat = child.stat()
        entries.append(
            {
                "name": child.name,
                "is_dir": child.is_dir(),
                "size_bytes": stat.st_size if not child.is_dir() else None,
            }
        )
    return entries


def read_file(config: WardenConfig, path: str, max_bytes: int = MAX_READ_BYTES_DEFAULT) -> str:
    target = resolve_scoped_path(path, config)
    if not target.is_file():
        raise FileNotFoundError(f"'{target}' is not a file")
    size = target.stat().st_size
    if size > max_bytes:
        raise ValueError(f"'{target}' is {size} bytes, exceeding max_bytes={max_bytes}")
    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"'{target}' does not look like a text file") from exc


def search_files(
    config: WardenConfig,
    root: str,
    glob_pattern: str = "*",
    content_regex: str | None = None,
    max_results: int = MAX_SEARCH_RESULTS_DEFAULT,
) -> list[dict[str, Any]]:
    base = resolve_scoped_path(root, config)
    if not base.is_dir():
        raise NotADirectoryError(f"'{base}' is not a directory")

    pattern = re.compile(content_regex) if content_regex else None
    results: list[dict[str, Any]] = []

    for candidate in sorted(base.rglob("*")):
        if len(results) >= max_results:
            break
        if not candidate.is_file() or not fnmatch.fnmatch(candidate.name, glob_pattern):
            continue
        if pattern is None:
            results.append({"path": str(candidate), "matching_lines": []})
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        matches = [
            {"line_number": i + 1, "line": line}
            for i, line in enumerate(text.splitlines())
            if pattern.search(line)
        ]
        if matches:
            results.append({"path": str(candidate), "matching_lines": matches[:20]})

    return results


def write_file(
    config: WardenConfig,
    confirmations: ConfirmationStore,
    path: str,
    content: str,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    target = resolve_scoped_path(path, config)
    exists = target.exists()

    if exists:
        fingerprint = f"write:{target}"
        if not confirm_token:
            token = confirmations.create("write_file", fingerprint)
            return {
                "status": "confirmation_required",
                "confirm_token": token,
                "summary": f"'{target}' already exists ({target.stat().st_size} bytes) "
                f"and would be overwritten. Call write_file again with this "
                f"confirm_token to proceed.",
            }
        if not confirmations.verify(confirm_token, "write_file", fingerprint):
            raise PermissionError("Invalid, expired, or already-used confirm_token for write_file")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"status": "ok", "path": str(target), "bytes_written": len(content.encode("utf-8"))}


def delete_file(
    config: WardenConfig,
    confirmations: ConfirmationStore,
    path: str,
    confirm_token: str | None = None,
) -> dict[str, Any]:
    target = resolve_scoped_path(path, config)
    if not target.is_file():
        raise FileNotFoundError(f"'{target}' is not a file")

    fingerprint = f"delete:{target}"
    if not confirm_token:
        token = confirmations.create("delete_file", fingerprint)
        return {
            "status": "confirmation_required",
            "confirm_token": token,
            "summary": f"This will permanently delete '{target}'. "
            f"Call delete_file again with this confirm_token to proceed.",
        }

    if not confirmations.verify(confirm_token, "delete_file", fingerprint):
        raise PermissionError("Invalid, expired, or already-used confirm_token for delete_file")

    target.unlink()
    return {"status": "ok", "path": str(target)}
