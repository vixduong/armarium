#!/usr/bin/env python3
# SessionStart context adapter, Windows (Python port of cbm-session-reminder.ps1: no PowerShell start, about 0.3 s less).
# Fail-open: it never blocks or logs hook/prompt content; a missing binary or any error is silent exit 0.
# `hook-augment` takes about 2 s, so its output is cached per cwd. Only graph context (additionalContext) is cached: a notice such as
# "no CBM daemon" describes one moment, and a cached copy replayed it to later sessions.
# Fresh cache (no index file changed since): replayed. Stale cache: replayed at once and refreshed by a detached child
# (stale-while-revalidate), so a session start never waits for hook-augment once a cache exists; the new context lands for the next session.
import hashlib, os, subprocess, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I drops the script dir; the shim is next to this file
sys.dont_write_bytecode = True  # no __pycache__ in the hooks folder (install.ps1 would copy it)
from run_cli_hook import resolve  # noqa: E402

LOCK_SECONDS = 60  # a refresh started less than this ago is not started twice
START_SECONDS = 7  # hook-augment limit at session start, under the hook's own 10 s timeout with room for the kill


def cache_dir():
    return os.path.join(os.path.expanduser("~"), ".cache", "codebase-memory-mcp")


def cache_path(inp):
    import json
    try:
        cwd = json.loads(inp.decode("utf-8")).get("cwd")
    except Exception:
        cwd = None
    if not cwd:
        return None
    return os.path.join(cache_dir(), "hook-cache", hashlib.sha1(os.path.normcase(cwd).encode("utf-8")).hexdigest()[:16] + ".json")


def has_context(text):
    return "additionalContext" in text


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def newest_index_mtime(d):
    try:
        return max((e.stat().st_mtime for e in os.scandir(d) if e.name.endswith(".db") and e.name != "activity.db"), default=None)
    except OSError:
        return None


def fresh(path, d):
    t = os.path.getmtime(path)
    newest = newest_index_mtime(d)
    return t > os.path.getmtime(d) and (newest is None or t > newest)


def kill_tree(p):
    # p.kill() stops only a .cmd shim's cmd.exe (npm, scoop); taskkill /T also stops the binary it started
    if os.name == "nt":
        try:
            # full path: CreateProcess searches the cwd (the user's project) before System32
            taskkill = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "taskkill.exe")
            if subprocess.run([taskkill, "/T", "/F", "/PID", str(p.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              creationflags=0x08000000, timeout=2).returncode == 0:
                return
        except (OSError, subprocess.SubprocessError):
            pass
    p.kill()


def augment(binary, inp, timeout):
    p = subprocess.Popen([binary, "hook-augment"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        out = p.communicate(inp, timeout=timeout)[0]
    except subprocess.TimeoutExpired:
        kill_tree(p)  # no wait for the pipe: a grandchild may still hold it open
        return None
    return "\n".join(out.decode("utf-8", "replace").splitlines())  # lines joined with LF, as the PowerShell hook did


def store(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    os.replace(tmp, path)


def take_lock(path):
    lock = path + ".lock"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)  # a cold start has no hook-cache dir yet
    except OSError:
        return None
    for _ in range(2):
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            return lock
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(lock) < LOCK_SECONDS:
                    return None
                os.remove(lock)  # a refresh that died: take over
            except OSError:
                return None
        except OSError:
            return None
    return None


def spawn_refresh(path, inp):
    lock = take_lock(path)
    if not lock:
        return
    # NO_WINDOW | NEW_GROUP, not DETACHED_PROCESS: a child without a console makes codebase-memory-mcp.exe open a visible console window
    kw = {"creationflags": 0x08000000 | 0x00000200} if os.name == "nt" else {"start_new_session": True}
    try:
        p = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--refresh"], stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
        p.stdin.write(inp)
        p.stdin.close()
    except OSError:
        try:
            os.remove(lock)
        except OSError:
            pass


def refresh(binary, inp):
    path = cache_path(inp)
    if not path:
        return
    try:
        out = augment(binary, inp, LOCK_SECONDS - 5)  # ends before its lock can be taken over
        if out and has_context(out):
            store(path, out)
    finally:
        try:
            os.remove(path + ".lock")
        except OSError:
            pass


def main(argv):
    binary = resolve("codebase-memory-mcp")
    if not binary:
        return 0
    inp = sys.stdin.buffer.read()
    if argv[:1] == ["--refresh"]:
        refresh(binary, inp)
        return 0
    path = cache_path(inp)
    cached = read(path) if path and os.path.exists(path) else None
    if cached is not None and has_context(cached):
        try:
            if not fresh(path, cache_dir()):
                spawn_refresh(path, inp)
        except OSError:
            pass
        sys.stdout.write(cached)
        return 0
    out = augment(binary, inp, START_SECONDS)
    if out is None:  # too slow for a session start: let a background refresh warm the cache for the next one
        if path:
            spawn_refresh(path, inp)
        return 0
    sys.stdout.write(out)
    if path and has_context(out):
        store(path, out)
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", newline="")
        sys.exit(main(sys.argv[1:]))
    except Exception:
        sys.exit(0)  # fail-open
