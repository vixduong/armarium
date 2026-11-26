"""Self-test for the bash hook memory-repo-symlink: python3 -I ~/.claude/hooks/test_memory_repo_symlink.py
Fake HOME and throwaway git repos, so the real ~/.claude/projects is never touched.
On Windows the hook is claude/windows/hooks/memory_repo_symlink.py (own test)."""
import os, re, subprocess, sys, tempfile

if sys.platform == "win32":
    print("skip on Windows"); sys.exit(0)
HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory-repo-symlink")
for k in [k for k in os.environ if k.startswith("GIT_")]:  # git exports GIT_INDEX_FILE to a pre-commit hook: the throwaway repos would use the real index
    del os.environ[k]
fails = 0


def check(name, ok):
    global fails
    fails += not ok
    print(("ok   " if ok else "FAIL ") + name)


def setup():
    root = os.path.realpath(tempfile.mkdtemp())  # macOS: /var is a link to /private/var, and git prints the real path
    home, repo = os.path.join(root, "home"), os.path.join(root, "repo")
    os.makedirs(home); os.makedirs(repo)
    subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
    proj = os.path.join(home, ".claude", "projects", re.sub(r"[/.]", "-", repo))
    return home, repo, os.path.join(proj, "memory"), os.path.join(repo, ".claude", "memory")


def run(home, repo):
    return subprocess.run(["bash", HOOK], capture_output=True, text=True, env=dict(os.environ, HOME=home, CLAUDE_PROJECT_DIR=repo)).returncode


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)


def read(path):
    with open(path) as f:
        return f.read()


home, repo, pm, rm = setup()
check("no Claude project dir: exit 0", run(home, repo) == 0)
check("no Claude project dir: nothing created", not os.path.exists(os.path.dirname(pm)) and not os.path.exists(rm))

home, repo, pm, rm = setup()
os.makedirs(os.path.dirname(pm))
check("project dir without memory: exit 0", run(home, repo) == 0)
check("project dir without memory: linked to the repo", os.path.islink(pm) and os.path.realpath(pm) == rm)

home, repo, pm, rm = setup()
put(os.path.join(pm, "a.md"), "session")
check("real memory dir: exit 0", run(home, repo) == 0)
check("real memory dir: files moved, then linked", os.path.islink(pm) and read(os.path.join(rm, "a.md")) == "session")
check("second run is a no-op", run(home, repo) == 0 and os.path.islink(pm) and not os.path.lexists(os.path.join(rm, "memory")))

home, repo, pm, rm = setup()
put(os.path.join(pm, "a.md"), "session"); put(os.path.join(pm, "b.md"), "b")
put(os.path.join(rm, "a.md"), "repo")
check("same name in the repo: exit 0", run(home, repo) == 0)
check("same name in the repo: repo file kept", read(os.path.join(rm, "a.md")) == "repo")
check("same name in the repo: other files moved", read(os.path.join(rm, "b.md")) == "b")
check("same name in the repo: real dir kept with the file left behind",
      not os.path.islink(pm) and os.path.isfile(os.path.join(pm, "a.md")) and read(os.path.join(pm, "a.md")) == "session")

print("FAILS", fails)
sys.exit(1 if fails else 0)
