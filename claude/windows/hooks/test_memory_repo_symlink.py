"""Self-test for memory_repo_symlink.py: python -I ~/.claude/hooks/test_memory_repo_symlink.py
Fake USERPROFILE and throwaway git repos, so the real ~/.claude/projects is never touched.
Checks: a junction (symlink off Windows) from ~/.claude/projects/<slug>/memory to <repo>/.claude/memory; no-op outside git or without a
Claude project dir; files in an existing real memory dir are moved in and never overwrite a repo file; a stale link is repointed without
touching its old target; a linked worktree uses the main checkout; the ~/.claude repo itself stores at <root>/memory."""
import os, re, shutil, subprocess, sys, tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_repo_symlink.py")
for k in [k for k in os.environ if k.startswith("GIT_")]:  # git exports GIT_INDEX_FILE to a pre-commit hook: the throwaway repos would use the real index
    del os.environ[k]
NT = os.name == "nt"
fails = 0


def check(name, ok, detail=""):
    global fails
    fails += not ok
    print(("ok   " if ok else "FAIL ") + name, str(detail)[:100])


def git(cwd, *a):
    return subprocess.run(["git", "-C", cwd, "-c", "user.name=t", "-c", "user.email=t@t", *a], capture_output=True, text=True).stdout.strip()


def mkrepo(parent, name="repo"):
    p = os.path.join(parent, name)
    os.makedirs(p)
    git(p, "init", "-q")
    return p


def slug_of(repo):
    top = os.path.normpath(git(repo, "rev-parse", "--show-toplevel")).rstrip("\\/")
    return re.sub(r"[:\\/ ]", "-", top).replace(".", "-")


def target_of(p):
    t = os.readlink(p)
    return os.path.normcase(os.path.normpath(t[4:] if t.startswith(("\\\\?\\", "\\??\\")) else t))


def is_link(p):
    try:
        st = os.lstat(p)
    except OSError:
        return False
    return os.path.islink(p) or bool(getattr(st, "st_file_attributes", 0) & 0x400)


def run(home, cwd, path=None, proc_cwd=None):
    env = {k: os.environ[k] for k in ("SYSTEMROOT", "SystemRoot", "TEMP", "TMP") if k in os.environ}
    env.update({"USERPROFILE": home, "HOME": home, "PATH": os.environ["PATH"] if path is None else path, "CLAUDE_PROJECT_DIR": cwd})
    p = subprocess.run([sys.executable, HOOK], input="{}", capture_output=True, text=True, env=env, cwd=proc_cwd)
    return p.returncode, p.stdout


def norm(p):
    return os.path.normcase(os.path.normpath(p))


def world():
    base = os.path.realpath(tempfile.mkdtemp())  # macOS: /var links to /private/var and git reports the resolved path
    home = os.path.join(base, "home")
    os.makedirs(os.path.join(home, ".claude", "projects"))
    return base, home, mkrepo(base)


def proj_mem(home, repo):
    return os.path.join(home, ".claude", "projects", slug_of(repo), "memory")


