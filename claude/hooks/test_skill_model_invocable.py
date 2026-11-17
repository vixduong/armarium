"""Self-test for skill-model-invocable: python3 -I ~/.claude/hooks/test_skill_model_invocable.py
Builds a fake HOME with skills in it, so the real ~/.claude/skills is never read or changed."""
import json, os, subprocess, sys, tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skill-model-invocable")  # the hook beside this test, not the installed one

SKILL = "---\nname: anim\ndescription: Reviews motion.\ndisable-model-invocation: true\n---\n\n# Body\n"
UNLOCKED = "---\nname: anim\ndescription: Reviews motion.\n---\n\n# Body\n"


def run(files, names):
    """files: {skill name: SKILL.md text}. Returns (exit code, stdout, {name: text after the run})."""
    home = tempfile.mkdtemp()
    for name, text in files.items():
        d = os.path.join(home, ".claude", "skills", name)
        os.makedirs(d)
        with open(os.path.join(d, "SKILL.md"), "w", encoding="utf-8", newline="") as f:
            f.write(text)
    p = subprocess.run([sys.executable, HOOK, *names], input="{}", capture_output=True, text=True, env=env(home))
    after = {}
    for name in files:
        with open(os.path.join(home, ".claude", "skills", name, "SKILL.md"), "rb") as f:
            after[name] = f.read().decode("utf-8", "replace")
    return p.returncode, p.stdout.strip(), after


def env(home):
    e = {"HOME": home, "PATH": os.environ["PATH"]}
    if sys.platform == "win32":  # expanduser reads USERPROFILE there, and Python needs SystemRoot to start
        e.update(USERPROFILE=home, SystemRoot=os.environ["SystemRoot"])
    return e


fails = total = 0


def check(label, ok, detail=""):
    global fails, total
    total += 1
    fails += not ok
    print(("ok   " if ok else "FAIL ") + label, detail if not ok else "")


rc, out, after = run({"anim": SKILL}, ["anim"])
check("flag in frontmatter is removed, rest kept", rc == 0 and after["anim"] == UNLOCKED, repr(after["anim"]))
check("reports the unlocked skill", "anim" in json.loads(out or "{}").get("systemMessage", ""), out)

rc, out, after = run({"anim": UNLOCKED}, ["anim"])
check("already unlocked: unchanged and silent", rc == 0 and out == "" and after["anim"] == UNLOCKED, out)

body_only = "---\nname: anim\n---\n\ndisable-model-invocation: true\n"
rc, out, after = run({"anim": body_only}, ["anim"])
check("flag text in the body is left alone", rc == 0 and out == "" and after["anim"] == body_only, repr(after["anim"]))

off = SKILL.replace(": true", ": false")
rc, out, after = run({"anim": off}, ["anim"])
check("disable-model-invocation: false is left alone", rc == 0 and out == "" and after["anim"] == off)

rc, out, after = run({}, ["missing"])
check("missing skill: exit 0, silent", rc == 0 and out == "", out)

rc, out, after = run({"anim": SKILL.replace("\n", "\r\n")}, ["anim"])
check("CRLF file: flag removed, line endings kept", after["anim"] == UNLOCKED.replace("\n", "\r\n"), repr(after["anim"]))

rc, out, after = run({"anim": SKILL, "other": SKILL}, ["anim"])
check("only the named skill changes", after["anim"] == UNLOCKED and after["other"] == SKILL)

rc, out, after = run({"anim": "# No frontmatter\ndisable-model-invocation: true\n"}, ["anim"])
check("no frontmatter: unchanged, exit 0", rc == 0 and out == "" and after["anim"].startswith("# No frontmatter"))

home = tempfile.mkdtemp()
d = os.path.join(home, ".claude", "skills", "anim")
os.makedirs(d)
with open(os.path.join(d, "SKILL.md"), "wb") as f:
    f.write(b"---\nname: \xff\ndisable-model-invocation: true\n---\n")
p = subprocess.run([sys.executable, HOOK, "anim"], capture_output=True, text=True, env=env(home))
check("non-UTF-8 file: exit 0, silent", p.returncode == 0 and p.stdout == "", p.stderr[-200:])

home = tempfile.mkdtemp()
d = os.path.join(home, ".claude", "skills", "anim")
os.makedirs(d)
f_ = os.path.join(d, "SKILL.md")
with open(f_, "w") as f:
    f.write(UNLOCKED)
os.utime(f_, (1, 1))
subprocess.run([sys.executable, HOOK, "anim"], capture_output=True, env=env(home))
check("nothing to remove: file is not rewritten", os.stat(f_).st_mtime == 1)

# The real install: ~/.claude/skills/<name> is a symlink into ~/.agents/skills/<name>
home = tempfile.mkdtemp()
real = os.path.join(home, ".agents", "skills", "anim")
os.makedirs(real)
os.makedirs(os.path.join(home, ".claude", "skills"))
os.symlink(real, os.path.join(home, ".claude", "skills", "anim"))
with open(os.path.join(real, "SKILL.md"), "w") as f:
    f.write(SKILL)
subprocess.run([sys.executable, HOOK, "anim"], capture_output=True, env=env(home))
with open(os.path.join(real, "SKILL.md")) as f:
    check("symlinked skill dir: the target file is unlocked", f.read() == UNLOCKED)

print("FAILS %d of %d" % (fails, total))
sys.exit(1 if fails else 0)
