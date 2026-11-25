"""Self-test for cbm_session_reminder.py: python -I ~/.claude/hooks/test_cbm_session_reminder.py
Fake HOME with a stub codebase-memory-mcp (counts calls, optional delay), so the real binary and cache are never touched.
Checks: no binary -> silent; cold start runs the binary once and caches graph context; fresh cache is replayed without a call;
a stale cache is served at once and refreshed in the background (once, even for two starts); a notice is passed through but never
cached; CRLF output is normalised like the PowerShell hook (lines joined with LF)."""
import hashlib, json, os, shutil, subprocess, sys, tempfile, time

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cbm_session_reminder.py")
GRAPH = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "[codebase-memory] graph"}})
OLD = json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "[codebase-memory] OLD"}})
NODAEMON = json.dumps({"systemMessage": "codebase-memory-mcp: no CBM daemon is running, so graph augmentation is currently skipped."})
CWD = "C:/repo/x"
NT = os.name == "nt"
fails = 0


def check(name, ok, detail=""):
    global fails
    fails += not ok
    print(("ok   " if ok else "FAIL ") + name, str(detail)[:100])


class Home:
    def __init__(self):
        self.home = tempfile.mkdtemp()
        self.bindir = os.path.join(self.home, "stub")
        self.cache = os.path.join(self.home, ".cache", "codebase-memory-mcp")
        os.makedirs(self.bindir)
        os.makedirs(self.cache)
        self.stub = os.path.join(self.bindir, "codebase-memory-mcp" + (".cmd" if NT else ""))
        self.say(GRAPH)
        self.sleep(0)
        with open(os.path.join(self.bindir, "stub.py"), "w") as f:
            f.write("import sys, time, os\nd = os.path.dirname(os.path.abspath(__file__))\nsys.stdin.buffer.read()\n"
                    "open(os.path.join(d, 'calls.log'), 'a').write('x\\n')\n"
                    "time.sleep(float(open(os.path.join(d, 'sleep.txt')).read()))\n"
                    "sys.stdout.buffer.write(open(os.path.join(d, 'out.txt'), 'rb').read())\n"
                    "open(os.path.join(d, 'done'), 'w').write('1')\n")
        py, st = sys.executable, os.path.join(self.bindir, "stub.py")
        with open(self.stub, "w") as f:
            f.write('@"%s" "%s" %%*\n' % (py, st) if NT else '#!/bin/sh\nexec "%s" "%s" "$@"\n' % (py, st))
        if not NT:
            os.chmod(self.stub, 0o755)

    def say(self, text):
        with open(os.path.join(self.bindir, "out.txt"), "wb") as f:
            f.write(text.encode("utf-8"))

    def sleep(self, s):
        with open(os.path.join(self.bindir, "sleep.txt"), "w") as f:
            f.write(str(s))

    def calls(self):
        p = os.path.join(self.bindir, "calls.log")
        return len(open(p).read().split()) if os.path.exists(p) else 0

    def done(self):
        return os.path.exists(os.path.join(self.bindir, "done"))

    def cache_file(self, cwd=CWD):
        return os.path.join(self.cache, "hook-cache", hashlib.sha1(os.path.normcase(cwd).encode("utf-8")).hexdigest()[:16] + ".json")

    def cached(self):
        p = self.cache_file()
        return open(p, encoding="utf-8").read() if os.path.exists(p) else None

    def seed(self, text, cache_age, db_age=None, dir_age=1000):
        """Cache file with mtime now-cache_age; a project db with mtime now-db_age; the cache dir itself at now-dir_age."""
        now = time.time()
        os.makedirs(os.path.dirname(self.cache_file()), exist_ok=True)
        with open(self.cache_file(), "w", encoding="utf-8") as f:
            f.write(text)
        os.utime(self.cache_file(), (now - cache_age, now - cache_age))
        if db_age is not None:
            db = os.path.join(self.cache, "proj.db")
            open(db, "w").close()
            os.utime(db, (now - db_age, now - db_age))
            act = os.path.join(self.cache, "activity.db")  # never counts as an index change
            open(act, "w").close()
        os.utime(self.cache, (now - dir_age, now - dir_age))

    def env(self, with_bin=True):
        e = {k: os.environ[k] for k in ("SYSTEMROOT", "SystemRoot", "TEMP", "TMP") if k in os.environ}
        e.update({"USERPROFILE": self.home, "HOME": self.home, "PATH": ""})
        if with_bin:
            e["CCT_CODEBASE_MEMORY_MCP_BIN"] = self.stub
        return e

    def start(self, with_bin=True):  # cwd = the fake home, as a hook runs in the user's project
        return subprocess.Popen([sys.executable, HOOK], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env(with_bin), cwd=self.home)

    def run(self, with_bin=True, cwd=CWD):
        p = self.start(with_bin)
        out, _ = p.communicate(json.dumps({"cwd": cwd}).encode())
        return p.returncode, out.decode("utf-8")


