"""Token storage backed by the OS keychain (via the `keyring` library).

Windows  -> Credential Manager
macOS    -> Keychain
Linux    -> Secret Service (GNOME Keyring / KWallet)

Two items are kept, scoped per instance so several instances can coexist:
  - "tokens"  : the JSON token record (access + refresh + expiry)
  - "pending" : the short-lived PKCE verifier between authorize and exchange

Nothing is written to disk in plaintext. The long-lived refresh token lives
only in the keychain.
"""
import json

import keyring
from keyring.errors import PasswordDeleteError

SERVICE_PREFIX = "sn-oauth"


def _service(instance):
    return "%s:%s" % (SERVICE_PREFIX, instance)


def _get(instance, name):
    raw = keyring.get_password(_service(instance), name)
    return json.loads(raw) if raw else None


def _set(instance, name, data):
    keyring.set_password(_service(instance), name, json.dumps(data))


def _del(instance, name):
    try:
        keyring.delete_password(_service(instance), name)
    except PasswordDeleteError:
        pass


def save_tokens(instance, record):
    _set(instance, "tokens", record)


def load_tokens(instance):
    return _get(instance, "tokens")


def clear_tokens(instance):
    _del(instance, "tokens")


def save_pending(instance, record):
    _set(instance, "pending", record)


def load_pending(instance):
    return _get(instance, "pending")


def clear_pending(instance):
    _del(instance, "pending")
