"""SubagentStop hook: append one line per finished devteam agent to .devteam/runs/activity.log."""
from __future__ import annotations

from datetime import datetime, timezone

from _common import find_devteam_root, read_input


def main() -> None:
    data = read_input()
    agent = str(data.get("agent_type") or data.get("subagent_type") or "")
    if agent and not agent.startswith("devteam:"):
        return
    root = find_devteam_root(data.get("cwd"))
    if root is None:
        return
    log = root / ".devteam" / "runs" / "activity.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with log.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp}\t{agent or 'subagent'}\t{data.get('agent_id', '')}\tstopped\n")


if __name__ == "__main__":
    main()
