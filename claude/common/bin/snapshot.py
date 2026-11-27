#!/usr/bin/env python3
"""snapshot.py [path...]: print the SHA of a commit holding the work tree (or only the named paths) on top of HEAD, so a
subagent can run `git diff HEAD <sha>` on uncommitted work and later edits leave that range fixed. Untracked and
intent-to-add files are included, ignored ones are not. The real index is never touched: a temporary index is built from
HEAD. `git stash create` fails on an intent-to-add file and leaves untracked files out.
shortcut: built from HEAD, so a skip-worktree file missing on disk counts as deleted and an ignored file force-added to the
real index is left out; start from a copy of the real index if that ever matters.
Self-test: python3 -I test_snapshot.py"""
import os, subprocess, sys, tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks"))  # path_only.py
sys.dont_write_bytecode = True
from path_only import which


def main(paths):
    try:
        git = which("git")  # full path: Windows would start a git.exe from the project folder first
        top = subprocess.run([git, "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
        head = subprocess.run([git, "-C", top, "rev-parse", "--verify", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        with tempfile.TemporaryDirectory() as d:
            env = dict(os.environ, GIT_INDEX_FILE=os.path.join(d, "index"))
            run = lambda *a: subprocess.run([git, "-C", top, *a], capture_output=True, text=True, env=env, check=True).stdout.strip()
            run("read-tree", head)
            run("add", "-A", "--", *[os.path.abspath(p) for p in paths] or [top])
            tree = run("write-tree")
            print(run("commit-tree", tree, "-p", head, "-m", "snapshot of the work tree"))
        return 0
    except FileNotFoundError:
        sys.stderr.write("snapshot: git not found on PATH\n")
    except subprocess.CalledProcessError as e:
        sys.stderr.write("snapshot: %s\n" % (e.stderr or "").strip())
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
