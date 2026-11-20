"""Self-test for the Windows Python hooks bash-ban-raw-tools.py and run_cli_hook.py:
python -I windows/hooks/test_bash_ban_raw_tools.py"""
import json, os, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "bash-ban-raw-tools.py")
SHIM = os.path.join(HERE, "run_cli_hook.py")
tmp = tempfile.mkdtemp()
# rtk must not resolve: empty PATH, every probe dir under tmp
BASE = {"PATH": "", "USERPROFILE": tmp, "APPDATA": tmp, "LOCALAPPDATA": tmp, "TEMP": tmp, "TMP": tmp,
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
fake_rtk = os.path.join(tmp, "rtk-fake.exe")
open(fake_rtk, "w").close()
RESOLVED = dict(BASE, CCT_RTK_BIN=fake_rtk)


def gate(cmd, tool="Bash", env=BASE, raw=None):
    data = raw if raw is not None else json.dumps({"tool_name": tool, "tool_input": {"command": cmd}}).encode()
    p = subprocess.run([sys.executable, GATE], input=data, capture_output=True, env=env, cwd=tmp)
    return p.returncode, p.stderr.decode("utf-8", "replace")


fails = 0
def check(name, got, want):
    global fails
    if got != want: fails += 1; print("FAIL", name, "got", got, "want", want)

BLOCK = ["cat a.txt", "  grep -n x f", "Get-Content f", "CAT a", "find . -name x", "wc -l f", "rg x src",
         "findstr x f", "grep -n ü f"]
ALLOW = ["ls -la", "rtk cat a", "RTK cat x", "git status", "", "echo cat", "python -c 1"]
for c in BLOCK: check("block " + c, gate(c)[0], 2)
for c in ALLOW: check("allow " + repr(c), gate(c)[0], 0)
check("type in PowerShell", gate("type f", "PowerShell")[0], 2)
check("type in Bash is a builtin", gate("type -a git")[0], 0)
check("other tool", gate("cat a", "Read")[0], 0)
check("bad json fails open", gate("", raw=b"{nope")[0], 0)
rc, err = gate("cat a.txt")
check("cat message", "BLOCKED 'cat'. Use the Read tool" in err, True)
rc, err = gate("grep x f | head -5")
check("pipe block", (rc, "'| tail'/'| head' pipeline" in err), (2, True))
check("pipe after non-reader passes", gate("ls | head -3")[0], 0)
# rtk resolves: readers defer to the rtk rewrite, the pipe rule still blocks
check("reader with rtk", gate("cat a.txt", env=RESOLVED)[0], 0)
check("pipe with rtk", gate("grep x f | tail", env=RESOLVED)[0], 2)
# unlock file, keyed on the hook's parent (this process)
unlock = os.path.join(tmp, "bash-raw-unlock-%d" % os.getpid())
open(unlock, "w").close()
check("fresh unlock", gate("cat a.txt")[0], 0)
future = time.time() + 3600
os.utime(unlock, (future, future))
check("future unlock is expired", (gate("cat a.txt")[0], os.path.exists(unlock)), (2, False))

# shim
def shim(args, env=BASE, data=b""):
    p = subprocess.run([sys.executable, SHIM] + args, input=data, capture_output=True, env=env, cwd=tmp)
    return p.returncode, p.stdout.decode("utf-8", "replace").strip()
open(os.path.join(tmp, "rtk.cmd"), "w").close()  # the cwd is never searched
check("which: cwd not searched", shim(["--which", "rtk"])[0], 1)
check("which: relative PATH entry skipped", shim(["--which", "rtk"], dict(BASE, PATH="."))[0], 1)
bindir = os.path.join(tmp, "bin"); os.mkdir(bindir)
on_path = os.path.join(bindir, "rtk.exe" if os.name == "nt" else "rtk")
open(on_path, "w").close(); os.chmod(on_path, 0o755)
rc, out = shim(["--which", "rtk"], dict(BASE, PATH=bindir))
check("which: PATH hit", (rc, os.path.normcase(out)), (0, os.path.normcase(on_path)))  # PATHEXT is upper case
check("which: override", shim(["--which", "rtk"], RESOLVED), (0, fake_rtk))
check("missing bin passes", shim(["nosuchtool", "x"])[0], 0)
# passthrough: stdin bytes in, stdout and exit code out (the child is python itself via the override)
echo = ["echo3", "-c", "import sys; sys.stdout.write(sys.stdin.read()); sys.exit(3)"]
check("passthrough", shim(echo, dict(BASE, CCT_ECHO3_BIN=sys.executable), b"hello\n"), (3, "hello"))

print("FAILS", fails)
sys.exit(1 if fails else 0)
