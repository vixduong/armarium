# Skills and scripts

`skills/claude-md-audit` is a user-invoked skill (`/claude-md-audit <session-id>`). It reads a session's transcript and checks it against the config the session ran under. The checks cover:

- whether each ✓ in the Exit table has evidence behind it
- whether each test went red before its code was written
- whether any commit range was reviewed twice
- what each model escalation cost in USD

Each finding is filed by layer: CLAUDE.md, rule, skill, agent, hook, plugin or repo. `scripts/session_audit.py` prints the cost per agent and every hook block and tool error. `scripts/wait_quiet.py` waits until a running session and all its subagents go quiet. The rows in `docs/rule-origins.md` under "Changed after watching one real session" came from its first run.

`bin/sync-runner-tools.mjs` keeps the `tools:` list in agent frontmatter in step with your live MCP servers. The agents that list `mcp__` tools need it, and it is optional for the others.

`bin/check` is the repo gate: it runs every self-test and the config checks listed at the top of the file. `.githooks/pre-commit` runs it, and `.github/workflows/check.yml` runs `bin/check --repo-only` on Linux, macOS and Windows.

`bin/hook-diff` prints the commands of `bin/hook-corpus.jsonl` that a hook in the work tree judges differently from `HEAD`. Run it after you edit a gate and before a review.
