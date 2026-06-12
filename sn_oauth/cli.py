"""Command-line interface for sn-oauth.

Commands
  login          interactive: print the authorize URL, read the pasted code,
                 exchange it, store the refresh token in the keychain
  authorize-url  print only the authorize URL (agent step 1); stores the
                 pending PKCE verifier in the keychain
  exchange CODE  exchange a pasted code (agent step 2); stores tokens
  token          print a valid access token (refresh silently if needed)
  status         show whether a token is stored for the configured instance
  logout         remove the stored tokens for the configured instance

Configuration (instance, client_id, redirect_uri) comes from sn-oauth.json,
SN_OAUTH_* environment variables, or the --instance / --client-id /
--redirect-uri flags. See config.py.
"""
import argparse
import sys
import time

from . import __version__, config, oauth, store


def _err(*parts):
    print(*parts, file=sys.stderr)


def _require(cfg, *keys):
    missing = [k for k in keys if not cfg.get(k)]
    if missing:
        _err("missing configuration: %s" % ", ".join(missing))
        _err("set it in sn-oauth.json, via SN_OAUTH_* env vars, or with flags "
             "(--instance, --client-id).")
        sys.exit(2)


def _build_authorize_url(cfg):
    verifier, challenge = oauth.new_pkce()
    state = oauth.new_state()
    store.save_pending(cfg["instance"], {
        "verifier": verifier,
        "state": state,
        "redirect_uri": cfg["redirect_uri"],
    })
    return oauth.authorize_url(
        cfg["instance"], cfg["client_id"], cfg["redirect_uri"],
        challenge, state, cfg.get("scope", ""),
    )


def cmd_authorize_url(cfg, args):
    _require(cfg, "instance", "client_id")
    print(_build_authorize_url(cfg))


def cmd_exchange(cfg, args):
    _require(cfg, "instance", "client_id")
    pending = store.load_pending(cfg["instance"])
    if not pending:
        _err("no pending authorization; run 'authorize-url' or 'login' first.")
        sys.exit(2)
    try:
        record = oauth.exchange_code(
            cfg["instance"], cfg["client_id"], pending["redirect_uri"],
            args.code.strip(), pending["verifier"],
        )
    except oauth.OAuthError as exc:
        _err("exchange failed: %s" % exc)
        _err("the code is single-use and short-lived; re-open the authorize "
             "URL for a fresh code, then exchange again.")
        sys.exit(1)
    store.save_tokens(cfg["instance"], record)
    store.clear_pending(cfg["instance"])
    _err("logged in. refresh token stored in the OS keychain for %s."
         % cfg["instance"])


def cmd_login(cfg, args):
    _require(cfg, "instance", "client_id")
    url = _build_authorize_url(cfg)
    _err("1) Open this URL and sign in to ServiceNow:\n")
    print(url)
    _err("\n2) Approve access, then copy the code shown on the page.")
    try:
        code = input("3) Paste the code here: ").strip()
    except (EOFError, KeyboardInterrupt):
        _err("\nno code entered; aborted.")
        sys.exit(2)
    if not code:
        _err("empty code; aborted.")
        sys.exit(2)
    args.code = code
    cmd_exchange(cfg, args)


def cmd_token(cfg, args):
    _require(cfg, "instance", "client_id")
    record = store.load_tokens(cfg["instance"])
    if not record:
        _err("not logged in for %s; run 'sn-oauth login'." % cfg["instance"])
        sys.exit(3)
    if record.get("access_token") and record.get("expires_at", 0) > time.time() + 60:
        print(record["access_token"])
        return
    if not record.get("refresh_token"):
        _err("access token expired and no refresh token; run 'sn-oauth login'.")
        sys.exit(3)
    try:
        record = oauth.refresh(cfg["instance"], cfg["client_id"],
                               record["refresh_token"])
    except oauth.OAuthError as exc:
        _err("refresh failed: %s" % exc)
        _err("run 'sn-oauth login' to re-authorize.")
        sys.exit(3)
    store.save_tokens(cfg["instance"], record)
    print(record["access_token"])


def cmd_status(cfg, args):
    instance = cfg.get("instance") or "(unset)"
    print("instance: %s" % instance)
    if not cfg.get("instance"):
        print("status: no instance configured")
        return
    record = store.load_tokens(cfg["instance"])
    if not record:
        print("status: not logged in")
        return
    valid = record.get("expires_at", 0) > time.time()
    print("status: logged in")
    print("access_token_valid: %s" % ("yes" if valid else "no (will refresh)"))
    print("has_refresh_token: %s" % ("yes" if record.get("refresh_token") else "no"))


def cmd_logout(cfg, args):
    _require(cfg, "instance")
    store.clear_tokens(cfg["instance"])
    store.clear_pending(cfg["instance"])
    _err("logged out; keychain entries for %s removed." % cfg["instance"])


COMMANDS = {
    "login": cmd_login,
    "authorize-url": cmd_authorize_url,
    "exchange": cmd_exchange,
    "token": cmd_token,
    "status": cmd_status,
    "logout": cmd_logout,
}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="sn-oauth",
        description="OAuth login and OS-keychain token storage for a "
                    "ServiceNow instance.",
    )
    parser.add_argument("--version", action="version",
                        version="sn-oauth %s" % __version__)
    parser.add_argument("--instance", help="e.g. acme.service-now.com")
    parser.add_argument("--client-id", dest="client_id")
    parser.add_argument("--redirect-uri", dest="redirect_uri")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        sp = sub.add_parser(name)
        if name == "exchange":
            sp.add_argument("code", help="the authorization code from the "
                                         "landing page")
    args = parser.parse_args(argv)

    cfg = config.load_config({
        "instance": args.instance,
        "client_id": args.client_id,
        "redirect_uri": args.redirect_uri,
    })
    COMMANDS[args.command](cfg, args)
