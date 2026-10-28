---
description: Set up devteam in this repo — check gh auth, create labels and config, install strict linting, CI workflows and git hooks.
argument-hint: "[--auto] [--base main]"
model: claude-opus-5-5
---

You are the devteam **orchestrator** (Opus 5.5) doing one-time setup for this repository. Arguments: `$ARGUMENTS`

Load the `devteam:github-pr-protocol` skill first.

1. **Checks.** Run and report any failure clearly, then stop on hard failures:
   - `git rev-parse --show-toplevel` (must be a git repo with an `origin` on GitHub)
   - `gh auth status` — the token needs `repo` and `workflow` scopes (`gh auth refresh -s repo,workflow` if not)
   - `gh repo view --json nameWithOwner,defaultBranchRef`
   - `python3 --version` (the safety hooks need it), `node --version` if it's a JS project
2. **Local state.** Create `.devteam/{tmp,runs,worktrees}` and add these three folders (`.devteam/tmp/`, `.devteam/runs/`, `.devteam/worktrees/`) to `.git/info/exclude`. `.devteam/config.json` itself **is** committed, because CI and every teammate read it.
3. **Config.** Detect the stack from manifest files and write `.devteam/config.json`, starting from `${CLAUDE_PLUGIN_ROOT}/templates/config.json`. Fill in `base_branch` (default branch unless `--base`), `test_cmd`, `dev_server_cmd`, `app_url`, and `autonomy` (`"auto"` if `--auto` was passed, else `"gated"`). Show the user the config and ask them to confirm the commands.
4. **Labels.** Create every label from the protocol §2 with `gh label create "<name>" --color <hex> --description "<…>" --force`.
5. **Linting.** Delegate to `devteam:lint-guardian` in Mode A (setup), passing `MAIN`, `REPO`, `BASE` and the detected stack. It opens a `chore/devteam-lint-setup` PR and fills the lint commands into the config.
6. **Workflows.** On the same branch as the lint PR (ask lint-guardian's report for the worktree path), commit `.devteam/config.json`, copy `${CLAUDE_PLUGIN_ROOT}/templates/dependabot.yml` to `.github/dependabot.yml` (drop ecosystems the repo doesn't use), and copy the GitHub Actions workflows from `${CLAUDE_PLUGIN_ROOT}/templates/workflows/` into `.github/workflows/`:
   - `devteam-ci.yml` — lint, format, typecheck, tests, build, Playwright e2e
   - `devteam-pr-hygiene.yml` — Conventional Commit PR titles, linked issue, size label
   - `devteam-security.yml` — dependency review, CodeQL, gitleaks
   - `devteam-labels.yml` — moves `devteam:` labels on PR events (merged → closes the flow)
   - `devteam-claude.yml` — **optional**, only if the user wants the team to react to `@devteam` comments on GitHub; needs the `ANTHROPIC_API_KEY` repo secret.
   Adapt the CI job's install/lint/test commands to the config, run `actionlint` on them if available, commit as `ci: add devteam workflows` with trailer `Devteam-Role: orchestrator`, and push.
7. **Git hooks.** Install the repo's pre-commit tooling that lint-guardian chose (`pre-commit install` or `npx lefthook install`), plus `${CLAUDE_PLUGIN_ROOT}/templates/githooks/commit-msg` into `.git/hooks/commit-msg` (enforces Conventional Commits) and `chmod +x` it. Don't overwrite an existing hook; chain it instead.
8. **Branch protection (recommend, don't apply).** Tell the user the one command to require the CI checks and one approval on `BASE`, and let them run it:
   `gh api -X PUT repos/<REPO>/branches/<BASE>/protection --input .devteam/tmp/protection.json` (write that JSON for them).
9. **Reviewer identity.** Run `"${CLAUDE_PLUGIN_ROOT}/scripts/gh-as-reviewer" --check`. If it exits 3, tell the user that reviews will be comments only until they run `/devteam:reviewer-setup`, and offer to start it now.
10. Finish with: the setup PR link, what still needs the user (approve config, merge the setup PR, optional secret and reviewer token), and how to start: `/devteam:ship <idea or #issue>`.
