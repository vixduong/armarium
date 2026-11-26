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
#   {"ev": "tool", "tool": "bash", "input": {...}, "ui": bool, "yes": bool} -> tool_call result
DRIVER = """
const ext = (await import(process.argv[1])).default;
const handlers = {};
ext({ on: (name, fn) => { handlers[name] = fn; } });
const out = [];
for (const s of JSON.parse(process.argv[2])) {
  if (s.ev === "start") {
    const argv = process.argv;
    process.argv = [...argv, ...(s.argv ?? [])];
    const event = { messageType: s.type ?? "user", systemPrompt: "", systemPromptOptions: { appendSystemPrompt: "", ...s.opts,
      contextFiles: [{ path: "/proj/AGENTS.md", content: "project rules" }] } };
    await handlers.before_agent_start(event, {});
    process.argv = argv;
    out.push(event.systemPromptOptions.contextFiles);
  } else if (s.ev === "msg") {
    const content = [];
    if (s.thinking) content.push({ type: "thinking", thinking: s.thinking });
    if (s.text) content.push({ type: "text", text: s.text });
    for (let i = 0; i < (s.calls ?? 0); i++) content.push({ type: "toolCall", id: "t" + i, name: "read", arguments: {} });
    await handlers.message_end({ type: "message_end", message: { role: "assistant", content } }, {});
    out.push(null);
  } else {
    const asked = [];
    const ctx = { hasUI: !!s.ui, signal: undefined, ui: { confirm: async (t, m, o) => { asked.push({ m, timeout: o?.timeout }); return !!s.yes; } } };
    const r = await handlers.tool_call({ type: "tool_call", toolName: s.tool, toolCallId: "t", input: s.input }, ctx);
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

def run(steps):
    p = subprocess.run(["node", "--no-warnings", "--input-type=module", "-e", DRIVER, pathlib.Path(EXT).as_uri(), json.dumps(steps)],
                       capture_output=True, encoding="utf-8", cwd=HERE)
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
for name in ["subagent, appended prompt", "-nc"]:
    r = run([{"ev": "start", **SKIPS[name]}, bash("git push --force")])
    check(name + ": risky still blocked", blocked(r[1]), r[1])

print("FAILS %d of %d" % (fails, total))
sys.exit(1 if fails else 0)
