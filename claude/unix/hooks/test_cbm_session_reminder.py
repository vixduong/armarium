"""Self-test for cbm-session-reminder: python3 -I ~/.claude/hooks/test_cbm_session_reminder.py
Builds a fake HOME with a stub codebase-memory-mcp, so the real binary and cache are never touched.
Checks: graph context is cached and replayed; a "no CBM daemon" notice is passed through but never cached,
and an old cached notice is ignored."""
import json, os, subprocess, sys, tempfile

if sys.platform == "win32":  # Windows runs claude/windows/hooks/cbm_session_reminder.py (own test there), not this bash hook
    print("skip on Windows"); sys.exit(0)
HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cbm-session-reminder")
GRAPH = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "[codebase-memory] graph"}})
NODAEMON = json.dumps({"systemMessage": "codebase-memory-mcp: no CBM daemon is running, so graph augmentation is currently skipped."})


def setup():
    home = tempfile.mkdtemp()
    os.makedirs(os.path.join(home, ".local", "bin"))
    os.makedirs(os.path.join(home, ".cache", "codebase-memory-mcp"))
    return home


def stub(home, out):
    p = os.path.join(home, ".local", "bin", "codebase-memory-mcp")
    with open(p, "w") as f:
        f.write("#!/bin/sh\ncat >/dev/null\nprintf '%%s' '%s'\n" % out.replace("'", "'\\''"))
    os.chmod(p, 0o755)


def run(home, cwd="/repo/x"):
    env = {"HOME": home, "PATH": os.environ["PATH"]}
    p = subprocess.run([HOOK], input=json.dumps({"cwd": cwd}), capture_output=True, text=True, env=env)
    return p.returncode, p.stdout.strip()


def cached(home):
    d = os.path.join(home, ".cache", "codebase-memory-mcp", "hook-cache")
    return [open(os.path.join(d, f)).read() for f in os.listdir(d)] if os.path.isdir(d) else []


fails = 0
def check(name, ok, detail=""):
    global fails
    fails += not ok
    print(("ok   " if ok else "FAIL ") + name, detail[:80])

# graph output: printed, cached, then replayed from cache
h = setup(); stub(h, GRAPH)
rc, out = run(h)
check("graph printed", rc == 0 and out == GRAPH, out)
check("graph cached", cached(h) == [GRAPH])
stub(h, "")  # binary now prints nothing: the answer must come from the cache
os.utime(os.path.join(h, ".cache", "codebase-memory-mcp"), (1, 1))  # cache newer than its dir, as after any later run
rc, out = run(h)
check("graph replayed from cache", rc == 0 and out == GRAPH, out)

# no-daemon notice: printed, not cached
h = setup(); stub(h, NODAEMON)
rc, out = run(h)
check("notice printed", rc == 0 and out == NODAEMON, out)
check("notice not cached", cached(h) == [], str(cached(h)))

# an old cached notice is ignored once the daemon answers
stub(h, GRAPH)
d = os.path.join(h, ".cache", "codebase-memory-mcp", "hook-cache"); os.makedirs(d, exist_ok=True)
rc0, _ = run(h)  # find the cache file name the hook uses
for f in os.listdir(d):
    open(os.path.join(d, f), "w").write(NODAEMON)
os.utime(os.path.join(h, ".cache", "codebase-memory-mcp"), (1, 1))  # cache newer than its dir, as in the field
rc, out = run(h)
check("stale notice ignored", rc == 0 and out == GRAPH, out)

# no cwd in input: still passes the binary output through
h = setup(); stub(h, GRAPH)
env = {"HOME": h, "PATH": os.environ["PATH"]}
p = subprocess.run([HOOK], input="{}", capture_output=True, text=True, env=env)
check("no cwd passes through", p.returncode == 0 and p.stdout.strip() == GRAPH, p.stdout)
sys.exit(1 if fails else 0)
