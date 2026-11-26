"""Self-test for pi/armarium-pi/index.ts: python3 -I pi/test_armarium_pi.py
Drives the extension's handlers with a fake pi in node (needs node >= 22.18 for .ts); never touches ~/.pi."""
import json, os, pathlib, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EXT = os.path.join(HERE, "armarium-pi", "index.ts")
if not shutil.which("node"):
    print("skip: node not on PATH"); sys.exit(0)

# argv[2] = JSON list of steps, run in order against one extension instance; prints one result per step.
#   {"ev": "start", "type": "user"|"custom", "argv": [...], "opts": {...}} -> contextFiles after before_agent_start
#   {"ev": "msg", "text": "...", "thinking": "...", "calls": n}            -> null (assistant message_end with n tool calls)
#   {"ev": "settle", "outcome": "completed"|"aborted"|"error", "entries": [...]} -> agent_before_settle result
#   {"ev": "tool", "tool": "bash", "input": {...}, "ui": bool, "yes": bool} -> tool_call result
#   {"ev": "session_start", "file": str|null, "id": str} / {"ev": "session_shutdown"} -> pi-subagents required-extension registry
#   {"ev": "preset", "key": str, "entries": [...]}                    -> registry (another host registered first)
DRIVER = """
const ext = (await import(process.argv[1])).default;
const handlers = {}, second = {};
ext({ on: (name, fn) => { handlers[name] = fn; } });
ext({ on: (name, fn) => { second[name] = fn; } });  // a second copy in the same session; steps with "twice" reach both, in pi's order
let step = 0;
const out = [];
const REG = Symbol.for("pi-subagents.required-child-extensions.v1");
const reg = () => Object.fromEntries(globalThis[REG]?.bySession ?? []);
const presets = {};
let session = { getSessionFile: () => undefined, getSessionId: () => "none" };
for (const s of JSON.parse(process.argv[2])) {
  const copies = s.twice ? [handlers, second] : [handlers];
  step++;
  if (s.ev === "preset") {
    globalThis[REG] ??= { version: 1, bySession: new Map() };
    presets[s.key] = Object.freeze(s.entries);
    globalThis[REG].bySession.set(s.key, presets[s.key]);
    out.push(reg());
  } else if (s.ev === "same") {
    out.push(globalThis[REG]?.bySession.get(s.key) === presets[s.key]);
  } else if (s.ev === "session_start" || s.ev === "session_shutdown") {
    if (s.ev === "session_start") session = { getSessionFile: () => s.file ?? undefined, getSessionId: () => s.id };
    await handlers[s.ev]({ type: s.ev, reason: "startup" }, { sessionManager: session });
    out.push(reg());
  } else if (s.ev === "start") {
    const argv = process.argv;
    process.argv = [...argv, ...(s.argv ?? [])];
    const event = { messageType: s.type ?? "user", systemPrompt: "", systemPromptOptions: { appendSystemPrompt: "", ...s.opts,
      contextFiles: [{ path: "/proj/AGENTS.md", content: "project rules" }] } };
    for (const h of copies) await h.before_agent_start(event, { sessionManager: session });
    if (s.reg) { out.push(reg()); process.argv = argv; continue; }
    process.argv = argv;
    out.push(event.systemPromptOptions.contextFiles);
  } else if (s.ev === "settle") {
    let entries = s.entries ?? [], go = false, any = false;  // pi's emitBoundary: each handler sees what the ones before it returned
    for (const h of copies) {
      const r = await h.agent_before_settle?.({ type: "agent_before_settle", entries, continue: go,
        outcome: s.outcome ?? "completed", context: {} }, { sessionManager: session });
      if (r) any = true;
      if (r?.entries !== undefined) entries = r.entries;
      if (r?.continue !== undefined) go = r.continue;
    }
    out.push(any ? { entries, continue: go } : null);
  } else if (s.ev === "msg") {
    const content = [];
    if (s.thinking) content.push({ type: "thinking", thinking: s.thinking });
    if (s.text) content.push({ type: "text", text: s.text });
    for (let i = 0; i < (s.calls ?? 0); i++) content.push({ type: "toolCall", id: "t" + i, name: "read", arguments: {} });
    for (const h of copies) await h.message_end({ type: "message_end", message: { role: "assistant", content } }, {});
    out.push(null);
  } else {
    const asked = [];
    const ctx = { hasUI: !!s.ui, signal: undefined, ui: { confirm: async (t, m, o) => { asked.push({ m, timeout: o?.timeout }); return !!s.yes; } } };
    ctx.sessionManager = session;
    let r;  // pi's emitToolCall: the first block ends the chain
    for (const h of copies) {
      r = (await h.tool_call({ type: "tool_call", toolName: s.tool, toolCallId: "t" + step, input: s.input,
        ...(s.parent ? { parentToolCallId: s.parent } : {}) }, ctx)) ?? r;
      if (r?.block) break;
    }
    out.push({ result: r ?? null, asked });
  }
}
console.log(JSON.stringify(out));
"""

