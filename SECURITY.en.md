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

agentdeck **never calls Anthropic or OpenAI usage APIs**: Claude Code and Codex usage numbers come from local status files and session logs, and those records are never uploaded. The app does contact a public pricing table, the public Claude and Codex status pages, the GitHub Releases endpoint, and the signed-in user's Antigravity quota endpoint; see the README privacy section for the complete scope.
