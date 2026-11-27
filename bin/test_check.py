"""Self-test for bin/check: python3 -I bin/test_check.py
Each case builds a small fixture repo and a fake HOME, then expects check to pass or to name the problem."""
import json, os, re, stat, subprocess, sys, tempfile

CHECK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "check")
SETTINGS = {"hooks": {"SessionStart": [{"hooks": [
    {"type": "command", "command": "~/.claude/hooks/good-hook"},
    {"type": "command", "command": "~/.claude/hooks/skill-model-invocable unlocked"}]}]}}


def fixture(files=None, settings=SETTINGS, skills=None, home_files=None):
    """files: {repo-relative path: text}. skills: {name: SKILL.md text} under the fake HOME. home_files: {HOME-relative path: text}."""
    root = tempfile.mkdtemp()
    repo, home = os.path.join(root, "repo"), os.path.join(root, "home")
    base = {
        "claude/common/CLAUDE.md": "Read `~/.claude/CODING_STANDARDS.md` and `agent-tuning.md`; call `anim`.\n",
        "claude/common/CODING_STANDARDS.md": "Rules.\n",
        "claude/common/agent-tuning.md": "Tiers.\n",
        "claude/common/hooks/good-hook": "#!/bin/sh\n",
        "claude/common/hooks/skill-model-invocable": "#!/bin/sh\n",
        "claude/windows/settings.example.json": "{}",
    }
    base.update(files or {})
    for rel, text in base.items():
        p = os.path.join(repo, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:  # check reads UTF-8; Windows' default is the ANSI code page
            f.write(text)
        if re.match(r"claude/(common|unix)/hooks/", rel) and not rel.endswith(".py"):
            os.chmod(p, 0o755)
    os.makedirs(os.path.join(repo, "claude", "unix"), exist_ok=True)
    with open(os.path.join(repo, "claude", "unix", "settings.example.json"), "w") as f:
        json.dump(settings, f)
    for name, text in (skills or {"anim": "---\nname: anim\n---\n"}).items():
        d = os.path.join(home, ".claude", "skills", name)
        os.makedirs(d)
        with open(os.path.join(d, "SKILL.md"), "w") as f:
            f.write(text)
    for rel, text in (home_files or {}).items():
        p = os.path.join(home, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text.replace("{HOME}", home.replace("\\", "/")))  # inside JSON: a backslash path is not a valid string
    return repo, home


def run(repo, home, args=(), env_extra=None):
    env = dict({"HOME": home, "PATH": os.environ["PATH"]}, **(env_extra or {}))
    if sys.platform == "win32":  # expanduser reads USERPROFILE there, so HOME alone left the real ~/.claude in play
        env.update(USERPROFILE=home, SystemRoot=os.environ["SystemRoot"])
    p = subprocess.run([sys.executable, CHECK, repo, *args], capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


LOCKED = "---\nname: anim\ndisable-model-invocation: true\n---\n"
fails = total = 0


def case(label, want_rc, want_text, **kw):
    global fails, total
    pre, args, absent, env_extra = kw.pop("pre", None), kw.pop("args", ()), kw.pop("absent", None), kw.pop("env", None)
    repo, home = fixture(**kw)
    if pre:
        pre(repo)
    rc, out = run(repo, home, args, env_extra)
    ok = rc == want_rc and (want_text in out) and (absent is None or absent not in out)
    total += 1
    fails += not ok
    print(("ok   " if ok else "FAIL ") + label, "" if ok else "rc=%s %s" % (rc, out[-300:]))


case("clean fixture passes", 0, "check: ok")
case("dead ~/.claude pointer", 1, "~/.claude/enforcement.md",
     files={"claude/common/CODING_STANDARDS.md": "See `~/.claude/enforcement.md`.\n"})
case("dead bare .md pointer", 1, "enforcement.md",
     files={"claude/common/CODING_STANDARDS.md": "See `enforcement.md` (AC-09).\n"})
case("settings calls a hook the repo lacks", 1, "hooks/missing-hook",
     settings={"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "~/.claude/hooks/missing-hook"}]}]}})
if sys.platform != "win32":  # Windows has no exec bit: os.access(X_OK) is always true there
    case("hook not executable", 1, "hooks/good-hook",
         pre=lambda repo: os.chmod(os.path.join(repo, "claude/common/hooks/good-hook"), stat.S_IRUSR | stat.S_IWUSR))
case("settings may call a unix-only hook", 0, "check: ok",
     files={"claude/unix/hooks/bash-hook": "#!/bin/sh\n"},
     settings={"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "~/.claude/hooks/bash-hook"}]}]}})
case("model told to call a user-only skill", 1, "anim", skills={"anim": LOCKED})
case("user-only skill written as /name passes", 0, "check: ok", skills={"anim": LOCKED},
     files={"claude/common/CLAUDE.md": "Suggest `/anim`.\n"})
case("user-only skill unlocked by skill-model-invocable passes", 0, "check: ok", skills={"anim": LOCKED},
     settings={"hooks": {"SessionStart": [{"hooks": [
         {"type": "command", "command": "~/.claude/hooks/good-hook"},
         {"type": "command", "command": "~/.claude/hooks/skill-model-invocable anim"}]}]}})
case("broken JSON in windows settings", 1, "claude/windows/settings.example.json",
     files={"claude/windows/settings.example.json": "{"})
case("a failing hook self-test", 1, "test_broken.py",
     files={"claude/common/hooks/test_broken.py": "import sys; sys.exit(1)\n"})
case("a failing skill script self-test", 1, "test_skill_broken.py",
     files={"claude/common/skills/demo/scripts/test_skill_broken.py": "import sys; sys.exit(1)\n"})

case("missing claude/unix/settings.example.json", 1, "claude/unix/settings.example.json",
     pre=lambda repo: os.remove(os.path.join(repo, "claude/unix/settings.example.json")))
case("flag text after the frontmatter does not count", 0, "check: ok",
     skills={"anim": "---\nname: anim\n---\n\ndisable-model-invocation: true\n\n---\n"})
case("windows settings call a file the repo lacks", 1, "hooks/gone.ps1",
     files={"claude/windows/settings.example.json": json.dumps({"hooks": {"Stop": [{"hooks": [
         {"type": "command", "command": "powershell -File C:/Users/YOU/.claude/hooks/gone.ps1"}]}]}})})
case("windows settings may call a shared python hook", 0, "check: ok",
     files={"claude/windows/settings.example.json": json.dumps({"hooks": {"Stop": [{"hooks": [
         {"type": "command", "command": "python C:/Users/YOU/.claude/hooks/good-hook"}]}]}})})

def plugins(installed, cache):
    """installed: {plugin: version} in Claude Code's install record. cache: {"plugin/version/path": text}."""
    record = {"version": 2, "plugins": {p + "@mk": [{"scope": "user", "version": v,
              "installPath": "{HOME}/.claude/plugins/cache/mk/%s/%s" % (p, v)}] for p, v in installed.items()}}
    files = {".claude/plugins/installed_plugins.json": json.dumps(record)}
    files.update({".claude/plugins/cache/mk/" + k: t for k, t in cache.items()})
    return files


HF = "---\nname: hf\n---\n"
HF_PLUGIN = plugins({"hf": "1.0"}, {"hf/1.0/skills/hf/SKILL.md": HF})
ROUTE = "Read `~/.claude/CODING_STANDARDS.md` and `agent-tuning.md`.\n| Task | Flow | Lead skill | Done |\n|---|---|---|---|\n"
case("lead skill that is not installed", 1, "ghost",
     files={"claude/common/CLAUDE.md": ROUTE + "| Video | Code flow | `ghost` | done |\n"})
case("lead skills found as plugin skill, user skill, agent and built-in pass", 0, "check: ok",
     files={"claude/common/CLAUDE.md": ROUTE + "| Video | Code flow | `hf:hf` · `anim` · `scout` agent · `update-config` | done |\n",
            "claude/common/agents/scout.md": "---\nname: scout\n---\n"},
     home_files=HF_PLUGIN)
case("misnamed skill of an installed plugin outside the Route table", 1, "hf:gone",
     files={"claude/common/CLAUDE.md": ROUTE + "Then call `hf:gone`; cite `file:line`.\n"}, home_files=HF_PLUGIN)
case("plugin that is one skill at its root passes as a lead skill", 0, "check: ok",
     files={"claude/common/CLAUDE.md": ROUTE + "| Doc | Deliverable flow | `hz` | done |\n"},
     home_files=plugins({"hz": "4.0.0"}, {"hz/4.0.0/SKILL.md": "---\nname: hz\n---\n"}))
case("a skill only an older cached version has does not count", 1, "hf:old",
     files={"claude/common/CLAUDE.md": ROUTE + "| Video | Code flow | `hf:old` | done |\n"},
     home_files=plugins({"hf": "2.0"}, {"hf/1.0/skills/old/SKILL.md": HF, "hf/2.0/skills/hf/SKILL.md": HF}))
case("a cached plugin that is not installed does not count", 1, "hf:hf",
     files={"claude/common/CLAUDE.md": ROUTE + "| Video | Code flow | `hf:hf` | done |\n"},
     home_files=plugins({}, {"hf/1.0/skills/hf/SKILL.md": HF}))
case("model told to call a user-only plugin skill", 1, "/hf:hf",
     files={"claude/common/CLAUDE.md": ROUTE + "| Video | Code flow | `hf:hf` | done |\n"},
     home_files=plugins({"hf": "1.0"}, {"hf/1.0/skills/hf/SKILL.md": "---\nname: hf\ndisable-model-invocation: true\n---\n"}))

case("plugin agent named plugin:agent passes as a lead", 0, "check: ok",
     files={"claude/common/CLAUDE.md": ROUTE + "| Video | Code flow | `hf:scout` agent | done |\n"},
     home_files=plugins({"hf": "1.0"}, {"hf/1.0/agents/scout.md": "---\nname: scout\n---\n"}))
case("user-only plugin skill named bare gets the qualified /plugin:skill fix", 1, "write `/ctx:stats`",
     files={"claude/common/CLAUDE.md": ROUTE + "| Video | Code flow | `stats` | done |\n"},
     home_files=plugins({"ctx": "2.0"}, {"ctx/2.0/skills/stats/SKILL.md": "---\nname: stats\ndisable-model-invocation: true\n---\n"}))
case("plugin the settings declare but this machine lacks is skipped", 0, "check: ok",
     settings=dict(SETTINGS, enabledPlugins={"hf@mk": False}),
     files={"claude/common/CLAUDE.md": ROUTE + "| Video | Code flow | `hf:hf` | done |\n"})
case("plugin prefix neither declared nor installed still fails", 1, "hx:hf",
     settings=dict(SETTINGS, enabledPlugins={"hf@mk": False}),
     files={"claude/common/CLAUDE.md": ROUTE + "| Video | Code flow | `hx:hf` | done |\n"})

# Windows hooks run in the user's project, and CreateProcess searches that cwd before PATH
case("bare program name in a Windows hook", 1, "runs bare 'git'",
     files={"claude/windows/hooks/x.py": 'import subprocess\nsubprocess.run(["git", "status"])\n'})
case("bare program at the head of a concatenated argv", 1, "runs bare 'git'",
     files={"claude/windows/statusline.py": 'import subprocess\nargs = ["x"]\nsubprocess.run(("git", "-C", ".") + tuple(args))\n'})
case("full path, resolved or computed program passes", 0, "check: ok",
     files={"claude/windows/hooks/x.py": 'import os, subprocess, sys\nexe = "x"\nsubprocess.run(["C:/Windows/System32/cmd.exe", "/c"])\n'
            'subprocess.Popen([exe, "a"])\nsubprocess.run([sys.executable, "-I"])\nsubprocess.run([exe] + ["b"])\n'})

case("bare program name in a shared Python hook", 1, "runs bare 'git'",
     files={"claude/common/hooks/py-hook": '#!/usr/bin/env python3\nimport subprocess\nsubprocess.run(["git", "status"])\n'})
case("shared Python hook that resolves the program passes", 0, "check: ok",
     files={"claude/common/hooks/py-hook": '#!/usr/bin/env python3\nimport subprocess\nfrom path_only import which\n'
            'subprocess.run([which("git"), "status"])\n'})

# CI has the repo but not the owner's skills, plugins or settings: --repo-only skips what only that machine can answer
case("--repo-only skips a lead skill that is not installed", 0, "check: ok", args=["--repo-only"],
     files={"claude/common/CLAUDE.md": ROUTE + "| Video | Code flow | `ghost` | done |\n"})
case("--repo-only skips a ~/.claude pointer the repo does not ship", 0, "check: ok", args=["--repo-only"],
     files={"claude/common/CODING_STANDARDS.md": "See `~/.claude/enforcement.md`.\n"})
case("--repo-only still fails a dead bare .md pointer", 1, "enforcement.md", args=["--repo-only"],
     files={"claude/common/CODING_STANDARDS.md": "See `enforcement.md` (AC-09).\n"})

# every hook a settings file calls is described in that OS's README
case("unix settings call a hook README.md does not name", 1, "README.md does not name",
     files={"README.md": "Hooks: `skill-model-invocable`.\n"})
case("docs/hooks.md is the hook page when it exists: a hook only README.md names fails", 1, "docs/hooks.md does not name",
     files={"README.md": "Hooks: `good-hook`, `skill-model-invocable`.\n", "docs/hooks.md": "Hooks: `skill-model-invocable`.\n"})
case("docs/hooks.md names every hook: passes", 0, "check: ok",
     files={"README.md": "See docs.\n", "docs/hooks.md": "Hooks: `good-hook`, `skill-model-invocable`.\n"})
case("README.md names every hook the unix settings call", 0, "check: ok",
     files={"README.md": "Hooks: `good-hook`, `skill-model-invocable`.\n"})
WIN_HOOK = json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "python C:/Users/YOU/.claude/hooks/good-hook"}]}]}})
case("windows settings call a hook the Windows README does not name", 1, "claude/windows/README.md does not name",
     files={"claude/windows/settings.example.json": WIN_HOOK, "claude/windows/README.md": "Ports.\n"})

