"""Self-test for bash_gate.py, the one Windows process for the Bash/PowerShell PreToolUse gate: python -I test_bash_gate.py
Runs the gate as Claude Code does (JSON on stdin; exit code, stdout, stderr) from a temp folder holding it and the hooks it runs."""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
COMMON = os.path.join(HERE, "..", "..", "common", "hooks")  # repo layout; installed, every hook sits in HERE
hooks = tempfile.mkdtemp()
for name in ("bash_gate.py", "bash-ban-raw-tools.py", "run_cli_hook.py", "bash-ban-shell-writes", "path_only.py"):
    src = os.path.join(HERE, name)
    shutil.copy(src if os.path.exists(src) else os.path.join(COMMON, name), hooks)
GATE = os.path.join(hooks, "bash_gate.py")
tmp = tempfile.mkdtemp()
# rtk must not resolve: empty PATH, every probe dir under tmp. The stand-in CLI is python itself (CCT_PY_BIN).
BASE = {"PATH": "", "USERPROFILE": tmp, "APPDATA": tmp, "LOCALAPPDATA": tmp, "TEMP": tmp, "TMP": tmp,
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
CLI_ENV = dict(BASE, CCT_PY_BIN=sys.executable)
CLI = ["py", "-c", "import sys; d = sys.stdin.read(); sys.stdout.write('ran:' + d); sys.exit(3 if 'exit3' in d else 0)"]


def gate(cmd, tool="Bash", env=CLI_ENV, raw=None, tid="toolu_01", agent=None, cli=CLI):
    d = {"tool_name": tool, "tool_use_id": tid, "tool_input": {"command": cmd}}
    if agent:
        d["agent_type"] = agent
    data = raw if raw is not None else json.dumps(d).encode()
    p = subprocess.run([sys.executable, GATE] + cli, input=data, capture_output=True, env=env, cwd=tmp, timeout=30)
    return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")


fails = 0
def check(name, got, want):
    global fails
    if got != want:
        fails += 1
        print("FAIL", name, "got", repr(got)[:300], "want", repr(want)[:300])


# rtk absent: the raw-tools ban blocks readers
rc, out, err = gate("cat a.txt", env=BASE, cli=["rtk", "hook", "claude"])
check("reader blocked when rtk is absent", (rc, "BLOCKED 'cat'" in err, out), (2, True, ""))
rc, out, err = gate("git status", env=BASE, cli=["rtk", "hook", "claude"])
check("rtk absent: allowed, nothing printed", (rc, out), (0, ""))
# the shell-writes ban
rc, out, err = gate("echo hi > f.txt")
check("shell write blocked, CLI not run", (rc, "writes a file from Bash" in err, out), (2, True, ""))
rc, out, err = gate("ls > out.txt", agent="reviewer")
check("read-only agent: its own message", (rc, "reviewer is read-only" in err), (2, True))
# both ban: both messages, as two parallel hooks gave
rc, out, err = gate("cat a > b.txt", env=BASE, cli=["rtk", "hook", "claude"])
check("both bans block: both messages", (rc, "BLOCKED 'cat'" in err, "writes a file from Bash" in err), (2, True, True))
check("shell-writes runs first: it does no I/O, so a stalled PATH probe cannot hold it up", err.index("writes a file") < err.index("BLOCKED 'cat'"), True)
# nothing blocks: the CLI gets the same stdin; its stdout and exit code pass through
rc, out, err = gate("git status")
check("allowed: CLI ran with the whole input", (rc, out.startswith("ran:{") and '"git status"' in out), (0, True))
rc, out, err = gate("exit3")
check("CLI exit code passes through", (rc, out.startswith("ran:")), (3, True))
rc, out, err = gate("git status", tid="repl_6f1c2d")
check("REPL call skips the CLI", (rc, out), (0, ""))
fake_rtk = os.path.join(tmp, "rtk-fake.exe")
open(fake_rtk, "w").close()
rc, out, err = gate("cat a.txt", env=dict(CLI_ENV, CCT_RTK_BIN=fake_rtk))
check("rtk resolves: a reader goes to the CLI", (rc, out.startswith("ran:")), (0, True))
# PowerShell: raw-tools applies, shell-writes does not (Bash only)
rc, out, err = gate("Get-Content f", tool="PowerShell", env=BASE, cli=["rtk", "hook", "claude"])
check("PowerShell reader blocked", rc, 2)
rc, out, err = gate("echo hi > f.txt", tool="PowerShell")
check("PowerShell write is not shell-writes' call", (rc, out.startswith("ran:")), (0, True))
# unlock file: named by the gate's parent PID, as each hook did on its own
rc, out, err = gate("touch bash-raw-unlock-1")
check("naming the unlock file blocks", (rc, "names the unlock file" in err), (2, True))
# fail open
rc, out, err = gate("", raw=b"{nope")
check("bad JSON: no block", rc in (0,), True)
with open(os.path.join(hooks, "bash-ban-raw-tools.py"), "w") as f:
    f.write("raise RuntimeError('boom')\n")
rc, out, err = gate("git status")
check("a ban that crashes lets the call through to the CLI", (rc, out.startswith("ran:")), (0, True))
check("a crashed ban says so on stderr, as its own failing hook did", "RuntimeError: boom" in err, True)
rc, out, err = gate("echo hi > f.txt")
check("the other ban still blocks", rc, 2)
with open(os.path.join(hooks, "bash-ban-raw-tools.py"), "w") as f:
    f.write("print('noise')\n")
rc, out, err = gate("git status")
check("a ban's stdout does not reach Claude Code", out.startswith("ran:"), True)
print("ok" if not fails else "%d failed" % fails)
sys.exit(1 if fails else 0)
