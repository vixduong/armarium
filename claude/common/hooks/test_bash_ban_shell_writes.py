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
    # found by a pi review session, 2026-11-27: one wrapper or one quote was enough to pass
    "'cat' > f",
    "\"echo\" x > f",
    "(echo x > f)",
    "{ echo x > f; }",
    "sudo echo x > f",
    "nice -n 5 printf x > f",
    "if true; then echo x > f; fi",
    "true & echo x > f",
    "x=$(echo y > f)",
    "ls `echo y > f`",
    "echo \"it's\" > f; echo 'x'",          # an apostrophe inside double quotes is text
    "echo '<<X'\necho x > f",               # << inside quotes opens no heredoc
    "echo x \\\n> f",                       # backslash-newline joins the lines
    "bash -c \"echo x > f\"",
    "sh -c 'cd /tmp && printf x > f'",
    "eval 'echo x > f'",
    "bash <<EOF\necho x > f\nEOF",          # a heredoc fed to a shell is commands, not data
    "cat <<EOF | sh\necho x > f\nEOF",
    "echo 'sed -i s/a/b/ f' | bash",
    "touch /tmp/bash-raw-unlock-$PPID",      # the unlock file is the user's to create
    "ls > /tmp/bash-raw-unlock-1",
    "git diff --output=/tmp/bash-raw-unlock-1",
    "git init -q /tmp/bash-raw-unlock-1",
    "sed -n 'w /tmp/bash-raw-unlock-1' /dev/null",
    "python3 <<< \"open('f','w')\"",          # a here-string with no script file is the script
    "{ echo x; } > f",                        # the redirect sits on the group
    "for i in 1; do echo x; done>f",
    "if true; then echo x; fi>f",
    "(echo x; true) > f",
    "(echo x)>f",
    "case 1 in 1) echo x;; esac > f",
    "for i in 1 2; do echo $i; done > f",
    "if true; then printf a; fi >> f",
    "sudo -u root echo x > f",                # a wrapper option with a word for its value
    "env -u HOME printf x > f",
    "xargs -I {} echo {} > f",
    "touch /tmp/bash-raw-unl\\ock-$PPID",   # a backslash or a quote inside the name still names it
    "touch /tmp/bash-raw-'un'lock-1",
    "git -c alias.x='!touch /tmp/bash-raw-unlock-1' x",
    "echo \"$(date) > x\" >> log.txt",       # the redirect after a $( ) belongs to the outer command
    "echo \"## $(date)\" >> notes.md",
    # found by the security review of the lexer, 2026-11-27
    "# don't\necho hi > f",                 # an apostrophe in a comment opens no quote
    "echo $'a\\'' > f",                    # $'..' takes \' inside
    "echo hi > f; : " + "$(" * 1000,          # too deep to parse is blocked, not waved through
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
    "git commit -q -m \"$(cat <<'EOF'\nfix: say \"x\" > y, it's done\necho x > f\nEOF\n)\"",  # the usual commit form: quotes and > in the body are text
    "git commit -m \"it's > done; echo x > f\"",
    "echo \"a > b\"",
    "bash -c 'cd x && make check'",
    "bash run.sh",
    "sleep 5 & wait",
    "{ make check; } > /tmp/check.log 2>&1",
    "(make a; make b) > /tmp/build.log 2>&1",
    "echo start; { make check; } > /tmp/log 2>&1",   # the echo before the group is not in it
    "echo hi && for f in a b; do make $f; done > /tmp/log 2>&1",
    "python3 -I x.py <<< data",                      # a here-string beside a script file is its input
    "case $x in a) make;; esac > /tmp/case.log",
    "for f in a b; do make $f; done > /tmp/build.log",
    "sudo -u root make install",
    "make check 2>&1 &",
    "(cd x && make check > /tmp/check.log 2>&1)",
    "sudo make install",
    "git grep -n bash-raw-unlock",
    "grep -rn 'bash-raw-unlock' claude",
    "echo \"$(date) > x\"",
    "echo \"built $(git rev-parse --short HEAD)\" && make check > /tmp/check.log 2>&1",
    "ls # it's fine",
    "echo a#b > /dev/null",
    "echo $'a\\nb'",
    "echo ${#x} $# '#'",
    "ls -la /tmp/bash-raw-unlock-1",
    "echo \"$(date)\"",
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
    ("reviewer", "[[ x ]] > f"),               # the redirect after a test is still a redirect
    ("oracle", "[[ 1 ]] 2> f"),
    ("reviewer", "git diff --output=d.patch main"),
    ("reviewer", "git format-patch -1"),
    ("reviewer", "git archive -o x.tar HEAD"),
    ("reviewer", "git gc"),
    ("reviewer", "git stash"),
    ("reviewer", "git stash pop"),
    ("reviewer", "git apply x.patch"),
    ("reviewer", "git apply --check --apply a.diff"),   # --apply applies even after --check
    ("reviewer", "curl -sSo x https://example.com"),
    ("reviewer", "tar -C d -xzf a.tar"),
    ("reviewer", "tar --extract -f a.tar"),
    ("reviewer", "git tag --contains HEAD v9"),          # one name too many: that one is created
    ("reviewer", "git branch --sort=refname newb"),
    ("reviewer", "curl -o f https://example.com"),
    ("reviewer", "patch -p1 -i x.diff"),
    ("reviewer", "tar -xf a.tar"),
    ("reviewer", "git update-ref refs/heads/x HEAD"),
    ("reviewer", "git worktree add ../w main"),
    ("reviewer", "git branch -D old"),
    ("reviewer", "git tag v1"),
    ("reviewer", "git config user.name x"),
    ("oracle", "find . -name '*.pyc' -delete"),
    ("reviewer", "find . -name x -exec rm {} +"),
    ("reviewer", "ln -s a b"),
    ("reviewer", "dd if=a of=b"),
    ("reviewer", "ls | xargs rm"),
    ("reviewer", "chmod +x run.sh"),
    ("reviewer", "truncate -s 0 f"),
]
RO_ALLOW = [
    ("reviewer", "git show main:a.java | sed -n '1,80p'"),
    ("reviewer", "git -C repo grep -nE 'a>b' main -- src 2>/dev/null"),
    ("reviewer", "git diff --stat main..fix"),
    ("reviewer", "git -C repo log --oneline -3 && git -C repo branch --list"),
    ("worker", "git show main:a.java > .scratch/a.java"),
    ("reviewer", "[[ 3 > 2 ]] && echo yes"),
    ("reviewer", "[[ -n $a && $b > 1 ]] && git log -1"),
    ("reviewer", "if [[ \"$a\" > \"$b\" ]]; then git log -1; fi"),
    ("reviewer", "git branch --list"),
    ("reviewer", "git branch --sort=-committerdate"),
    ("reviewer", "git branch --format=%(refname)"),
    ("reviewer", "git tag --contains HEAD"),
    ("reviewer", "git stash list"),
    ("reviewer", "git stash show -p"),
    ("reviewer", "git apply --check x.patch"),
    ("reviewer", "python3 -I x.py <<< data"),
    ("reviewer", "curl -s https://example.com"),
    ("reviewer", "tar -tf a.tar"),
    ("reviewer", "git branch -a"),
    ("reviewer", "git tag -l"),
    ("reviewer", "git config --get user.name"),
    ("reviewer", "git remote -v"),
    ("reviewer", "find . -name '*.py' -newer x"),
    ("reviewer", "python3 -I claude/common/hooks/test_reviewer_gate.py"),
]

