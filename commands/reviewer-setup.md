---
description: Give the devteam reviewers their own GitHub identity (a GitHub App bot) so their reviews are real Approve / Request changes, even on PRs you opened.
argument-hint: "[app-name]"
model: claude-sonnet-5-5
---

Help the user set up the devteam **reviewer identity**. Arguments: `$ARGUMENTS` (optional app name; default `devteam-reviewer-<github-username>`).

Why: GitHub never lets a PR's author approve or request changes on their own PR. The agents push and open PRs as the user, so reviewers need a different identity. A GitHub App is the cleanest: its reviews appear as `<app-name>[bot]` and count as real approvals.

1. Check first: run `"${CLAUDE_PLUGIN_ROOT}/scripts/gh-as-reviewer" --check`. If it prints `ok`, tell the user it's already set up and stop.
2. Get the user's login: `gh api user -q .login`. Get the repo: `gh repo view --json nameWithOwner -q .nameWithOwner`.
3. Build this link (URL-encode the name) and give it to the user to open. GitHub pre-fills the form from these parameters:
   `https://github.com/settings/apps/new?name=<APP_NAME>&description=devteam%20AI%20code%20reviewer&url=https://github.com/<REPO>&public=false&webhook_active=false&pull_requests=write&issues=write&contents=read&metadata=read&checks=read`
   (For an organisation-owned repo use `https://github.com/organizations/<ORG>/settings/apps/new?…` instead.)
4. Walk them through the three clicks, one at a time, and wait for each:
   a. **Create GitHub App** at the bottom of the form. Note the **App ID** shown at the top of the next page.
   b. On that page, **Generate a private key**. A `.pem` file downloads.
   c. **Install App** (left sidebar) → choose their account → **Only select repositories** → pick this repo (and any others devteam will work on) → **Install**.
5. Ask for the App ID and the path of the downloaded `.pem` (usually `~/Downloads/<app-name>.<date>.private-key.pem`). Then:
   ```bash
   mkdir -p ~/.config/devteam && chmod 700 ~/.config/devteam
   mv "<pem path>" ~/.config/devteam/reviewer.pem && chmod 600 ~/.config/devteam/reviewer.pem
   printf '{"app_id": %s, "private_key_path": "~/.config/devteam/reviewer.pem"}\n' <APP_ID> > ~/.config/devteam/reviewer.json
   ```
   Never print the key's contents, and never commit it.
6. Verify: `"${CLAUDE_PLUGIN_ROOT}/scripts/gh-as-reviewer" --check`, then `"${CLAUDE_PLUGIN_ROOT}/scripts/gh-as-reviewer" api repos/<REPO> -q .full_name`.
7. Recommend branch protection on the base branch that requires **1 approving review** and the devteam CI checks, so a ✅ from the bot is what unlocks the merge button. Write the JSON to `.devteam/tmp/protection.json` and give the user the `gh api -X PUT repos/<REPO>/branches/<BASE>/protection --input …` command to run themselves.
8. Tell them what changes now: code-reviewer and security-reviewer post real **Approve** / **Request changes** reviews as `<app-name>[bot]`; everything else (commits, PRs, issues, comments) still runs as their account.

Alternative if they can't create apps (e.g. org policy): a second "machine user" GitHub account with write access to the repo; they set `export DEVTEAM_REVIEWER_TOKEN=<that account's fine-grained token>` in their shell profile. Same effect.
