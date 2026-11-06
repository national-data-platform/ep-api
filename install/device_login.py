#!/usr/bin/env python3
"""
Sign in to the identity provider with the OAuth 2.0 device flow (RFC 8628).

Used by install.sh to get the installing user's NDP access token without
asking them to copy it by hand (issue #397): it asks the realm for a device
code, tells the user where to open it and which code to enter, and waits until
they have signed in there.

Usage: device_login.py <issuer> <client-id> [<timeout-seconds>]

<issuer> is the realm URL, e.g. https://idp.nationaldataplatform.org/realms/NDP.
The client must be a public client with the device flow enabled.

The access token is the only thing written to stdout; the instructions go to
stderr, so the caller can capture the token without showing it. Exit codes:
0 signed in, 1 the user did not sign in (denied, expired or timed out),
2 the identity provider could not be used (unreachable, unknown client, device
flow not enabled).
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
REQUEST_TIMEOUT = 20


class LoginError(Exception):
    """The identity provider could not be used for the device flow."""


def _post(url, fields):
    """POST a form; return (status, decoded JSON body or {})."""
    data = urllib.parse.urlencode(fields).encode()
    request = urllib.request.Request(
        url, data=data, headers={"Accept": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            status, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        status, raw = exc.code, exc.read()
    except (urllib.error.URLError, OSError) as exc:
        raise LoginError(f"could not reach {url}: {exc}") from exc
    try:
        body = json.loads(raw or b"{}")
    except ValueError:
        body = {}
    return status, body if isinstance(body, dict) else {}


def start(issuer, client_id):
    """Ask the realm for a device code."""
    url = f"{issuer.rstrip('/')}/protocol/openid-connect/auth/device"
    status, body = _post(url, {"client_id": client_id, "scope": "openid"})
    if status != 200 or not body.get("device_code"):
        reason = body.get("error_description") or body.get("error") or f"HTTP {status}"
        raise LoginError(f"the identity provider refused the device flow: {reason}")
    return body


def wait_for_token(
    issuer, client_id, device, timeout, sleep=time.sleep, now=time.monotonic
):
    """Poll the token endpoint until the user signs in; None if they do not."""
    url = f"{issuer.rstrip('/')}/protocol/openid-connect/token"
    interval = int(device.get("interval") or 5)
    deadline = now() + min(timeout, int(device.get("expires_in") or timeout))
    while now() < deadline:
        sleep(interval)
        status, body = _post(
            url,
            {
                "grant_type": DEVICE_GRANT,
                "client_id": client_id,
                "device_code": device["device_code"],
            },
        )
        if status == 200 and body.get("access_token"):
            return body["access_token"]
        error = body.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        if error in ("access_denied", "expired_token"):
            return None
        reason = body.get("error_description") or error or f"HTTP {status}"
        raise LoginError(f"the identity provider refused the sign-in: {reason}")
    return None


def main(argv):
    if len(argv) not in (3, 4):
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    issuer, client_id = argv[1], argv[2]
    timeout = int(argv[3]) if len(argv) == 4 else 600
    try:
        device = start(issuer, client_id)
        link = device.get("verification_uri_complete") or device.get("verification_uri")
        print("", file=sys.stderr)
        print("  Open this link and sign in with your NDP account:", file=sys.stderr)
        print(f"    {link}", file=sys.stderr)
        print(f"  Code: {device.get('user_code', '')}", file=sys.stderr)
        print("  Waiting for you to sign in...", file=sys.stderr)
        token = wait_for_token(issuer, client_id, device, timeout)
    except LoginError as exc:
        print(f"  {exc}", file=sys.stderr)
        return 2
    if not token:
        print("  The sign-in was not completed.", file=sys.stderr)
        return 1
    print(token)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
