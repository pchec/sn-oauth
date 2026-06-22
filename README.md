# sn-oauth

OAuth authorization-code (PKCE) login and OS-keychain token storage for
ServiceNow instances.

It lets a local tool or an AI agent obtain and reuse an access token for a
ServiceNow instance with:

- **no stored password** (you sign in through ServiceNow's normal login, SSO included),
- **no localhost server** and no browser plugin,
- **no extra service account** (the token acts as the real user who signs in),
- the long-lived **refresh token kept only in the OS keychain** (Windows
  Credential Manager / macOS Keychain), never in a plaintext file.

It works on any ServiceNow instance. The instance host and OAuth client id are
configuration; nothing in this repository is specific to any one organisation.

---

## For AI agents: start here

If you are an agent that needs to call a ServiceNow instance, this is the whole
flow:

1. **Check prerequisites.** A registered OAuth client must exist in the target
   instance (see [1. Register an OAuth client](#1-register-an-oauth-client-in-servicenow)).
   If one does not, guide the user through creating it. You will need its
   `client_id` and its redirect URL.
2. **Configure** `sn-oauth.json` with the instance, `client_id`, and
   `redirect_uri` (see [2. Configure](#2-configure)).
3. **Install** by running the launcher once; it bootstraps Python if needed
   (see [3. Install](#3-install)).
4. **Log in (human in the loop).** Run `sn-oauth authorize-url`, show the
   printed URL to the user, and tell them to **copy and paste the whole URL**
   into their browser rather than clicking it (a terminal can truncate a long
   link, and a truncated URL fails with `unauthorized_client`). Ask them to sign
   in and paste back the code the page displays. Then run
   `sn-oauth exchange <code>`. The refresh token is now in the keychain.
5. **Use it.** Whenever you need to call ServiceNow, run `sn-oauth token` to get
   a valid access token (it refreshes silently) and send it as
   `Authorization: Bearer <token>`.

You only do steps 1 to 4 once per user per instance. After that, step 5 is all
you need.

---

## Prerequisites

- A ServiceNow instance and an OAuth client registered in it (next section).
- An OS keychain: Windows Credential Manager or macOS Keychain work out of the
  box. On Linux, `keyring` needs a Secret Service backend (GNOME Keyring or
  KWallet).
- Python 3.8 or newer. If it is missing, the installer offers to install it.

---

## 1. Register an OAuth client in ServiceNow

This is a one-time setup per instance, done by someone with admin rights. The
tool cannot do it for you, because OAuth requires a client that the instance
already trusts.

1. In ServiceNow, go to **All > System OAuth > Application Registry**.
2. Click **New**, then **Create an OAuth API endpoint for external clients**.
3. Set:
   - **Name**: anything, e.g. `Agent OAuth`.
   - **Public Client**: **checked**. This makes it a PKCE client that needs no
     client secret on the user's machine.
   - **Redirect URL**: the page ServiceNow sends the code to after sign-in.
     - If your instance has the **ServiceNow SDK** installed, you can reuse its
       copy-the-code page: `https://<instance>/sdk-oauth.do`.
     - Otherwise, point it at your own landing page that displays the `code`
       query parameter for the user to copy.
4. Save, then open the record and copy the **Client ID**.

**Critical:** the `redirect_uri` you put in `sn-oauth.json` must match this
**Redirect URL exactly**. A mismatch is the most common cause of a bare
`access_denied` at the exchange step.

The user who signs in can be any account that can log in to the instance,
including SSO accounts. The token acts as that user, with that user's roles.

---

## 2. Configure

Copy the example and fill in your values:

```
cp sn-oauth.example.json sn-oauth.json
```

```json
{
  "instance": "your-instance.service-now.com",
  "client_id": "your_oauth_client_id",
  "redirect_uri": "/sdk-oauth.do"
}
```

- `instance`: host only, no `https://`. The value is canonicalised to its FQDN
  before use, so a short name (`acme`), the full host (`acme.service-now.com`),
  and even a pasted URL all resolve to the **same** stored token. You cannot
  split your session across two spellings of the same instance.
- `client_id`: from the OAuth client you registered above.
- `redirect_uri`: must match the client's Redirect URL. A path like
  `/sdk-oauth.do` is resolved against the instance.

`sn-oauth.json` is gitignored so your instance details never get committed.
Configuration can also come from environment variables
(`SN_OAUTH_INSTANCE`, `SN_OAUTH_CLIENT_ID`, `SN_OAUTH_REDIRECT_URI`) or from
`--instance` / `--client-id` / `--redirect-uri` flags.

---

## 3. Install

```
# macOS / Linux
./sn-oauth login

# Windows
.\sn-oauth.cmd login
```

The first run bootstraps a local Python virtual environment and installs the
package. If Python 3.8+ is not found, the installer offers to install it
(Homebrew on macOS, winget on Windows) or points you to python.org. Approve the
prompt and it continues.

You can also run the bootstrap explicitly: `bootstrap/install.sh` (macOS/Linux)
or `bootstrap/install.ps1` (Windows).

---

## 4. Log in

**Interactive (a person at a terminal):**

```
sn-oauth login
```

It prints a URL. Copy the whole URL and paste it into your browser (do not click
it; a terminal can truncate a long link). Sign in, approve access, then paste
back the code the page shows. Done.

**Agent-driven (two steps):**

```
sn-oauth authorize-url      # prints the URL to show the user
sn-oauth exchange <code>    # exchanges the code the user pasted back
```

The code is **single-use and short-lived**. If it expires before you exchange
it, just **re-open the same authorize URL** to get a fresh one; the stored PKCE
verifier still matches, so you do not start over.

---

## Using the token

`sn-oauth token` prints a valid access token to stdout and nothing else (status
and errors go to stderr), so it is safe to capture in a command substitution:

```
TOKEN=$(sn-oauth token)
curl -H "Authorization: Bearer $TOKEN" \
  "https://your-instance.service-now.com/api/now/table/incident?sysparm_limit=1"
```

The token is valid for about 30 minutes. `sn-oauth token` reuses it until it is
close to expiry, then refreshes silently using the stored refresh token. You do
not manage that yourself.

---

## Commands

| Command | What it does |
|---|---|
| `sn-oauth login` | Interactive: print the URL, read the pasted code, store tokens. |
| `sn-oauth authorize-url` | Print only the authorize URL (agent step 1). |
| `sn-oauth exchange <code>` | Exchange a pasted code (agent step 2). |
| `sn-oauth token` | Print a valid access token, refreshing if needed. |
| `sn-oauth status` | Show whether a token is stored for the configured instance. |
| `sn-oauth logout` | Remove the stored tokens for the configured instance. |

---

## Troubleshooting

- **`unauthorized_client` (the client credentials are not valid or not trusted).**
  The `client_id` reaching ServiceNow is not one it recognises. The most common
  cause is opening a **truncated** authorize URL: clicking a long link in a
  terminal can clip it, so copy and paste the whole URL instead. Otherwise the
  `client_id` in your config is wrong or carries a stray character. Confirm the
  `client_id` in the URL `authorize-url` prints matches your registered client
  exactly.
- **`access_denied` at exchange.** Almost always the `redirect_uri` in your
  config does not match the OAuth client's Redirect URL, or the code was issued
  for a different `client_id`, or the code was already used or has expired.
  Check the redirect match first, then re-open the authorize URL for a fresh
  code.
- **`no pending authorization`.** Run `authorize-url` (or `login`) before
  `exchange`.
- **`not logged in`.** Run `sn-oauth login`.
- **Python install declined or unavailable.** Install Python 3.8+ from
  python.org and re-run the launcher.
- **Linux: no keychain backend.** Install and run a Secret Service provider
  (GNOME Keyring or KWallet); headless servers need extra setup for `keyring`.
- **Windows / Git Bash.** The `./sn-oauth` launcher handles the Windows venv
  layout (`.venv/Scripts/`) and disables MSYS path conversion automatically, so
  a path-style `redirect_uri` like `/sdk-oauth.do` is not rewritten into a
  Windows path. Run through the launcher (`./sn-oauth ...`); if you must call the
  venv Python directly, set `MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'`
  yourself first.

---

## How it works

- Authorization-code grant with PKCE (S256). The verifier never leaves your
  machine, so a public client needs no secret.
- After exchange, only `access_token`, `refresh_token`, and the expiry are kept,
  in the OS keychain, scoped per instance.
- `token` serves the cached access token until ~60s before expiry, then uses the
  refresh token to get a new one.
- The only ServiceNow URLs used are the standard `/oauth_auth.do` and
  `/oauth_token.do`, identical on every instance.

---

## License

MIT. See [LICENSE](LICENSE).
