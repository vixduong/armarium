#!/usr/bin/env python3
# SessionStart, Windows (Python port of codemode-ponytail-band.ps1: no PowerShell start, about 0.3 s less). Warn when Code Mode is on
# but ponytail's band mod is registered again. The band (a JS mod that checks tool calls) makes Code Mode fall back to ordinary
# tools; a ponytail update restores it. Fail-open: any missing file or tool -> silent exit 0.
# Self-test: python -I test_codemode_ponytail_band.py (in claude/hooks)
import json, os, sys


def main():
    if os.environ.get("CLAUDE_CODE_EXPERIMENTAL_CODE_MODE") != "1":
        return 0
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    try:
        with open(os.path.join(home, ".claude", "plugins", "installed_plugins.json"), encoding="utf-8-sig") as f:
            d = json.load(f)["plugins"]["ponytail@ponytail"][0]["installPath"]
        if not d:
            return 0
        with open(os.path.join(d, ".claude-plugin", "plugin.json"), encoding="utf-8-sig") as f:
            hooks = json.load(f).get("hooks")
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError):
        return 0
    if "claude-band" not in json.dumps(hooks):
        return 0
    leaf = os.path.basename(d.rstrip("/\\"))
    msg = ('Code Mode is on, but ponytail %s registers its band mod again, so Code Mode falls back to ordinary tools. '
           'Remove "./hooks/claude-band.json" from %s/.claude-plugin/plugin.json.' % (leaf, d))
    sys.stdout.write(json.dumps({"systemMessage": msg}, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
