# warden

An MCP server that gives an LLM real, scoped control over a machine — reading and writing files, running commands, launching apps, inspecting processes — without handing it the whole computer.

```
$ warden --config warden.config.json

Claude: "Clean up the old log files in this project"
  → list_directory("D:/projects/myapp/logs")          [read-only, runs immediately]
  → delete_file("D:/projects/myapp/logs/old.log")      [destructive]
    ← {"status": "confirmation_required", "confirm_token": "a3f9..."}
  → delete_file("D:/projects/myapp/logs/old.log", confirm_token="a3f9...")
    ← {"status": "ok"}
```

*(real output shape — every destructive call above genuinely round-trips through the confirmation step; nothing is deleted on the first call.)*

## Why this exists, and why it isn't "computer use"

Most "AI controls your PC" demos work by taking a screenshot, asking a vision model where to click, and simulating mouse/keyboard input. That's flashy but fragile — it breaks on DPI changes, window focus races, and anything that isn't pixel-perfect where the model expects it.

**warden deliberately does not do that.** It exposes structured, reliable OS-level primitives instead — read/write/search files, run an allowlisted command, launch an allowlisted app, list processes, get system info — the same category of operations a real automation script would use. That's a real tradeoff: warden can't "click a button in some app whose internals it doesn't understand." What it gets in exchange is determinism, and a security model that's actually enforceable, because the boundary is a file path, a command name, or a pid — not a coordinate guess on a screenshot.

## The safety model

Three independent layers, none of which the LLM controls:

1. **Allowlists, set by the operator, not the model.** `allowed_roots` scopes every file operation to specific directories (checked against the *resolved* path, so `..` traversal and symlinks can't escape it). `allowed_commands` and `allowed_apps` do the same for `run_command` and `launch_app`. There's an `unsafe_shell` escape hatch for `run_command`, but it lives in the config file the operator writes — never in a tool argument the model can set.
2. **Two-step confirmation for anything irreversible.** `delete_file`, `kill_process`, and overwriting an *existing* file with `write_file` don't execute on the first call. They return a `confirm_token` bound to that exact action and target (a token minted for deleting file A cannot be replayed against file B), which expires after a configurable TTL. The model has to make a second, distinct tool call to actually go through with it — which means every destructive action is always at least two visible steps, not one.
3. **An audit trail of everything.** Every tool call — successful, rejected, or errored — is appended to a local JSONL log (`~/.warden/audit.log` by default): timestamp, tool, arguments, outcome. It's the thing you'd actually want to check after letting an LLM operate your machine unattended for a while.

## Tools

| Tool | Side effects | Notes |
|---|---|---|
| `list_directory`, `read_file`, `search_files` | none | scoped to `allowed_roots` |
| `write_file` | new file: none · overwrite: destructive | confirmation only when overwriting |
| `delete_file` | destructive | always requires confirmation |
| `list_processes`, `get_system_info` | none | |
| `run_command` | runs a process | scoped to `allowed_commands` unless `unsafe_shell` |
| `kill_process` | destructive | always requires confirmation |
| `launch_app` | launches a process | scoped to `allowed_apps` |

## Install

```bash
pip install -e ".[dev]"
```

## Configure

Write a config file (no config = safe defaults: `allowed_roots` is just your home directory, a short list of common dev-tool commands, no apps allowed):

```json
{
  "allowed_roots": ["D:/projects/myapp"],
  "allowed_commands": ["git", "python", "npm", "pytest"],
  "allowed_apps": ["code", "notepad"],
  "unsafe_shell": false,
  "confirmation_ttl_seconds": 120
}
```

```bash
export WARDEN_CONFIG=/path/to/warden.config.json
warden
```

### Claude Desktop

```json
{
  "mcpServers": {
    "warden": {
      "command": "warden",
      "env": { "WARDEN_CONFIG": "/path/to/warden.config.json" }
    }
  }
}
```

## Tests

96% of this project's logic lives in `warden/core/*.py` as plain functions with no MCP machinery involved, so it's tested directly — no mock transport, no fake protocol client. 52 tests: every allowlist boundary (including the `..`-traversal escape attempt), the full confirm/verify lifecycle (single-use tokens, expiry, cross-target token reuse rejected), a real child process spawned and killed through the two-step flow, and the audit log's on-disk format.

```bash
pytest
ruff check src tests
ruff format src tests
```

## What's deliberately out of scope for v1

- **No mouse/keyboard/screenshot automation.** See "Why this exists" above — this is a scoping decision, not a missing feature I forgot.
- **No network/HTTP tools.** Keeps the threat model to "things on this machine," not "things this machine can reach."
- **`unsafe_shell` is all-or-nothing.** A per-command-with-args allowlist (e.g. "git status but not git push") is the natural next step but adds real parsing complexity; v1 keeps the boundary at the executable name.
