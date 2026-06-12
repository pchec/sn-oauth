"""sn-oauth: OAuth authorization-code (PKCE) login and OS-keychain token
storage for ServiceNow instances.

Generic. No instance, client id, or organisation is hard-coded; all of that is
configuration (see config.py). The only ServiceNow-specific constants are the
platform's standard OAuth endpoints, which are identical on every instance.
"""

__version__ = "0.1.0"