# agent-no-downgrade's ALLOWED_DROPS and agent-tuning.md's "Drop when" column say the same
DROPS_HOOK = '#!/usr/bin/env python3\nALLOWED_DROPS = {"worker": {"haiku"}, "oracle": {"opus", "sonnet"}}\n'
TUNING = ("| Agent | Default | Why | Raise when | Drop when |\n|---|---|---|---|---|\n"
          "| `explorer` | haiku / medium | recon | sonnet: wide | low: files named |\n"
          "| `worker` | sonnet / medium | writes | — | haiku / medium: mechanical edits |\n"
          "| `oracle` | fable / medium | judgment | — | %s when the Fable limit is exhausted |\n")
case("ALLOWED_DROPS lists a drop agent-tuning.md does not", 1, "oracle",
     files={"claude/common/hooks/agent-no-downgrade": DROPS_HOOK, "claude/common/agent-tuning.md": TUNING % "sonnet / high"})
case("ALLOWED_DROPS matches the Drop when column", 0, "check: ok",
     files={"claude/common/hooks/agent-no-downgrade": DROPS_HOOK, "claude/common/agent-tuning.md": TUNING % "opus / high, else sonnet / high,"})

# a machine that runs pi (~/.pi/agent/settings.json) without this repo's pi package has none of armarium-pi's gates: warn, never fail
PI_PKG = {"pi/package.json": "{}"}
def pi_settings(packages): return {".pi/agent/settings.json": json.dumps({"packages": packages})}
case("pi settings without this repo's pi package: a warning, exit 0", 0, "WARN pi", files=PI_PKG, home_files=pi_settings(["npm:pi-subagents"]))
case("the warning names the install command", 0, "pi install", files=PI_PKG, home_files=pi_settings([]))
case("pi settings list this repo's pi package: no warning", 0, "check: ok", absent="WARN", files=PI_PKG,
     home_files=pi_settings(["npm:pi-subagents", "{HOME}/../repo/pi"]))