def wait_for(cond, secs=15):
    end = time.time() + secs
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.1)
    return cond()


# no binary: exit 0, nothing printed
h = Home()
rc, out = h.run(with_bin=False)
check("no binary: exit 0, silent", rc == 0 and out == "", (rc, out))

# cold start: binary runs once, graph context printed and cached
h = Home()
rc, out = h.run()
check("cold: prints graph context", rc == 0 and out == GRAPH, (rc, out))
check("cold: one binary call", h.calls() == 1, h.calls())
check("cold: context cached", h.cached() == GRAPH, h.cached())

# fresh cache: replayed, no binary call
h = Home()
h.seed(OLD, cache_age=10, db_age=500)
rc, out = h.run()
check("fresh: replays the cache", rc == 0 and out == OLD, (rc, out))
check("fresh: no binary call", h.calls() == 0, h.calls())

# stale cache (index changed after it): served at once, refreshed in the background
h = Home()
h.seed(OLD, cache_age=500, db_age=10)
h.sleep(1.5)
rc, out = h.run()
check("stale: serves the old context at once", rc == 0 and out == OLD, (rc, out))
check("stale: the hook returned before the refresh finished", not h.done())
check("stale: refresh updates the cache", wait_for(lambda: h.cached() == GRAPH), h.cached())
check("stale: exactly one refresh", h.calls() == 1, h.calls())

# two starts on a stale cache: one refresh
h = Home()
h.seed(OLD, cache_age=500, db_age=10)
h.sleep(1.0)
p1, p2 = h.start(), h.start()
req = json.dumps({"cwd": CWD}).encode()
o1, o2 = p1.communicate(req)[0], p2.communicate(req)[0]
check("two stale starts: both serve the old context", o1.decode() == OLD and o2.decode() == OLD, (o1, o2))
wait_for(lambda: h.cached() == GRAPH)
time.sleep(0.5)
check("two stale starts: one refresh", h.calls() == 1, h.calls())

# lock: removed after a refresh; a young lock blocks a second refresh; an old lock (dead child) is taken over
h = Home()
h.seed(OLD, cache_age=500, db_age=10)
lock = h.cache_file() + ".lock"
h.run()
check("lock: cleared after the refresh", wait_for(lambda: h.cached() == GRAPH and not os.path.exists(lock)), os.path.exists(lock))
h = Home()
h.seed(OLD, cache_age=500, db_age=10)
open(h.cache_file() + ".lock", "w").close()
rc, out = h.run()
time.sleep(1.0)
check("lock: a young lock blocks the refresh", out == OLD and h.calls() == 0 and h.cached() == OLD, (out, h.calls()))
os.utime(h.cache_file() + ".lock", (time.time() - 120, time.time() - 120))
h.run()
check("lock: an old lock is taken over", wait_for(lambda: h.cached() == GRAPH) and h.calls() == 1, h.calls())
h = Home()
h.seed(OLD, cache_age=500, db_age=10)
h.say(NODAEMON)
h.run()
check("refresh with no context: cache kept, lock cleared", wait_for(lambda: h.calls() == 1 and not os.path.exists(h.cache_file() + ".lock")) and h.cached() == OLD, h.cached())

