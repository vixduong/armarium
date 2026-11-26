"""Self-test for flow-skill-check: python3 -I ~/.claude/hooks/test_flow_skill_check.py
Runs the hook under a temporary HOME whose ~/.claude/skills holds only tdd and lean-build."""
import atexit, json, os, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")  # failure lines quote ✓ and ✗; a Windows console is cp1252

FAKE_HOME = tempfile.mkdtemp()
atexit.register(shutil.rmtree, FAKE_HOME, True)
for n in ("tdd", "lean-build"):
    os.makedirs(os.path.join(FAKE_HOME, ".claude", "skills", n)); open(os.path.join(FAKE_HOME, ".claude", "skills", n, "SKILL.md"), "w").close()
ENV = dict(os.environ, HOME=FAKE_HOME, USERPROFILE=FAKE_HOME)  # expanduser reads HOME on Unix, USERPROFILE on Windows
HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow-skill-check")  # the hook beside this test, not the installed one

def asst(*blocks):
    return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}
def text(t): return {"type": "text", "text": t}
def skill(n): return {"type": "tool_use", "name": "Skill", "input": {"skill": n}}
def repl(code): return {"type": "tool_use", "name": "REPL", "input": {"code": code}}
def slash(n): return {"type": "user", "message": {"role": "user", "content": "<command-message>%s</command-message>\n<command-name>/%s</command-name>" % (n, n)}}
def prompt(t): return {"type": "user", "message": {"role": "user", "content": t}}
def image_prompt(t): return {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": t}, {"type": "image", "source": {}}]}}
def tool_result(t): return {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": t}]}}
FLOW = text("Flow: Code flow (feature track: `lean-build` + `tdd`; spec is the contract, `/implement`)")
DONE = text("- ✓ gate green: bin/check")  # a final reply with an Exit list

def run(records, active=False, path=None, last=None, cwd=None):
    if path is None:
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        f.write("\n".join(json.dumps(r) for r in records)); f.close(); path = f.name
    stdin = {"transcript_path": path, "stop_hook_active": active, "cwd": cwd}
    if last is not None:
        stdin["last_assistant_message"] = last  # the turn's final reply, which the transcript may not hold yet
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(stdin, ensure_ascii=False),  # raw UTF-8, as Claude Code sends it
                       capture_output=True, text=True, encoding="utf-8", env=ENV)
    out = p.stdout.strip()
    return p.returncode, (json.loads(out) if out else {})

def blocked(r): return r[0] == 0 and r[1].get("decision") == "block"

CASES = [  # (name, records, active, expect_block)
    ("both called", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(DONE)], False, False),
    ("none called", [asst(FLOW), asst(text("done"))], False, True),
    ("one missing", [asst(FLOW, skill("lean-build")), asst(text("done"))], False, True),
    ("called in REPL code", [asst(FLOW, repl("await tools.Skill({skill: 'lean-build'}); await tools.Skill({skill:\"tdd\"})")), asst(DONE)], False, False),
    ("called before the Flow line does not count", [asst(skill("tdd"), skill("lean-build")), asst(FLOW), asst(text("done"))], False, True),
    ("called for an earlier task, Flow names it again", [asst(FLOW), asst(skill("tdd"), skill("lean-build")), asst(text("done")), asst(FLOW), asst(text("done"))], False, True),
    ("called after the Flow line", [asst(FLOW), asst(skill("tdd")), asst(skill("lean-build")), asst(DONE)], False, False),
    ("listed as x in the last reply", [asst(FLOW), asst(text("- ✗ `lean-build` and `tdd` not called: no new code"))], False, False),
    ("listed as x in an earlier reply", [asst(FLOW), asst(text("- ✗ `lean-build` and `tdd` not called: no new code")), asst(DONE)], False, False),
    ("stop hook already active", [asst(FLOW)], True, False),
    ("no Flow line", [asst(text("hi"))], False, False),
    ("Flow repeated later without names", [asst(FLOW), asst(text("Flow: Code flow (feature track, spec as contract)"))], False, True),
    ("started by slash command", [slash("lean-build"), slash("tdd"), asst(FLOW), asst(DONE)], False, False),
    ("slash command of an earlier task does not count", [slash("lean-build"), slash("tdd"), asst(FLOW), asst(text("done")), asst(FLOW), asst(text("done"))], False, True),
    ("an earlier task's Flow line does not block a later turn", [asst(FLOW), prompt("next question"), asst(text("answer"))], False, False),
    ("a prompt with an image starts a new turn", [asst(FLOW), image_prompt("what is this?"), asst(text("answer"))], False, False),
    ("list-content hook feedback is not a new turn", [asst(FLOW), dict(image_prompt("x"), isMeta=True), asst(text("ok"))], False, True),
    ("list-content task notification is not a new turn", [asst(FLOW), dict(image_prompt("x"), origin={"kind": "task-notification"}), asst(text("ok"))], False, True),
    ("hook feedback is not a new turn", [asst(FLOW), dict(prompt("Stop hook feedback: ..."), isMeta=True), asst(text("ok"))], False, True),
    ("x before the Flow line does not count", [asst(text("- ✗ `lean-build` and `tdd` not called")), asst(FLOW), asst(text("done"))], False, True),
    ("command tag quoted in a task notification", [asst(FLOW), {"type": "user", "origin": {"kind": "task-notification"}, "message": {"role": "user", "content": "<task-notification><result>quotes <command-name>/lean-build</command-name> and <command-name>/tdd</command-name></result></task-notification>"}}], False, True),
    ("command tag inside a tool result", [asst(FLOW), tool_result("<command-name>/lean-build</command-name> <command-name>/tdd</command-name>")], False, True),
    ("subagent records ignored", [asst(FLOW), dict(asst(skill("lean-build"), skill("tdd")), isSidechain=True)], False, True),
    ("final reply has no Exit list", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("done"))], False, True),
    ("Exit list only in an earlier reply", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(DONE), asst(text("one more note"))], False, True),
    ("a mark on the Flow line is not an Exit list", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("Flow: Writing (✓ later)"))], False, True),
    ("no Exit needed in a turn without a Flow line", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(DONE), prompt("thanks"), asst(text("ok"))], False, False),
    ("a ✓ item names an exception", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("- ✓ test red before code (trừ trigger và SQL)"))], False, True),
    ("a ✓ item's sub-bullet names an exception", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("- ✓ red before code:\n  - pure tests red first\n  - but the SQL went red after the code"))], False, True),
    ("a ✗ item may name an exception", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("- ✓ gate green: bin/check\n- ✗ red before code: except the SQL\n  - but planned"))], False, False),
    ("'only' is evidence, not an exception", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("- ✓ only the asked op ran: git push"))], False, False),
    ("an exclusions item may say except", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("- ✓ exclusions stated: all rows except refunds\n- ✓ loại trừ hoàn tiền đã nêu"))], False, False),
    ("'chưa' in a count is not an exception", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("- ✓ 0 P0/P1 chưa xử lý"))], False, False),
    ("prose that mentions ✓ is not an Exit item", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("- Fix 2: the hook blocks a ✓ item that says but\n- ✓ gate green: bin/check"))], False, False),
    ("a bold ✓ item still counts", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("- **✓ red first**, but not the SQL"))], False, True),
    ("a keyword inside backticks is code", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("- ✓ red: the test for `except OSError` failed first"))], False, False),
]
fails = 0
for name, recs, active, want in CASES:
    r = run(recs, active)
    if blocked(r) != want: fails += 1; print("FAIL:", name, r)
    if name == "none called" and blocked(r) and "`lean-build`" not in r[1].get("reason", ""): fails += 1; print("reason should name lean-build:", r)
    if name == "none called" and blocked(r) and "Done-when" not in r[1].get("reason", ""): fails += 1; print("one block should carry both reasons:", r)
    if name == "final reply has no Exit list" and blocked(r) and "Done-when" not in r[1].get("reason", ""): fails += 1; print("reason should ask for the Done-when list:", r)
    if name == "one missing" and blocked(r) and ("`tdd`" not in r[1]["reason"] or "`lean-build`" in r[1]["reason"]): fails += 1; print("reason should name only tdd:", r)