case("the package listed as {source}: no warning", 0, "check: ok", absent="WARN", files=PI_PKG,
     home_files=pi_settings([{"source": "{HOME}/../repo/pi", "skills": []}]))
case("no pi on this machine: no warning", 0, "check: ok", absent="WARN", files=PI_PKG)
case("--repo-only: no warning", 0, "check: ok", absent="WARN", args=["--repo-only"], files=PI_PKG, home_files=pi_settings([]))

# a self-test that skips part of its work says so on a line starting with "skip": check counts those files
case("a self-test that skips is counted", 0, "1 self-tests, 1 with a skip",
     files={"claude/common/hooks/test_partial.py": 'print("skip on Windows")\n'})
case("no skip: the count line stays as it was", 0, "check: ok (1 self-tests)",
     files={"claude/common/hooks/test_whole.py": 'print("ok   skip-free")\n'})

# pi: the tiers this machine runs (subagents.agentOverrides) and the ones pi/settings.example.json shows are the same
def overrides(reviewer): return json.dumps({"packages": ["{HOME}/../repo/pi"], "subagents": {"agentOverrides": {
    "reviewer": {"model": reviewer}, "researcher": {"subagentOnlyExtensions": ["{HOME}/.pi/x.js"]}}}})
EXAMPLE = json.dumps({"subagents": {"agentOverrides": {"reviewer": {"model": "opus"}, "researcher": {"subagentOnlyExtensions": ["/Users/YOU/.pi/x.js"]}}}})
case("pi tiers differ from the example: a warning that names the agent", 0, "WARN pi tier of reviewer",
     files=dict(PI_PKG, **{"pi/settings.example.json": EXAMPLE}), home_files={".pi/agent/settings.json": overrides("sonnet")})
