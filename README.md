# Armarium

My Claude Code setup in one repo: a global `CLAUDE.md`, `settings.json`, hooks, subagents, rules and the notes that go with them. Copy what you like, and tell me what is wrong with the rest.

*Armarium* is Latin for a chest where tools and records are kept. This one holds a rule set and a toolbox.

## What the rules do

`CLAUDE.md` sorts every task into a flow before any work starts.

- A Route table maps each kind of task (code, UI, report, writing, research, video, settings) to a flow, a lead skill and a list of "done when" items.
- Code work follows eight ordered steps: intake, clarify, explore and ripple, plan, delegate, TDD, verify, review.
- Every final reply lists the "done when" items, each marked with its evidence or the reason it failed.
- A separate section covers when to use subagents, how to prompt them, and how to check what they report.

## What is inside

```
claude/                      common/ plus one OS overlay mirrors ~/.claude
├── common/                  every OS
│   ├── CLAUDE.md            the rules
│   ├── CODING_STANDARDS.md  judgement calls a linter cannot make
│   ├── RTK.md               how to read condensed command output
│   ├── agent-tuning.md      why each agent has its model and effort
│   ├── agents/              oracle, reviewer, worker, tester, explorer,
│   │                        researcher, evidence-auditor
│   ├── hooks/               the Python hooks; see below
│   ├── rules/               frontend.md, video.md (stack gates)
│   ├── skills/claude-md-audit/  audits how this config steered a session
│   └── bin/                 sync-runner-tools.mjs, sync-copilot.mjs
├── unix/                    macOS and Linux
│   ├── settings.example.json    opt-in: env, permissions, hooks, plugins, models
│   ├── statusline-command.sh    status line: tokens, cost, limits
│   └── hooks/               the bash hooks; see below
└── windows/                 Python hooks, status line, settings and installer; see claude/windows/README.md
pi/                          the same rule set for the pi coding agent, as a pi package
├── AGENTS.md                the rules, in pi's tool, agent and skill names
├── armarium-pi/index.ts     loads AGENTS.md into every pi run and enforces two of its rules
├── package.json             the package manifest
└── settings.example.json    opt-in: packages, skills, models, subagent tiers
bin/check                    repo gate: self-tests and config checks; .githooks/pre-commit runs it
docs/
└── rule-origins.md          the incident and evidence behind each rule
```

Hooks (each runs only once its entry from `settings.example.json` is in your `settings.json`):

- `agent-no-downgrade` blocks an `Agent` call whose `model` is below that agent's frontmatter model, except the drops listed in `agent-tuning.md`. Self-test: `python3 -I hooks/test_agent_no_downgrade.py`.
- `flow-skill-check` (Stop) blocks the end of a turn once when a `Flow:` line names a skill with no `Skill` call after that line, no `/skill` command that started the task, and no later reply listing it as ✗. It also blocks once when a turn with a Flow line ends on a reply with no ✓ or ✗ line (no Exit list), when a ✓ item names an exception, and when the turn changed files the frontend gate covers but its Flow line has no UI row. Only skill names found under `~/.claude/skills` are checked, so a plugin skill such as `humanizer` is not. Only Flow lines after the last user message are checked, and the final reply is read from the hook's `last_assistant_message` input. Self-test: `python3 -I hooks/test_flow_skill_check.py`.
- `reviewer-gate` (Stop) blocks the end of a turn once when a turn with a Flow line changed more than 200 lines or more than 3 files (markdown and text excluded) and no `reviewer` agent or `code-review` call followed. It also blocks once when a security-only `reviewer` ran although `git rev-parse origin/HEAD` resolves and `security-review` was not called. Self-test: `python3 -I hooks/test_reviewer_gate.py`.
- `bash-ban-raw-tools` blocks raw `cat`, `head`, `tail`, `find`, `grep`, `rg` and `wc` in Bash and points to the dedicated tools. Once `rtk` is installed it lets those readers through, since `rtk` filters their output, and blocks only a `| head` or `| tail` after one. A temporary unlock file lasts 10 minutes.
- `bash-ban-shell-writes` blocks file writes from Bash: a heredoc into a file, `echo`/`printf`/`cat > file`, `sed -i`, `perl -i`, `tee`, and a python script fed on stdin. It lets through a heredoc into a command (`git commit -F -`), log redirects (`make check > log 2>&1`) and `/dev/null`. It shares the unlock file with `bash-ban-raw-tools`. Self-test: `python3 -I hooks/test_bash_ban_shell_writes.py`.
- `run-cli-hook` finds a CLI such as `rtk` when the hook environment has no PATH, and exits 0 if it is not installed.
- `cbm-session-reminder` adds `codebase-memory-mcp` graph context when a session starts, cached per folder until an index changes; a notice such as "no CBM daemon" is shown but never cached. It does nothing if the binary is missing. Self-test: `python3 -I hooks/test_cbm_session_reminder.py`.
- `codemode-ponytail-band` runs at session start when `CLAUDE_CODE_EXPERIMENTAL_CODE_MODE=1`. Code Mode falls back to ordinary tools while a plugin's JS mod checks tool calls, and ponytail ships one (`hooks/claude-band.json`). Removing that entry from the cached `plugin.json` lets Code Mode start; a ponytail update puts it back, and this hook says so. Self-test: `python3 -I hooks/test_codemode_ponytail_band.py`.
- `armarium-links` runs at session start when `~/.claude/CLAUDE.md` is a symlink into a clone of this repo. It links every file the repo tracks under `claude/common/` and `claude/unix/` that `~/.claude` lacks, and reports files there that are copies, without replacing them. A copy install is left alone. Self-test: `python3 -I hooks/test_armarium_links.py`.
- `skill-model-invocable <skill>…` runs at session start and removes `disable-model-invocation: true` from the frontmatter of each skill it names. An update such as `npx skills update` puts the line back, and the next session start removes it again. Self-test: `python3 -I hooks/test_skill_model_invocable.py`.
- `memory-repo-symlink` runs at session start inside a git repo (outside one it does nothing). It moves `~/.claude/projects/<slug>/memory` into `<repo>/.claude/memory` and symlinks it back, so read it before you enable it. A file whose name the repo already has stays where it is, and the link waits until you have merged it by hand. Self-test: `python3 -I hooks/test_memory_repo_symlink.py`. Add `**/.claude/memory/` to your global gitignore first, or the notes get committed with the repo. `CLAUDE.md` (Context) keeps each note to one decision with a `status`, so an old choice is marked `replaced` instead of sitting beside the new one.