fails = total = 0

def check(label, ok, detail=""):
    global fails, total
    total += 1
    fails += not ok
    print(("ok   " if ok else "FAIL ") + label, "" if ok else detail)

def run(steps, path=None):
    """path: the PATH the extension sees (node itself is started by full path)."""
    p = subprocess.run([shutil.which("node"), "--no-warnings", "--input-type=module", "-e", DRIVER, pathlib.Path(EXT).as_uri(), json.dumps(steps)],
                       capture_output=True, encoding="utf-8", cwd=HERE, env=None if path is None else dict(os.environ, PATH=path))
    if p.returncode:
        check("driver runs", False, p.stderr[-1500:])
        return [None] * len(steps)
    return json.loads(p.stdout)

START = {"ev": "start"}
FLOW = {"ev": "msg", "text": "Flow: Code flow, Small"}
def bash(cmd, **kw): return {"ev": "tool", "tool": "bash", "input": {"command": cmd}, **kw}
def blocked(r): return bool(r and r["result"] and r["result"].get("block"))
def reason(r): return (r and r["result"] or {}).get("reason", "")

# --- rules injection ---
PROJECT = {"path": "/proj/AGENTS.md", "content": "project rules"}
SKIPS = {"subagent, appended prompt": {"opts": {"appendSystemPrompt": '<active_agent name="worker"/>\n\nbody'}},
         "subagent, replaced prompt": {"opts": {"customPrompt": '<active_agent name="reviewer"/>\n\nbody'}},
         "--no-context-files": {"argv": ["--no-context-files"]}, "-nc": {"argv": ["-nc"]}}
got = run([START, START] + [{"ev": "start", **v} for v in SKIPS.values()])
main = got[0] or []
check("rules first, project file after (project AGENTS.md overrides)", len(main) == 2 and main[1] == PROJECT, main)
rules = main[0] if len(main) == 2 else {"path": "", "content": ""}
check("rules path is pi/AGENTS.md", rules["path"] == os.path.join(HERE, "AGENTS.md"), rules["path"])
check("rules content is the rules", "## Route" in rules["content"])
check("no ~/.pi/agent/ pointer left", "~/.pi/agent/" not in rules["content"])
shared = os.path.join(REPO, "claude", "common")
paths = set(re.findall(re.escape(shared) + r"[\\/][\w./\\-]*\w", rules["content"]))
check("pointers resolve to files in claude/common", paths and all(os.path.exists(x) for x in paths),
      sorted(x for x in paths if not os.path.exists(x)))
check("a second run adds the rules once again, not twice", got[1] == main, got[1])
for name, r in zip(SKIPS, got[2:]):
    check(name + ": rules skipped", r == [PROJECT], r)

# --- Flow gate ---
READ = {"ev": "tool", "tool": "read", "input": {"path": "x"}}
r = run([START, READ])
check("tool call before any Flow line is blocked", blocked(r[1]), r[1])
check("block reason names the Flow line", "Flow:" in reason(r[1]), reason(r[1]))
r = run([START, FLOW, READ])
check("tool call after a Flow line in reply text runs", not blocked(r[2]), r[2])
r = run([START, {"ev": "msg", "thinking": "Flow: Code flow", "text": "checking"}, READ])
check("a Flow line only in thinking does not count", blocked(r[2]), r[2])
for form in ["**Flow:** Git", "  Flow: Git", "> Flow: Git"]:
    r = run([START, {"ev": "msg", "text": "ok\n" + form}, READ])
    check("Flow line written as %r counts" % form, not blocked(r[2]), r[2])
