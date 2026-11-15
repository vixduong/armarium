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
claude/                      mirrors ~/.claude
├── CLAUDE.md                the rules
├── CODING_STANDARDS.md      judgement calls a linter cannot make
├── RTK.md                   how to read condensed command output
├── agent-tuning.md          why each agent has its model and effort
├── settings.json            env, permissions, hooks, plugins, models
├── statusline-command.sh    status line: tokens, cost, limits
├── agents/                  oracle, reviewer, worker, tester, explorer,
│                            researcher, evidence-auditor, codebase-memory x3
├── hooks/                   see below
├── rules/                   frontend.md, video.md (stack gates)
└── bin/                     sync-runner-tools.mjs, sync-copilot.mjs
```

Hooks:

- `bash-ban-raw-tools` blocks raw `cat`, `head`, `tail`, `find`, `grep`, `rg` and `wc` in Bash and points to the dedicated tools. A temporary unlock file lasts 10 minutes.
- `run-cli-hook` finds a CLI such as `rtk` when the hook environment has no PATH, and exits 0 if it is not installed.
- `cbm-session-reminder` and `cbm-subagent-reminder` add `codebase-memory-mcp` context when a session or subagent starts. They do nothing if the binary is missing.
- `memory-repo-symlink` runs at session start inside a git repo. It moves `~/.claude/projects/<slug>/memory` into `<repo>/.claude/memory` and symlinks it back, so read it before you enable it.

`bin/sync-runner-tools.mjs` keeps the `tools:` list in agent frontmatter in step with your live MCP servers. The agents that list `mcp__` tools need it, and it is optional for the others.

## Requirements

The files above call out to other projects. None of them are copied here.

| What | Used by | Where to get it |
|---|---|---|
| `jq` | hooks | `brew install jq` |
| `rtk` | `settings.json` hook, `RTK.md` | `brew install rtk` ([rtk-ai.app](https://www.rtk-ai.app/)) |
| `codebase-memory-mcp` | cbm hooks, three agents | [DeusData/codebase-memory-mcp](https://github.com/DeusData/codebase-memory-mcp), install script in its README |
| `ponytail` plugin | `settings.json` | [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) |
| `humanizer` plugin | `settings.json`, writing flow | [blader/humanizer](https://github.com/blader/humanizer) |
| `context-mode` plugin | `settings.json`, tool rules | [mksglu/context-mode](https://github.com/mksglu/context-mode) |
| `context7` plugin | `settings.json`, docs lookups | `claude-plugins-official` marketplace |

`settings.json` already lists the marketplaces and enables the plugins. If one is missing after you copy it, add it with `/plugin marketplace add <owner/repo>` and then `/plugin install`.

Skills named in `CLAUDE.md`:

| Skills | Source |
|---|---|
| `tdd`, `diagnosing-bugs`, `grill-me`, `wayfinder`, `to-spec`, `to-tickets`, `implement`, `code-review`, `writing-for-agents`, `research` | [mattpocock/skills](https://github.com/mattpocock/skills) |
| `lean-build`, `surgical-patch`, `investigate-first`, `safe-refactor`, `migration` | [JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman) |
| `ui-ux-pro-max` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) |
| `remotion-best-practices` | [remotion-dev/skills](https://github.com/remotion-dev/skills) |
| `security-review`, `update-config` | built into Claude Code |
| `artifact-design`, `dataviz` | built into the Claude desktop app |
| `review-animations` | a local skill with no public source, so it is not here. The animation review steps in `CLAUDE.md` and `rules/` call it, and you need your own version for them to work. |

## Install

Back up `~/.claude` first.

```bash
git clone https://github.com/vixduong/armarium.git
cd armarium
cp -Ri claude/. ~/.claude/
```

`-i` asks before each overwrite. If you already have a `settings.json`, merge it by hand instead of replacing it. Then install the requirements above.

## Read before you copy

- `settings.json` sets `defaultMode` to `auto` and turns on `skipDangerousModePermissionPrompt` and `skipAutoPermissionPrompt`. That suits how I work, and it may not suit you. It also pins my model choices (`haiku` as default, `claude-opus-5-5` as advisor).
- `CODING_STANDARDS.md` came from a larger project. It mentions `enforcement.md`, rule IDs such as R07 and AC-05, and a `--wb-*` token set, none of which are in this repo. Treat those as examples to rewrite.
- `CLAUDE.md` points at `~/.claude/commands/`, `~/.claude/skills/` and `~/.claude/projects/`. Those are folders on my machine, not files in this repo.
- I run macOS and zsh, and I have not tested any of this on Linux or Windows.

## Feedback

Issues and pull requests are welcome. I most want opinions on three things: the Route table and its "done when" column, the review rules in step 8 of the code flow, and the model and effort tiers in `agent-tuning.md`.

## License

MIT for the files in this repo. The plugins and skills in the tables belong to their authors and carry their own licenses.
