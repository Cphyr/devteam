---
name: github-pr-protocol
description: The shared GitHub working agreement for every devteam agent — branches, commits, issues, PR reviews, inline comments, replying to and resolving threads, labels and hand-offs. Use whenever a devteam agent touches git or GitHub.
---

# devteam GitHub protocol

Every devteam agent follows this protocol. The repository's issues and pull requests are the team's shared workspace: all hand-offs, findings and decisions are written there so a human can follow the whole conversation on GitHub.

## 0. Ground rules

- Use the `gh` CLI for everything GitHub. Never paste tokens into commands or comments.
- Read `.devteam/config.json` first (base branch, commands, autonomy). If it's missing, stop and ask the orchestrator to run `/devteam:setup`.
- Work only inside the worktree path the orchestrator gives you. Prefix every shell command with `cd <WORKTREE> &&` because `cd` does not persist between commands.
- Never push to the base branch. Never force-push. Never merge a PR (only a human merges, unless `allow_agent_merge` is true in config). A safety hook blocks these anyway.
- Write scratch files (review.json, reply.md, pr.md…) to `$MAIN/.devteam/tmp/`, never inside the worktree, so they can't be committed. Setup git-excludes `.devteam/tmp/`, `.devteam/runs/` and `.devteam/worktrees/`; only `.devteam/config.json` is committed.
- If something is ambiguous, don't guess on anything irreversible: write the question in the issue or PR, add the `devteam:needs-human` label and report back.

## 1. Identity and signatures

All agents share one GitHub account, so each comment and commit says which role wrote it.

Every comment, review body and issue body starts with a role header and ends with a hidden machine marker:

```
**🤖 devteam · <role>**

<content>

<!-- devteam role=<role> kind=<kind> verdict=<VERDICT> round=<n> -->
```

- `<role>`: planner, user-researcher, market-researcher, solutions-analyst, feasibility-analyst, business-analyst, rejection-panel, approval-panel, orchestrator, product-manager, issue-manager, architect, lint-guardian, test-engineer, developer, code-reviewer, security-reviewer, qa-tester, release-manager.
- `<kind>`: spec, plan, handoff, review, lint, qa, fix-summary, release, question, status.
- `<VERDICT>`: `PASS`, `CHANGES_REQUESTED`, `BLOCKED` or `NA`.

To address another role, write `@<role>` in bold text (e.g. **@developer**). These are not GitHub mentions; the orchestrator reads them.

Commits use Conventional Commits plus a role trailer:

```bash
git commit -m "feat(auth): add password reset endpoint" \
  -m "Refs #42" \
  --trailer "Devteam-Role: developer"
```

Types: feat, fix, test, refactor, style, docs, chore, ci, perf, build.

### Two identities: author and reviewer

GitHub never lets a PR's author approve or request changes on that PR. So the team uses two identities:

- **Author identity** — the user's normal `gh` login. Used for commits, pushes, PRs, issues, labels, hand-off comments and thread replies.
- **Reviewer identity** — a GitHub App bot (e.g. `devteam-reviewer[bot]`) or a machine user, set up once with `/devteam:reviewer-setup`. Used **only** by code-reviewer, security-reviewer and lint-guardian to submit reviews and, when needed, to dismiss their own earlier reviews.

Run any `gh` command as the reviewer with the wrapper:

```bash
REVIEWER="${CLAUDE_PLUGIN_ROOT}/scripts/gh-as-reviewer"
"$REVIEWER" --check            # exit 0 = reviewer identity available, 3 = not configured
"$REVIEWER" api "repos/$REPO/pulls/<n>/reviews" -X POST --input review.json
```

The bot's reviews are real: **APPROVE** turns the PR green for branch protection, **REQUEST_CHANGES** blocks it until a later approval from the bot. This works on PRs the developer agent opened **and on PRs the user opened themselves**.

If `--check` exits 3, fall back to the author identity with `"event": "COMMENT"` and keep the verdict in the marker, and mention once in the review body that `/devteam:reviewer-setup` enables real approvals.

## 2. Labels

`/devteam:setup` creates these labels. Keep exactly one `devteam:` status label on each PR.

| Label | Meaning |
|---|---|
| `devteam:backlog` | Issue is specified, not started |
| `devteam:in-progress` | Someone is working on it |
| `devteam:needs-review` | PR is waiting for the review panel |
| `devteam:changes-requested` | At least one reviewer asked for changes |
| `devteam:lint-failed` | Lint, format or type-check gate failed |
| `devteam:qa` | Review passed, waiting for QA |
| `devteam:ready-to-merge` | Every gate passed, a human can merge |
| `devteam:needs-human` | Blocked on a human decision |
| `role:<role>` | Which role owns the next step |
| `type:feature`, `type:bug`, `type:chore`, `type:follow-up`, `type:decision` | Issue type (`decision` = a planning-team GO / PIVOT / NO-GO) |
| `prio:p0` … `prio:p3` | Priority |

Swap a status label:

```bash
gh pr edit <n> --remove-label "devteam:needs-review" --add-label "devteam:changes-requested"
```

## 3. Issues (issue-manager owns these)

```bash
gh issue create --title "<imperative title>" --body-file issue.md \
  --label "type:feature,devteam:backlog,prio:p2" [--milestone "<name>"]
gh issue comment <n> --body-file comment.md
gh issue edit <n> --add-label "devteam:in-progress"
gh issue close <n> --comment "Closed by #<pr>" --reason completed
```

An issue body has: **Context**, **User story**, **Acceptance criteria** (numbered `AC-1`, `AC-2`… in Given/When/Then form), **Out of scope**, **Dependencies** (`Blocked by #n`) and **Definition of done**.

## 4. Branches and worktrees

