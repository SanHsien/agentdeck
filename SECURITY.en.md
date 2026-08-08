# Security Policy

> 繁體中文版本：[SECURITY.md](SECURITY.md)

## Reporting a Vulnerability

If you find a security vulnerability in agentdeck, **please do not open a public Issue.** Report it privately instead:

📧 **sanhsien@pm.me**

Please include where you can:

- The affected version (or commit)
- Steps to reproduce, or a proof of concept
- Your assessment of the impact

This is a single-maintainer project; I'll do my best to respond and address reports within a reasonable timeframe, and will credit you in the release notes once a fix ships (unless you prefer to stay anonymous).

## Supported Versions

agentdeck ships on a rolling basis; security fixes target the **latest release only**. Please confirm you're on the [latest release](https://github.com/SanHsien/agentdeck/releases/latest) before reporting.

## Security Design

agentdeck **calls no LLM usage API** — checking your quota never spends your tokens. Your prompts, conversations and usage numbers never leave your machine.

**Claude Code and Codex** numbers come entirely from files already on your disk: the status file written by the Claude Code status line hook, and Codex's session logs. Reading either requires no network access at all.

**Antigravity is different, and that deserves to be stated plainly**: its quota does not live on your disk, so agentdeck fetches it over the network.

### Every outbound connection

| Purpose | Endpoint | When |
|---|---|---|
| Antigravity quota | `https://daily-cloudcode-pa.googleapis.com/v1internal:retrieveUserQuotaSummary` | Polled while the app runs, and only when Antigravity is signed in |
| Antigravity token refresh | `https://oauth2.googleapis.com/token` | When the locally stored access token expires |
| Service status alerts | `https://status.claude.com/api/v2/summary.json`<br>`https://status.openai.com/api/v2/summary.json` | Every 5 minutes (`service_status.CACHE_TTL_SECONDS`) |
| Token price table | `https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json` | On first need, then every 7 days (`pricing.CACHE_TTL_DAYS`) |
| Update check | `https://api.github.com/repos/SanHsien/agentdeck/releases/latest` | At most once every 24 hours (`update_gate.AUTO_CHECK_TTL_SECONDS`), and can be turned off from the menu |

None of these carry your usage data, prompts or conversation content. The status, pricing and update endpoints are plain unauthenticated GETs.

`tools/check_upstream_updates.py` also reaches `https://api.github.com`, but it is a maintainer CI tool: it is not distributed with the app and never runs on your machine.

**Every response is size-capped** (`MAX_RESPONSE_BYTES`): `urlopen().read()` with no argument buffers whatever the endpoint sends, so each of the reads above takes the cap plus one byte and refuses anything larger.

### Credential access

To read Antigravity quota, agentdeck reads the OAuth credential the Antigravity CLI already stores on your machine (**Credential Manager** on Windows). The access is read-only: agentdeck never writes or modifies that credential, and never sends it anywhere except Google's own token and quota endpoints — exactly what the Antigravity CLI itself does. **If you do not use Antigravity, agentdeck never reads any credential.**

Claude Code and Codex need no credential access whatsoever.

### About the OAuth client constants in the source

`providers/agy_quota_probe.py` contains a plaintext `_CLIENT_ID` and `_CLIENT_SECRET` (the `GOCSPX-` prefix). **This is not a leaked credential.** Under [RFC 8252](https://datatracker.ietf.org/doc/html/rfc8252), an app installed on a user's machine cannot keep a client secret confidential, so this is a *public client* and not a security boundary. It is not your credential and grants nothing on its own — the authorization comes from the Antigravity OAuth token already on your machine. Secret scanners flag this prefix by design. If Google rotates these constants, the token request fails, the probe returns `None`, and only Antigravity quota disappears.
