"""Self-test for pi/extension.ts: python3 -I pi/test_extension.py
Drives the extension's before_agent_start handler with a fake pi in node (needs node >= 22.18 for .ts); never touches ~/.pi."""
import json, os, pathlib, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
EXT = os.path.join(HERE, "extension.ts")
if not shutil.which("node"):
    print("skip: node not on PATH"); sys.exit(0)

# argv[2] = JSON list of runs: {argv: extra process.argv, opts: extra systemPromptOptions}; prints contextFiles per run.
DRIVER = """
const ext = (await import(process.argv[1])).default;
const handlers = {};
ext({ on: (name, fn) => { handlers[name] = fn; } });
const out = [];
for (const run of JSON.parse(process.argv[2])) {
  const argv = process.argv;
  process.argv = [...argv, ...run.argv];
  const event = { systemPrompt: "", systemPromptOptions: { appendSystemPrompt: "", ...run.opts,
    contextFiles: [{ path: "/proj/AGENTS.md", content: "project rules" }] } };
  await handlers.before_agent_start(event, {});
  process.argv = argv;
  out.push(event.systemPromptOptions.contextFiles);
}
console.log(JSON.stringify(out));
"""
PROJECT = {"path": "/proj/AGENTS.md", "content": "project rules"}
RUNS = {"main": {"argv": [], "opts": {}},
        "main again": {"argv": [], "opts": {}},
        "subagent, appended prompt": {"argv": [], "opts": {"appendSystemPrompt": '<active_agent name="worker"/>\n\nbody'}},
        "subagent, replaced prompt": {"argv": [], "opts": {"customPrompt": '<active_agent name="reviewer"/>\n\nbody'}},
        "--no-context-files": {"argv": ["--no-context-files"], "opts": {}},
        "-nc": {"argv": ["-nc"], "opts": {}}}

fails = total = 0

def check(label, ok, detail=""):
    global fails, total
    total += 1
    fails += not ok
    print(("ok   " if ok else "FAIL ") + label, "" if ok else detail)

p = subprocess.run(["node", "--no-warnings", "--input-type=module", "-e", DRIVER, pathlib.Path(EXT).as_uri(), json.dumps(list(RUNS.values()))],
                   capture_output=True, encoding="utf-8", cwd=HERE)
check("handler runs", p.returncode == 0, p.stderr[-2000:])
got = dict(zip(RUNS, json.loads(p.stdout))) if p.returncode == 0 else {k: [] for k in RUNS}

main = got["main"]
check("rules first, project file after (project AGENTS.md overrides)", len(main) == 2 and main[1] == PROJECT, main)
rules = main[0] if len(main) == 2 else {"path": "", "content": ""}
check("rules path is pi/AGENTS.md", rules["path"] == os.path.join(HERE, "AGENTS.md"), rules["path"])
check("rules content is the rules", "## Route" in rules["content"])
check("no ~/.pi/agent/ pointer left", "~/.pi/agent/" not in rules["content"])
shared = os.path.join(REPO, "claude", "common")
paths = set(re.findall(re.escape(shared) + r"[\\/][\w./\\-]*\w", rules["content"]))
check("pointers resolve to files in claude/common", paths and all(os.path.exists(x) for x in paths),
      sorted(x for x in paths if not os.path.exists(x)))
check("a second run adds the rules once again, not twice", got["main again"] == main, len(got["main again"]))
for name in ["subagent, appended prompt", "subagent, replaced prompt", "--no-context-files", "-nc"]:
    check(name + ": rules skipped", got[name] == [PROJECT], got[name])

print("FAILS %d of %d" % (fails, total))
sys.exit(1 if fails else 0)
