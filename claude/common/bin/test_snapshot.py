"""Self-test for snapshot.py: python3 -I test_snapshot.py
snapshot.py prints a commit SHA whose tree is the work tree (or the named paths) on top of HEAD, for `git diff HEAD <sha>`,
and leaves the real index alone. Each case builds a throwaway repo."""
import os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SNAP = os.path.join(HERE, "snapshot.py")
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
ENV.pop("GIT_INDEX_FILE", None)


def git(repo, *a):
    return subprocess.run(["git", "--no-optional-locks", "-C", repo, *a], capture_output=True, text=True, env=ENV, check=True).stdout


def write(repo, name, text):
    with open(os.path.join(repo, name), "w", newline="\n") as f:
        f.write(text)


def repo_with_changes():
    r = tempfile.mkdtemp()
    git(r, "init", "-q")
    for n in ("kept.txt", "edited.txt", "gone.txt"):
        write(r, n, n + "\n")
    write(r, ".gitignore", "ignored.txt\n")
    git(r, "add", "-A"); git(r, "commit", "-qm", "base")
    write(r, "edited.txt", "new text\n")
    os.remove(os.path.join(r, "gone.txt"))
    write(r, "untracked.txt", "u\n")
    write(r, "ita.txt", "i\n"); git(r, "add", "-N", "ita.txt")  # git stash create fails on this
    write(r, "ignored.txt", "x\n")
    return r


def snap(repo, *paths):
    p = subprocess.run([sys.executable, "-I", SNAP, *paths], capture_output=True, text=True, env=ENV, cwd=repo)
    return p.returncode, p.stdout.strip(), p.stderr


fails = 0
def check(name, got, want):
    global fails
    if got != want:
        fails += 1
        print("FAIL", name, "got", repr(got)[:300], "want", repr(want)[:300])


r = repo_with_changes()
index = os.path.join(r, ".git", "index")
before = (open(index, "rb").read(), git(r, "status", "--porcelain"))
rc, sha, err = snap(r)
check("exit 0", (rc, err), (0, ""))
check("one SHA on stdout", len(sha) in (40, 64) and all(c in "0123456789abcdef" for c in sha), True)
if rc == 0 and sha:
    check("parent is HEAD", git(r, "rev-parse", sha + "^").strip(), git(r, "rev-parse", "HEAD").strip())
    check("every change and nothing ignored", git(r, "diff", "--name-status", "HEAD", sha).split("\n"),
          ["M\tedited.txt", "D\tgone.txt", "A\tita.txt", "A\tuntracked.txt", ""])
    check("edited content", git(r, "show", sha + ":edited.txt"), "new text\n")
check("real index and status untouched", (open(index, "rb").read(), git(r, "status", "--porcelain")), before)

rc, sha, err = snap(r, "edited.txt", "untracked.txt")
check("named paths only: exit 0", (rc, bool(sha)), (0, True))
if rc == 0 and sha:
    check("named paths only", git(r, "diff", "--name-only", "HEAD", sha).split(), ["edited.txt", "untracked.txt"])

os.makedirs(os.path.join(r, "sub"))
write(r, os.path.join("sub", "deep.txt"), "d\n")
p = subprocess.run([sys.executable, "-I", SNAP, "deep.txt"], capture_output=True, text=True, env=ENV, cwd=os.path.join(r, "sub"))
check("a relative path from a subfolder", (p.returncode, p.returncode == 0 and git(r, "diff", "--name-only", "HEAD", p.stdout.strip()).split()),
      (0, ["sub/deep.txt"]))

clean = tempfile.mkdtemp()
git(clean, "init", "-q"); write(clean, "a.txt", "a\n"); git(clean, "add", "-A"); git(clean, "commit", "-qm", "base")
rc, sha, err = snap(clean)
check("clean tree: same tree as HEAD", (rc, bool(sha) and git(clean, "rev-parse", sha + "^{tree}") == git(clean, "rev-parse", "HEAD^{tree}")), (0, True))

rc, sha, err = snap(tempfile.mkdtemp())
check("outside a repo: an error, no SHA", (rc != 0, sha, "snapshot:" in err), (True, "", True))
print("ok" if not fails else "%d failed" % fails)
sys.exit(1 if fails else 0)
