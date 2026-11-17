"""Self-test for flow-skill-check: python3 -I ~/.claude/hooks/test_flow_skill_check.py
Uses the real skills in ~/.claude/skills (tdd, lean-build)."""
import json, os, subprocess, sys, tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow-skill-check")  # the hook beside this test, not the installed one

def asst(*blocks):
    return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}
def text(t): return {"type": "text", "text": t}
def skill(n): return {"type": "tool_use", "name": "Skill", "input": {"skill": n}}
def repl(code): return {"type": "tool_use", "name": "REPL", "input": {"code": code}}
FLOW = text("Flow: Code flow (feature track: `lean-build` + `tdd`; spec is the contract, `/implement`)")

def run(records, active=False, path=None):
    if path is None:
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        f.write("\n".join(json.dumps(r) for r in records)); f.close(); path = f.name
    p = subprocess.run([sys.executable, HOOK], input=json.dumps({"transcript_path": path, "stop_hook_active": active}),
                       capture_output=True, text=True, encoding="utf-8")
    out = p.stdout.strip()
    return p.returncode, (json.loads(out) if out else {})

def blocked(r): return r[0] == 0 and r[1].get("decision") == "block"

CASES = [  # (name, records, active, expect_block)
    ("both called", [asst(FLOW, skill("lean-build"), skill("tdd")), asst(text("done"))], False, False),
    ("none called", [asst(FLOW), asst(text("done"))], False, True),
    ("one missing", [asst(FLOW, skill("lean-build")), asst(text("done"))], False, True),
    ("called in REPL code", [asst(FLOW, repl("await tools.Skill({skill: 'lean-build'}); await tools.Skill({skill:\"tdd\"})")), asst(text("done"))], False, False),
    ("called earlier in session", [asst(skill("tdd"), skill("lean-build")), asst(FLOW), asst(text("done"))], False, False),
    ("listed as x in the last reply", [asst(FLOW), asst(text("- ✗ `lean-build` and `tdd` not called: no new code"))], False, False),
    ("listed as x in an earlier reply", [asst(FLOW), asst(text("- ✗ `lean-build` and `tdd` not called: no new code")), asst(text("next task done"))], False, False),
    ("stop hook already active", [asst(FLOW)], True, False),
    ("no Flow line", [asst(text("hi"))], False, False),
    ("Flow repeated later without names", [asst(FLOW), asst(text("Flow: Code flow (feature track, spec as contract)"))], False, True),
    ("subagent records ignored", [asst(FLOW), dict(asst(skill("lean-build"), skill("tdd")), isSidechain=True)], False, True),
]
fails = 0
for name, recs, active, want in CASES:
    r = run(recs, active)
    if blocked(r) != want: fails += 1; print("FAIL:", name, r)
    if name == "none called" and blocked(r) and "`lean-build`" not in r[1].get("reason", ""): fails += 1; print("reason should name lean-build:", r)
    if name == "one missing" and blocked(r) and ("`tdd`" not in r[1]["reason"] or "`lean-build`" in r[1]["reason"]): fails += 1; print("reason should name only tdd:", r)
miss = run([], path="C:/no/such/file.jsonl")
if miss[0] != 0 or blocked(miss): fails += 1; print("missing transcript should pass")
print("FAILS", fails, "of", len(CASES) + 1)
sys.exit(1 if fails else 0)
