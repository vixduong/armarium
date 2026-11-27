"""Self-test for the run-cli-hook shim: a REPL call (tool_use_id repl_...) goes through untouched, any other call reaches the CLI.
Code Mode scripts parse what `$` returns, so rtk's condensed output ("ok stash create") breaks them."""
import json, os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
SHIM = [sys.executable, os.path.join(HERE, "run_cli_hook.py")]
ENV = dict(os.environ, CCT_PY_BIN=sys.executable)  # the "CLI" is python itself
CLI = ["py", "-c", "import sys; d = sys.stdin.read(); sys.stdout.write('ran:' + d); sys.exit(3 if 'exit3' in d else 0)"]

def run(stdin):
    p = subprocess.run(SHIM + CLI, input=stdin, capture_output=True, text=True, env=ENV, timeout=20)
    return p.returncode, p.stdout

def call(tid, command="git stash create"):
    return json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_use_id": tid, "tool_input": {"command": command}})

fails = 0
for name, stdin, want_ran, want_code in [
    ("a REPL call skips the CLI", call("repl_6f1c2d"), False, 0),
    ("a REPL call with spaced JSON skips the CLI", call("repl_6f1c2d").replace('":', '": '), False, 0),
    ("a Bash tool call reaches the CLI", call("toolu_01ABC"), True, 0),
    ("a command that quotes a REPL id still reaches the CLI", call("toolu_01ABC", 'echo "tool_use_id":"repl_x"'), True, 0),
    ("input with no tool_use_id reaches the CLI", json.dumps({"tool_name": "Bash"}), True, 0),
    ("input that is not JSON reaches the CLI", "not json", True, 0),
    ("the CLI's exit code passes through", call("toolu_01ABC", "exit3"), True, 3),
]:
    code, out = run(stdin)
    ran = out.startswith("ran:")
    intact = not ran or out.rstrip("\n") == "ran:" + stdin.rstrip("\n")  # bash's <<< adds one newline
    if code != want_code or ran != want_ran or not intact:
        fails += 1; print("FAIL %s: exit=%s out=%r" % (name, code, out[:80]))
print("ok" if not fails else "%d failed" % fails)
sys.exit(1 if fails else 0)
