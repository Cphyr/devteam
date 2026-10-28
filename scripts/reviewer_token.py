#!/usr/bin/env python3
"""Print a GitHub token for the devteam *reviewer* identity.

The reviewer must be a different GitHub identity from the PR author, otherwise
GitHub refuses APPROVE / REQUEST_CHANGES reviews. Two ways to provide one:

1. GitHub App (recommended): an app such as "devteam-reviewer" installed on the
   repo. Its reviews show as  devteam-reviewer[bot]  with real approvals.
   Configure with ~/.config/devteam/reviewer.json:
       {"app_id": 123456, "private_key_path": "~/.config/devteam/reviewer.pem"}
   or env vars DEVTEAM_REVIEWER_APP_ID and DEVTEAM_REVIEWER_KEY_FILE.

2. Machine user: a second GitHub account with write access.
   export DEVTEAM_REVIEWER_TOKEN=<its personal access token>

Exit codes: 0 = token printed, 3 = no reviewer identity configured,
1 = configured but failed (message on stderr).

Standard library only; JWT signing uses the `openssl` CLI.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "devteam" / "reviewer.json"
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "devteam"
API = os.environ.get("GITHUB_API_URL", "https://api.github.com")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def app_jwt(app_id: str, key_path: Path) -> str:
    now = int(time.time())
    header = b64url(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    payload = b64url(json.dumps({"iat": now - 60, "exp": now + 540, "iss": str(app_id)}).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(key_path)],
        input=signing_input, capture_output=True, check=True,
    ).stdout
    return f"{header}.{payload}.{b64url(sig)}"


def api(method: str, path: str, token: str, scheme: str = "Bearer") -> dict:
    req = urllib.request.Request(
        f"{API}{path}", method=method,
        headers={
            "Authorization": f"{scheme} {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "devteam-reviewer",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode() or "{}")


def current_repo() -> str:
    repo = os.environ.get("DEVTEAM_REPO") or os.environ.get("GITHUB_REPOSITORY")
    if repo:
        return repo
    url = subprocess.run(
        ["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=False
    ).stdout.strip()
    url = url.removesuffix(".git")
    for prefix in ("git@github.com:", "https://github.com/", "ssh://git@github.com/"):
        if url.startswith(prefix):
            return url[len(prefix):]
    raise SystemExit("devteam-reviewer: can't tell which GitHub repo this is (set DEVTEAM_REPO=owner/name).")


def load_app_config() -> tuple[str, Path] | None:
    app_id = os.environ.get("DEVTEAM_REVIEWER_APP_ID")
    key = os.environ.get("DEVTEAM_REVIEWER_KEY_FILE")
    if not (app_id and key) and CONFIG.is_file():
        cfg = json.loads(CONFIG.read_text())
        app_id = app_id or str(cfg.get("app_id", ""))
        key = key or cfg.get("private_key_path", "")
    if app_id and key:
        return app_id, Path(key).expanduser()
    return None


def main() -> int:
    pat = os.environ.get("DEVTEAM_REVIEWER_TOKEN")
    if pat:
        print(pat)
        return 0

    app = load_app_config()
    if app is None:
        print("devteam-reviewer: no reviewer identity configured. Run /devteam:reviewer-setup.", file=sys.stderr)
        return 3
    app_id, key_path = app
    if not key_path.is_file():
        print(f"devteam-reviewer: private key not found at {key_path}", file=sys.stderr)
        return 1

    repo = current_repo()
    cache = CACHE_DIR / f"reviewer-{app_id}-{repo.replace('/', '__')}.json"
    if cache.is_file():
        cached = json.loads(cache.read_text())
        if cached.get("expires", 0) > time.time() + 300:
            print(cached["token"])
            return 0

    try:
        jwt = app_jwt(app_id, key_path)
        inst = api("GET", f"/repos/{repo}/installation", jwt)
        tok = api("POST", f"/app/installations/{inst['id']}/access_tokens", jwt)
    except urllib.error.HTTPError as e:
        hint = " Is the app installed on this repo?" if e.code == 404 else ""
        print(f"devteam-reviewer: GitHub API error {e.code}.{hint}", file=sys.stderr)
        return 1
    except (subprocess.CalledProcessError, OSError, KeyError) as e:
        print(f"devteam-reviewer: could not create token ({e}).", file=sys.stderr)
        return 1

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(CACHE_DIR, 0o700)
    # GitHub installation tokens last one hour.
    cache.write_text(json.dumps({"token": tok["token"], "expires": time.time() + 3300}))
    os.chmod(cache, 0o600)
    print(tok["token"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
