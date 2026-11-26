"""Self-test for claude/unix/statusline-command.sh: python3 -I ~/.claude/hooks/test_statusline_command.py
On Windows the status line is claude/windows/statusline.py (own test)."""
import json, os, subprocess, sys, tempfile

if sys.platform == "win32":
    print("skip on Windows"); sys.exit(0)
here = os.path.dirname(os.path.abspath(__file__))
SCRIPT = next(p for p in (os.path.join(here, "..", "statusline-command.sh"), os.path.join(here, "statusline-command.sh")) if os.path.exists(p))
fails = 0


def check(name, ok, detail=""):
    global fails
    fails += not ok
    print(("ok   " if ok else "FAIL ") + name, str(detail)[:100])


def run(data, cwd):
    p = subprocess.run(["bash", SCRIPT], input=json.dumps(data), capture_output=True, text=True, cwd=cwd,
                       env={"HOME": cwd, "PATH": os.environ["PATH"]})
    return p.returncode, p.stdout, p.stderr


d = tempfile.mkdtemp()
rc, out, err = run({"model": {"display_name": "Opus"}, "workspace": {"current_dir": d}}, d)
check("prints the model", "Opus" in out, out)
# expires_at goes into shell arithmetic: a value that is not a number must never be evaluated
rc, out, err = run({"model": {"display_name": "Opus"}, "workspace": {"current_dir": d},
                    "prompt_cache": {"expires_at": "a[$(touch %s/pwned)]" % d}}, d)
check("a non-numeric expires_at runs nothing", not os.path.exists(os.path.join(d, "pwned")), err)
check("and still prints the model", "Opus" in out, out)
print("FAILS", fails)
sys.exit(1 if fails else 0)
