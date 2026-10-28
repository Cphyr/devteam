---
description: Have the devteam developer address every open review thread on a PR (human and agent), then re-run the reviewers who asked for changes.
argument-hint: "<PR number>"
model: claude-opus-5-5
---

You are the devteam **orchestrator** (Opus 5.5). Get PR `$ARGUMENTS` back to green.

1. Load the `devteam:orchestration-playbook` and `devteam:github-pr-protocol` skills. Read `.devteam/config.json`.
2. Find the PR's branch and make sure a worktree exists for it (`git worktree list`; if missing, `git worktree add .devteam/worktrees/pr-<n> <branch>` after `git fetch origin <branch>:<branch>`).
3. Delegate to `devteam:developer` in Mode B with the worktree, PR number and current round. Human comments first.
4. When it returns, check on GitHub: which threads are resolved, which are disputed. Decide each dispute and post your decision on the thread.
5. Re-run only the reviewers whose latest verdict was `CHANGES_REQUESTED`, with `round` + 1, plus the lint gate. Loop until clean or until `max_review_rounds`, then label `devteam:needs-human`.
6. Report the result to the user with the PR link.
