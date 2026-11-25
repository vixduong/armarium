#!/usr/bin/env python3
# SessionStart hook, Windows (Python port of memory-repo-symlink.ps1: no PowerShell start, about 0.5 s less).
# Point ~/.claude/projects/<slug>/memory at <repo>/.claude/memory so memory lives in the repo. Uses a junction (no admin rights needed).
# Fail-open: any error is silent exit 0. Self-test: python -I test_memory_repo_symlink.py
import os, re, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I drops the script dir; the shim is next to this file
sys.dont_write_bytecode = True  # no __pycache__ in the hooks folder (install.ps1 would copy it)
from run_cli_hook import resolve  # noqa: E402

NO_WINDOW = 0x08000000 if os.name == "nt" else 0
REPARSE = 0x400  # FILE_ATTRIBUTE_REPARSE_POINT: a junction or a symlink


def git(cwd, *args):
    exe = resolve("git")  # PATH only: a bare "git" also runs a git.exe in the cwd, the user's project
    if not exe:
        return None  # git is not installed
    try:
        r = subprocess.run([exe, "-C", cwd] + list(args), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
    except OSError:
        return None  # git is not installed
    return r.stdout.decode("utf-8", "replace").strip() if r.returncode == 0 else None


def norm(p):
    return os.path.normcase(os.path.normpath(p))


def is_link(p):
    try:
        st = os.lstat(p)
    except OSError:
        return False
    return os.path.islink(p) or bool(getattr(st, "st_file_attributes", 0) & REPARSE)


def link_target(p):
    try:
        t = os.readlink(p)
    except OSError:
        return None
    for prefix in ("\\\\?\\", "\\??\\"):
        if t.startswith(prefix):
            return t[len(prefix):]
    return t


def remove_link(p):
    try:
        os.rmdir(p)  # a junction or directory symlink: removes the link, never its target
    except OSError:
        os.unlink(p)


def make_link(link, target):
    if os.name != "nt":
        os.symlink(target, link)
        return
    try:
        import _winapi
        _winapi.CreateJunction(target, link)
    except (ImportError, AttributeError, OSError):
        cmd = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "cmd.exe")  # not a cmd.exe in the cwd
        subprocess.run([cmd, "/c", "mklink", "/J", link, target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=NO_WINDOW)


def main():
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    top = git(cwd, "rev-parse", "--show-toplevel")
    if not top:
        return 0
    root = os.path.normpath(top).rstrip("\\/")
    # In a linked worktree, use the main checkout so memory outlives the worktree.
    common = git(cwd, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if common:
        common = os.path.normpath(common).rstrip("\\/")
        if os.path.basename(common) == ".git":
            root = os.path.dirname(common)
    # shortcut: slug rule inferred from observed project dir names; if it mismatches we simply do nothing (no junk dirs).
    slug = re.sub(r"[:\\/ ]", "-", root).replace(".", "-")
    home = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    claude_home = os.path.join(home, ".claude")
    pm = os.path.join(claude_home, "projects", slug, "memory")
    rm = os.path.join(root, "memory") if norm(root) == norm(claude_home) else os.path.join(root, ".claude", "memory")
    # Only act on project dirs Claude Code already created -> no orphan dirs.
    if not os.path.isdir(os.path.dirname(pm)):
        return 0
    os.makedirs(rm, exist_ok=True)

    linked = is_link(pm)
    if linked:
        t = link_target(pm)
        if not t or norm(t) == norm(rm):  # already right, or a reparse point that is no junction/symlink (OneDrive placeholder): leave it
            return 0
    elif os.path.lexists(pm):
        if not os.path.isdir(pm):
            return 0
        # Existing real dir with contents -> move them into the repo first. Never overwrite a repo file; if anything stays
        # behind, keep the real dir and retry next session.
        for name in os.listdir(pm):
            dst = os.path.join(rm, name)
            if not os.path.lexists(dst):
                try:
                    shutil.move(os.path.join(pm, name), dst)
                except OSError:
                    pass
        if os.listdir(pm):
            return 0
        os.rmdir(pm)
    if linked:
        remove_link(pm)  # a link that points elsewhere: drop the link only, then recreate it
    make_link(pm, rm)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
