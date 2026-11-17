# armarium
- Gate: `bin/check` runs every self-test plus the config checks (settings paths, pointers, user-only skills). `.githooks/pre-commit` runs it; enable per clone with `git config core.hooksPath .githooks`.
- `claude/` mirrors `~/.claude`; on this machine its files are symlinked there, so an edit is live in every session at once.
