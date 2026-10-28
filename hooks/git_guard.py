"""PreToolUse(Bash) guard for repos that use devteam.

Blocks, in any repo that has .devteam/config.json:
  * force pushes (--force, -f, --force-with-lease, +refspec)
  * pushes to the base branch or any protected branch (incl. deleting them)
  * --no-verify on git commit / git push (skipping the lint hooks)
  * gh pr merge, unless config allow_agent_merge is true AND DEVTEAM_ALLOW_MERGE=1
  * gh repo delete, and gh api calls with the DELETE method

Repos without .devteam/config.json are never touched.
Escape hatch for a human: export DEVTEAM_GUARD=off
"""
from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

from _common import block, find_devteam_root, git, load_config, read_input

SEGMENT_SPLIT = re.compile(r"\s*(?:&&|\|\||;|\||\n)\s*")


def tokens_of(segment: str) -> list[str]:
    try:
        return shlex.split(segment, comments=False)
    except ValueError:
        return segment.split()


def strip_prefix(toks: list[str]) -> list[str]:
    """Drop env assignments and wrappers like `sudo`, `command`, `env X=1`."""
    i = 0
    while i < len(toks):
        t = toks[i]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t) or t in {"sudo", "command", "env", "time", "nohup"}:
            i += 1
            continue
        break
    return toks[i:]


def git_subcommand(toks: list[str]) -> tuple[str | None, list[str], str | None]:
    """Return (subcommand, args after it, -C dir) for a git invocation."""
    i, cdir = 1, None
    while i < len(toks) and toks[i].startswith("-"):
        if toks[i] == "-C" and i + 1 < len(toks):
            cdir = toks[i + 1]
            i += 2
            continue
        if toks[i] in {"-c", "--git-dir", "--work-tree", "--namespace"} and i + 1 < len(toks):
            i += 2
            continue
        i += 1
    if i >= len(toks):
        return None, [], cdir
    return toks[i], toks[i + 1 :], cdir


def check_push(args: list[str], workdir: str, protected: set[str]) -> None:
    flags = [a for a in args if a.startswith("-")]
    positional = [a for a in args if not a.startswith("-")]

    for f in flags:
        if f in {"--force", "-f", "--force-if-includes"} or f.startswith("--force-with-lease") or (
            re.fullmatch(r"-[a-zA-Z]+", f) and "f" in f[1:]
        ):
            block("force-push is not allowed. Merge the base branch in instead of rewriting history.")
        if f == "--no-verify":
            block("--no-verify skips the lint/commit hooks. Fix the reported problems instead.")
        if f in {"--mirror", "--all", "--delete", "-d"}:
            if f in {"--delete", "-d"} and any(p in protected for p in positional[1:]):
                block("deleting a protected branch is not allowed.")
            if f in {"--mirror", "--all"}:
                block(f"git push {f} is not allowed; push your task branch only.")

    refspecs = positional[1:]  # positional[0] is the remote
    for spec in refspecs:
        if spec.startswith("+"):
            block("force-push via +refspec is not allowed.")
        dst = spec.split(":", 1)[1] if ":" in spec else spec
        dst = dst.removeprefix("refs/heads/")
        if dst in {"HEAD", "@"}:
            dst = git(["rev-parse", "--abbrev-ref", "HEAD"], workdir)
        if dst in protected:
            block(f"pushing to protected branch '{dst}' is not allowed. Open a PR from a task branch.")

    if not refspecs:
        current = git(["rev-parse", "--abbrev-ref", "HEAD"], workdir)
        if current in protected:
            block(f"you are on protected branch '{current}'. Switch to a task branch before pushing.")
        if current == "HEAD" and len(positional) <= 1:
            block("detached HEAD push without a refspec; push an explicit task branch.")


def main() -> None:
    data = read_input()
    if os.environ.get("DEVTEAM_GUARD", "").lower() == "off":
        return
    if data.get("tool_name") != "Bash":
        return
    command = (data.get("tool_input") or {}).get("command") or ""
    cwd = data.get("cwd") or os.getcwd()

    root = find_devteam_root(cwd)
    if root is None:
        # Also catch commands that cd into a devteam repo from elsewhere.
        m = re.search(r"\bcd\s+([^\s;&|]+)", command)
        root = find_devteam_root(m.group(1)) if m else None
    if root is None:
        return

    cfg = load_config(root)
    protected = {"main", "master", "develop", "production", "release"}
    if cfg.get("base_branch"):
        protected.add(str(cfg["base_branch"]))
    protected.update(str(b) for b in cfg.get("protected_branches", []))

    workdir = cwd
    for segment in SEGMENT_SPLIT.split(command):
        if not segment.strip():
            continue
        toks = strip_prefix(tokens_of(segment))
        if not toks:
            continue
        prog = Path(toks[0]).name

        if prog == "cd" and len(toks) > 1:
            target = Path(toks[1]).expanduser()
            workdir = str(target if target.is_absolute() else Path(workdir) / target)
            continue

        if prog == "git":
            sub, args, cdir = git_subcommand(toks)
            where = cdir or workdir
            if sub == "push":
                check_push(args, where, protected)
            elif sub == "commit" and ("--no-verify" in args or any(
                re.fullmatch(r"-[a-zA-Z]*n[a-zA-Z]*", a) for a in args if not a.startswith("--")
            )):
                block("git commit --no-verify skips the lint hooks. Fix the reported problems instead.")
            elif sub == "branch" and any(a in {"-D", "-d", "--delete"} for a in args) and any(
                a in protected for a in args
            ):
                block("deleting a protected branch is not allowed.")

        elif prog in {"gh", "gh-as-reviewer"} and len(toks) > 1:
            if toks[1] == "pr" and len(toks) > 2 and toks[2] == "merge":
                allowed = bool(cfg.get("allow_agent_merge")) and os.environ.get("DEVTEAM_ALLOW_MERGE") == "1"
                if not allowed:
                    block(
                        "agents don't merge PRs. Label the PR devteam:ready-to-merge and let the human merge "
                        "(or set allow_agent_merge in .devteam/config.json and DEVTEAM_ALLOW_MERGE=1)."
                    )
            if toks[1] == "repo" and len(toks) > 2 and toks[2] in {"delete", "archive", "rename"}:
                block(f"gh repo {toks[2]} is not allowed.")
            if toks[1] == "api":
                joined = " ".join(toks).upper()
                if re.search(r"(-X|--METHOD)[ =]?DELETE\b", joined):
                    block("DELETE calls through gh api are not allowed for agents.")


if __name__ == "__main__":
    main()
