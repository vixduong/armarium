# Armarium

My Claude Code setup in one repo: a global `CLAUDE.md`, `settings.json`, hooks, subagents, rules and the notes that go with them. Copy what you like, and tell me what is wrong with the rest.

*Armarium* is Latin for a chest where tools and records are kept. This one holds a rule set and a toolbox.

## What the rules do

`CLAUDE.md` sorts every task into a flow before any work starts.

- A Route table maps each kind of task (code, UI, scene, report, writing, research, video, settings) to a flow, a lead skill and a list of "done when" items.
- Code work follows eight ordered steps: intake, clarify, explore and ripple, plan, delegate, TDD, verify, review.
- Every final reply lists the "done when" items, each marked with its evidence or the reason it failed.
- A separate section covers when to use subagents, how to prompt them, and how to check what they report.

Hooks enforce the rules a model tends to skip. `agent-no-downgrade`, `flow-skill-check`, `reviewer-gate`, `write-fold-guard`, `bash-ban-raw-tools` and `bash-ban-shell-writes` block a tool call or the end of a turn; five more run at session start, and `run-cli-hook` finds a CLI such as `rtk` for the others. [docs/hooks.md](docs/hooks.md) says what each one does, and [docs/rule-origins.md](docs/rule-origins.md) records the incident behind each rule.

## What is inside

```
claude/common/    shared by every OS: CLAUDE.md, CODING_STANDARDS.md, agent-tuning.md,
                  agents/, hooks/, rules/, skills/
claude/unix/      macOS and Linux: bash hooks, status line, settings.example.json
claude/windows/   Python ports of those hooks, status line, installer
pi/               the same rule set for the pi coding agent, as a pi package
bin/              check (the repo gate) and hook-diff
docs/             the detail this page leaves out
```

`claude/common/` plus one OS folder mirror `~/.claude`.

| Read | For |
|---|---|
| [docs/hooks.md](docs/hooks.md) | what each hook blocks or does, and its self-test |
| [docs/requirements.md](docs/requirements.md) | the tools, plugins and skills the files call, and where to get them |
| [docs/tools.md](docs/tools.md) | the `claude-md-audit` skill, `bin/check`, `bin/hook-diff` and the sync scripts |
| [docs/pi.md](docs/pi.md) | installing the pi package and what it checks |
| [claude/windows/README.md](claude/windows/README.md) | the Windows install and its known gaps |
| [docs/rule-origins.md](docs/rule-origins.md) | the incident and evidence behind each rule |

## Install

Back up `~/.claude` first.

```bash
git clone https://github.com/vixduong/armarium.git
cd armarium
cp -Ri claude/common/. claude/unix/. ~/.claude/
```

`-i` asks before each overwrite. The copy leaves your `settings.json` alone: the repo ships only `settings.example.json`, so nothing changes your permissions until you choose to. Then install the [requirements](docs/requirements.md).

To follow the repo instead of copying it, link each file and enable the `armarium-links` hook, which links files added later. The loop skips a file that already exists in `~/.claude`, so move yours aside first if you want the repo's version:

```bash
git ls-files claude/common claude/unix | grep -v settings.example.json | while read f; do d=~/.claude/${f#claude/*/}; mkdir -p "$(dirname "$d")"; [ -e "$d" ] || ln -s "$PWD/$f" "$d"; done
```

Settings are opt-in. `settings.example.json` sets `defaultMode` to `auto` and turns on `skipDangerousModePermissionPrompt` and `skipAutoPermissionPrompt`, so Claude Code stops asking before many actions. It also pins my model choices (`haiku` as default, `claude-opus-5-5` as advisor). Copy into your own `settings.json` only the blocks you want, at least the `hooks` block if you want the hooks to run.

Windows and pi have their own steps: [claude/windows/README.md](claude/windows/README.md) and [docs/pi.md](docs/pi.md).

Before you commit here, run `git config core.hooksPath .githooks` once, so `bin/check` runs on each commit.

## Read before you copy
- `CLAUDE.md` points at `~/.claude/commands/`, `~/.claude/skills/` and `~/.claude/projects/`. Those are folders on my machine, not files in this repo.
- `claude-md-audit` writes its reports to `/Users/Shared/claude-evals/` and adds rows to `~/projects/armarium/docs/rule-origins.md`. Change both paths in its step 7. Its prices in `session_audit.py` date from November 2026.
- I run macOS and zsh. CI runs the self-tests on Linux and Windows; I have not used the setup there.

## Feedback

Issues and pull requests are welcome. I most want opinions on three things: the Route table and its "done when" column, the review rules in step 8 of the code flow, and the model and effort tiers in `agent-tuning.md`.

## License

MIT for the files in this repo. The plugins and skills in the tables belong to their authors and carry their own licenses.
