"""Self-test for write-fold-guard: python3 -I ~/.claude/hooks/test_write_fold_guard.py"""
import json, os, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8")

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "write-fold-guard")  # the hook beside this test
# The fold texts are split so this file never matches the guard itself when it is written or edited.
CTX = ('mcp__plugin_context-mode_context-mode__ctx_search({queries:["sed -n \'1,400p\' \'a.py\'"], source:"s35"}) '
       "searches the whole " + "output (5093 B). Or run: node 'C:\\x\\search.mjs' s35 'sed' 'C:\\r'")
STORED = ("def f():\n    return 1\n\nThe full output (5758 B) is stored as s3b; above is the " + "best-matching part. "
          "Read the file with offset and limit for other lines. Or run: node 'C:\\x\\search.mjs' s3b 'q' 'C:\\r'")
RTK = "1:# Title\n2:\n3:line\n  +25 more in C:/r/a.md [+25 hidden: rtk " + "recall 1749f4a5270b89e4]"

def run(tool, inp):
    p = subprocess.run([sys.executable, HOOK], input=json.dumps({"tool_name": tool, "tool_input": inp}),
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stderr

CASES = [  # (name, tool, input, expect_exit)
    ("Write of a context-mode pointer", "Write", {"file_path": "/r/a.md", "content": CTX}, 2),
    ("Write of a context-mode stored-output fold", "Write", {"file_path": "/r/a.py", "content": STORED}, 2),
    ("Write of an rtk fold", "Write", {"file_path": "/r/a.md", "content": RTK}, 2),
    ("Edit whose new text is a pointer", "Edit", {"file_path": "/r/a.py", "old_string": "x", "new_string": CTX}, 2),
    ("MultiEdit with a folded edit", "MultiEdit", {"file_path": "/r/a.py", "edits": [{"old_string": "a", "new_string": "b"}, {"old_string": "c", "new_string": STORED}]}, 2),
    ("ordinary Write", "Write", {"file_path": "/r/a.py", "content": "print('hi')\n"}, 0),
    ("long doc that quotes a pointer", "Write", {"file_path": "/r/report.md", "content": "notes\n" * 1000 + CTX}, 0),
    ("other tool", "Bash", {"command": CTX}, 0),
    ("tool_input that is not an object", "Write", ["x"], 0),
    ("edits that is not a list", "MultiEdit", {"file_path": "/r/a.py", "edits": 5}, 0),
]
fails = 0
for name, tool, inp, expect in CASES:
    code, err = run(tool, inp)
    if code != expect:
        fails += 1; print("FAIL %s: exit=%s %s" % (name, code, err[:200]))
code, err = run("Write", {"file_path": "/r/a.md", "content": CTX})
if code == 2 and "slice" not in err:
    fails += 1; print("FAIL reason names the way to read the file: %s" % err)
for bad in ("not json", "[]"):
    p = subprocess.run([sys.executable, HOOK], input=bad, capture_output=True, text=True)
    if p.returncode != 0:
        fails += 1; print("FAIL input %r passes: exit=%s" % (bad, p.returncode))
print("ok" if not fails else "%d failed" % fails)
sys.exit(1 if fails else 0)