# Rewrites that must not change the hook's verdict: a blocked command stays blocked, an allowed one stays allowed.
# A change to the hook's patterns that opens one shows up here.
def variants(c):
    out = ["cd /tmp && " + c, "true; " + c, 'cat <<< "x"\n' + c]
    if " > " in c:
        out += [c.replace(" > ", " 1> ", 1), c.replace(" > ", " >| ", 1), c.replace(" > ", " >", 1)]
    return out

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
VARIANTS = [v for c in BLOCK for v in variants(c)]
for v in VARIANTS:
    if run(v) != 2: fails += 1; print("SHOULD BLOCK (variant):", repr(v))
for c in ALLOW:
    if run("cd /tmp && " + c) != 0: fails += 1; print("SHOULD ALLOW (variant):", repr("cd /tmp && " + c))
for a, c in RO_BLOCK:
    if run(c, a) != 2: fails += 1; print("SHOULD BLOCK for", a, repr(c))
for a, c in RO_ALLOW:
    if run(c, a) != 0: fails += 1; print("SHOULD ALLOW for", a, repr(c))
nb = subprocess.run([sys.executable, HOOK], input=json.dumps({"tool_name": "Read", "tool_input": {}}), capture_output=True, text=True).returncode
if nb != 0: fails += 1; print("non-Bash tool should pass")
# The user's unlock file (keyed on the hook's parent, this test) opens the write rules, but never the rule about the file itself.
unlock = os.path.join(os.environ.get("TEMP") or "/tmp" if os.name == "nt" else "/tmp", "bash-raw-unlock-%d" % os.getpid())
open(unlock, "w").close()
try:
    if run("echo x > f") != 0: fails += 1; print("unlocked: a write should pass")
    if run("touch " + unlock) != 2: fails += 1; print("unlocked: touching the unlock file should still be blocked")
    if run("echo x > f", "reviewer") != 2: fails += 1; print("unlocked: a read-only agent stays blocked")
finally:
    os.remove(unlock)
# The hook must never fall over: any other exit than 0 or 2 is a hook error, which Claude Code lets through, so a command
# that crashes the parser would pass the gate. Fixed seed, so a failure names a command that fails every time.
import random
rnd = random.Random(20261127)
PARTS = ["'", '"', "\\", "$(", ")", "(", "`", "<<", "<<<", ">", ">>", "|", "&", ";", "#", "\n", " ", "$'", "{", "}", "EOF", "echo", "cat", "bash", "-c", "f", "x"]
NASTY = ["$(" * 1000 + "echo x > f", '"$(' * 1000, "`" * 999, "'" * 5001, "\\", "echo x \\", "cat <<EOF\nnever closed", "((((" * 5000, "))))" * 5000,
         "echo \0 > f", "x" * 50000, "<<" * 5000, "$'\\", "bash -c " * 300 + "'echo x > f'"]
FUZZ = NASTY + ["".join(rnd.choice(PARTS) for _ in range(rnd.randint(1, 60))) for _ in range(150)]
for c in FUZZ:
    try:
        rc = subprocess.run([sys.executable, HOOK], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": c}}),
                            capture_output=True, text=True, timeout=10).returncode
    except subprocess.TimeoutExpired:
        rc = "timeout"
    if rc not in (0, 2): fails += 1; print("HOOK ERROR (exit %s) on:" % rc, repr(c[:120]))
print("FAILS", fails, "of", len(BLOCK) + 2 * len(ALLOW) + len(VARIANTS) + len(RO_BLOCK) + len(RO_ALLOW) + 4 + len(FUZZ))
sys.exit(1 if fails else 0)
