#!/usr/bin/env python3
# PreToolUse Bash/PowerShell gate, Windows (Python port of bash-ban-raw-tools.ps1, whose PowerShell start cost ~860 ms a call).
# Blocks a command whose first word is cat/head/tail/find/grep/rg/wc, or Get-Content/gc/type/Select-String/sls/findstr
# (type only in PowerShell: in Bash it is a builtin). rtk wrappers pass. When rtk resolves, readers pass too: the rtk hook
# rewrites them. A '| head'/'| tail' after a reader always blocks. Matching is case-insensitive, as PowerShell's was.
# Escape hatch: %TEMP%\bash-raw-unlock-<parent pid>, valid 10 min. Fail-open: any parse/IO error lets the call through.
# Self-test: python -I test_bash_ban_raw_tools.py
import json, os, re, sys, time

PIPE_MSG = """BLOCKED: '| tail'/'| head' pipeline. Output truncation not allowed - raw output still floods context before trim.

REPLACE WITH mcp__plugin_context-mode_context-mode__ctx_execute:
  language: "shell", code: "<the same pipeline>"

Sandbox keeps the full output out of context; print only the answer.
For ONE short command (<20 lines) drop the pipe - just run it raw."""

MSGS = [
    (r"^(cat|head|tail|Get-Content|gc|type)$", "BLOCKED '{0}'. Use the Read tool (absolute path + offset/limit), or ctx_execute(language:'shell') for big files."),
    (r"^find$", "BLOCKED 'find'. Use the Glob tool (pattern='**/...') if listed, else ctx_execute(language:'shell')."),
    (r"^(grep|rg|Select-String|sls|findstr)$", "BLOCKED '{0}'. Use the Grep tool (pattern, glob, output_mode) if listed, else ctx_execute(language:'shell')."),
    (r"^wc$", "BLOCKED 'wc'. If you need line count, Read the file (line count is visible) or pipe via 'rtk wc'."),
]


def main():
    p = json.loads(sys.stdin.buffer.read())  # bytes: UTF-8, not the ANSI code page
    tool = str(p.get("tool_name") or "").lower()
    if tool not in ("bash", "powershell"):
        return 0

    cmd = str((p.get("tool_input") or {}).get("command") or "")
    first = re.split(r"\s+", cmd.lstrip())[0]
    # The unlock file is the user's to create, from a terminal of their own: a command that names it (quotes, backslashes
    # and PowerShell backticks inside the name aside) may look at it and nothing else. Holds while unlocked too.
    # shortcut: a name built from variables or a wildcard gets past, as in bash-ban-shell-writes.
    looks = re.match(r"^(Get-ChildItem|gci|ls|dir|Test-Path|Get-Item|gi|Select-String|sls|findstr|grep|rg|stat)$", first, re.I) or re.match(
        r"^\s*git\s+(grep|log|show|blame)\b(?!.*--output)", cmd, re.I | re.S)
    if "bash-raw-unlock" in re.sub(r"""['"`^]""", "", cmd) and (not looks or re.search(r"[>|;&\n(){}]", cmd)):  # one plain command, nothing nested or chained
        sys.stderr.write("BLOCKED: this command names the unlock file. Only the user creates it, from a terminal of their own. "
                         "Ask the user in your reply if the block is in the way.\n")
        return 2

    # Unlock is per session and absent from the block messages: it is for the user.
    # Expires after 10 min; a future mtime (clock skew, forged) counts as expired.
    temp = os.environ.get("TEMP")
    if temp:
        unlock = os.path.join(temp, "bash-raw-unlock-%d" % os.getppid())
        try:
            age = time.time() - os.stat(unlock).st_mtime
            if os.path.isfile(unlock) and 0 <= age < 600:  # a folder of that name is no unlock
                return 0
            os.remove(unlock)
        except OSError:
            pass

    if first.lower() == "rtk":  # rtk wraps git/cargo/pytest/docker/etc.
        return 0

    typ = "|type" if tool == "powershell" else ""
    readers = "cat|head|tail|find|grep|rg|wc|Get-Content|gc|Select-String|sls|findstr" + typ

    # A truncation pipe after a file reader still floods context before the trim.
    if re.search(r"\|\s*(tail|head)(?![-\w])", cmd, re.I) and re.match(
            r"^(cat|grep|rg|find|Get-Content|gc|Select-String|sls|findstr%s)$" % typ, first, re.I):
        sys.stderr.write(PIPE_MSG + "\n")
        return 2

    if not re.match(r"^(%s)$" % readers, first, re.I):
        return 0

    # The rtk PreToolUse hook rewrites these into compact `rtk ...` forms, so blocking here only costs a turn.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # -I leaves the script dir off sys.path
    sys.dont_write_bytecode = True  # no __pycache__ in the hooks folder (install.ps1 would copy it)
    from run_cli_hook import resolve
    if resolve("rtk"):
        return 0

    for pat, msg in MSGS:
        if re.match(pat, first, re.I):
            sys.stderr.write(msg.format(first) + "\n")
            return 2
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception:
        code = 0
    sys.exit(code)
