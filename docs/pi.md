# Pi

`pi/AGENTS.md` carries the same Route table and flows as `claude/common/CLAUDE.md`, written for [pi](https://github.com/earendil-works/pi)'s tools, the `pi-subagents` agents and the skills under `~/.agents/skills`. `pi/` is a pi package.

## Install

Install it once with `pi install /path/to/armarium/pi` on any OS, or put that path in `packages` in your `settings.json`, as the last entry in `settings.example.json` shows. Check with `pi list`: until the package is listed there, no pi run has any of the checks below. The repo's own `.pi/settings.json` does not count for `pi --print`, which ignores project files unless you pass `--approve`.

## What it loads

Pi then loads `pi/armarium-pi/index.ts` from the repo, and before each run it adds `AGENTS.md` to the prompt, ahead of any project `AGENTS.md`, with its `~/.pi/agent/` paths pointed at `claude/common/`. Subagent runs and `--no-context-files` runs skip it, the same as a global `~/.pi/agent/AGENTS.md`. An edit to `AGENTS.md` applies from the next prompt. If an older install left `AGENTS.md`, `CODING_STANDARDS.md`, `RTK.md` or `rules/` in `~/.pi/agent`, remove them: nothing reads them now, and a leftover `AGENTS.md` loads the rules twice.

## Settings

`settings.example.json` is this machine's `settings.json` minus per-machine state. Merge the parts you want by hand and replace `/Users/YOU`.

## Checks

Pi runs none of the Claude Code hooks. In their place, armarium-pi blocks a run's first tool calls (at most two assistant messages' worth) until its `Flow:` line is written, and stops a destructive or credential command (`drop database`, `kill`, `rm -r`, force push, `--no-verify`, a git credential helper) until you say yes. With no UI, as in `pi --print`, that command is blocked and the model has to ask. A `bash` call made from a `codemode` script is checked the same way, and so is a `write` or `edit` into a `.git` directory. armarium-pi also hands every `bash` command to `claude/common/hooks/bash-ban-shell-writes`, the hook Claude Code runs, and blocks the command when the hook does; this needs `python3` or `python` on PATH, and without it the command runs unchecked. A `reviewer` or `oracle` subagent gets the hook's read-only rules: no file write from `bash` at all. When a run whose `Flow:` line names a row other than `answer directly` ends on a reply with no ✓ or ✗ line, armarium-pi gives it one more turn with a reminder, once per prompt; what the list says is not checked.

## Limits

The `Flow:` and command checks match patterns in the text. They catch the usual spellings, but miss a command hidden in a variable, `eval`, a script file or another language.

## Subagents

armarium-pi also registers itself with pi-subagents as a required child extension, so every pi subagent loads it, whatever its agent settings say, and a subagent launch fails if it cannot. A subagent has no UI, so a matched command is always blocked there, even if the parent agent approves it. Agents that run an external CLI (`claude-code`, `codex-exec`, `cursor-agent`) or on another machine cannot load a pi extension, so pi-subagents refuses to launch them while armarium-pi is loaded. The other rules depend on the model alone.
