"""PostToolUse(Edit|Write) hook: lint the file Claude just changed.

Runs `lint_file_cmd` from .devteam/config.json (with {file} replaced) on the
edited file, only inside devteam repos and only when `lint_on_edit` is true.
Problems are fed back to Claude (exit 2) so it fixes them right away instead
of waiting for the PR lint gate.
"""
from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

from _common import find_devteam_root, load_config, read_input

MAX_OUTPUT = 4000


def main() -> None:
    data = read_input()
    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path")
    if not file_path:
        return

    path = Path(file_path)
    if not path.is_absolute():
        path = Path(data.get("cwd") or ".") / path
    if not path.is_file():
        return

    root = find_devteam_root(path.parent)
    if root is None:
        return
    # Never lint devteam's own scratch files.
    if ".devteam" in path.parts and "worktrees" not in path.parts:
        return

    cfg = load_config(root)
    if not cfg.get("lint_on_edit", True):
        return
    template = cfg.get("lint_file_cmd")
    if not template or "{file}" not in template:
        return

    exts = cfg.get("lint_extensions")
    if exts and path.suffix not in exts:
        return

    # Run from the checkout that owns the file (a worktree or the main checkout).
    workdir = path.parent
    for candidate in (path.parent, *path.parent.parents):
        if (candidate / ".git").exists():
            workdir = candidate
            break

    cmd = template.replace("{file}", shlex.quote(str(path)))
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=workdir, capture_output=True, text=True, timeout=80, check=False
        )
    except subprocess.TimeoutExpired:
        return

    if result.returncode != 0:
        output = (result.stdout + "\n" + result.stderr).strip()
        if len(output) > MAX_OUTPUT:
            output = output[:MAX_OUTPUT] + "\n… (truncated)"
        print(
            f"devteam lint: {path.name} has problems. Fix them now (don't disable rules):\n{output}",
            file=sys.stderr,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
