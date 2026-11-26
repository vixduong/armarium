"""Self-test for pi/unix/install.sh: python3 -I pi/unix/test_install.py
Runs the installer against a throwaway PI_CODING_AGENT_DIR, so the real ~/.pi/agent is never read or changed."""
import os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
INSTALL = os.path.join(HERE, "install.sh")
REPO = os.path.dirname(os.path.dirname(HERE))
SHARED = os.path.join(REPO, "claude", "common")
WANT = {"AGENTS.md": os.path.join(REPO, "pi", "common", "AGENTS.md"),
        "CODING_STANDARDS.md": os.path.join(SHARED, "CODING_STANDARDS.md"),
        "RTK.md": os.path.join(SHARED, "RTK.md"),
        "rules/frontend.md": os.path.join(SHARED, "rules", "frontend.md"),
        "rules/video.md": os.path.join(SHARED, "rules", "video.md")}
if sys.platform == "win32":
    print("skip: pi/windows/install.ps1 installs on Windows"); sys.exit(0)

fails = total = 0


def check(label, ok, detail=""):
    global fails, total
    total += 1
    fails += not ok
    print(("ok   " if ok else "FAIL ") + label, "" if ok else detail)


def run(dest):
    p = subprocess.run(["sh", INSTALL], capture_output=True, text=True,
                       env={"PATH": os.environ["PATH"], "HOME": dest, "PI_CODING_AGENT_DIR": dest})
    return p.returncode, p.stdout + p.stderr


dest = os.path.join(tempfile.mkdtemp(), "agent")  # missing dir: the installer creates it
rc, out = run(dest)
for name, src in WANT.items():
    p = os.path.join(dest, name)
    check("links " + name, rc == 0 and os.path.islink(p) and os.readlink(p) == src and os.path.isfile(src), out)
with open(WANT["AGENTS.md"], encoding="utf-8") as f:
    pointers = set(re.findall(r"~/\.pi/agent/([\w./-]+\.\w+)", f.read()))
check("every ~/.pi/agent/<file> AGENTS.md points to is installed", pointers and all(os.path.isfile(os.path.join(dest, p)) for p in pointers),
      sorted(p for p in pointers if not os.path.isfile(os.path.join(dest, p))))
rc, out = run(dest)
check("second run: unchanged, says same", rc == 0 and out.count("same") == len(WANT), out)

dest = tempfile.mkdtemp()
with open(os.path.join(dest, "AGENTS.md"), "w") as f:
    f.write("mine")
rc, out = run(dest)
check("an existing AGENTS.md is kept and reported", rc == 0 and open(os.path.join(dest, "AGENTS.md")).read() == "mine"
      and "skip" in out and "AGENTS.md" in out, out)
check("the other files are still linked", os.path.islink(os.path.join(dest, "rules", "video.md")), out)

print("FAILS %d of %d" % (fails, total))
sys.exit(1 if fails else 0)
