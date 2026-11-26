"""Self-test for reviewer-gate: python3 -I ~/.claude/hooks/test_reviewer_gate.py"""
import json, os, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reviewer-gate")  # the hook beside this test

def asst(*blocks): return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}
def text(t): return {"type": "text", "text": t}
def write(path, n): return {"type": "tool_use", "name": "Write", "input": {"file_path": path, "content": "\n".join("x" for _ in range(n))}}
def edit(path, old, new): return {"type": "tool_use", "name": "Edit", "input": {"file_path": path, "old_string": "\n".join("o" for _ in range(old)), "new_string": "\n".join("n" for _ in range(new))}}
def agent(t): return {"type": "tool_use", "name": "Agent", "input": {"subagent_type": t, "prompt": "review"}}
def skill(n): return {"type": "tool_use", "name": "Skill", "input": {"skill": n}}
def repl(code): return {"type": "tool_use", "name": "REPL", "input": {"code": code}}
def prompt(t, ts=None): return {"type": "user", "message": {"role": "user", "content": t}, **({"timestamp": ts} if ts else {})}
FLOW = text("Flow: UI page or component in a repo, Code flow + frontend gate")

def run(records, active=False, cwd=None):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    f.write("\n".join(json.dumps(r) for r in records)); f.close()
    p = subprocess.run([sys.executable, HOOK], input=json.dumps({"transcript_path": f.name, "stop_hook_active": active, "cwd": cwd}),
                       capture_output=True, text=True, encoding="utf-8")
    out = p.stdout.strip()
    return p.returncode, (json.loads(out) if out else {})

def blocked(r): return r[0] == 0 and r[1].get("decision") == "block"

CASES = [  # (name, records, active, expect_block)
    ("big write, no reviewer", [asst(FLOW, write("/r/index.html", 250)), asst(text("done"))], False, True),
    ("big write, reviewer after", [asst(FLOW, write("/r/index.html", 250)), asst(agent("reviewer")), asst(text("done"))], False, False),
    ("small write", [asst(FLOW, write("/r/index.html", 150)), asst(text("done"))], False, False),
    ("edits add up past 200", [asst(FLOW, edit("/r/a.js", 60, 60), edit("/r/a.js", 50, 50)), asst(text("done"))], False, True),
    ("more than 3 files", [asst(FLOW, *(write("/r/f%d.js" % i, 5) for i in range(4))), asst(text("done"))], False, True),
    ("markdown only", [asst(FLOW, write("/r/REPORT.md", 400)), asst(text("done"))], False, False),
    ("no Flow line this turn", [asst(write("/r/index.html", 250)), asst(text("done"))], False, False),
    ("stop hook already active", [asst(FLOW, write("/r/index.html", 250))], True, False),
    ("reviewer launched from REPL code", [asst(FLOW, write("/r/index.html", 250)), asst(repl("await tools.Agent({subagent_type: 'reviewer', prompt: 'x'})")), asst(text("done"))], False, False),
    ("code-review skill counts", [asst(FLOW, write("/r/index.html", 250)), asst(skill("code-review")), asst(text("done"))], False, False),
    ("other agent type does not count", [asst(FLOW, write("/r/index.html", 250)), asst(agent("worker")), asst(text("done"))], False, True),
    ("reviewer of an earlier turn does not count", [asst(agent("reviewer")), prompt("next"), asst(FLOW, write("/r/index.html", 250)), asst(text("done"))], False, True),
    ("writes of an earlier turn do not count", [asst(FLOW, write("/r/index.html", 250)), prompt("next"), asst(FLOW), asst(text("done"))], False, False),
]

fails = 0
for name, records, active, expect in CASES:
    r = run(records, active)
    if r[0] != 0 or blocked(r) != expect:
        fails += 1; print("FAIL %s: exit=%s out=%s" % (name, r[0], r[1]))
r = run([asst(FLOW, write("/r/index.html", 250))])
if blocked(r) and "250" not in r[1].get("reason", ""):
    fails += 1; print("FAIL reason names the line count: %s" % r[1])
