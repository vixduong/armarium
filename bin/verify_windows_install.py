"""Checks this machine after `windows/install.ps1 -Apply` + the settings merge. Run by hand: the name has no test_ prefix, so bin/check skips it (it reads ~/.claude).
python -I bin/verify_windows_install.py [settings.json]   # default ~/.claude/settings.json"""
import json, os, re, shutil, subprocess, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOT = os.path.expanduser("~/.claude")
SETTINGS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DOT, "settings.json")
failed = []
def check(name, ok):
    print("ok  " if ok else "FAIL", name)
    if not ok:
        failed.append(name)

# settings.json: merged keys
with open(SETTINGS, encoding="utf-8") as fh:
    s = json.load(fh)
check("settings parses", True)
check("deny Read(**/.env)", "Read(**/.env)" in s.get("permissions", {}).get("deny", []))
check("defaultMode kept", s.get("permissions", {}).get("defaultMode") == "auto")
check("worktree.baseRef is fresh", s.get("worktree", {}).get("baseRef") == "fresh")
check("statusLine runs statusline.py", s.get("statusLine", {}).get("command", "").endswith("/.claude/statusline.py"))
start = [h["command"] for g in s.get("hooks", {}).get("SessionStart", []) for h in g["hooks"]]
for want in ("hooks/armarium-links", "hooks/skill-model-invocable review-animations",  # new
             "hooks/memory-repo-symlink.ps1", "hooks/cbm-session-reminder.ps1", "hooks/codemode-ponytail-band.ps1"):  # kept
    check("SessionStart runs " + want, any(c.endswith(want) or want + " " in c for c in start))
check("armarium-links runs first", bool(start) and start[0].endswith("hooks/armarium-links"))

# every ~/.claude path a hook or the status line calls exists
cmds = [h["command"] for ev in s.get("hooks", {}).values() for g in ev for h in g["hooks"]] + [s.get("statusLine", {}).get("command", "")]
paths = {m for c in cmds for m in re.findall(r"[A-Za-z]:/Users/[^/\s]+/\.claude/[^\s]+", c)}
check("hook paths found", len(paths) > 0)
for p in sorted(paths):
    check("exists " + p.split("/.claude/")[1], os.path.exists(p))

# installed files
for f in ("hooks/armarium-links", "hooks/skill-model-invocable", "hooks/test_armarium_links.py", "hooks/test_skill_model_invocable.py"):
    check("installed " + f, os.path.isfile(os.path.join(DOT, f)))
md = open(os.path.join(DOT, "CLAUDE.md"), encoding="utf-8").read()
check("CLAUDE.md: no zsh line", "Shell is zsh" not in md)
check("CLAUDE.md: no ~/.local/bin path", "~/.local/bin/codebase-memory-mcp" not in md)
check("CLAUDE.md: Two shells line", "**Two shells**" in md)
check("CLAUDE.md: RTK covers PowerShell", "Bash and PowerShell run as `rtk" in md)

# armarium-links leaves a copy install alone (it acts only when CLAUDE.md is a symlink)
if not os.path.islink(os.path.join(DOT, "CLAUDE.md")):
    p = subprocess.run([sys.executable, "-I", os.path.join(DOT, "hooks", "armarium-links")], input="{}", capture_output=True, text=True)
    check("armarium-links: exit 0, silent on a copy install", p.returncode == 0 and not p.stdout.strip())

# the installer has nothing left to do
ps = shutil.which("pwsh") or shutil.which("powershell")
p = subprocess.run([ps, "-NoProfile", "-File", os.path.join(REPO, "windows", "install.ps1")], capture_output=True, text=True)
check("install.ps1 dry run: no new/replace left", p.returncode == 0 and not re.search(r"^(new|replace)\s", p.stdout, re.M))

print("FAILS %d" % len(failed) if failed else "all passed")
sys.exit(1 if failed else 0)
