# DevTeam — an AI web-app team that works on GitHub

DevTeam is a Claude Code plugin that runs a whole software team through your GitHub repository. A **Claude Opus 5.5 orchestrator** leads eleven roles, ten of them **Claude Sonnet 5.5** specialists. They open issues, write tests, push commits, open pull requests, leave inline review comments, reply to and resolve each other's threads, and hand work to each other in the PR timeline, so you can follow everything on GitHub like a real team. A human always does the final merge.

## The team

| Role | Model | What it does on GitHub |
|---|---|---|
| **orchestrator** | Opus 5.5 | Plans the run, delegates, reads verdicts, settles disputes, posts status comments |
| **product-manager** | Sonnet 5.5 | Turns an idea into a spec with testable acceptance criteria (`AC-1`, `AC-2`…) |
| **issue-manager** | Sonnet 5.5 | Opens the epic and story issues, labels, links, `Blocked by`, follow-ups and bugs, closes issues |
| **architect** | Sonnet 5.5 | Posts the design on the epic, splits work into tasks and parallel-safe waves |
| **lint-guardian** | Sonnet 5.5 | Installs the strictest lint/format/type-check setup; gates every PR; commits autofixes |
| **test-engineer** | Sonnet 5.5 | Writes failing acceptance tests *before* the code exists |
| **developer** | Sonnet 5.5 | Implements until tests and lint pass, opens the PR, fixes review threads and resolves them |
| **code-reviewer** | Sonnet 5.5 | Adversarial review with inline comments and `suggestion` blocks |
| **security-reviewer** | Sonnet 5.5 | OWASP-focused review of every new input path |
| **qa-tester** | Sonnet 5.5 | Runs the app and checks each AC in a real browser with Playwright |
| **release-manager** | Sonnet 5.5 | Final PR description, changelog, merge checklist, `ready-to-merge` label |

No agent both writes code and judges it: tests are fixed targets for the developer, and reviewers can't edit code.

## How a feature flows

```
idea ─► product-manager ─► issue-manager (epic + issues) ─► architect (design, waves)
     ─► [you approve the plan]                                          ← gate G1
     ─► per task, in parallel worktrees:
          test-engineer (failing tests) ─► developer (code, draft PR)
     ─► lint-guardian ∥ code-reviewer ∥ security-reviewer  (inline reviews)
          ↺ developer fixes, replies, resolves threads (max 3 rounds)
     ─► qa-tester (browser) ─► release-manager ─► issue-manager (follow-ups)
     ─► [you merge]                                                     ← gate G2
```

Every comment is signed (`🤖 devteam · code-reviewer`) and carries a hidden machine-readable verdict, and every commit has a `Devteam-Role:` trailer.

## Requirements

- Claude Code (CLI, desktop or IDE extension)
- `git`, `python3` (for the safety hooks) and the GitHub CLI `gh`, logged in with `repo` and `workflow` scopes: `gh auth login` then `gh auth refresh -s repo,workflow`
- A repository on GitHub. Node and/or Python depending on your app.

## Install

Put this folder in a GitHub repo (e.g. `your-user/devteam`), then in Claude Code:

```
/plugin marketplace add your-user/devteam
/plugin install devteam@devteam
```

Or, to try it from a local folder: `/plugin marketplace add /path/to/devteam`.

## Use

| Command | What it does |
|---|---|
| `/devteam:setup` | One-time per repo: checks, labels, `.devteam/config.json`, strict linting, CI workflows, git hooks. Opens a setup PR. |
| `/devteam:reviewer-setup` | One-time per machine: creates the reviewer bot so reviews are real Approve / Request changes. |
| `/devteam:ship <idea>` or `/devteam:ship #42` | The full pipeline. `--resume <slug>` continues an interrupted run. |
| `/devteam:review <PR>` | Runs the review panel on any PR, including ones you wrote. Add `--qa` for a browser test. |
| `/devteam:fix <PR>` | The developer works through every open thread (yours first), then reviewers re-check. |
| `/devteam:status` | The board: what's waiting on you, in review, in progress, backlog. |

For headless or scripted runs: `claude --agent devteam:orchestrator "Ship issue #42"`.

## Linting ("the best linting")

`lint-guardian` detects your stack and installs a strict baseline:

- **TypeScript/JS:** ESLint flat config with `typescript-eslint` `strictTypeChecked` + `stylisticTypeChecked`, React/Hooks/`jsx-a11y`, Next or Vue plugins, `unicorn`, `sonarjs`, `security`, `regexp`, `import-x`, test and Playwright plugins; strict `tsconfig` (`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`…); Prettier; stylelint; knip.
- **Python:** ruff with `select = ["ALL"]` and `ruff format`, `mypy --strict` (or basedpyright strict).
- **Everywhere:** pre-commit hooks, markdownlint, actionlint, hadolint, gitleaks.

