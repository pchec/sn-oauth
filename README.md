# sn-oauth

OAuth authorization-code (PKCE) login and OS-keychain token storage for
ServiceNow instances. Lets a local tool or AI agent obtain and reuse an access
token for a ServiceNow instance without a stored password, a localhost server,
or any extra service account. The refresh token lives only in the operating
system keychain (Windows Credential Manager / macOS Keychain).

> Status: early. The full self-documenting guide (including the agent
> walkthrough and the ServiceNow-side OAuth client setup) is in progress.

## Quick start

```
# macOS / Linux
./sn-oauth login

# Windows
.\sn-oauth.cmd login
```

First run bootstraps a local Python environment (offering to install Python if
it is missing), then prompts you to sign in and paste the code shown by
ServiceNow. After that:

```
sn-oauth token     # prints a valid access token (refreshes silently)
sn-oauth status    # shows whether you are logged in
sn-oauth logout    # removes the stored tokens
```

## Configuration

Copy `sn-oauth.example.json` to `sn-oauth.json` and fill in your instance and
the client id of an OAuth client registered in that instance:

```json
{
  "instance": "your-instance.service-now.com",
  "client_id": "your_oauth_client_id",
  "redirect_uri": "/sdk-oauth.do"
}
```

Configuration can also come from `SN_OAUTH_INSTANCE` / `SN_OAUTH_CLIENT_ID` /
`SN_OAUTH_REDIRECT_URI` environment variables, or `--instance` / `--client-id`
flags.

## For agents (non-interactive)

```
sn-oauth authorize-url      # prints the URL to show the user
sn-oauth exchange <code>    # exchanges the pasted code, stores the refresh token
sn-oauth token              # prints a valid access token on demand
```

## License

MIT. See [LICENSE](LICENSE).