# a notice is printed but never cached; an old cached notice is ignored
h = Home()
h.say(NODAEMON)
rc, out = h.run()
check("notice: printed", rc == 0 and out == NODAEMON, (rc, out))
check("notice: not cached", h.cached() is None, h.cached())
h.seed(NODAEMON, cache_age=10, db_age=500)
h.say(GRAPH)
rc, out = h.run()
check("old cached notice ignored: binary runs", out == GRAPH and h.calls() == 2, (out, h.calls()))

# CRLF output: lines joined with LF, no trailing newline (as the PowerShell hook did)
h = Home()
h.say("line1\r\nline2\r\n")
rc, out = h.run()
check("CRLF normalised", out == "line1\nline2", repr(out))

# cwd case and slashes do not split the cache (Windows paths are case-insensitive)
if NT:
    h = Home()
    h.seed(OLD, cache_age=10, db_age=500)
    rc, out = h.run(cwd="c:\\REPO\\x")
    check("cwd case: same cache", out == OLD and h.calls() == 0, (out, h.calls()))

# a hung hook-augment is cut off before the hook's own 10 s limit: nothing printed, nothing cached
# and hands off to a background refresh (55 s budget), so a slow-but-working binary still warms the cache
h = Home()
h.sleep(9)
if NT:  # a taskkill.exe in the project dir must not run: the real one comes from System32
    shutil.copy(sys.executable, os.path.join(h.home, "taskkill.exe"))
t0 = time.time()
rc, out = h.run()
took = time.time() - t0
check("hung binary: returns in time, silent", rc == 0 and out == "" and took < 10 and h.cached() is None, (rc, out, round(took, 1)))
time.sleep(max(0, t0 + 10.5 - time.time()))  # the cut-off stub would have finished at about 9 s; the refresh runs until about 17 s
check("hung binary: the whole process tree is stopped (a .cmd shim's child too)", not h.done())
check("hung binary: background refresh warms the cache", wait_for(lambda: h.cached() == GRAPH, 20), h.cached())

# --refresh has its own limit (LOCK_SECONDS - 5): cut off, cache kept, lock cleared. In-process with a short LOCK_SECONDS.
sys.path.insert(0, os.path.dirname(HOOK))
sys.dont_write_bytecode = True  # no __pycache__ beside the hooks
import cbm_session_reminder as hook_mod  # noqa: E402
h = Home()
h.seed(OLD, cache_age=500, db_age=10)
h.sleep(6)
open(h.cache_file() + ".lock", "w").close()
saved = {k: os.environ.get(k) for k in ("USERPROFILE", "HOME")}
os.environ.update(USERPROFILE=h.home, HOME=h.home)
hook_mod.LOCK_SECONDS = 8
t0 = time.time()
try:
    hook_mod.refresh(h.stub, json.dumps({"cwd": CWD}).encode())
finally:
    for k, v in saved.items():
        if v is None: os.environ.pop(k, None)
        else: os.environ[k] = v
took = time.time() - t0
check("refresh: cut off at LOCK_SECONDS - 5, cache kept, lock cleared", took < 5 and h.cached() == OLD and not os.path.exists(h.cache_file() + ".lock"), round(took, 1))

# importing run_cli_hook leaves no __pycache__ beside the hook (install.ps1 would copy it)
d = tempfile.mkdtemp()
for f in (HOOK, os.path.join(os.path.dirname(HOOK), "run_cli_hook.py")):
    shutil.copy(f, d)
h = Home()
subprocess.run([sys.executable, os.path.join(d, "cbm_session_reminder.py")], input=b"{}", capture_output=True, env=h.env(with_bin=False))
check("no __pycache__ written", not os.path.exists(os.path.join(d, "__pycache__")), os.listdir(d))

sys.exit(1 if fails else 0)
