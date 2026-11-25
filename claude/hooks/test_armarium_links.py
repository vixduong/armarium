"""Self-test for armarium-links: python3 -I ~/.claude/hooks/test_armarium_links.py
Builds a throwaway git repo and a fake HOME, so the real ~/.claude is never read or changed."""
import json, os, subprocess, sys, tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "armarium-links")  # the hook beside this test, not the installed one
with tempfile.TemporaryDirectory() as probe:  # the hook and every case need symlinks
    try:
        os.symlink(probe, os.path.join(probe, "link"))
    except OSError as e:
        if getattr(e, "winerror", None) != 1314: raise
        print("skip: Windows allows symlinks only with Developer Mode or elevated"); sys.exit(0)


def setup(link_claude_md=True):
    root = tempfile.mkdtemp()
    repo, home = os.path.join(root, "repo"), os.path.join(root, "home")
    for rel in ["CLAUDE.md", "hooks/armarium-links", "hooks/new-hook", "hooks/old-hook", "settings.example.json", "skills/x/SKILL.md"]:
        p = os.path.join(repo, "claude", rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(rel)
    subprocess.run(["git", "init", "-q", repo], check=True)
    subprocess.run(["git", "-C", repo, "add", "-A"], check=True)
    dot = os.path.join(home, ".claude")
    os.makedirs(os.path.join(dot, "hooks"))
    if link_claude_md:
        os.symlink(os.path.join(repo, "claude", "CLAUDE.md"), os.path.join(dot, "CLAUDE.md"))
    else:
        with open(os.path.join(dot, "CLAUDE.md"), "w") as f:
            f.write("copy")
    with open(os.path.join(dot, "hooks", "old-hook"), "w") as f:  # a stale copy, not a link
        f.write("old")
    return repo, home, dot


def run(home):
    env = {"HOME": home, "PATH": os.environ["PATH"]}
    if sys.platform == "win32":
        env.update(USERPROFILE=home, SystemRoot=os.environ["SystemRoot"])
    p = subprocess.run([sys.executable, HOOK], input="{}", capture_output=True, text=True, env=env)
    return p.returncode, p.stdout.strip()


fails = total = 0


def check(label, ok, detail=""):
    global fails, total
    total += 1
    fails += not ok
    print(("ok   " if ok else "FAIL ") + label, "" if ok else detail)


repo, home, dot = setup()
rc, out = run(home)
msg = json.loads(out or "{}").get("systemMessage", "")
new = os.path.join(dot, "hooks", "new-hook")
check("a new repo file is linked", os.path.islink(new) and os.path.realpath(new) == os.path.realpath(os.path.join(repo, "claude", "hooks", "new-hook")), out)
check("nested new file is linked", os.path.islink(os.path.join(dot, "skills", "x", "SKILL.md")))
check("settings.example.json is not linked", not os.path.lexists(os.path.join(dot, "settings.example.json")))
check("a stale copy is left in place", open(os.path.join(dot, "hooks", "old-hook")).read() == "old")
check("message names the linked file and the stale copy", rc == 0 and "hooks/new-hook" in msg and "hooks/old-hook" in msg, out)

rc, out = run(home)
check("second run: only the stale copy is reported", rc == 0 and "hooks/old-hook" in out and "new-hook" not in out, out)

repo, home, dot = setup(link_claude_md=False)
rc, out = run(home)
check("copy install (CLAUDE.md not a link): silent, nothing linked", rc == 0 and out == "" and not os.path.lexists(os.path.join(dot, "hooks", "new-hook")), out)

repo, home, dot = setup()
os.remove(os.path.join(repo, "claude", "hooks", "armarium-links"))  # CLAUDE.md links into some other repo
rc, out = run(home)
check("CLAUDE.md links into a repo that is not armarium: silent, nothing linked", rc == 0 and out == "" and not os.path.lexists(os.path.join(dot, "hooks", "new-hook")), out)

print("FAILS %d of %d" % (fails, total))
sys.exit(1 if fails else 0)
