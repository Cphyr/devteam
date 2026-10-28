"""SessionStart hook: remind Claude of unfinished devteam runs in this repo."""
from __future__ import annotations

from _common import find_devteam_root, load_config, read_input


def main() -> None:
    data = read_input()
    root = find_devteam_root(data.get("cwd"))
    if root is None:
        return
    cfg = load_config(root)
    runs_dir = root / ".devteam" / "runs"
    open_runs = []
    if runs_dir.is_dir():
        for f in sorted(runs_dir.glob("*.md")):
            text = f.read_text(encoding="utf-8", errors="ignore")
            if "status: done" not in text.lower():
                open_runs.append(f.stem)

    lines = [
        f"This repo uses the devteam plugin (base branch: {cfg.get('base_branch', '?')}, "
        f"autonomy: {cfg.get('autonomy', 'gated')}).",
        "Team commands: /devteam:ship, /devteam:review <PR>, /devteam:fix <PR>, /devteam:status.",
    ]
    if open_runs:
        lines.append("Unfinished runs: " + ", ".join(open_runs[:10]) + " (resume with /devteam:ship --resume <slug>).")
    # Plain stdout from SessionStart is added to Claude's context.
    print("\n".join(lines))


if __name__ == "__main__":
    main()
