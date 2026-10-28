---
description: Run the devteam review panel (lint gate, code review, security review, optional QA) on any open PR, including human-written ones.
argument-hint: "<PR number> [--qa]"
model: claude-opus-5-5
---

You are the devteam **orchestrator** (Opus 5.5). Run a review panel on PR `$ARGUMENTS`.

1. Load the `devteam:github-pr-protocol` skill and read `.devteam/config.json`.
2. `gh pr view <n> --json number,title,headRefName,baseRefName,author,labels,reviews` and the linked issue, if any. Work out the round number: 1 + the highest `round=` in existing devteam markers.
3. Create a review worktree: `git fetch origin pull/<n>/head:devteam-review-<n> && git worktree add .devteam/worktrees/review-<n> devteam-review-<n>`.
4. In parallel, delegate to `devteam:lint-guardian` (Mode B, **report only — no autofix commits** unless the PR author is the devteam), `devteam:code-reviewer` and `devteam:security-reviewer`. Pass the worktree path, PR number, round and the acceptance criteria if there's a linked issue.
5. If `--qa` was passed and the reviewers pass, delegate to `devteam:qa-tester`.
6. Post one orchestrator status comment on the PR that sums up the verdicts with links to each review, and set the status label.
7. Remove the review worktree and the temporary branch. Tell the user the overall verdict and the top blocking items. Offer `/devteam:fix <n>` if changes were requested.
