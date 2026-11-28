---
name: claude-md-audit
description: "Judge how well CLAUDE.md and its config (rules, agents, hooks, plugins) steered a session, and propose fixes."
disable-model-invocation: true
---

A retrospective on the **config**, not the code: for one or more sessions, find where `~/.claude/CLAUDE.md` and what it pulls in (rules, skills, agents, `agent-tuning.md`, hooks, plugins, settings) steered the agent wrong, cost more than it earned, or was never triggered. Every finding pairs a **claim** with its **evidence** from the transcript.

## Steps

1. **Load** `writing-for-agents` (Skill tool). Every fix you propose edits a document an agent reads.

2. **Collect facts.** Session ids come from the user. The current session as the target → tell the user to run `/claude-md-audit <id>` from a new session, and stop: an audit in place rereads the whole work context on every request. A session still running → wait first: `scripts/wait_quiet.py <transcript> [pid]` with Bash `run_in_background`. Never pause a session by signal: `SIGSTOP` on a foreground TUI does not resume. Then run:
   ```bash
   python3 -I ~/.claude/skills/claude-md-audit/scripts/session_audit.py <session-id>
   ```
   It prints per agent: cost in USD and its mix, first-request and peak context, REPL, Poll-only, context-mode and CBM calls, folds received. For the main thread: the `Flow:` lines, Skill and Agent calls, instruction files loaded, hook messages, blocks and tool errors. With `--turns` it adds a row per prompt (cost, context range, Poll-only requests, whether a `Flow:` line came first, skills called before the first write); with `--exits`, each turn's Done-when list. Done when the table's total and the commit range of the work are written down.

3. **Read the config as the session saw it**: `~/.claude/CLAUDE.md`, the project `CLAUDE.md`, every rule file, agent `.md` and skill `SKILL.md` the session loaded, `~/.claude/agent-tuning.md`, and the hooks block of `~/.claude/settings.json`. Edited since? Use `git log` in `~/projects/armarium` to get the version the session ran under.

4. **Run every check** below, group by group, against the transcript. Done when each check has a verdict: ✓, ✗ with evidence, or n/a with a reason.

5. **File each ✗** under one of retro's categories (read `~/.claude/skills/retro/SKILL.md` step 3) and one **layer**: CLAUDE.md, rule file, skill, agent, hook, plugin/harness, or repo. The layer decides where the fix goes.

6. **Propose fixes.**
   - A mechanical failure (a fixed pattern, a missing ignore, a banned command) gets a hook or check, not prose.
   - A judgement failure gets one sentence, in the single place that owns that rule; a sentence that adds to a rule names the sentence it merges with or replaces. Two instructions that conflict get resolved in one of them, never both.
   - A fix whose gain and cost only a run can weigh (a plugin, a hook, a model or effort choice) → an A/B kit under `~/projects/armarium-audits/evals/`, run with `/eval-kit`; the kit's verdict decides, not the audit.
   - A removal candidate (any number of sessions): a rule whose row in `docs/rule-origins.md` sits in a `## Changed after …` section with one session as evidence, with 5 or more later sections and no report under `/Users/Shared/claude-evals/session-*/report.md` written after it that names the rule. Every such heading counts as one section; a section's date is the `git log` date of the commit that added its heading. A candidate with no row is listed as "no row".
   - Evidence from one session (n = 1) goes under "Still open", not into a rule. Once the user has the report, each such item becomes an issue: `gh issue create --repo vixduong/armarium-audits --label audit`.

7. **Report** to `/Users/Shared/claude-evals/session-<id8>/report.md`, never inside the project repo. Sections in this order:
   - outcome and cost table
   - checks table: one block per group with its yes/no answer, then every check, its verdict (✓, ✗, n/a) and evidence
   - findings, most severe first, each with evidence (transcript line or `file:line`) and its fix
   - what to remove: step 6's removal candidates and the Never triggered ones, each with its row in `docs/rule-origins.md`; an empty section says so
   - what worked
   - still open

   It is a Report row: a `reviewer` re-derives the headline numbers from the raw `.jsonl`, then `humanizer` runs on the final text. The user picks which fixes to apply. For each fix applied, add a row to `~/projects/armarium/docs/rule-origins.md`, in a new section `## Changed after the <id8> session audit` placed right before `## Still open`: one intro sentence with the report path, then the table.

## Checks

Four groups, each a question the report answers; a group with any ✗ answers no.

### Flow: did the agent walk the route CLAUDE.md sets, and does its Exit table tell the truth?