One issue → one branch → one PR. The branch name is `<type>/<issue#>-<slug>`, e.g. `feat/42-password-reset`.

The orchestrator creates the worktree:

```bash
git fetch origin
git worktree add .devteam/worktrees/42 -b feat/42-password-reset origin/<base>
```

If a task depends on an unmerged PR, branch from that PR's branch instead and open the PR with `--base <that-branch>` (a stacked PR).

Keep the branch current by merging the base branch in, never by rebasing:

```bash
cd <WORKTREE> && git fetch origin && git merge origin/<base>
```

## 5. Pull requests

The developer opens a draft PR right after the first commit:

```bash
cd <WORKTREE> && git push -u origin HEAD
gh pr create --draft --base <base> --title "feat(auth): password reset (#42)" \
  --body-file pr.md --label "devteam:in-progress,role:developer"
```

A PR body has: **Summary**, **Closes #42**, **How it works**, **Acceptance criteria → tests** (a table mapping each AC to its test), **Screenshots / QA notes** and a **Checklist**.

Mark it ready when the developer is done: `gh pr ready <n>`.

## 6. Reviews with inline comments

Get the owner/repo and the head commit:

```bash
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
HEAD=$(gh pr view <n> --json headRefOid -q .headRefOid)
```

Post one review that bundles every inline comment. Write `review.json` with the Write tool, then send it:

```json
{
  "commit_id": "<HEAD>",
  "event": "COMMENT",
  "body": "**🤖 devteam · code-reviewer**\n\nSummary…\n\n<!-- devteam role=code-reviewer kind=review verdict=CHANGES_REQUESTED round=1 -->",
  "comments": [
    { "path": "src/auth/reset.ts", "line": 48, "side": "RIGHT",
      "body": "**[blocking]** Token compared with `===`. Use a constant-time compare.\n\n```suggestion\nif (!timingSafeEqual(a, b)) {\n```" }
  ]
}
```

Set `event` from your verdict, and submit as the reviewer identity:

| Verdict | `event` with reviewer identity | `event` without it |
|---|---|---|
| `PASS` | `COMMENT` | `COMMENT` |
| `CHANGES_REQUESTED` | `REQUEST_CHANGES` | `COMMENT` |
| `BLOCKED` | `COMMENT` | `COMMENT` |

```bash
REVIEWER="${CLAUDE_PLUGIN_ROOT}/scripts/gh-as-reviewer"
if "$REVIEWER" --check >/dev/null 2>&1; then
  "$REVIEWER" api "repos/$REPO/pulls/<n>/reviews" -X POST --input review.json
else
  gh api "repos/$REPO/pulls/<n>/reviews" -X POST --input review.json   # event must be COMMENT here
fi
```

All reviewer roles share one bot, and GitHub keeps only the bot's latest blocking state. So individual reviewers never approve: they block with `REQUEST_CHANGES` or report `PASS` as a comment. The **orchestrator** submits the single bot **APPROVE** when every reviewer's latest marker on the current round is `PASS` and CI is green (playbook step 10). That approval replaces the bot's earlier change request.

Rules for inline comments:

- `line` must be a line that appears in the PR diff, on the new side (`RIGHT`). For a multi-line range, add `start_line` and `start_side`.
- If the API rejects a comment (HTTP 422, line not in diff), move that finding into the review body with `path:line`.
- Start each comment with a severity tag: `**[blocking]**`, `**[should-fix]**` or `**[nit]**`. Only `[blocking]` findings can make the verdict `CHANGES_REQUESTED`.
- Use GitHub ```` ```suggestion ```` blocks for small, exact fixes.
- Things that are real but out of scope for this PR become `**[follow-up]**`. The issue-manager files them as new issues.

## 7. Replying to and resolving threads (developer)

List the review threads that are still open:

```bash
gh api graphql -F owner=<owner> -F repo=<repo> -F n=<n> -f query='
query($owner:String!,$repo:String!,$n:Int!){
  repository(owner:$owner,name:$repo){
    pullRequest(number:$n){
      reviewThreads(first:100){
        nodes{ id isResolved isOutdated
          comments(first:20){ nodes{ databaseId author{login} body path line } } }
      }
    }
  }
}'
```

For each open thread:

1. Fix it in code and commit (`fix(review): … ` + `Refs #<n>`).
2. Reply in the thread with what changed and the commit SHA. Write the reply to `reply.md` with the Write tool (role header and marker included), then:
   ```bash
   gh api "repos/$REPO/pulls/<n>/comments/<first_comment_databaseId>/replies" \
     -X POST -F body=@reply.md
   ```
3. Resolve the thread:
   ```bash
   gh api graphql -F id=<thread_id> -f query='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}'
   ```

Resolving uses the author identity (plain `gh`); the reviewer bot re-checks on the next round.

If you disagree with a finding, don't resolve it. Reply with your reasoning and tag **@orchestrator**; the orchestrator decides.

Human comments (any author whose comment doesn't carry a devteam marker) take priority over agent comments. Never resolve a human's thread yourself: reply and leave it open for them.

## 8. Hand-offs

When a role finishes a step, it posts a hand-off comment on the PR (or on the issue before a PR exists):

```
**🤖 devteam · test-engineer**

Wrote 6 failing acceptance tests (AC-1…AC-4) in `tests/e2e/reset.spec.ts`, commit 9f2c1aa.
Next: **@developer** — make them pass without editing these files.

<!-- devteam role=test-engineer kind=handoff verdict=NA round=0 -->
```

Then swap the `role:` label to the next owner.

## 9. Reading the team's state

```bash
gh pr view <n> --json number,title,state,isDraft,labels,reviews,comments,statusCheckRollup,headRefName
gh pr checks <n>
gh issue list --label "devteam:backlog" --json number,title,labels
```

The latest marker per role on the current round is that role's verdict.
