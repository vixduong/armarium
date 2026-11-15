"""Self-test for bash-ban-shell-writes: python3 -I ~/.claude/hooks/test_bash_ban_shell_writes.py"""
import json, os, subprocess, sys

HOOK = os.path.expanduser("~/.claude/hooks/bash-ban-shell-writes")

BLOCK = [
    "cat > notes.md <<'EOF'\nhello > world\nEOF",
    "cat <<EOF > out.txt\nx\nEOF",
    "cat >> log.md <<EOF\nx\nEOF",
    "printf '%s\\n' a > f.txt",
    "echo hi >> README.md",
    "cd /tmp && echo x > a.txt",
    "sed -i '' 's/a/b/' file.txt",
    "sed -Ei 's/a/b/' file.txt",
    "perl -pi -e 's/a/b/' f",
    "ls | tee out.txt",
    "tee -a f.log < input",
    "python3 - <<'EOF'\nopen('f','w').write('x')\nEOF",
    "python3 <<EOF\nprint(1)\nEOF",
    "python - < script.py",
    "FOO=1 echo x > f",
    "rtk proxy echo x > f",
    "tr a b <<EOF > f\nx\nEOF",
]
ALLOW = [
    "ls -la",
    "git commit -q -F - <<'EOF'\nfix: x > y\nEOF",
    "git commit -m \"use sed -i and echo x > f\"",
    "make check > /tmp/check.log 2>&1",
    "echo hi > /dev/null",
    "echo hi >&2",
    "echo hi 2>&1",
    "sed -n '1,5p' file.txt",
    "sed -E 's/i/j/' file.txt",
    "python3 -I script.py",
    "python3 -c 'print(1)'",
    "jq -r .x f.json | tee /dev/null",
    "cat file.txt",
    "claude -p \"$Q\" < /dev/null > out.jsonl 2>&1",
    "",
]

def run(cmd):
    p = subprocess.run([HOOK], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                       capture_output=True, text=True)
    return p.returncode

fails = 0
for c in BLOCK:
    if run(c) != 2: fails += 1; print("SHOULD BLOCK:", repr(c))
for c in ALLOW:
    if run(c) != 0: fails += 1; print("SHOULD ALLOW:", repr(c))
nb = subprocess.run([HOOK], input=json.dumps({"tool_name": "Read", "tool_input": {}}), capture_output=True, text=True).returncode
if nb != 0: fails += 1; print("non-Bash tool should pass")
print("FAILS", fails, "of", len(BLOCK) + len(ALLOW) + 1)
sys.exit(1 if fails else 0)
