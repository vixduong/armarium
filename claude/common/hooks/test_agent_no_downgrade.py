"""Self-test for agent-no-downgrade: python3 -I ~/.claude/hooks/test_agent_no_downgrade.py
Uses the real agent files in ~/.claude/agents (reviewer=opus, worker=sonnet, oracle=fable, explorer=haiku)."""
import json, os, subprocess, sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent-no-downgrade")  # the hook beside this test, not the installed one

BLOCK = [
    {"subagent_type": "reviewer", "model": "haiku"},
    {"subagent_type": "reviewer", "model": "claude-haiku-5-5"},
    {"subagent_type": "reviewer", "model": "sonnet"},     # below its opus default, and no listed drop
    {"subagent_type": "evidence-auditor", "model": "haiku"},
    {"subagent_type": "oracle", "model": "haiku"},
]
ALLOW = [
    {"subagent_type": "reviewer"},
    {"subagent_type": "reviewer", "model": "opus"},
    {"subagent_type": "reviewer", "model": "claude-fable-5-2"},
    {"subagent_type": "worker", "model": "haiku"},       # listed drop: mechanical edits
    {"subagent_type": "worker", "model": "fable"},
    {"subagent_type": "oracle", "model": "opus"},        # listed drop: Fable limit exhausted
    {"subagent_type": "oracle", "model": "sonnet"},
    {"subagent_type": "explorer", "model": "haiku"},
    {"subagent_type": "general-purpose", "model": "sonnet"},  # no frontmatter: default unknown
    {"subagent_type": "Explore", "model": "haiku"},
    {"subagent_type": "no-such-agent", "model": "haiku"},
    {"subagent_type": "reviewer", "model": "inherit"},
    {"model": "haiku"},
]

def run(tool, inp):
    p = subprocess.run([sys.executable, HOOK], input=json.dumps({"tool_name": tool, "tool_input": inp}),
                       capture_output=True, text=True)
    return p.returncode

fails = 0
for i in BLOCK:
    if run("Agent", i) != 2: fails += 1; print("SHOULD BLOCK:", i)
for i in ALLOW:
    if run("Agent", i) != 0: fails += 1; print("SHOULD ALLOW:", i)
if run("Bash", {"command": "ls"}) != 0: fails += 1; print("non-Agent tool should pass")
if run("Task", {"subagent_type": "reviewer", "model": "haiku"}) != 2: fails += 1; print("the Task tool name is the same tool: SHOULD BLOCK")
print("FAILS", fails, "of", len(BLOCK) + len(ALLOW) + 2)
sys.exit(1 if fails else 0)
