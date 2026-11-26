# armarium
- Gate: `bin/check` runs every self-test plus the config checks (settings paths, pointers, user-only skills). `.githooks/pre-commit` runs it; enable per clone with `git config core.hooksPath .githooks`.
- `claude/common/` (shared) plus one OS overlay mirror `~/.claude`. macOS/Linux: `common/` and `unix/` are symlinked there, so an edit is live at once. Windows: `claude/windows/install.ps1 -Apply` copies `common/` then `windows/`, so re-run it after an edit.
- `pi/AGENTS.md` is the pi edition of `claude/common/CLAUDE.md`, in pi's tool, agent and skill names. A rule change in one goes into the other in the same commit.
