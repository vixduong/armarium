"""Self-test for the bash hook bash-ban-raw-tools (pipe rule): python3 -I ~/.claude/hooks/test_bash_ban_raw_tools.py
On Windows the hook is claude/windows/hooks/bash-ban-raw-tools.py (own test); set TEST_BASH to a Git Bash to run this one there."""
import json, os, shutil, subprocess, sys, tempfile

BASH = os.environ.get("TEST_BASH") or "bash"
if sys.platform == "win32" and not os.environ.get("TEST_BASH"):  # bash on PATH may be WSL's
    print("skip on Windows"); sys.exit(0)
HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bash-ban-raw-tools")
home = tempfile.mkdtemp()
os.makedirs(os.path.join(home, ".claude", "hooks"))
stub = os.path.join(home, ".claude", "hooks", "run-cli-hook")  # rtk "resolves": readers pass, only the pipe rule blocks
with open(stub, "w", newline="\n") as f:
    f.write("#!/bin/sh\nexit 0\n")
os.chmod(stub, 0o755)
env = dict(os.environ, HOME=home)

fails = 0
def check(cmd, want):
    global fails
    p = subprocess.run([BASH, HOOK], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}).encode(), capture_output=True, env=env)
    ok = p.returncode == want
    fails += not ok
    print(("ok   " if ok else "FAIL ") + repr(cmd), p.returncode, "want", want)

check("grep x f | head -5", 2)
check("cat f |head", 2)
check("rg x | tail", 2)
check("grep x f | head-foo", 0)  # not head: a different command
check("grep x f | headx", 0)
check("grep x f | head_x", 0)
check("cat f", 0)
shutil.rmtree(home, ignore_errors=True)
sys.exit(1 if fails else 0)