case("pi settings with subagents: null do not break the gate", 0, "check: ok", absent="Traceback",
     files=dict(PI_PKG, **{"pi/settings.example.json": EXAMPLE}),
     home_files={".pi/agent/settings.json": json.dumps({"packages": ["{HOME}/../repo/pi"], "subagents": None})})
case("pi contextMode differs from the example: a warning", 0, "WARN pi contextMode differs",
     files=dict(PI_PKG, **{"pi/settings.example.json": json.dumps({"contextMode": {"excludeTools": ["subagent"]}})}),
     home_files={".pi/agent/settings.json": json.dumps({"packages": ["{HOME}/../repo/pi"]})})
case("pi contextMode matches the example: no warning", 0, "check: ok", absent="WARN",
     files=dict(PI_PKG, **{"pi/settings.example.json": json.dumps({"contextMode": {"excludeTools": ["subagent"]}})}),
     home_files={".pi/agent/settings.json": json.dumps({"packages": ["{HOME}/../repo/pi"], "contextMode": {"excludeTools": ["subagent"]}})})
case("pi tiers match the example, home path aside: no warning", 0, "check: ok", absent="WARN",
     files=dict(PI_PKG, **{"pi/settings.example.json": EXAMPLE}), home_files={".pi/agent/settings.json": overrides("opus")})