r = run([START, FLOW, READ, START, READ])
check("a new user prompt needs a new Flow line", not blocked(r[2]) and blocked(r[4]), r[2:])
r = run([START, FLOW, {"ev": "start", "type": "custom"}, READ])
check("a run started by an extension message keeps the Flow line", not blocked(r[3]), r[3])
for name, v in SKIPS.items():
    r = run([{"ev": "start", **v}, READ])
    check(name + ": no Flow gate", not blocked(r[1]), r[1])
for text in ["We follow Flow: x", "the Workflow: step"]:
    r = run([START, {"ev": "msg", "text": text}, READ])
    check("mid-sentence %r does not count" % text, blocked(r[2]), r[2])
CALLS = {"ev": "msg", "text": "checking", "calls": 1}
r = run([START, CALLS, READ, CALLS, READ, CALLS, READ, CALLS, READ])
check("third message without Flow lets calls through (no endless loop)",
      blocked(r[2]) and blocked(r[4]) and not blocked(r[6]) and not blocked(r[8]), r[2::2])
r = run([START, {"ev": "msg", "text": "", "calls": 3}, READ, READ, READ])
check("parallel calls in one message are all blocked", all(blocked(x) for x in r[2:]), r[2:])

# --- risky commands ---
RISKY = ['docker compose exec -T db psql -U postgres -c "drop database if exists test_x with (force)"',
         "cd /r && kill 34473 34478", "pkill -f pytest", "rm -rf build", "rm -fr build", "rm --recursive build",
         "git -C /r push -f origin main", "rtk git push --force", "git reset --hard HEAD~1", "git -C /r clean -xdf",
         "git commit -n -m wip", "git push --no-verify", "git checkout -- .", "git branch -D old",
         "git stash drop", "git -c credential.helper='!gh auth git-credential' push https://github.com/a/b.git main",
         "gh auth token", "gh auth setup-git", "git remote set-url origin https://x", "dropdb test_x", "redis-cli FLUSHALL",
         " rm -rf x", "if true; then rm -rf y; fi", "command kill 123", "/bin/rm -rf x", "\\rm -rf x", "env FOO=1 rm -rf x",
         "RM -rf x", "rm -f -r x", "rm --force --recursive x", "rm -Rf x", "git --no-pager push -f", "git push -fu origin main",
         "git push origin +main", "git push --force-with-lease", "git commit -nm wip", "git checkout .", "git clean --force",
         "git clean -d --force", "git restore .", "git stash clear", "psql -c 'TRUNCATE TABLE x'", "git credential fill",
         "gh auth status -t"]
BENIGN = ["git status", "git push origin feature-fix", "git push", "echo skill", 'git commit -m "kill switch"',
          "grep -n kill file.py", "git rm -r --cached build", "rm file.txt", "git branch -d merged", "ls ~/.ssh",
          "git checkout -- ./src/x.py", "git checkout main", "git push -u origin main", "git push --follow-tags origin main",
          "rm -f file.txt", "gh auth status"]
r = run([START, FLOW] + [bash(c) for c in RISKY + BENIGN])[2:]
for c, x in zip(RISKY, r):
    check("no UI, risky blocked: " + c, blocked(x) and "ask" in reason(x).lower(), x)
for c, x in zip(BENIGN, r[len(RISKY):]):
    check("benign runs: " + c, not blocked(x), x)
r = run([START, FLOW, bash("kill 1", ui=True, yes=True), bash("kill 1", ui=True, yes=False)])
asked = (r[2] or {}).get("asked") or [{}]
check("UI yes: risky runs after asking", not blocked(r[2]) and "kill 1" in asked[0].get("m", ""), r[2])
check("confirm times out after 60 s", asked[0].get("timeout") == 60000, asked[0])
check("UI no: risky blocked", blocked(r[3]), r[3])
r = run([START, FLOW, bash("echo " + "a" * 900 + "\nrm -rf ~", ui=True, yes=False)])
asked = (r[2] or {}).get("asked") or [{}]
check("confirm shows the risky part first, even after long padding", "rm -rf ~" in asked[0].get("m", "")[:300], asked[0].get("m", "")[:300])
r = run([START, FLOW, bash("echo " + "a" * 900 + "; rm -rf ~", ui=True, yes=False)])
asked = (r[2] or {}).get("asked") or [{}]
check("confirm shows the risky part first, padding on the same line", "rm -rf ~" in asked[0].get("m", "")[:300], asked[0].get("m", "")[:300])
r = run([START, FLOW, {"ev": "tool", "tool": "ctx_batch", "input": {"commands": ["git status"], "queries": ["kill signal handling", "rm -rf docs"]}}])
check("ctx_batch queries are not commands", not blocked(r[2]), r[2])
r = run([START, FLOW, {"ev": "tool", "tool": "ctx_batch", "input": {"commands": ["git status", "kill 1"], "queries": ["x"]}},
         {"ev": "tool", "tool": "ctx_execute", "input": {"language": "shell", "code": "echo hi\nrm -rf /data"}}])
