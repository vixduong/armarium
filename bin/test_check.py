"""Self-test for bin/check: python3 -I bin/test_check.py
Each case builds a small fixture repo and a fake HOME, then expects check to pass or to name the problem."""
import json, os, stat, subprocess, sys, tempfile

CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check")
SETTINGS = {"hooks": {"SessionStart": [{"hooks": [
    {"type": "command", "command": "~/.claude/hooks/good-hook"},
    {"type": "command", "command": "~/.claude/hooks/skill-model-invocable unlocked"}]}]}}


def fixture(files=None, settings=SETTINGS, skills=None):
    """files: {repo-relative path: text}. skills: {name: SKILL.md text} under the fake HOME."""
    root = tempfile.mkdtemp()
    repo, home = os.path.join(root, "repo"), os.path.join(root, "home")
    base = {
        "claude/CLAUDE.md": "Read `~/.claude/CODING_STANDARDS.md` and `agent-tuning.md`; call `anim`.\n",
        "claude/CODING_STANDARDS.md": "Rules.\n",
        "claude/agent-tuning.md": "Tiers.\n",
        "claude/hooks/good-hook": "#!/bin/sh\n",
        "claude/hooks/skill-model-invocable": "#!/bin/sh\n",
        "windows/settings.example.json": "{}",
    }
    base.update(files or {})
    for rel, text in base.items():
        p = os.path.join(repo, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)
        if rel.startswith("claude/hooks/") and not rel.endswith(".py"):
            os.chmod(p, 0o755)
    with open(os.path.join(repo, "claude", "settings.example.json"), "w") as f:
        json.dump(settings, f)
    for name, text in (skills or {"anim": "---\nname: anim\n---\n"}).items():
        d = os.path.join(home, ".claude", "skills", name)
        os.makedirs(d)
        with open(os.path.join(d, "SKILL.md"), "w") as f:
            f.write(text)
    return repo, home


def run(repo, home):
    p = subprocess.run([sys.executable, CHECK, repo], capture_output=True, text=True,
                       env={"HOME": home, "PATH": os.environ["PATH"]})
    return p.returncode, p.stdout + p.stderr


LOCKED = "---\nname: anim\ndisable-model-invocation: true\n---\n"
fails = total = 0


def case(label, want_rc, want_text, **kw):
    global fails, total
    pre = kw.pop("pre", None)
    repo, home = fixture(**kw)
    if pre:
        pre(repo)
    rc, out = run(repo, home)
    ok = rc == want_rc and (want_text in out)
    total += 1
    fails += not ok
    print(("ok   " if ok else "FAIL ") + label, "" if ok else "rc=%s %s" % (rc, out[-300:]))


case("clean fixture passes", 0, "check: ok")
case("dead ~/.claude pointer", 1, "~/.claude/enforcement.md",
     files={"claude/CODING_STANDARDS.md": "See `~/.claude/enforcement.md`.\n"})
case("dead bare .md pointer", 1, "enforcement.md",
     files={"claude/CODING_STANDARDS.md": "See `enforcement.md` (AC-09).\n"})
case("settings calls a hook the repo lacks", 1, "hooks/missing-hook",
     settings={"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "~/.claude/hooks/missing-hook"}]}]}})
case("hook not executable", 1, "hooks/good-hook",
     pre=lambda repo: os.chmod(os.path.join(repo, "claude/hooks/good-hook"), stat.S_IRUSR | stat.S_IWUSR))
case("model told to call a user-only skill", 1, "anim", skills={"anim": LOCKED})
case("user-only skill written as /name passes", 0, "check: ok", skills={"anim": LOCKED},
     files={"claude/CLAUDE.md": "Suggest `/anim`.\n"})
case("user-only skill unlocked by skill-model-invocable passes", 0, "check: ok", skills={"anim": LOCKED},
     settings={"hooks": {"SessionStart": [{"hooks": [
         {"type": "command", "command": "~/.claude/hooks/good-hook"},
         {"type": "command", "command": "~/.claude/hooks/skill-model-invocable anim"}]}]}})
case("broken JSON in windows settings", 1, "windows/settings.example.json",
     files={"windows/settings.example.json": "{"})
case("a failing hook self-test", 1, "test_broken.py",
     files={"claude/hooks/test_broken.py": "import sys; sys.exit(1)\n"})
case("a failing skill script self-test", 1, "test_skill_broken.py",
     files={"claude/skills/demo/scripts/test_skill_broken.py": "import sys; sys.exit(1)\n"})

case("missing claude/settings.example.json", 1, "claude/settings.example.json",
     pre=lambda repo: os.remove(os.path.join(repo, "claude/settings.example.json")))
case("flag text after the frontmatter does not count", 0, "check: ok",
     skills={"anim": "---\nname: anim\n---\n\ndisable-model-invocation: true\n\n---\n"})
case("windows settings call a file the repo lacks", 1, "hooks/gone.ps1",
     files={"windows/settings.example.json": json.dumps({"hooks": {"Stop": [{"hooks": [
         {"type": "command", "command": "powershell -File C:/Users/YOU/.claude/hooks/gone.ps1"}]}]}})})
case("windows settings may call a shared python hook", 0, "check: ok",
     files={"windows/settings.example.json": json.dumps({"hooks": {"Stop": [{"hooks": [
         {"type": "command", "command": "python C:/Users/YOU/.claude/hooks/good-hook"}]}]}})})

print("FAILS %d of %d" % (fails, total))
sys.exit(1 if fails else 0)
