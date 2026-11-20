"""Self-test for windows/statusline.py: python -I windows/hooks/test_statusline.py
Expected rows are written by hand from the statusline.ps1 rules (.NET rounding: half away from zero)."""
import json, os, re, subprocess, sys, tempfile, time

SL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "statusline.py")
ANSI = re.compile(r"\x1b\[[0-9;]*m")
fails = 0


def run(payload, raw=None):
    data = raw if raw is not None else json.dumps(payload).encode()
    p = subprocess.run([sys.executable, SL], input=data, capture_output=True)
    return p.returncode, p.stdout.decode("utf-8").replace("\r", "")


def check(name, got, want):
    global fails
    if got != want: fails += 1; print("FAIL", name, "\n got ", repr(got), "\n want", repr(want))


plain = tempfile.mkdtemp(prefix="slplain")
folder = os.path.basename(plain)
now = time.time()
full = {"model": {"display_name": "Opus 5.5"}, "effort": {"level": "high"}, "workspace": {"current_dir": plain},
        "context_window": {"used_percentage": 42.25, "context_window_size": 1000000, "total_input_tokens": 272000,
                           "total_output_tokens": 1500,
                           "current_usage": {"cache_read_input_tokens": 0, "cache_creation_input_tokens": 2500}},
        "prompt_cache": {"hit_ratio": 0.875, "expires_at": now + 4000}, "cost": {"total_cost_usd": 1.2345},
        "rate_limits": {"five_hour": {"used_percentage": 55.5}, "seven_day": {"used_percentage": 12}}}
rc, out = run(full)
check("full rows", (rc, ANSI.sub("", out)),
      (0, folder + " | Opus 5.5 · think high | ctx 42.3% of 1M\n"
          "in 272k · out 1.5k · cache read 0 · write 2.5k · hit 88% · idle 1h6m · $1.235 | 5h 56% · 7d 12%\n"))
check("ctx green", "\x1b[32m42.3%\x1b[0m" in out, True)
check("5h yellow", "\x1b[33m56%\x1b[0m" in out, True)
check("separator is dim", "\x1b[2m | \x1b[0m" in out, True)

# a fresh session reports 0 for tokens and cost: hidden; no rate limits -> no second row
fresh = {"model": {"display_name": "Haiku"}, "cwd": plain,
         "context_window": {"used_percentage": 85, "context_window_size": 272000, "total_input_tokens": 0,
                            "total_output_tokens": 0}, "cost": {"total_cost_usd": 0}}
rc, out = run(fresh)
check("fresh", ANSI.sub("", out), folder + " | Haiku | ctx 85.0% of 272k\n")
check("ctx red", "\x1b[31m85.0%\x1b[0m" in out, True)

# values sit mid-bucket: a slow subprocess start must not move the expected text
for left, want, colour in ((-10, r"cold", "31"), (330, r"5m", "33"), (45, r"(3\d|4\d)s", "31"), (7330, r"2h2m", "32")):
    rc, out = run({"prompt_cache": {"expires_at": time.time() + left}})
    check("idle %d" % left, bool(re.fullmatch(r"\x1b\[2midle\x1b\[0m \x1b\[%sm%s\x1b\[0m\n" % (colour, want), out)), True)

for size, want in ((999, "999"), (1234567, "1.2M"), (1500000, "1.5M"), (2000, "2k")):
    rc, out = run({"context_window": {"used_percentage": 1, "context_window_size": size}})
    check("kfmt %d" % size, ANSI.sub("", out), "ctx 1.0%% of %s\n" % want)

check("bad json", run(None, raw=b"{nope"), (0, ""))
check("empty input", run(None, raw=b""), (0, ""))

# git: branch name and a dirty mark
repo = tempfile.mkdtemp(prefix="slrepo")
subprocess.run(["git", "init", "-q", "-b", "feat-x", repo], check=True)
open(os.path.join(repo, "f.txt"), "w").close()
rc, out = run({"workspace": {"current_dir": repo}})
check("git dirty", ANSI.sub("", out), os.path.basename(repo) + " · git feat-x*\n")

print("FAILS", fails)
sys.exit(1 if fails else 0)
