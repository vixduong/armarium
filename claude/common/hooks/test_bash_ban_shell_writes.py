"""Self-test for bash-ban-shell-writes: python3 -I ~/.claude/hooks/test_bash_ban_shell_writes.py"""
import json, os, subprocess, sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bash-ban-shell-writes")  # the hook beside this test, not the installed one

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
    "echo x 1> out.py",
    "echo x >| out.py",
    "printf x &> out.py",
    "sed -n p src.py \\>| tee dst.py",  # an escaped > is a word, so this | is a pipe
    "cat <<< \"x\"\nsed -i 's/a/b/' f",  # a here-string opens no heredoc body
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
    "cat <<< \"x\"",
    "make check &> /tmp/check.log",
    "echo hi 1>&2",
    "",
]

# Read-only agents (agent_type in the hook input): no file written from Bash at all, log redirects included.
RO_BLOCK = [
    ("reviewer", "git show main:a.java > .scratch/a.java"),
    ("reviewer", "cd repo && git grep -n x main > 'C:/p/.scratch/g.txt' 2>&1"),
    ("oracle", "make check > /tmp/check.log 2>&1"),
    ("reviewer", "mkdir -p .scratch"),
    ("reviewer", "cd x && rm -f a.txt"),
    ("oracle", "mv a b"),
    ("reviewer", "cp a b"),
    ("reviewer", "touch /tmp/bash-raw-unlock-1"),
    ("reviewer", "git checkout fix/x"),
    ("reviewer", "git -C 'C:/p/repo' switch main"),
    ("oracle", "git -c core.x=1 commit -qam x"),
    ("reviewer", "cd repo; git stash"),
    ("reviewer", "rtk git reset --hard HEAD~1"),
    ("reviewer", "make check &> out.log"),
    ("oracle", "git log 2> err.txt"),
]
RO_ALLOW = [
    ("reviewer", "git show main:a.java | sed -n '1,80p'"),
    ("reviewer", "git -C repo grep -nE 'a>b' main -- src 2>/dev/null"),
    ("reviewer", "git diff --stat main..fix"),
    ("reviewer", "git -C repo log --oneline -3 && git -C repo branch --list"),
    ("worker", "git show main:a.java > .scratch/a.java"),
]

def run(cmd, agent=None):
    data = {"tool_name": "Bash", "tool_input": {"command": cmd}}
    if agent: data["agent_type"] = agent
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(data), capture_output=True, text=True)
    return p.returncode

fails = 0
for c in BLOCK:
    if run(c) != 2: fails += 1; print("SHOULD BLOCK:", repr(c))
for c in ALLOW:
    if run(c) != 0: fails += 1; print("SHOULD ALLOW:", repr(c))
for a, c in RO_BLOCK:
    if run(c, a) != 2: fails += 1; print("SHOULD BLOCK for", a, repr(c))
for a, c in RO_ALLOW:
    if run(c, a) != 0: fails += 1; print("SHOULD ALLOW for", a, repr(c))
nb = subprocess.run([sys.executable, HOOK], input=json.dumps({"tool_name": "Read", "tool_input": {}}), capture_output=True, text=True).returncode
if nb != 0: fails += 1; print("non-Bash tool should pass")
print("FAILS", fails, "of", len(BLOCK) + len(ALLOW) + len(RO_BLOCK) + len(RO_ALLOW) + 1)
sys.exit(1 if fails else 0)