if blocked(r) and "review-animations" not in r[1].get("reason", ""):
    fails += 1; print("FAIL reason names review-animations for animated diffs: %s" % r[1])

# Writes the transcript cannot see (REPL write()/edit(), subagents, Bash) are counted from git: files changed since the turn's prompt.
def git(repo, *a): subprocess.run(["git", "-C", repo, *a], capture_output=True, check=True)
def lines_file(path, n): open(path, "w").write("\n".join("y" for _ in range(n)) + "\n")
T0 = "2026-01-01T00:00:00.000Z"  # the turn's prompt; files touched now are newer
OLD = 1700000000  # 2023: an mtime before the prompt
with tempfile.TemporaryDirectory() as repo:
    git(repo, "init", "-q"); git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "base")
    REPL_TURN = [prompt("build it", T0), asst(FLOW, repl("await write('app.js', s)")), asst(text("done"))]
    lines_file(os.path.join(repo, "app.js"), 250)
    r = run(REPL_TURN, cwd=repo)
    if blocked(r) != True: fails += 1; print("FAIL REPL write seen by git: %s" % (r,))
    lines_file(os.path.join(repo, "notes.md"), 400); os.remove(os.path.join(repo, "app.js"))
    r = run(REPL_TURN, cwd=repo)
    if blocked(r): fails += 1; print("FAIL markdown seen by git does not count: %s" % (r,))
    lines_file(os.path.join(repo, "old.js"), 250); os.utime(os.path.join(repo, "old.js"), (OLD, OLD))
    r = run(REPL_TURN, cwd=repo)
    if blocked(r): fails += 1; print("FAIL file dirty from before the turn does not count: %s" % (r,))
    lines_file(os.path.join(repo, "w.js"), 150)
    r = run([prompt("go", T0), asst(FLOW, write(os.path.join(repo, "w.js"), 150)), asst(text("done"))], cwd=repo)
    if blocked(r): fails += 1; print("FAIL a Write git also sees is counted once (150, not 300): %s" % (r,))
    os.remove(os.path.join(repo, "w.js")); os.remove(os.path.join(repo, "old.js"))
    os.makedirs(os.path.join(repo, "src")); lines_file(os.path.join(repo, "src", "a.js"), 60)
    r = run([prompt("go", T0), asst(FLOW, write(os.path.join(repo, "src", "a.js"), 60)), asst(text("done"))], cwd=repo)
    if blocked(r): fails += 1; print("FAIL file in a subdirectory counted once: %s" % (r,))
    open(os.path.join(repo, "shot.png"), "wb").write(b"\x89PNG\0" + b"\n" * 300)
    r = run(REPL_TURN, cwd=repo)
    if blocked(r): fails += 1; print("FAIL untracked binary does not count: %s" % (r,))
    os.remove(os.path.join(repo, "shot.png"))
    outside = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False); outside.write("z\n" * 300); outside.close()
    try:
        os.symlink(outside.name, os.path.join(repo, "link.js"))
    except OSError as e:
        if getattr(e, "winerror", None) != 1314: raise
        print("skip untracked symlink: Windows allows symlinks only with Developer Mode or elevated")
    else:
        r = run(REPL_TURN, cwd=repo)
        if blocked(r): fails += 1; print("FAIL untracked symlink is not followed: %s" % (r,))
        os.remove(os.path.join(repo, "link.js"))
    os.remove(outside.name)
    lines_file(os.path.join(repo, "t.js"), 10); git(repo, "add", "t.js")
    git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "t")
    lines_file(os.path.join(repo, "t.js"), 230)
    r = run(REPL_TURN, cwd=repo)
    if not blocked(r): fails += 1; print("FAIL tracked file edited this turn counts via numstat: %s" % (r,))