# the final reply is already in the transcript too: it must not count twice
r = run([slash("lean-build"), slash("tdd"), asst(text(FLOW["text"] + "\n" + DONE["text"]))], last=FLOW["text"] + "\n" + DONE["text"])
if blocked(r): fails += 1; print("FAIL: a reply already in the transcript counted twice", r)
# the final reply arrives on stdin before it reaches the transcript
r = run([asst(FLOW)], last="- ✗ `lean-build` and `tdd` not called: no new code")
if blocked(r): fails += 1; print("FAIL: x in last_assistant_message should clear", r)
r = run([asst(text("hi"))], last="Flow: Code flow (`lean-build` + `tdd`)")
if not blocked(r): fails += 1; print("FAIL: Flow line in last_assistant_message should count", r)
miss = run([], path="C:/no/such/file.jsonl")
if miss[0] != 0 or blocked(miss): fails += 1; print("missing transcript should pass")
# the final reply's Exit list arrives on stdin before it reaches the transcript
r = run([asst(FLOW, skill("lean-build"), skill("tdd"))], last=DONE["text"])
if blocked(r): fails += 1; print("FAIL: Exit list in last_assistant_message should clear", r)
# stdin wins over the transcript: an Exit list earlier in the transcript does not clear a final reply without one
r = run([asst(FLOW, skill("lean-build"), skill("tdd")), asst(DONE)], last="done")
if not blocked(r): fails += 1; print("FAIL: last_assistant_message without an Exit list should block", r)
r = run([asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("- ✓ red first, nhưng SQL đỏ sau code"))])
if blocked(r) and "exception" not in r[1].get("reason", ""): fails += 1; print("FAIL reason should name the exception rule:", r)