# CLAUDE.md and pi/AGENTS.md carry the same rules: a commit that stages one without the other gets a warning
def stage(*paths):
    def pre(repo):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}  # under pre-commit, GIT_INDEX_FILE names the real index
        subprocess.run(["git", "-C", repo, "init", "-q"], check=True, env=env)
        subprocess.run(["git", "-C", repo, "add", "--", *paths], check=True, env=env)
    return pre
TWIN = {"pi/AGENTS.md": "Rules.\n"}
case("CLAUDE.md staged without pi/AGENTS.md: a warning", 0, "WARN claude/common/CLAUDE.md is staged without pi/AGENTS.md",
     files=TWIN, pre=stage("claude/common/CLAUDE.md"))
case("pi/AGENTS.md staged without CLAUDE.md: a warning", 0, "WARN pi/AGENTS.md is staged without claude/common/CLAUDE.md",
     files=TWIN, pre=stage("pi/AGENTS.md"))
case("both staged: no warning", 0, "check: ok", absent="WARN", files=TWIN, pre=stage("claude/common/CLAUDE.md", "pi/AGENTS.md"))
case("neither staged: no warning", 0, "check: ok", absent="WARN", files=TWIN, pre=stage("claude/common/CODING_STANDARDS.md"))

# a file added with git add -N is in the work tree bin/check reads, but a commit leaves it out
def stage_ita(staged, ita):
    def pre(repo):
        stage(*staged)(repo)
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        subprocess.run(["git", "-C", repo, "add", "-N", "--", ita], check=True, env=env)
    return pre
