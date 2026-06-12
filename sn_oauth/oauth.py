"""ServiceNow OAuth 2.0 authorization-code flow with PKCE.

Only the two standard ServiceNow OAuth endpoints are referenced:
  /oauth_auth.do    (authorization)
  /oauth_token.do   (token exchange / refresh)
These are identical on every ServiceNow instance, so nothing here is
instance- or organisation-specific.
"""
import base64
import hashlib
import json
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request


class OAuthError(Exception):
    pass


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def new_pkce():
    """Return (verifier, challenge) for a PKCE S256 exchange."""
    verifier = _b64url(secrets.token_bytes(48))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def new_state():
    return _b64url(secrets.token_bytes(12))


def authorize_url(instance, client_id, redirect_uri, challenge, state, scope=""):
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if scope:
        params["scope"] = scope
    return "https://%s/oauth_auth.do?%s" % (instance, urllib.parse.urlencode(params))


def _post_token(instance, fields):
    body = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(
        "https://%s/oauth_token.do" % instance,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise OAuthError("token endpoint returned HTTP %s: %s" % (exc.code, detail))
    except urllib.error.URLError as exc:
        raise OAuthError("could not reach %s: %s" % (instance, exc.reason))


def _to_record(token):
    if not token.get("access_token"):
        raise OAuthError("response had no access_token: %r" % token)
    return {
        "access_token": token["access_token"],
        "refresh_token": token.get("refresh_token"),
        "expires_at": int(time.time()) + int(token.get("expires_in", 1800)),
    }


def exchange_code(instance, client_id, redirect_uri, code, verifier):
    return _to_record(_post_token(instance, {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": verifier,
    }))


def refresh(instance, client_id, refresh_token):
    return _to_record(_post_token(instance, {
        "grant_type": "refresh_token",
        "client_id": client_id,
        "refresh_token": refresh_token,
    }))