Linting is enforced at four levels: on every file Claude edits (Claude Code hook), on commit (git hook), on every PR (lint-guardian gate with inline comments), and in CI.

## Claude Code hooks (in `hooks/`)

| Hook | Event | Does |
|---|---|---|
| `git_guard.py` | PreToolUse · Bash | Blocks force-pushes, pushes to `main`/base/protected branches, `--no-verify`, `gh pr merge`, `gh repo delete` and `gh api` DELETEs |
| `lint_on_edit.py` | PostToolUse · Edit/Write | Lints the edited file with `lint_file_cmd` and makes Claude fix problems immediately |
| `session_start.py` | SessionStart | Tells Claude the repo uses devteam and lists unfinished runs |
| `activity_log.py` | SubagentStop | Logs each finished devteam agent to `.devteam/runs/activity.log` |

The hooks only act in repos that have `.devteam/config.json`; your other projects aren't affected. To switch the guard off for a moment, set `DEVTEAM_GUARD=off`.

## GitHub workflows (installed by setup into `.github/workflows/`)

| Workflow | Does |
|---|---|
| `devteam-ci.yml` | Lint, format check, typecheck, tests, build, Playwright e2e, using the same commands as the agents |
| `devteam-pr-hygiene.yml` | Conventional Commit PR titles, a linked issue, and `size:` labels |
| `devteam-security.yml` | Dependency review, gitleaks secret scan, CodeQL (`security-extended`), weekly scan |
| `devteam-labels.yml` | Keeps `devteam:` labels right when humans merge, re-draft, or request changes |
| `devteam-claude.yml` | *Optional.* Drive the team from GitHub by commenting `@devteam ship this` / `@devteam fix` |

Setup also adds `.github/dependabot.yml` and a `commit-msg` git hook for Conventional Commits.

## Real approvals: the reviewer bot

GitHub doesn't let the author of a PR approve or request changes on it, and the agents work as your account. So reviews come from a second identity:

1. Run `/devteam:reviewer-setup`. It gives you a pre-filled link that creates a private GitHub App (e.g. `devteam-reviewer-cfir`) with only pull-request, issue and read-only content permissions.
2. Click **Create**, **Generate a private key** and **Install** on your repo. Claude stores the key at `~/.config/devteam/reviewer.pem` (never in the repo).
3. From then on, the reviewers block a PR with a real **Request changes** from `devteam-reviewer-…[bot]`, and the orchestrator gives the real **Approve** once lint, code and security all pass and CI is green.

This works for PRs the agents open **and for PRs you open yourself**: run `/devteam:review <PR>` on your own PR and the bot approves it or requests changes. Add branch protection that requires one approval, and the bot's ✅ is what unlocks the merge button. You still click merge.

No App allowed in your org? Use a second "machine user" GitHub account instead and set `DEVTEAM_REVIEWER_TOKEN` to its token.

## Configuration — `.devteam/config.json`

Committed to the repo so CI and every agent share it. Key fields:

- `autonomy`: `"gated"` (default, you approve the plan) or `"auto"`
- `max_review_rounds` (3), `max_parallel_tasks` (3)
- `install_cmd`, `dev_server_cmd`, `app_url`, `test_cmd`, `e2e_cmd`, `build_cmd`
- `lint_cmd`, `lint_fix_cmd`, `format_check_cmd`, `typecheck_cmd`, `lint_file_cmd` (with `{file}`), `lint_extensions`, `lint_on_edit`
- `allow_agent_merge` (default `false`; even when `true`, merge also needs `DEVTEAM_ALLOW_MERGE=1`)

## Notes

- **Real approvals:** GitHub never lets a PR's author approve their own PR. DevTeam fixes this with two identities: your account writes the code, and a small GitHub App bot (`/devteam:reviewer-setup`, about 2 minutes) submits the reviews. See [Real approvals](#real-approvals-the-reviewer-bot).
- **Models:** the orchestrator and commands use `claude-opus-5-5`; specialists use `claude-sonnet-5-5`. Change the `model:` line in any `agents/*.md` file to swap. If your organization restricts models, Claude Code falls back automatically and tells you.
- **Cost:** a full `/devteam:ship` runs many agents. Start with small features, and use `/devteam:review` on its own to get a feel for it.