def touch(p, text="x"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        f.write(text)


# links the project memory dir to the repo
base, home, repo = world()
os.makedirs(os.path.dirname(proj_mem(home, repo)))
rc, out = run(home, repo)
pm = proj_mem(home, repo)
check("links project memory to <repo>/.claude/memory", rc == 0 and out == "" and is_link(pm) and target_of(pm) == norm(os.path.join(repo, ".claude", "memory")), (rc, out))

# already correct: left alone
touch(os.path.join(repo, ".claude", "memory", "keep.md"))
before = os.lstat(pm).st_ctime_ns
rc, out = run(home, repo)
check("already linked: no-op, link not recreated", rc == 0 and is_link(pm) and os.path.exists(os.path.join(pm, "keep.md")) and os.lstat(pm).st_ctime_ns == before)

# no Claude project dir yet: nothing is created
base, home, repo = world()
rc, out = run(home, repo)
check("no project dir: exit 0, nothing created", rc == 0 and not os.path.exists(os.path.dirname(proj_mem(home, repo))) and not os.path.exists(os.path.join(repo, ".claude")))

# outside git
base, home, repo = world()
plain = os.path.join(base, "plain")
os.makedirs(plain)
rc, out = run(home, plain)
check("not a git repo: exit 0, nothing created", rc == 0 and not os.path.exists(os.path.join(plain, ".claude")))

# git missing
os.makedirs(os.path.dirname(proj_mem(home, repo)))
rc, out = run(home, repo, path="")
check("git missing: exit 0, nothing created", rc == 0 and not os.path.exists(os.path.join(repo, ".claude")))

# real dir with files: moved in, then linked; a repo file is never overwritten
base, home, repo = world()
pm = proj_mem(home, repo)
touch(os.path.join(pm, "a.md"), "A")
touch(os.path.join(pm, "sub", "b.md"), "B")
rc, out = run(home, repo)
rm = os.path.join(repo, ".claude", "memory")
check("real dir: files moved into the repo and linked", rc == 0 and is_link(pm) and open(os.path.join(rm, "a.md")).read() == "A" and os.path.exists(os.path.join(rm, "sub", "b.md")), rc)
base, home, repo = world()
pm = proj_mem(home, repo)
rm = os.path.join(repo, ".claude", "memory")
touch(os.path.join(pm, "a.md"), "NEW")
touch(os.path.join(pm, "c.md"), "C")
touch(os.path.join(rm, "a.md"), "REPO")
rc, out = run(home, repo)
check("conflict: repo file kept, real dir kept, other files moved", rc == 0 and not is_link(pm) and open(os.path.join(rm, "a.md")).read() == "REPO"
      and open(os.path.join(pm, "a.md")).read() == "NEW" and open(os.path.join(rm, "c.md")).read() == "C", rc)

# stale link: repointed; the old target is not touched
base, home, repo = world()
pm = proj_mem(home, repo)
elsewhere = os.path.join(base, "elsewhere")
touch(os.path.join(elsewhere, "old.md"), "OLD")
os.makedirs(os.path.dirname(pm))
if NT:
    subprocess.run(["cmd", "/c", "mklink", "/J", pm, elsewhere], capture_output=True)
else:
    os.symlink(elsewhere, pm)
rc, out = run(home, repo)
check("stale link: repointed to the repo", rc == 0 and is_link(pm) and target_of(pm) == norm(os.path.join(repo, ".claude", "memory")), rc)
check("stale link: old target untouched", open(os.path.join(elsewhere, "old.md")).read() == "OLD")

# linked worktree: uses the main checkout
base, home, repo = world()
git(repo, "commit", "-q", "--allow-empty", "-m", "x")
wt = os.path.join(base, "wt")
git(repo, "worktree", "add", "-q", "--detach", wt)
os.makedirs(os.path.dirname(proj_mem(home, repo)))
rc, out = run(home, wt)
check("worktree: links to the main checkout's memory", rc == 0 and is_link(proj_mem(home, repo)) and target_of(proj_mem(home, repo)) == norm(os.path.join(repo, ".claude", "memory")), rc)

# a git.exe in the hook's working directory (a cloned repo's file) is never run: git comes from PATH
if NT:
    base, home, repo = world()
    os.makedirs(os.path.dirname(proj_mem(home, repo)))
    evil = os.path.join(base, "evil")
    os.makedirs(evil)
    shutil.copy(sys.executable, os.path.join(evil, "git.exe"))  # a python.exe that cannot answer git: links fail if it runs
    rc, out = run(home, repo, proc_cwd=evil)
    check("cwd git.exe: not run, PATH git links", rc == 0 and is_link(proj_mem(home, repo)), rc)

# the ~/.claude repo itself: <root>/memory
base = os.path.realpath(tempfile.mkdtemp())
home = os.path.join(base, "home")
ch = os.path.join(home, ".claude")
os.makedirs(ch)
git(ch, "init", "-q")
pm = os.path.join(ch, "projects", slug_of(ch), "memory")
os.makedirs(os.path.dirname(pm))
rc, out = run(home, ch)
check("~/.claude repo: stores at <root>/memory", rc == 0 and is_link(pm) and target_of(pm) == norm(os.path.join(ch, "memory")), rc)

sys.exit(1 if fails else 0)