# UI files changed this turn (by main, a subagent or a commit) need the UI row on the Flow line: rules/frontend.md paths
def git(repo, *a): subprocess.run(["git", "-C", repo, *a], capture_output=True, check=True)
T0 = "2026-01-01T00:00:00.000Z"  # the turn's prompt; files touched now are newer
def turn(flow): return [dict(prompt("build the page"), timestamp=T0), asst(text(flow), skill("lean-build"), skill("tdd")), asst(DONE)]
CODE_FLOW = "Flow: Code flow (`lean-build` + `tdd`)"
with tempfile.TemporaryDirectory() as repo:
    git(repo, "init", "-q"); git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "base")
    os.makedirs(os.path.join(repo, "src")); open(os.path.join(repo, "src", "page.tsx"), "w").write("x\n")
    git(repo, "add", "."); git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "page")
    UI_CASES = [  # (name, flow, expect_block)
        ("a UI file committed this turn, Flow without UI", CODE_FLOW, True),
        ("a UI file committed this turn, Flow names the UI row", "Flow: Code flow + UI row (`lean-build` + `tdd`)", False),
    ]
    for name, flow, want in UI_CASES:
        r = run(turn(flow), cwd=repo)
        if blocked(r) != want: fails += 1; print("FAIL", name, r)
        if want and blocked(r) and "UI" not in r[1].get("reason", ""): fails += 1; print("FAIL reason should ask for the UI row:", r)
    r = run(turn("Flow: Git (commit the page)"), cwd=repo)
    if blocked(r): fails += 1; print("FAIL a Git-row turn commits UI files without being UI work", r)
    r = run(turn(CODE_FLOW)[:1] + [asst(text("answer"))], cwd=repo)
    if blocked(r): fails += 1; print("FAIL no Flow line, no UI check", r)
with tempfile.TemporaryDirectory() as repo:
    git(repo, "init", "-q"); git(repo, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "base")
    open(os.path.join(repo, "app.py"), "w").write("x\n")
    r = run(turn(CODE_FLOW), cwd=repo)
    if blocked(r): fails += 1; print("FAIL a non-UI file does not need the UI row", r)
    open(os.path.join(repo, "style.css"), "w").write("x\n")
    r = run(turn(CODE_FLOW), cwd=repo)
    if not blocked(r): fails += 1; print("FAIL an uncommitted UI file changed this turn counts", r)
    os.utime(os.path.join(repo, "style.css"), (1700000000, 1700000000))
    r = run(turn(CODE_FLOW), cwd=repo)
    if blocked(r): fails += 1; print("FAIL a UI file dirty from before the turn does not count", r)
r = run(turn(CODE_FLOW), cwd="/nonexistent-dir")
if blocked(r): fails += 1; print("FAIL cwd that is not a repo", r)
print("FAILS", fails, "of", len(CASES) + 14)
sys.exit(1 if fails else 0)
