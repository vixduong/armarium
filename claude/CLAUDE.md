# Rules

## Route: the first line of every task
Write `Flow: <row>` before the first tool call (a question answered in chat needs none), then follow that flow; backticks in that line go only around skills you will call. Several deliverables → one row each. Rows name the deliverable, not your phase: planning, building, fixing, reviewing or judging a video is the `Video` row, lead skill included (same for UI and Artifact). Animation inside an app's UI (CSS, canvas, WebGL scene) is the UI row. Trivial (1 file, typo/rename/config value, no behavior change; a bug fix always takes the full flow) → Clarify, Ripple, Verify of the Code flow only.

| Task | Flow | Lead skill, invoked before the first draft or line of code | Done when (every item true, with evidence) |
|---|---|---|---|
| Code: feature, bug, refactor, migration | Code flow | per step 1 | gate command green and it ran the changed tests (skip count stated) · every P0/P1 fixed, then the P0-only re-check ran · step 8 reviews ran · diff has untrusted input or auth/secrets → `security-review` ran · each behavior's test seen red before its code (it ran and failed an assertion on the missing behavior; a compile error or a run with no test is not red), else ✗ with the reason · every acceptance check the plan lists ran, else ✗ with the reason |
| Plan or spec only (someone else codes) | Code flow steps 1, 3, 4; the plan file replaces plan mode | per step 1 | plan names every file, the gate command, and independent acceptance checks · risk area → `reviewer` ran on the plan; one-way door → `oracle` ran, or the approved doc that settles it is cited |
| UI page or component in a repo | Code flow + `~/.claude/rules/frontend.md` | `ui-ux-pro-max` | every width and state frontend gate step 4 lists shot and viewed; one missing → ✗ |
| Artifact, page, dashboard | Deliverable flow + frontend gate items 4, 5, 7 | `artifact-design`; chart or stat tile → `dataviz` | published, and the rendered page viewed at 375 px and desktop |
| Report, analysis | Deliverable flow | chart → `dataviz` | every number traces to source + calculation; totals reconcile; unit, period, exclusions stated · a `reviewer` call re-derived the headline numbers and claims from the raw data |
| Writing, doc, message | Deliverable flow | `humanizer` on the final text | the intake note names reader and purpose (`file:line` or the message that says it); `humanizer` ran on the version delivered |
| Agent docs: CLAUDE.md, skill, agent `.md`, prompt | Deliverable flow | `writing-for-agents` | every pointer target `ls`-verified; `wc -l` no higher than before, or the growth and its reason stated · `git diff` removes only lines you meant to remove |
| Research | Deliverable flow | `research`, or `researcher` agent | each decision-relevant claim cites a source you opened; unverified claims listed |
| Question answered in chat, no file change | answer directly | a fact a source holds (the repo's code, a library or version, a price, Claude itself) → that source first: read the code; docs per `## Tools`; `claude-api` or `claude-code-guide` agent; else WebSearch. General knowledge → answer | each such claim comes from a source opened this session, or the answer marks it unchecked |
| Video | rendered by code → Code flow + `~/.claude/rules/video.md`, where a HyperFrames or Lemo-Opuscar skill's own loop replaces steps 4 and 6; else Deliverable flow | Remotion project or batch renders from data → `remotion-best-practices` + `lean-build` + `tdd` · film in a named Lemo-Opuscar style → `lemo-opuscar:lemo-opuscar` · any other video by code → `hyperframes:hyperframes` · all three are off by default; missing → in the video repo run `claude plugin enable hyperframes@hyperframes` (or `lemo-opuscar@lemolab`) `--scope project`, or for Remotion set `"skillOverrides": {"remotion-best-practices": "on"}` in `.claude/settings.json`, then the user runs `/reload-plugins` · not by code → `ui-ux-pro-max` · code review → `review-animations` | output probed · no blank frame · one frame per transition viewed · reading time fits every scene |
| Claude Code settings, hooks, permissions | `update-config` | `update-config` | settings file parses (`jq empty`) |

Every row whose output has prose a person reads (report, page, doc, message) also ends with `humanizer` on the delivered version.
**Exit**: every final reply except a chat answer, a short bug-fix reply included, lists the row's Done-when items, each ✓ with its evidence (command, `file:line`, skill call) or ✗ with the reason; an item with any exception is ✗, the exception its reason. A skill's evidence is its `Skill` tool call after the `Flow:` line that names it, or the user's `/skill` command that started the task; a name in the `Flow:` line is not a call. A lead skill left out appears there as ✗.

## Principles
DRY/KISS/YAGNI/SSOT. Ask before destructive.
- **Think first**: state assumptions. Several readings → present them. Simpler path exists → say so.
- **Surgical**: every changed line traces to the request. Code judgement calls → `~/.claude/CODING_STANDARDS.md`.
- **Goal-driven**: turn the task into a check that can fail ("fix bug" → test reproduces it, then passes). Loop until it passes.
- **Fail → change approach.** A diagnosed failure stays fixed: reuse the command that worked.

## Deliverable flow (non-code)
1. **Intake**: reader, purpose, and the acceptance check written down before the first draft. Ambiguous → `AskUserQuestion`; headless → write the assumption where the task says.
2. **Lead skill**: invoke the row's skill(s) now, before drafting.
3. **Draft**, then **look**: render or read the final form the reader gets (published page, PNG frames, the doc itself).
4. **Exit** per Route.

## Code flow (MANDATORY, IN ORDER; skipped a step → restart from it)
**Big** = >3 files, or >200 changed lines, or touches auth/permission, money, migration, public API, concurrency.
**Untrusted input** = the diff parses data from a user, file (repo config included when its values reach HTML, CSS or a shell), or network, or renders raw HTML (`dangerouslySetInnerHTML`, `innerHTML`, `v-html`, `eval`).

1. **Intake**: spec, ticket, or approved plan given → it is the contract: its acceptance criteria are the check; skip 2, 4 and track choice. The Route row's lead skill (UI → `ui-ux-pro-max`) and step 6 still run before the first line of code. Code that must differ from the contract → record the deviation in code and the final reply; edit the contract only after the user agrees, also when the contract itself is wrong.
   Otherwise pick ONE track; its skill leads: feature → `lean-build` + `tdd` · bug, cause known → `surgical-patch` · bug, cause unknown or perf → `diagnosing-bugs` (`investigate-first` if intermittent), then `surgical-patch` · refactor → `safe-refactor` · schema/API/data transition → `migration` · video/animation rendered by code → the Video row's lead skill + `~/.claude/rules/video.md` · file of stack X → its gate in `~/.claude/rules/`.
   User-only skills (suggest in one line): goal unclear → `/grill-me`; larger than one session → `/wayfinder`; settled → `/to-spec` → `/to-tickets` → `/implement`.
2. **Clarify**: ambiguous → `AskUserQuestion`. Headless → write the assumption where the task says, then continue.
3. **Explore + Ripple**: any add/change/remove → the list of every site the change must reach: text search for the symbol and its string refs (config, templates, dynamic dispatch). Refactor or signature change in an indexed repo → also the code graph's `trace_path` inbound (`## Tools`). "Only used here" is a claim to verify.
4. **Plan**: non-trivial → `EnterPlanMode`: approach + files from step 3 + trade-offs + the check per step.
   - Each acceptance check runs on its own (command + expected output); the implementer's own tests are never the only check for a behavior.
   - One gate command for lint + typecheck + test + build exists (`pnpm run check` or the stack's equivalent); the plan adds it if missing.
   - One-way door (architecture, library, data model, public contract) not settled by an approved spec/ADR/plan → `oracle` on the plan. A spec you are writing settles nothing yet.
   - Otherwise a risk area (auth/permission, money, migration, concurrency) → `reviewer` reviews the plan. Code starts after findings are in the plan.
5. **Delegate**: per `## Subagents`. A subagent runs steps 3, 6, 7 only. Plan spans ≥2 independent layers and >10 files → one `worker` per layer, plan as contract.
6. **TDD**: each behavior's failing test is seen red before its code, fix rounds included; the `tdd` skill is required only when step 1's track names it. Happy + fail + the edge cases that apply (empty/null/boundary/concurrency/tz/unicode/overflow/permission/network/partial). Pure presentation is checked by eye per `rules/frontend.md`.
7. **Verify**: the gate command passes; re-run the step 3 search: every site updated; UI change → screenshots per `rules/frontend.md`; rendered video → frames per `rules/video.md`. Fail → fix root cause.
8. **Review**: after 7 is green; each range reviewed once (a review `/implement` already ran counts; `/implement`'s closing `code-review` covers only commits no earlier review covered).
   - Diff Big → `reviewer` ← changed files + acceptance criteria (a plan or acceptance file another agent wrote counts as criteria). A spec or ticket a person wrote → `code-review` instead. Last open ticket of a spec → `code-review` on the whole spec range.
   - Untrusted input or auth/secrets → also a security review, whatever the size: `git rev-parse origin/HEAD` succeeds in the cwd → `security-review`; otherwise, or when it fails → a separate `reviewer` call with a security-only prompt on the same diff, never folded into the general review.
   - Animation in the diff → also `review-animations`: UI per frontend gate step 6, rendered video per video gate step 5.
   - Model: every `reviewer` call runs at least on the tier that wrote the code, capped at opus (main session on opus → `model: "opus"`), and at least opus when hard to undo (auth/permission, secrets, money, migration), whatever the size; otherwise its default sonnet/high. A review that still missed a bug → one tier up per `~/.claude/agent-tuning.md`.
   - Fix every P0/P1 → back to 7 → one P0-only re-check. Still P0 after 2 rounds → stop and report. A P0/P1 you cannot fix (it needs access, an environment or a decision you lack) stays ✗ in Exit, naming what it needs and from whom. P2 → list in the final reply.

**New gate** for a stack or medium: `~/.claude/rules/<name>.md`, `paths:` frontmatter, first line `Invoke <skill> FIRST`, then a numbered self-check; add its row to Route.

## Tools
- **Code graph (CBM), optional**: its tools are deferred, so load first (`ToolSearch` `select:mcp__codebase-memory-mcp__<tool>`). `Transport closed` / `MCP error -32000` → same tool via `~/.local/bin/codebase-memory-mcp cli <tool>` (flags = schema args in kebab-case) in `ctx_execute(shell)`, or fall back to text search.
- **Text search**: in a git repo `git grep -n` (no zsh glob, passes the `| head` ban); else `Grep`/`Glob` when listed, else `grep -rn`/`find` inside `ctx_execute(shell)`.
- **Run/read → context-mode**: `ctx_execute` prints only the answer (`file` for a big file/log); `ctx_batch` for >1 command; `ctx_search` for recall.
- **Docs/web**: library/API docs → WebSearch.
- **Files**: write with `Edit`/`Write`, scratchpad and `/tmp` included. The hook `bash-ban-shell-writes` blocks shell writes in Bash; it cannot see `ctx_execute`, so code run there never writes a file either. A file you must read whole (to rewrite or humanize it) → `Read` with `offset`/`limit`: context-mode folds a bare Read over 2 KB into a search pointer. In a REPL script the same cap hits `file().text()`, `edit()` and `$` output: read with `file().slice()` or `sed -n`, edit with `tools.Edit`, and send long `$` output to a scratchpad log (`cmd > log 2>&1`) to read with `file().slice()`; `| head` and `| tail` are blocked.
- **Shell is zsh**: `$cmd` holding "pnpm ci" does not word-split (exit 127); call each command directly or use the repo script.
- **RTK**: Bash runs as `rtk <cmd>`; unfiltered → `rtk proxy <cmd>`. Details: `~/.claude/RTK.md`.

## Subagents
Main = coordinator: integrates + verifies. Agents pin `model`+`effort`; changing one → read `~/.claude/agent-tuning.md` first.
- **Delegate**: online research, refactor >2 files, summarize >1 file, audit, unknown-repo recon, big log triage. Inline: one chain of dependent steps, work that fits one context.
- **Parallel**: max 3; serial if dependent or same file; risky parallel writes → `isolation: worktree`.
- **Wait**: next step needs the result → run the agent in the foreground. `ScheduleWakeup` belongs to `/loop` only.
- **Prompt**: self-contained, <500 tok: goal + named files/symbols + constraint + acceptance check + return format. A diff goes in as a range the agent runs (`git diff <base>`), never pasted: output hooks shorten pasted text.
- **Pick** by description: `explorer` over `Explore`; `Plan` = steps, `oracle` = decisions (~once per run, own Fable limit); `evidence-auditor` before a decision rests on `researcher` claims.
- **Report = claim**: check the diff, re-run cited evidence, confirm the acceptance check passed.

## Replies
Plain verbs, concrete nouns, numbers over adjectives. Answer first. Bullets > prose. Mermaid when diagram > prose. Deliverables follow their skill's style.

## Context
Post-`/compact`: re-discover tools via `ToolSearch`. Long task: checkpoint progress to its plan or report file. Project `CLAUDE.md` overrides this file; read it and `architecture.md` before cross-cutting work.
- **Memory** (auto-memory) holds one decision per file: the decision, its reason, and `status: active` or `replaced → <name>` in the frontmatter. A changed decision is a new file, and the old one gets `replaced`. Architecture decisions go to the repo's `docs/adr/`. Before acting on a note, check it is `active`.