# Step 8: a security-only reviewer stands in for `security-review` only when origin/HEAD does not resolve in the cwd.
def sec_agent(): return {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "reviewer", "prompt": "SECURITY-ONLY review of the diff"}}
SEC_REPL = repl("await tools.Agent({subagent_type: 'reviewer', prompt: 'SECURITY-ONLY review of x.diff: authorization, IDOR'})")
def general(p): return {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "reviewer", "prompt": p}}
with tempfile.TemporaryDirectory() as remote, tempfile.TemporaryDirectory() as plain:
    for repo in (remote, plain):
        git(repo, "init", "-q"); git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "base")
    git(remote, "update-ref", "refs/remotes/origin/main", "HEAD"); git(remote, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
    SEC_CASES = [  # (name, records, cwd, active, expect_block)
        ("security-only reviewer although origin/HEAD resolves", [asst(sec_agent()), asst(text("done"))], remote, False, True),
        ("security-only reviewer from REPL code", [asst(SEC_REPL), asst(text("done"))], remote, False, True),
        ("security-only reviewer, no origin/HEAD", [asst(sec_agent()), asst(text("done"))], plain, False, False),
        ("security-review skill also called", [asst(sec_agent(), skill("security-review")), asst(text("done"))], remote, False, False),
        ("security-review called from REPL code", [asst(sec_agent(), repl("await tools.Skill({skill: 'security-review'})")), asst(text("done"))], remote, False, False),
        ("general reviewer only", [asst(agent("reviewer")), asst(text("done"))], remote, False, False),
        ("general reviewer prompt mentions a security review", [asst(general("Review x.diff; a separate security review follows")), asst(text("done"))], remote, False, False),
        ("general reviewer from REPL mentions a security review", [asst(repl("await tools.Agent({subagent_type: 'reviewer', prompt: 'no security review needed'})")), asst(text("done"))], remote, False, False),
        ("stop hook already active", [asst(sec_agent())], remote, True, False),
        ("security reviewer of an earlier turn", [asst(sec_agent()), prompt("next"), asst(text("done"))], remote, False, False),
    ]
    for name, records, cwd, active, expect in SEC_CASES:
        r = run(records, active, cwd=cwd)
        if r[0] != 0 or blocked(r) != expect:
            fails += 1; print("FAIL %s: exit=%s out=%s" % (name, r[0], r[1]))
        elif expect and "`security-review`" not in r[1].get("reason", ""):
            fails += 1; print("FAIL %s: reason should name security-review: %s" % (name, r[1]))
LIST_PROMPT = {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "next"}, {"type": "image", "source": {}}]}}
r = run([asst(FLOW, write("/r/index.html", 250)), LIST_PROMPT, asst(FLOW), asst(text("done"))])
if blocked(r): fails += 1; print("FAIL a prompt with an image starts a new turn: %s" % (r,))
r = run(REPL_TURN, cwd="/nonexistent-dir")
if blocked(r) or r[0] != 0: fails += 1; print("FAIL cwd that is not a repo: %s" % (r,))
# Windows starts a bare program name from the cwd (the user's project) before PATH; PATH=. gives the same lookup here.
if os.name != "nt":
    for name, records in (("change count", REPL_TURN), ("origin/HEAD check", [prompt("go", T0), asst(sec_agent()), asst(text("done"))])):
        with tempfile.TemporaryDirectory() as proj:
            with open(os.path.join(proj, "git"), "w") as f: f.write("#!/bin/sh\n: > ran\n")
            os.chmod(os.path.join(proj, "git"), 0o755)
            t = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
            t.write("\n".join(json.dumps(x) for x in records)); t.close()
            subprocess.run([sys.executable, HOOK], input=json.dumps({"transcript_path": t.name, "cwd": proj}), capture_output=True,
                           text=True, cwd=proj, env=dict(os.environ, PATH="."))
            if os.path.exists(os.path.join(proj, "ran")): fails += 1; print("FAIL %s ran a git from the cwd" % name)
print("ok" if not fails else "%d failed" % fails)
sys.exit(1 if fails else 0)
