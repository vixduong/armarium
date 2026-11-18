---
name: claude-md-audit
description: "Judge how well CLAUDE.md and its config (rules, agents, hooks, plugins) steered a session, and propose fixes."
disable-model-invocation: true
---

A retrospective on the **config**, not the code: for one or more sessions, find where `~/.claude/CLAUDE.md` and what it pulls in (rules, skills, agents, `agent-tuning.md`, hooks, plugins, settings) steered the agent wrong, cost more than it earned, or was never triggered. Every finding pairs a **claim** with its **evidence** from the transcript.

## Steps

1. **Load** `writing-for-agents` (Skill tool). Every fix you propose edits a document an agent reads.

2. **Collect facts.** Session ids come from the user, or default to the current session. A session still running → wait first: `scripts/wait_quiet.py <transcript> [pid]` with Bash `run_in_background`. Never pause a session by signal: `SIGSTOP` on a foreground TUI does not resume. Then run:
   ```bash
   python3 -I ~/.claude/skills/claude-md-audit/scripts/session_audit.py <session-id>
   ```
   It prints cost per agent in USD, the `Flow:` lines, Skill and Agent calls, hook blocks, folds and tool errors. Done when the table's total and the commit range of the work are written down.

3. **Read the config as the session saw it**: `~/.claude/CLAUDE.md`, the project `CLAUDE.md`, every rule file, agent `.md` and skill `SKILL.md` the session loaded, `~/.claude/agent-tuning.md`, and the hooks block of `~/.claude/settings.json`. Edited since? Use `git log` in `~/projects/armarium` to get the version the session ran under.

4. **Run every check** in the list below against the transcript. Done when each check has a verdict: ✓, ✗ with evidence, or n/a with a reason.

5. **File each ✗** under one of retro's categories (read `~/.claude/skills/retro/SKILL.md` step 3) and one **layer**: CLAUDE.md, rule file, skill, agent, hook, plugin/harness, or repo. The layer decides where the fix goes.

6. **Propose fixes.**
   - A mechanical failure (a fixed pattern, a missing ignore, a banned command) gets a hook or check, not prose.
   - A judgement failure gets one sentence, in the single place that owns that rule.
   - Two instructions that conflict get resolved in one of them, never both.
   - Evidence from one session (n = 1) goes under "Still open", not into a rule.

7. **Report** to `/Users/Shared/claude-evals/session-<id8>/report.md`, never inside the project repo. Sections in this order:
   - outcome and cost table
   - findings, most severe first, each with evidence (transcript line or `file:line`) and its fix
   - what worked
   - still open

   It is a Report row: a `reviewer` re-derives the headline numbers from the raw `.jsonl`, then `humanizer` runs on the final text. The user picks which fixes to apply. For each fix applied, add a row to `~/projects/armarium/docs/rule-origins.md`.

## Checks

- **Route**: a `Flow:` line before the first tool call names a real row. Each lead skill is a `Skill` call made before the first code `Write`/`Edit`. A name that appears only in prose is not a call.
- **Exit honesty**: open the evidence behind every ✓ in the final Done-when table. Where the table cites a gate (`rules/frontend.md` step 4, `rules/video.md`), compare it with everything that gate demands: widths, states, frames. A ✓ the evidence does not cover is the most severe finding.
- **Missing Done-when items**: a CLAUDE.md step the agent broke that no Done-when item covers, so the Exit table never showed it (e.g. step 6 red-first).
- **TDD**: per worker and per behavior, the order of test write, test run with its failure reason, and code write. Read the run output: an exit 1 from a collection error or a refused DB connection is not red. Red evidence that arrives only after the code (guard removed, test re-run) counts as partial.
- **Plan gates**: `oracle` called for a one-way door unless an approved doc settled it (cite the doc). A plan in a risk area went to `reviewer`.
- **Reviews**: list each review agent with the commit range it covered. The same range reviewed twice is cost to explain. Security review: the branch CLAUDE.md step 8 picks, and its fallback when the skill fails.
- **Models**: every per-call `model` against `agent-tuning.md`. Price each escalation in USD and set it against what it found (P0/P1 count).
- **Conflicts**: a skill step against a CLAUDE.md step (e.g. `/implement` → `code-review` vs step 8). Note which one the agent followed.
- **Cost sinks**: the three biggest agents by USD. Main thread context per request; recon or fix rounds the main did itself.
- **Friction**: each hook block, fold, denial or tool error, traced to its layer. A block repeated by the same agent means that agent's prompt lacks the rule. The script's event counts are upper bounds: Code Mode repeats a result inside its REPL event, so count distinct commands before quoting a number.
- **Verification**: the main re-ran the gate itself rather than trusting a worker's report.
- **Never triggered** (two or more sessions): rules, agents or hooks with zero hits. These are candidates for retro's no-ops category.
