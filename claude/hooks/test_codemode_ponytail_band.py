"""Self-test for codemode-ponytail-band: python3 -I ~/.claude/hooks/test_codemode_ponytail_band.py
Builds a fake HOME with a ponytail install record, so the real plugin cache is never read or changed."""
import json, os, subprocess, sys, tempfile

HOOK = os.path.expanduser("~/.claude/hooks/codemode-ponytail-band")


def run(hooks_field, code_mode, registered=True):
    home = tempfile.mkdtemp()
    plugin = os.path.join(home, "cache", "ponytail", "5.3.3")
    os.makedirs(os.path.join(plugin, ".claude-plugin"))
    os.makedirs(os.path.join(home, ".claude", "plugins"))
    with open(os.path.join(plugin, ".claude-plugin", "plugin.json"), "w") as f:
        json.dump({"name": "ponytail", "hooks": hooks_field}, f)
    reg = {"plugins": {"ponytail@ponytail": [{"installPath": plugin}]}} if registered else {"plugins": {}}
    with open(os.path.join(home, ".claude", "plugins", "installed_plugins.json"), "w") as f:
        json.dump(reg, f)
    env = {"HOME": home, "PATH": os.environ["PATH"], "CLAUDE_CODE_EXPERIMENTAL_CODE_MODE": code_mode}
    p = subprocess.run([HOOK], input="{}", capture_output=True, text=True, env=env)
    return p.returncode, p.stdout.strip()


BAND = ["./hooks/claude-codex-hooks.json", "./hooks/claude-band.json"]
NO_BAND = ["./hooks/claude-codex-hooks.json"]
WARN = [(BAND, "1", True), ("./hooks/claude-band.json", "1", True)]          # array and single-string forms
SILENT = [(NO_BAND, "1", True), (BAND, "0", True), (BAND, "", True), (BAND, "1", False)]

fails = 0
for case in WARN:
    rc, out = run(*case)
    ok = rc == 0 and "claude-band.json" in json.loads(out or "{}").get("systemMessage", "")
    fails += not ok
    print("warn  " + ("ok  " if ok else "FAIL"), case[1:], out[:60])
for case in SILENT:
    rc, out = run(*case)
    ok = rc == 0 and out == ""
    fails += not ok
    print("silent" + (" ok  " if ok else " FAIL"), case[1:], out[:60])
sys.exit(1 if fails else 0)
