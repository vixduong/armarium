# Requirements

The files above call out to other projects. None of them are copied here.

| What | Used by | Where to get it |
|---|---|---|
| `jq` | hooks | `brew install jq` |
| `python3` | `bash-ban-shell-writes`, `agent-no-downgrade`, `flow-skill-check`, `reviewer-gate`, `skill-model-invocable`, `armarium-links`, `bin/check`, armarium-pi's shell-write check | preinstalled on macOS; your package manager elsewhere |
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
