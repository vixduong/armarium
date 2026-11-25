#!/usr/bin/env python3
# Hook shim, Windows (Python port of hooks/run-cli-hook for the per-call hot path: rtk hook claude). Resolve a CLI by name,
# then run it with stdin and the remaining args. A missing binary is not an error: exit 0 and let the tool call through.
#   python run_cli_hook.py <bin> [args...]   run <bin>, passing stdin, stdout, stderr and the exit code through
#   python run_cli_hook.py --which <bin>     print the resolved path, exit 1 if unresolvable
# cbm_session_reminder.py imports resolve() from here. Self-test: python -I test_bash_ban_raw_tools.py
import os, subprocess, sys


def resolve(name):
    # Explicit override wins: CCT_RTK_BIN, CCT_CODEBASE_MEMORY_MCP_BIN, ...
    o = os.environ.get("CCT_" + name.upper().replace(".", "_").replace("-", "_") + "_BIN")
    if o and os.path.isfile(o):
        return o
    # PATH only, like Get-Command: shutil.which on Windows also searches the cwd, and the cwd is the user's project
    exts = [e for e in os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";") if e] if os.name == "nt" else [""]
    for d in os.environ.get("PATH", "").split(os.pathsep):
        d = d.strip('"')  # Windows PATH entries may be quoted
        if d and os.path.isabs(d):
            for e in exts:
                p = os.path.join(d, name + e)
                if os.path.isfile(p) and (os.name == "nt" or os.access(p, os.X_OK)):
                    return p
    # Dirs a hook's PATH may lack: user-level installers and package managers
    u, a, l = (os.environ.get(k, "") for k in ("USERPROFILE", "APPDATA", "LOCALAPPDATA"))
    dirs = [os.path.join(u, s) for s in (r".local\bin", r".cargo\bin", r".bun\bin", r".volta\bin") if u]
    dirs += [os.path.join(a, "npm")] if a else []
    dirs += [os.path.join(u, r"scoop\shims")] if u else []
    dirs += [os.path.join(l, r"Microsoft\WinGet\Links"), os.path.join(l, "Programs", name)] if l else []
    try:
        import site
        dirs.append(os.path.join(site.getuserbase(), "Scripts"))  # pip install --user
    except Exception:
        pass
    for d in dirs:
        for e in (".exe", ".cmd", ".bat"):
            if os.path.isfile(os.path.join(d, name + e)):
                return os.path.join(d, name + e)
    return None


def main(argv):
    which = bool(argv) and argv[0] == "--which"
    rest = argv[1:] if which else argv
    if not rest:
        return 1 if which else 0
    b = resolve(rest[0])
    if not b:
        return 1 if which else 0
    if which:
        print(b)
        return 0
    data = sys.stdin.buffer.read()  # bytes: no code-page decoding on the way through
    return subprocess.run([b] + rest[1:], input=data).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
