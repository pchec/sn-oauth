"""Configuration resolution for sn-oauth.

Resolution order (later wins):
  1. defaults
  2. a JSON config file, first found of:
       ./sn-oauth.json
       <repo root>/sn-oauth.json
       ~/.config/sn-oauth/config.json
  3. environment variables  SN_OAUTH_INSTANCE / SN_OAUTH_CLIENT_ID /
     SN_OAUTH_REDIRECT_URI / SN_OAUTH_SCOPE
  4. explicit overrides (CLI flags)

Nothing here is organisation-specific. A deployer supplies `instance` and
`client_id` for their own ServiceNow instance and OAuth client.
"""
import json
import os

ENV_PREFIX = "SN_OAUTH_"
KEYS = ("instance", "client_id", "redirect_uri", "scope")

DEFAULTS = {
    # The ServiceNow SDK's copy-the-code page. Present on any instance with the
    # SDK installed. Override this if your OAuth client uses a different
    # redirect/landing page.
    "redirect_uri": "/sdk-oauth.do",
    "scope": "",
}


def _candidate_files():
    here = os.getcwd()
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    home = os.path.expanduser("~")
    return [
        os.path.join(here, "sn-oauth.json"),
        os.path.join(repo, "sn-oauth.json"),
        os.path.join(home, ".config", "sn-oauth", "config.json"),
    ]


def load_config(overrides=None):
    cfg = dict(DEFAULTS)

    for path in _candidate_files():
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                cfg.update({k: v for k, v in data.items() if v not in (None, "")})
            except (OSError, ValueError):
                pass
            break

    for key in KEYS:
        env = os.environ.get(ENV_PREFIX + key.upper())
        if env:
            cfg[key] = env

    if overrides:
        cfg.update({k: v for k, v in overrides.items() if v})

    # Strip surrounding whitespace, including non-breaking spaces, that a
    # rich-text editor or a copy-paste can leave around a value. A stray space
    # in client_id is invisible in the JSON but makes ServiceNow reject the
    # request with "unauthorized_client" even though the value looks correct.
    for key in KEYS:
        if isinstance(cfg.get(key), str):
            cfg[key] = cfg[key].strip()

    return cfg
