"""Self-test for bin/hook-diff: python3 -I bin/test_hook_diff.py
Builds a throwaway git repo with a tiny hook committed and a changed copy in the work tree."""
import json, os, subprocess, sys, tempfile

TOOL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hook-diff")
ENV = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}  # under pre-commit, GIT_INDEX_FILE names the real index
HOOK = "hooks/gate"
OLD = "import json, sys\nc = json.load(sys.stdin)['tool_input']['command']\nsys.exit(2 if 'rm' in c else 0)\n"
NEW = ("import json, sys\nd = json.load(sys.stdin)\nc = d['tool_input']['command']\n"
       "if 'boom' in c: raise SystemExit(1)\n"
       "sys.exit(2 if 'rm' in c or ('cp' in c and d.get('agent_type') == 'reviewer') else 0)\n")
fails = 0


def check(name, ok, detail=""):
    global fails
    fails += not ok
    print(("ok   " if ok else "FAIL ") + name, str(detail)[:160])


def git(repo, *a):
    subprocess.run(["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True, env=ENV)


repo = tempfile.mkdtemp()
os.makedirs(os.path.join(repo, "hooks"))
with open(os.path.join(repo, HOOK), "w") as f:
    f.write(OLD)
git(repo, "init", "-q"); git(repo, "add", "."); git(repo, "commit", "-q", "-m", "old")
with open(os.path.join(repo, HOOK), "w") as f:
    f.write(NEW)
corpus = os.path.join(repo, "corpus.jsonl")
ROWS = [["", "ls -la"], ["", "rm x"], ["", "cp a b"], ["reviewer", "cp a b"], ["", "echo one\necho two"], ["", "boom"]]
with open(corpus, "w") as f:
    f.write("# a comment line\n\n" + "\n".join(json.dumps(r) for r in ROWS) + "\n")


def run(*args, stdin=None):
    p = subprocess.run([sys.executable, TOOL, "--repo", repo, "--hook", HOOK, *args], input=stdin, capture_output=True, text=True, env=ENV)
    return p.returncode, p.stdout + p.stderr


rc, out = run(corpus)
check("exit 0: the tool reports, it does not judge", rc == 0, (rc, out))
check("a command whose verdict changed is listed with both exits", "0 -> 2" in out and "[reviewer] cp a b" in out, out)
check("the same command for the main agent is not listed", "[] cp a b" not in out and out.count("cp a b") == 1, out)
check("an unchanged block is not listed", "rm x" not in out, out)
check("a hook error (exit other than 0 or 2) is listed and named", "0 -> 1" in out and "boom" in out and "hook error" in out, out)
check("the summary counts the rows and the changes", "6 commands, 2 changed" in out, out)
rc, out = run("-", stdin=json.dumps(["reviewer", "cp x y"]) + "\n" + json.dumps(["", "ls"]) + "\n")
check("rows from stdin", rc == 0 and "[reviewer] cp x y" in out and "2 commands, 1 changed" in out, out)
rc, out = run("--all", corpus)
check("--all prints every row with its exits", "0 -> 0  [] ls -la" in out and "2 -> 2  [] rm x" in out, out)
rc, out = run(os.path.join(repo, "missing.jsonl"))
check("a missing corpus is an error, not an empty pass", rc != 0, (rc, out))
rc, out = run("-", stdin="5\n")
check("a line that is not a pair of strings exits 2", rc == 2 and "line 1" in out, (rc, out))
import shutil
shutil.rmtree(repo, ignore_errors=True)
print("FAILS", fails)
sys.exit(1 if fails else 0)
