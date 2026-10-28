---
description: Show the devteam board — open devteam issues and PRs, who owns the next step, verdicts, and what's waiting on you.
model: claude-sonnet-5-5
allowed-tools: Bash(gh issue list:*), Bash(gh pr list:*), Bash(gh pr view:*), Bash(gh pr checks:*), Read
---

Show the devteam status for this repository. Read-only; change nothing.

1. `gh pr list --state open --limit 100 --json number,title,labels,url,isDraft` and keep the PRs that have any `devteam:` label.
2. `gh issue list --state open --limit 200 --json number,title,labels,url` and keep the issues that have any `devteam:` label.
3. For each PR, read the latest devteam marker per role from `gh pr view <n> --json comments,reviews` and `gh pr checks <n>`.
4. Print a compact board: **Waiting on you** first (`devteam:ready-to-merge`, `devteam:needs-human`), then in review, in progress, backlog. One line per item: number, title, owner role, verdicts, CI, link.
5. List any `.devteam/runs/*.md` whose PRs are still open, with the `/devteam:ship --resume <slug>` command for each.
