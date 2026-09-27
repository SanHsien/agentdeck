---
name: Bug report
about: Report something that's broken, wrong, or unexpected
labels: bug
---

**Describe the bug**
<!-- A clear, concise description of what's happening. -->

**Steps to reproduce**
1.
2.
3.

**Expected behavior**
<!-- What you expected to happen instead. -->

**Environment**
- Windows version:
- Python version (`uv run --no-sync python --version`):
- agentdeck commit (`git rev-parse --short HEAD`):
- Mode: [system tray / TUI / mock / doctor]

**Logs**
Run `$env:AGENTDECK_DEBUG=1; uv run --no-sync python main.py` and paste any warnings here.

> ⚠️ **Privacy**: agentdeck reads files under `~/.claude/` and `~/.codex/`. **Do not paste**:
> - the contents of `~/.claude/agentdeck-status.json` or any `tt-status.json` / `usag-status.json`
> - any `~/.codex/sessions/**/*.jsonl` (these may include prompts, project names, and absolute paths)
> - absolute paths, project / repo names, session IDs, or cost figures
>
> Trim to the smallest snippet that reproduces the issue. When in doubt, replace identifiers with `<redacted>`.

```

```

**Additional context**
<!-- Screenshots, related issues, anything else. -->