`skills/claude-md-audit` is a user-invoked skill (`/claude-md-audit <session-id>`). It reads a session's transcript and checks it against the config the session ran under. The checks cover:

- whether each ✓ in the Exit table has evidence behind it
- whether each test went red before its code was written
- whether any commit range was reviewed twice
- what each model escalation cost in USD

Each finding is filed by layer: CLAUDE.md, rule, skill, agent, hook, plugin or repo. `scripts/session_audit.py` prints the cost per agent and every hook block and tool error. `scripts/wait_quiet.py` waits until a running session and all its subagents go quiet. The rows in `docs/rule-origins.md` under "Changed after watching one real session" came from its first run.

`bin/sync-runner-tools.mjs` keeps the `tools:` list in agent frontmatter in step with your live MCP servers. The agents that list `mcp__` tools need it, and it is optional for the others.

## Requirements

The files above call out to other projects. None of them are copied here.

| What | Used by | Where to get it |
|---|---|---|
| `jq` | hooks | `brew install jq` |
| `python3` | `bash-ban-shell-writes`, `agent-no-downgrade`, `flow-skill-check`, `reviewer-gate`, `skill-model-invocable`, `armarium-links`, `bin/check` | preinstalled on macOS; your package manager elsewhere |
| `rtk` | `settings.example.json` hook, `RTK.md` | `brew install rtk` ([rtk-ai.app](https://www.rtk-ai.app/)) |
| `codebase-memory-mcp` | cbm hooks, the optional code graph in `CLAUDE.md` | [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp), install script in its README |
| `ponytail` plugin | `settings.example.json` | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) |
| `humanizer` plugin | `settings.example.json`, writing flow | [blader/humanizer](https://github.com/blader/humanizer) |
| `context-mode` plugin | `settings.example.json`, tool rules | [mksglu/context-mode](https://github.com/mksglu/context-mode) |
| `context7` plugin | `settings.example.json` (off by default; optional docs lookups) | `claude-plugins-official` marketplace |
| `hyperframes` plugin | Video row in `CLAUDE.md` (off by default) | [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) |
| `lemo-opuscar` plugin | Video row in `CLAUDE.md` (off by default) | [lemomo-ai/lemo-opuscar](https://github.com/lemomo-ai/lemo-opuscar) |

`codebase-memory-mcp` re-indexes git repos when they change. A folder with no git stays at its first index unless you run `index_repository` again or set `config set watch_non_git true`. Each linked git worktree becomes its own permanent index; `config set ignore_worktrees true` skips them.

`settings.example.json` lists the marketplaces and enables the plugins. If one is missing after you merge it, add it with `/plugin marketplace add <owner/repo>` and then `/plugin install`.

The two video plugins are off in user settings. Their skill descriptions take about 1.4k tokens in every session (`claude plugin details <id>`), and only video work needs them. Turn them on in a video project with `claude plugin enable hyperframes@hyperframes --scope project` (or `lemo-opuscar@lemolab`). The command writes the project's `.claude/settings.json`, which overrides the user setting; `/reload-plugins` loads the skills into a session that is already open. `remotion-best-practices` is a plain skill, not a plugin, so user settings hide it with `skillOverrides`; a Remotion project turns it back on with `"skillOverrides": {"remotion-best-practices": "on"}` in its `.claude/settings.json`.

Skills named in `CLAUDE.md`:

| Skills | Source |
|---|---|
| `tdd`, `diagnosing-bugs`, `grill-me`, `wayfinder`, `to-spec`, `to-tickets`, `implement`, `code-review`, `writing-for-agents`, `research` | [mattpocock/skills](https://github.com/mattpocock/skills) |
| `lean-build`, `surgical-patch`, `investigate-first`, `safe-refactor`, `migration` | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |
| `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |
| `remotion-best-practices` | [remotion-dev/skills](https://github.com/remotion-dev/skills) |
| `security-review`, `update-config` | built into Claude Code |
| `artifact-design`, `dataviz` | built into the Claude desktop app |
| `retro` | source not recorded. `claude-md-audit` reads its category list (step 3), so you need your own copy or must edit that step. |
| `review-animations` | [emilkowalski/skills](https://github.com/emilkowalski/skills). It ships with `disable-model-invocation: true`, and the `skill-model-invocable` hook removes that line so the animation review steps in `CLAUDE.md` and `rules/` can call it. |

## Install

Back up `~/.claude` first.

```bash
git clone https://github.com/vixduong/armarium.git
cd armarium
cp -Ri claude/common/. claude/unix/. ~/.claude/
```

`-i` asks before each overwrite. The copy leaves your `settings.json` alone: the repo ships only `settings.example.json`, so nothing changes your permissions until you choose to. Then install the requirements above.

To follow the repo instead of copying it, link each file and enable the `armarium-links` hook, which links files added later. The loop skips a file that already exists in `~/.claude`, so move yours aside first if you want the repo's version:

```bash
git ls-files claude/common claude/unix | grep -v settings.example.json | while read f; do d=~/.claude/${f#claude/*/}; mkdir -p "$(dirname "$d")"; [ -e "$d" ] || ln -s "$PWD/$f" "$d"; done
```

### Pi

`pi/AGENTS.md` carries the same Route table and flows as `claude/common/CLAUDE.md`, written for [pi](https://github.com/earendil-works/pi)'s tools, the `pi-subagents` agents and the skills under `~/.agents/skills`. `pi/` is a pi package. Install it once with `pi install /path/to/armarium/pi` on any OS, or put that path in `packages` in your `settings.json`, as the last entry in `settings.example.json` shows. Pi then loads `pi/armarium-pi/index.ts` from the repo, and before each run it adds `AGENTS.md` to the prompt, ahead of any project `AGENTS.md`, with its `~/.pi/agent/` paths pointed at `claude/common/`. Subagent runs and `--no-context-files` runs skip it, the same as a global `~/.pi/agent/AGENTS.md`. An edit to `AGENTS.md` applies from the next prompt. If an older install left `AGENTS.md`, `CODING_STANDARDS.md`, `RTK.md` or `rules/` in `~/.pi/agent`, remove them: nothing reads them now, and a leftover `AGENTS.md` loads the rules twice. `settings.example.json` is this machine's `settings.json` minus per-machine state. Merge the parts you want by hand and replace `/Users/YOU`. Pi runs none of the Claude Code hooks. In their place, armarium-pi blocks a run's first tool calls (at most two assistant messages' worth) until its `Flow:` line is written, and stops a destructive or credential command (`drop database`, `kill`, `rm -r`, force push, `--no-verify`, a git credential helper) until you say yes. With no UI, as in `pi --print`, that command is blocked and the model has to ask. Both checks match patterns in the command text. They catch the usual spellings, but miss a command hidden in a variable, `eval`, a script file or another language. armarium-pi also registers itself with pi-subagents as a required child extension, so every pi subagent loads it, whatever its agent settings say, and a subagent launch fails if it cannot. A subagent has no UI, so a matched command is always blocked there, even if the parent agent approves it. Agents that run an external CLI (`claude-code`, `codex-exec`, `cursor-agent`) or on another machine cannot load a pi extension, so pi-subagents refuses to launch them while armarium-pi is loaded. The other rules depend on the model alone.

Before you commit here, run `git config core.hooksPath .githooks` once, so `bin/check` runs on each commit.

Settings are opt-in. `settings.example.json` sets `defaultMode` to `auto` and turns on `skipDangerousModePermissionPrompt` and `skipAutoPermissionPrompt`, so Claude Code stops asking before many actions. It also pins my model choices (`haiku` as default, `claude-opus-5-5` as advisor). Copy into your own `settings.json` only the blocks you want, at least the `hooks` block if you want the hooks to run.

## Read before you copy
- `CLAUDE.md` points at `~/.claude/commands/`, `~/.claude/skills/` and `~/.claude/projects/`. Those are folders on my machine, not files in this repo.
- `claude-md-audit` writes its reports to `/Users/Shared/claude-evals/` and adds rows to `~/projects/armarium/docs/rule-origins.md`. Change both paths in its step 7. Its prices in `session_audit.py` date from November 2026.
- I run macOS and zsh, and I have not tested any of this on Linux or Windows.

## Feedback

Issues and pull requests are welcome. I most want opinions on three things: the Route table and its "done when" column, the review rules in step 8 of the code flow, and the model and effort tiers in `agent-tuning.md`.

## License

MIT for the files in this repo. The plugins and skills in the tables belong to their authors and carry their own licenses.