check("ctx_batch with a risky command is checked", blocked(r[2]), r[2])
check("ctx_execute with a risky command is checked", blocked(r[3]), r[3])
# A codemode script reaches bash through ctx.executeTool(): pi fires tool_call with the nested tool's own name and a
# parentToolCallId (pi docs/extensions.md, "Calling Other Tools"), so codemode itself needs no entry in SHELL_TOOLS.
# Seen live on pi 1.6.1, 2026-11-27: `git reset --hard` from a codemode script came back blocked, the file unchanged.
r = run([START, FLOW, bash("git reset --hard", parent="call_1"), bash("git status", parent="call_1"), START, bash("ls", parent="call_2")])
check("a risky bash call nested in a codemode script is blocked", blocked(r[2]) and "ask" in reason(r[2]).lower(), r[2])
check("a benign nested call runs", not blocked(r[3]), r[3])
check("a nested call before the Flow line is blocked", blocked(r[5]) and "Flow:" in reason(r[5]), r[5])
# --- shell writes: a bash command goes through claude/common/hooks/bash-ban-shell-writes, the hook Claude Code runs ---
r = run([START, FLOW, bash("echo x > f.txt", ui=True, yes=True), bash("make check > log 2>&1"), bash("sed -i 's/a/b/' f", parent="call_1"),
         {"ev": "tool", "tool": "ctx_execute", "input": {"language": "python", "code": "print(1 > 0)\nprint('a' > 'b')"}}])
check("bash: echo into a file is blocked", blocked(r[2]) and "writes a file" in reason(r[2]), r[2])
check("bash: a blocked write does not ask the user", not (r[2] or {}).get("asked"), r[2])
check("bash: a log redirect runs", not blocked(r[3]), r[3])
check("bash nested in a codemode script: sed -i is blocked", blocked(r[4]) and "sed -i" in reason(r[4]), r[4])
check("ctx_execute code is not read as shell", not blocked(r[5]), r[5])
r = run([START, FLOW, bash("echo x > f.txt"), bash("rm -rf build")], path=os.path.join(HERE, "no-such-dir"))
check("no python on PATH: the write check lets the command through", not blocked(r[2]), r[2])
check("no python on PATH: the risky-command check still blocks", blocked(r[3]), r[3])
for name in ["subagent, appended prompt", "-nc"]:
    r = run([{"ev": "start", **SKIPS[name]}, bash("git push --force")])
    check(name + ": risky still blocked", blocked(r[1]), r[1])

# --- Exit list: a run with a Flow line that ends on a reply without a ✓ or ✗ line gets one more turn with a reminder ---
SETTLE = {"ev": "settle"}
WORK = {"ev": "msg", "text": "Flow: Code flow, Small", "calls": 1}
def said(t): return {"ev": "msg", "text": t}
def nudged(x): return bool(x and x.get("continue"))
r = run([START, WORK, said("done"), SETTLE, said("done again"), SETTLE])
check("final reply without an Exit list: one more turn", nudged(r[3]), r[3])
entry = ((r[3] or {}).get("entries") or [{}])[-1]
check("the reminder is a custom message that asks for the Exit list",
      entry.get("type") == "custom_message" and "✓" in str(entry.get("content")) and "Exit" in str(entry.get("content")), entry)
