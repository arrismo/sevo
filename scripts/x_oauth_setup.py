#!/usr/bin/env python3
"""Local OAuth 2.0 PKCE setup helper for Sevo's read-only X integration."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
from urllib.parse import parse_qs, urlencode, urlparse
import webbrowser

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
PENDING_PATH = PROJECT_ROOT / ".sevo" / "x_oauth_pending.json"
AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"
ME_URL = "https://api.x.com/2/users/me"
SCOPES = "tweet.read users.read offline.access"
DEFAULT_REDIRECT_URI = "http://127.0.0.1:3000/x/callback"


def _load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _write_env_updates(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen: set[str] = set()
    output: list[str] = []
    for line in lines:
        if "=" not in line or line.lstrip().startswith("#"):
            output.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in updates:
            output.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            output.append(line)
    if output and output[-1].strip():
        output.append("")
    for key, value in updates.items():
        if key not in seen:
            output.append(f"{key}={value}")
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return verifier, challenge


def _callback_code(callback_url: str, expected_state: str) -> str:
    parsed = urlparse(callback_url.strip())
    query = parse_qs(parsed.query)
    if query.get("error"):
        raise RuntimeError(f"X returned an OAuth error: {query['error'][0]}")
    state = query.get("state", [""])[0]
    if state != expected_state:
        raise RuntimeError("OAuth state did not match; refusing to exchange the code.")
    code = query.get("code", [""])[0]
    if not code:
        raise RuntimeError("No OAuth code found in the callback URL.")
    return code


def _start() -> int:
    env = {**_load_env(ENV_PATH), **os.environ}
    client_id = env.get("X_CLIENT_ID", "").strip()
    redirect_uri = env.get("X_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip()

    if not client_id:
        print("Missing X_CLIENT_ID. Add it to .env first.", file=sys.stderr)
        return 1

    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(24)
    auth_url = f"{AUTHORIZE_URL}?" + urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": SCOPES,
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
    )
    PENDING_PATH.parent.mkdir(parents=True, exist_ok=True)
    PENDING_PATH.write_text(
        json.dumps({"verifier": verifier, "state": state, "redirect_uri": redirect_uri}),
        encoding="utf-8",
    )

    print("Opening X authorization page for read-only access...")
    print("If your browser does not open, visit this URL:\n")
    print(auth_url)
    print("\nAfter approving, copy the full redirected callback URL from the browser address bar.")
    print("Then run:")
    print("  python scripts/x_oauth_setup.py --finish 'PASTE_CALLBACK_URL_HERE'")
    webbrowser.open(auth_url)
    return 0


def _finish(callback_url: str) -> int:
    env = {**_load_env(ENV_PATH), **os.environ}
    client_id = env.get("X_CLIENT_ID", "").strip()
    client_secret = env.get("X_CLIENT_SECRET", "").strip()
    client_type = env.get("X_CLIENT_TYPE", "public").strip().casefold()
    if not PENDING_PATH.exists():
        print("No pending OAuth flow found. Run python scripts/x_oauth_setup.py --start first.", file=sys.stderr)
        return 1
    pending = json.loads(PENDING_PATH.read_text(encoding="utf-8"))
    verifier = pending["verifier"]
    state = pending["state"]
    redirect_uri = pending["redirect_uri"]
    code = _callback_code(callback_url, state)

    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }
    auth: tuple[str, str] | None = None
    if client_type == "confidential" and client_secret:
        auth = (client_id, client_secret)
    else:
        token_data["client_id"] = client_id

    with httpx.Client(timeout=20.0) as client:
        token_response = client.post(
            TOKEN_URL,
            data=token_data,
            auth=auth,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if token_response.is_error:
            print("X token exchange failed:", file=sys.stderr)
            print(token_response.text, file=sys.stderr)
            token_response.raise_for_status()
        token_payload = token_response.json()
        access_token = token_payload["access_token"]
        refresh_token = token_payload.get("refresh_token", "")

        me_response = client.get(ME_URL, headers={"Authorization": f"Bearer {access_token}"})
        me_response.raise_for_status()
        user_id = me_response.json()["data"]["id"]

    updates = {
        "SEVO_X_SOURCE": "api",
        "X_BEARER_TOKEN": access_token,
        "X_USER_ID": user_id,
        "X_REDIRECT_URI": redirect_uri,
    }
    if refresh_token:
        updates["X_REFRESH_TOKEN"] = refresh_token
    _write_env_updates(ENV_PATH, updates)

    print("\nX OAuth setup complete.")
    print(f"Saved read-only user token and X_USER_ID={user_id} to .env.")
    print("Restart Sevo with: docker compose up --build")
    PENDING_PATH.unlink(missing_ok=True)
    return 0


def main() -> int:
    if len(sys.argv) >= 2 and sys.argv[1] == "--start":
        return _start()
    if len(sys.argv) >= 3 and sys.argv[1] == "--finish":
        return _finish(sys.argv[2])
    result = _start()
    if result != 0:
        return result
    callback_url = input("Callback URL: ").strip()
    return _finish(callback_url)


if __name__ == "__main__":
    raise SystemExit(main())