ITA = dict(TWIN, **{"claude/common/hooks/test_new.py": "print('ok')\n"})
case("an intent-to-add file beside a staged one fails the gate", 1, "claude/common/hooks/test_new.py is intent-to-add",
     files=ITA, pre=stage_ita(["claude/common/CLAUDE.md", "pi/AGENTS.md"], "claude/common/hooks/test_new.py"))
case("an intent-to-add file with nothing staged passes", 0, "check: ok", files=ITA, pre=stage_ita([], "claude/common/hooks/test_new.py"))
# git -z prints raw UTF-8 paths: D-stroke is C4 90, and 0x90 has no cp1252 character
DSTROKE = "docs/" + chr(0x110) + ".md"
case("an intent-to-add file with a non-ASCII name is named, no traceback", 1, "is intent-to-add", absent="Traceback",
     files=dict(TWIN, **{DSTROKE: "x\n"}), pre=stage_ita(["claude/common/CLAUDE.md", "pi/AGENTS.md"], DSTROKE))

# a self-test that hangs must not hang the commit: it is cut off and reported
case("a self-test that hangs is cut off and fails the gate", 1, "test_hang.py timed out", env={"CHECK_TEST_TIMEOUT": "1"},
     files={"claude/common/hooks/test_hang.py": "import time\ntime.sleep(30)\n"})

# the repo's own pi files: .pi/settings.json and pi/package.json parse, and the local paths they name exist
case("broken JSON in .pi/settings.json", 1, ".pi/settings.json", files={".pi/settings.json": "{"})
case(".pi/settings.json names a local package that is not there", 1, "../nope", files={".pi/settings.json": json.dumps({"packages": ["../nope", "npm:x"]})})
case(".pi/settings.json names the pi package: passes", 0, "check: ok", files=dict(PI_PKG, **{".pi/settings.json": json.dumps({"packages": ["../pi"]})}))
case("pi/package.json names an extension that is not there", 1, "gone.ts", files={"pi/package.json": json.dumps({"pi": {"extensions": ["./gone.ts"]}})})
case("pi/package.json names an extension that exists: passes", 0, "check: ok",
     files={"pi/package.json": json.dumps({"pi": {"extensions": ["./ext/index.ts"]}}), "pi/ext/index.ts": "export default () => {}\n"})

print("FAILS %d of %d" % (fails, total))
sys.exit(1 if fails else 0)