- **Route**: a `Flow:` line before the first tool call names a real row. Each lead skill is a `Skill` call made before the first code `Write`/`Edit`. A name that appears only in prose is not a call.
- **Plan gates**: `oracle` called for a one-way door unless an approved doc settled it (cite the doc). A plan in a risk area went to `reviewer`.
- **TDD**: per worker and per behavior, the order of test write, test run with its failure reason, and code write. Read the run output: an exit 1 from a collection error or a refused DB connection is not red. Red evidence that arrives only after the code (guard removed, test re-run) counts as partial.
- **Verification**: the main re-ran the gate itself rather than trusting a worker's report.
- **Reviews**: list each review agent with the commit range it covered. The same range reviewed twice is cost to explain. Security review: the branch CLAUDE.md step 8 picks, and its fallback when the skill fails.
- **Exit honesty**: open the evidence behind every ✓ in the final Done-when table. Where the table cites a gate (`rules/frontend.md` step 4, `rules/video.md`), compare it with everything that gate demands: widths, states, frames. A ✓ the evidence does not cover is the most severe finding.
- **Missing Done-when items**: a CLAUDE.md step the agent broke that no Done-when item covers, so the Exit table never showed it (e.g. step 6 red-first).

### Cost and cache: what did each request carry, how much of it was reused, and who spent the money?

- **Cost sinks**: the three biggest agents by USD. Main thread context per request; recon or fix rounds the main did itself.
- **Models**: every per-call `model` against `agent-tuning.md`. Price each escalation in USD and set it against what it found (P0/P1 count).
- **Context load**: each agent's `ctx0` against sessions of the same mode (Code Mode main ≈37k tokens, classic ≈75k, measured 2026-11-23). In `loaded`, a CLAUDE.md outside `~/.claude` and the project (`~/.nvm`, a plugin cache) → `claudeMdExcludes`. A `peak` near `autoCompactWindow` means the work outgrew one session.
- **Cache hit**: per agent, hit rate = `cache_read` / (`cache_read` + `cache_wr`), both columns of the cost table; the main thread's rate goes in the report. Cache write and cache read are the price of context, and a write costs 1.25× to 2× input where a read costs a fraction of it. A subagent starts cold, so its first request is all write: judge it by whether reads overtake writes as `req` grows. Give every `cold cache write` line on the main, and every agent past 5 requests whose `cache_wr` exceeds its `cache_read`, a cause read from the transcript at that time: an idle gap past the TTL (`gap_min`; 5 min or 1 h), a foreground wait that long (an agent, a build, Poll), a resume or `/compact`, a prefix change (`/model`, an MCP server connecting or dropping), or subagents spawned for work one context held. ✗ when the config asked for the wait or the spawn, layer by the rule that asked; the user away → n/a.
- **Code Mode**: Poll-only requests each re-read the whole context to wait; price them. Subagents without `repl` calls follow the non-REPL route in `## Tools`: check it covered them.

### Plugins and hooks: did each rewrite, fold or block help the agent that received it?

- **Plugins, main vs subagent**: per agent, context-mode and CBM calls against `folds`. An agent with folds and no `ctx_search` ignored them: its prompt or the `## Tools` route it follows lacks the step. A hook message repeated across sessions (e.g. "no CBM daemon") is a stale hook or cache, layer hook.
- **Plugins in Code Mode**: list every plugin, CLI hook (`rtk`) and pi extension that rewrites, folds or denies tool calls, with its matchers (the plugin's `hooks/*.json`, `settings.json`, `~/.pi/agent/extensions/`) and what its README or skill tells the agent. A REPL `$` or `file()` call reaches them as a Bash or Read call with an id starting `repl_`, and its output goes to a script, not to the model. Each rewrite, fold or denial a script then parsed or wrote is a finding, layer plugin: rtk's `ok <cmd>` or `[+N hidden: rtk recall …]`, a context-mode pointer in place of the data, a Read denial on `file()`. So is a doc that assumes the model reads the output. pi: the same for `codemode`'s `tools.bash` under the rtk extension.
- **Friction**: each hook block, fold, denial or tool error, traced to its layer. A block repeated by the same agent means that agent's prompt lacks the rule. The script's `hook blocks` are real and distinct. Its other event counts are upper bounds: Code Mode repeats a result inside its REPL event, so count distinct commands before quoting a number.

### Config health: which instructions conflict, went unused, or are already on file?

- **Conflicts**: a skill step against a CLAUDE.md step (e.g. `/implement` → `code-review` vs step 8). Note which one the agent followed.
- **Memory**: memory files in `loaded` carry the frontmatter CLAUDE.md `## Context` asks for. A decision the session made that no memory file or ADR holds is a missed save; a memory restating what the repo holds is load to cut.
- **Never triggered** (two or more sessions): rules, agents, hooks or plugin tools with zero hits. These are candidates for retro's no-ops category.
- **Open issues**: `gh issue list --repo vixduong/armarium-audits --label audit --state open`, each one against this session. Seen again → comment with the evidence; a second session moves it out of "Still open" into a proposed fix. The session ran under its fix → say whether the fix held, and close it if it did. Else n/a.
