"""Shared helpers for devteam hooks. Standard library only."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def read_input() -> dict[str, Any]:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}


def find_devteam_root(start: str | os.PathLike[str] | None) -> Path | None:
    """Walk up from `start` to the first directory holding .devteam/config.json.

    Worktrees live under <main>/.devteam/worktrees/, so walking up from a
    worktree also finds the main checkout's config.
    """
    if not start:
        return None
    p = Path(start).expanduser()
    try:
        p = p.resolve()
    except OSError:
        return None
    for candidate in (p, *p.parents):
        if (candidate / ".devteam" / "config.json").is_file():
            return candidate
    return None


def load_config(root: Path | None) -> dict[str, Any]:
    if root is None:
        return {}
    try:
        return json.loads((root / ".devteam" / "config.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def git(args: list[str], cwd: str | os.PathLike[str]) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=5, check=False
        )
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def block(message: str) -> None:
    """Exit code 2 blocks the tool call and shows stderr to Claude."""
    print(f"devteam guard: {message}", file=sys.stderr)
    sys.exit(2)
