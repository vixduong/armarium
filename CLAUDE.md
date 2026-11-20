# armarium
- Gate: `bin/check` runs every self-test plus the config checks (settings paths, pointers, user-only skills). `.githooks/pre-commit` runs it; enable per clone with `git config core.hooksPath .githooks`.
- `claude/` mirrors `~/.claude`. macOS: files are symlinked there, so an edit is live at once. Windows: `windows/install.ps1 -Apply` copies them, so re-run it after an edit.
