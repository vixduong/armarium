#!/usr/bin/env python3
# Status line for Claude Code, Windows (Python port of statusline.ps1, whose PowerShell start cost ~670 ms a refresh).
# Each block is one purpose; " | " separates blocks, " · " separates items inside a block.
# Numbers format like the .NET Framework did: half away from zero. Self-test: python -I hooks/test_statusline.py
import json, math, os, re, subprocess, sys, time
from decimal import Decimal, ROUND_HALF_UP

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks"))  # run_cli_hook.py sits in hooks/ beside this file
sys.dont_write_bytecode = True  # no __pycache__ in the hooks folder (install.ps1 would copy it)
from run_cli_hook import resolve  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


def paint(c, t): return "\x1b[%sm%s\x1b[0m" % (c, t)
def dim(t): return paint(2, t)
def has(v): return v is not None and str(v) != ""
def zero(v): return float(v) == 0
def fixed(v, places):  # .NET ToString('0.0'): 15 significant digits, then half away from zero
    d = Decimal(format(float(v), ".15g")).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return format(d, "f")
def pct_color(p):
    i = math.trunc(float(p))
    return 31 if i >= 80 else 33 if i >= 50 else 32
def kfmt(v):  # 272000 -> 272k, 1000000 -> 1M, 1234567 -> 1.2M
    n = float(v)
    if n >= 1e6: x, s = n / 1e6, "M"
    elif n >= 1e3: x, s = n / 1e3, "k"
    else: return str(round(n))
    return "%d%s" % (x, s) if x == math.floor(x) else fixed(x, 1) + s
def join_by(sep, items): return sep.join(i for i in items if i)
def get(d, *path):
    for k in path:
        d = d.get(k) if isinstance(d, dict) else None
    return d


DOT = dim(" · ")
BAR = dim(" | ")

GIT = resolve("git")  # PATH only: a bare "git" also runs a git.exe in the cwd, the user's project


def git(cwd, *args):
    if not GIT:
        return ""
    try:
        r = subprocess.run([GIT, "-C", cwd] + list(args), capture_output=True, text=True, encoding="utf-8",
                           env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
        return r.stdout.strip() if r.returncode == 0 else ""
    except OSError:
        return ""


def main():
    try:
        d = json.loads(sys.stdin.buffer.read())
    except Exception:
        return
    if not d or not isinstance(d, dict):
        return

    cwd = get(d, "workspace", "current_dir") or d.get("cwd")
    folder = branch_seg = None
    if cwd:
        folder = paint("1;36", ([p for p in re.split(r"[\\/]", str(cwd)) if p] or [""])[-1])
        branch = git(cwd, "symbolic-ref", "--short", "HEAD") or git(cwd, "rev-parse", "--short", "HEAD")
        if branch:
            dirty = "*" if git(cwd, "status", "--porcelain") else ""
            branch_seg = dim("git") + " " + paint("1;35", branch + dirty)

    model_seg = paint("1;33", get(d, "model", "display_name")) if get(d, "model", "display_name") else None
    effort_seg = dim("think") + " " + paint(35, get(d, "effort", "level")) if get(d, "effort", "level") else None

    cw = d.get("context_window")
    ctx_seg = None
    if has(get(cw, "used_percentage")):
        up = get(cw, "used_percentage")
        ctx_seg = dim("ctx") + " " + paint(pct_color(up), fixed(up, 1) + "%")
        if has(get(cw, "context_window_size")):
            ctx_seg += " " + dim("of") + " " + paint(36, kfmt(get(cw, "context_window_size")))

    # A fresh session reports 0 for tokens and cost: hide them until there is something to show
    def tok(label, v, hide_zero):
        if has(v) and not (hide_zero and zero(v)):
            return dim(label) + " " + paint(36, kfmt(v))
    in_seg = tok("in", get(cw, "total_input_tokens"), True)
    out_seg = tok("out", get(cw, "total_output_tokens"), True)
    cache_seg = tok("cache read", get(cw, "current_usage", "cache_read_input_tokens"), False)
    write_seg = tok("write", get(cw, "current_usage", "cache_creation_input_tokens"), False)
    pc = d.get("prompt_cache")
    hit = get(pc, "hit_ratio")
    hit_seg = dim("hit") + " " + paint(32, fixed(float(hit) * 100, 0) + "%") if has(hit) else None
    cost = get(d, "cost", "total_cost_usd")
    cost_seg = paint(33, "$" + fixed(cost, 3)) if has(cost) and not zero(cost) else None

    # Idle budget: time left until the prompt cache goes cold (next turn then re-caches in full)
    idle_seg = None
    exp = get(pc, "expires_at")
    if has(exp):
        left = math.floor(float(exp)) - int(time.time())
        if left <= 0:
            idle_seg = dim("idle") + " " + paint(31, "cold")
        else:
            t = ("%dh%dm" % (left // 3600, (left % 3600) // 60) if left >= 3600
                 else "%dm" % (left // 60) if left >= 60 else "%ds" % left)
            idle_seg = dim("idle") + " " + paint(31 if left < 120 else 33 if left < 600 else 32, t)

    rl = d.get("rate_limits")
    def limit(label, v):
        if has(v):
            return dim(label) + " " + paint(pct_color(v), fixed(v, 0) + "%")
    five_seg = limit("5h", get(rl, "five_hour", "used_percentage"))
    week_seg = limit("7d", get(rl, "seven_day", "used_percentage"))

    row1 = join_by(BAR, [join_by(DOT, [folder, branch_seg]), join_by(DOT, [model_seg, effort_seg]), ctx_seg])
    row2 = join_by(BAR, [join_by(DOT, [in_seg, out_seg, cache_seg, write_seg, hit_seg, idle_seg, cost_seg]),
                         join_by(DOT, [five_seg, week_seg])])
    for row in (row1, row2):
        if row:
            print(row)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