check("one reminder per prompt", r[5] is None, r[5])
r = run([START, WORK, said("Fixed.\n- ✓ gate green: bin/check\n- ✗ review: Small"), SETTLE])
check("final reply with an Exit list settles", r[3] is None, r[3])
r = run([START, WORK, said("- ✗ gate: bin/check failed"), said("so it is not done"), SETTLE])
check("only the last reply counts", nudged(r[4]), r[4])
r = run([START, said("4"), SETTLE])
check("no Flow line (chat answer): settles", r[2] is None, r[2])
r = run([START, {"ev": "msg", "text": "Flow: answer directly", "calls": 1}, said("It is 4."), SETTLE])
check("Flow: answer directly needs no Exit list", r[3] is None, r[3])
r = run([START, WORK, said("done"), {"ev": "settle", "outcome": "aborted"}, {"ev": "settle", "outcome": "error"}])
check("an aborted or failed run is left alone", r[3] is None and r[4] is None, r[3:])
KEPT = {"type": "custom", "customType": "other-extension"}
r = run([START, WORK, said("done"), {"ev": "settle", "entries": [KEPT]}])
check("entries another extension added are kept", ((r[3] or {}).get("entries") or [None])[0] == KEPT, r[3])
r = run([{"ev": "start", **SKIPS["subagent, appended prompt"]}, WORK, said("done"), SETTLE])
check("a subagent run gets no Exit reminder", r[3] is None, r[3])
r = run([START, WORK, said("done"), SETTLE, START, WORK, said("done"), SETTLE])
check("a new user prompt is checked again", nudged(r[3]) and nudged(r[7]), [r[3], r[7]])

# --- loaded twice in one session (a second path to the same package, or -e beside it): each effect happens once ---
def twice(s): return dict(s, twice=True)
r = run([twice(START)])
check("loaded twice: the rules are added once", [f["path"] for f in r[0] or []] == [rules["path"], PROJECT["path"]], [f["path"] for f in r[0] or []])
r = run([twice(START), twice(WORK), twice(said("done")), twice(SETTLE)])
got = [e for e in (r[3] or {}).get("entries", []) if e.get("customType") == "armarium-exit"]
check("loaded twice: one Exit reminder", len(got) == 1 and nudged(r[3]), r[3])
r = run([twice(START), twice(FLOW), twice(bash("kill 1", ui=True, yes=True)), twice(bash("kill 1", ui=True, yes=False))])
check("loaded twice: the user is asked once, and a yes runs the command", len((r[2] or {}).get("asked", [])) == 1 and not blocked(r[2]), r[2])
check("loaded twice: a yes covers that one call only", len((r[3] or {}).get("asked", [])) == 1 and blocked(r[3]), r[3])
r = run([twice(START), twice(READ)])
check("loaded twice: the Flow gate still blocks", blocked(r[1]), r[1])

# --- every pi-subagents child of this session must load this extension ---
# requireForAllRunners: pi-subagents then refuses machine and external-CLI launches and keeps the snapshot with the run.
SELF = [{"id": "armarium-pi", "path": os.path.realpath(EXT), "requireForAllRunners": True}]
A = {"ev": "session_start", "file": "/s/a.jsonl", "id": "a"}  # pi-subagents keys the registry by session id, never the file
RUN = {"ev": "start", "reg": True}
r = run([A])
check("session start registers under the session id (a /run before any prompt is gated)", r[0] == {"a": SELF}, r[0])
r = run([A, RUN])
check("a run keeps the one registration", r[1] == {"a": SELF}, r[1])
r = run([A, {"ev": "session_start", "file": "/s/b.jsonl", "id": "b"}])
check("a new session moves the registration", r[1] == {"b": SELF}, r[1])
r = run([A, {"ev": "session_shutdown"}])
check("shutdown removes the registration", r[1] == {}, r[1])
r = run([{"ev": "start", **SKIPS["subagent, appended prompt"], "reg": True}])
check("a subagent child registers too, so its own children load the gate", r[0] == {"none": SELF}, r[0])
r = run([A, {"ev": "session_shutdown"}, {"ev": "tool", "tool": "subagent", "input": {}}, {"ev": "same", "key": "x"}])
check("a subagent call registers again when the key is missing", r[2] and r[2]["result"] is None, r[2])
r2 = run([A, {"ev": "session_shutdown"}, {"ev": "tool", "tool": "subagent", "input": {}}, {"ev": "preset", "key": "zz", "entries": []}])
check("and the registry then holds it", r2[3].get("a") == SELF, r2[3])
OTHER = [{"id": "other", "path": "/x/other.ts"}]
r = run([{"ev": "preset", "key": "a", "entries": OTHER}, A, {"ev": "session_shutdown"}, {"ev": "same", "key": "a"}])
check("a host that registered first keeps its entry beside ours", r[1] == {"a": OTHER + SELF}, r[1])
check("shutdown restores the other host's exact array, so its dispose() still matches", r[3] is True, r[2:])

print("FAILS %d of %d" % (fails, total))
sys.exit(1 if fails else 0)
