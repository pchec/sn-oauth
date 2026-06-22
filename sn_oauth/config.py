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


def canonical_instance(instance):
    """Normalise an instance string to its canonical FQDN form.

    A ServiceNow instance is addressable by a short name (``danonesandbox``)
    or its full host (``danonesandbox.service-now.com``). The keychain store
    keys tokens by the exact instance string, so the two forms used to land in
    two *different* keychain entries: a token saved under the FQDN was invisible
    to a probe done with the short name, which then read as "not logged in"
    (the false-lapse footgun). Canonicalising to one form here, before the
    instance is ever used as a store key or in a URL, closes that gap whichever
    form the caller passed.

    Rule: if the value has no dot, append ``.service-now.com``. A value that
    already contains a dot (a full host, or a custom domain) is left as-is, only
    lower-cased and stripped, since hostnames are case-insensitive.
    """
    if not instance:
        return instance
    inst = instance.strip().lower()
    # Tolerate a pasted URL: keep only the host.
    if "://" in inst:
        inst = inst.split("://", 1)[1]
    inst = inst.split("/", 1)[0]
    if "." not in inst:
        inst = inst + ".service-now.com"
    return inst

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

    # Canonicalise the instance to its FQDN so the short form and the full host
    # resolve to one keychain entry. Done last, after all sources have been
    # merged, so it applies regardless of where the instance came from.
    if cfg.get("instance"):
        cfg["instance"] = canonical_instance(cfg["instance"])

    return cfg
