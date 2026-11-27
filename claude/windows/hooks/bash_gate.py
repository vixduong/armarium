#!/usr/bin/env python3
# PreToolUse Bash/PowerShell gate, Windows: one python.exe where three hooks each started their own (bash-ban-raw-tools.py,
# bash-ban-shell-writes, run_cli_hook.py rtk hook claude); on a slow, busy machine every start counts against the timeout.
#   python bash_gate.py <bin> [args...]   the two bans on this stdin, then run_cli_hook.py <bin> [args...] if neither blocks
# Either ban exits 2 → the stderr of each that did, exit 2, the CLI not run (two parallel hooks: the deny beat rtk's rewrite).
# A ban that crashes or exits anything else lets the call through, as a failing hook did. The bans print nothing to stdout;
# what they print is dropped, so the CLI's JSON reaches Claude Code whole. Self-test: python -I test_bash_gate.py
import io, os, runpy, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
BANS = ("bash-ban-shell-writes", "bash-ban-raw-tools.py")  # no I/O first: raw-tools probes PATH for rtk, which can stall


def run_ban(name, data):
    """Run one ban as its own __main__ on this input; return (exit code, stderr)."""
    path = os.path.join(HERE, name)
    saved = sys.stdin, sys.stdout, sys.stderr, sys.argv
    err = io.StringIO()
    sys.stdin = io.TextIOWrapper(io.BytesIO(data), encoding="utf-8", errors="replace")  # Claude Code sends UTF-8
    sys.stdout, sys.stderr, sys.argv = io.StringIO(), err, [path]
    try:
        runpy.run_path(path, run_name="__main__")
        code = 0
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except BaseException:  # a crashed hook never blocked; its traceback still shows, as a failing hook's notice did
        code = 1
        err.write(traceback.format_exc())
    finally:
        sys.stdin, sys.stdout, sys.stderr, sys.argv = saved
    return code, err.getvalue()


def main(argv):
    data = sys.stdin.buffer.read()
    results = [run_ban(name, data) for name in BANS]
    blocks = [msg for code, msg in results if code == 2]
    if blocks:
        sys.stderr.write("".join(blocks))
        return 2
    sys.stderr.write("".join(msg for code, msg in results if code not in (0, 2)))
    sys.path.insert(0, HERE)  # -I leaves the script dir off sys.path
    sys.dont_write_bytecode = True  # no __pycache__ in the hooks folder (install.ps1 would copy it)
    import run_cli_hook
    sys.stdin = io.TextIOWrapper(io.BytesIO(data))  # run_cli_hook reads sys.stdin.buffer
    return run_cli_hook.main(argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
