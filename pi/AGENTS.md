# Rules

## Route: the first line of every task
Write `Flow: <row>` before the first tool call (a chat answer that calls no tool needs none; one that calls tools writes `Flow: answer directly`), then follow that flow; backticks in that line go only around skills you will load; a skill only a later branch may need stays bare. Several deliverables → one row each. Rows name the deliverable, not your phase: planning, building, fixing, reviewing or judging a video is the `Video` row, lead skill included (same for UI). Animation inside an app's UI (CSS, a canvas chart) is the UI row; a picture drawn by code (3D scene, illustration, shader background) is the Scene row, and the page around it the UI row. Trivial (1 file, typo/rename/config value, no behavior change; a bug fix takes at least the Small flow) → Clarify, Ripple, Verify of the Code flow only.

A skill is loaded with `read` on its SKILL.md (path in the skills list); that read is the skill call.

| Task | Flow | Lead skill, loaded before the first draft or line of code | Done when (every item true, with evidence) |
|---|---|---|---|
| Code: feature, bug, refactor, migration | Code flow | per step 1 | gate command green and it ran the changed tests (skip count stated) · every P0/P1 fixed; a P0 found → the P0-only re-check ran · step 8 reviews ran (Small: skipped) · diff has untrusted input or auth/secrets → the security review ran · each behavior's test seen red before its code (it ran and failed an assertion on the missing behavior; a compile error or a run with no test is not red), else ✗ with the reason · every acceptance check the plan lists ran, else ✗ with the reason · diff Big → the contract is named: the spec, ticket or plan step 1 was given, else the plan file, current with the last fix round, with its gate command |
| Git: commit, push, merge, rebase, tag | run only the op asked; files outside the request (uncommitted or unrelated), a failing hook, an auth or remote error → stop and ask | none | only the asked op ran, else ✗ with what stopped it · `git status` before and after shown · nothing outside the request staged |
| Plan or spec only (someone else codes) | Code flow steps 1, 3, 4 | per step 1 | plan names every file, the gate command, and independent acceptance checks · risk area → `reviewer` ran on the plan; one-way door → `oracle` ran, or the approved doc that settles it is cited |
| UI in a repo: page, component, canvas or WebGL tool | Code flow + `~/.pi/agent/rules/frontend.md` | none required; design skills optional per frontend gate | every width and state frontend gate step 4 lists shot and viewed; one missing → ✗ · motion in the diff → `review-animations` ran, Small included |
| Scene by code in a repo: 3D or WebGL scene, illustration, shader or generative background | `~/.pi/agent/rules/scene.md`: the look first; Code flow and its track skill start for the scene's systems after step 5's first look review | none; a reference video or link → suggest `/video-ref` | the reference pack's paths and the target look named · the hero still and the reference viewed in one call, every named element judged · a look-only `reviewer` call saw both: its P1s fixed, P2s listed · a frame strip viewed for each moving element |
| Report, analysis | Deliverable flow | chart → frontend gate item 7 | every number traces to source + calculation; totals reconcile; unit, period, exclusions stated · a `reviewer` call re-derived the headline numbers and claims from the raw data |
| Writing, doc, message | Deliverable flow | `humanizer` on the final text | the intake note names reader and purpose (`file:line` or the message that says it); `humanizer` ran on the version delivered |
| Agent docs: AGENTS.md, CLAUDE.md, skill, agent `.md`, prompt | Deliverable flow | `writing-for-agents` | every pointer target `ls`-verified; `wc -l` no higher than before, or the growth and its reason stated · `git diff` removes only lines you meant to remove |
| Research | Deliverable flow | `research`, or `researcher` agent | each decision-relevant claim cites a source you opened; unverified claims listed |
| Question answered in chat, no file change | answer directly | a fact a source holds (the repo's code, a library or version, a price, pi itself) → that source first: read the code; docs per `## Tools`; pi → its docs (paths in the system prompt); else `web_search`. General knowledge → answer | each such claim comes from a source opened this session, or the answer marks it unchecked |
| Video | rendered by code → Code flow as `~/.pi/agent/rules/video.md` adapts it; else Deliverable flow | by code → its toolchain skill per `~/.pi/agent/rules/video.md` (read it before the first line); design skills optional · code review → `review-animations` | output probed · no blank frame · one frame per transition viewed · reading time fits every scene |
| Pi settings, extensions, packages | Code flow, Small | pi docs: `settings.md`, `extensions.md`, `packages.md` | settings file parses (`jq empty`) · `/reload` or a fresh `pi --print` shows the change took |

Every row whose output has prose a person reads (report, page, doc, message) also ends with `humanizer` on the delivered version.
**Exit**: every final reply except a chat answer, a short bug-fix reply included, lists the row's Done-when items, each ✓ with its evidence (command, `file:line`, skill read) or ✗ with the reason; an item with any exception is ✗, the exception its reason. A skill's evidence is its SKILL.md `read` after the `Flow:` line that names it, or the user's `/skill:name` command that started the task; a name in the `Flow:` line is not a read. A lead skill left out appears there as ✗. No hook enforces this: you are the check.

## Principles
DRY/KISS/YAGNI/SSOT. Ask before destructive.
- **Think first**: state assumptions. Several readings → present them. Simpler path exists → say so.
- **Surgical**: every changed line traces to the request. Code judgement calls → `~/.pi/agent/CODING_STANDARDS.md`.
- **Goal-driven**: turn the task into a check that can fail ("fix bug" → test reproduces it, then passes). Loop until it passes.
- **Fail → change approach.** A diagnosed failure stays fixed: reuse the command that worked.

## Deliverable flow (non-code)
1. **Intake**: reader, purpose, and the acceptance check written down before the first draft. Ambiguous → ask in the reply and end the turn; as a subagent → `contact_supervisor`; headless → write the assumption where the task says.
2. **Lead skill**: load the row's skill(s) now, before drafting.
3. **Draft**, then **look**: render or read the final form the reader gets (page, PNG frames, the doc itself).
4. **Exit** per Route.

## Code flow (MANDATORY, IN ORDER; skipped a step → restart from it)
**Big** = >3 files, or >200 changed lines, or touches auth/permission, money, migration, public API, concurrency.
**Small** = ≤2 files and ≤80 changed lines, not Big, no untrusted input or auth/secrets → steps 1–3, 6, 7 (one track); skip 4, 5, 8. Neither Big nor Small → Small's steps plus step 8.
**Untrusted input** = data another party can set (request, CLI arg, env, uploaded or repo file, browser storage or URL, queue message, DB rows users wrote, LLM output) that the diff parses or passes to a sink: SQL, shell, file path, HTML or template (`innerHTML`, `v-html`, `dangerouslySetInnerHTML`), `eval`, deserializer (`pickle`, `yaml.load`), redirect URL, or a loop or allocation sized by it. Repo config counts only when it reaches a sink.

1. **Intake**: spec, ticket, or approved plan given → it is the contract: its acceptance criteria are the check; skip 2, 4 and track choice. The Route row's lead skill and step 6 still run before the first line of code. Code that must differ from the contract → record the deviation in code and the final reply; edit the contract only after the user agrees, also when the contract itself is wrong.
   Otherwise pick ONE track (bug fix plus feature → feature); its skill leads: feature → `lean-build` + `tdd` · bug, cause known → `surgical-patch` · bug, cause unknown or perf → `diagnosing-bugs` (`investigate-first` if intermittent), then `surgical-patch` · refactor → `safe-refactor` · schema/API/data transition → `migration` · video/animation rendered by code → `~/.pi/agent/rules/video.md` (its toolchain skill leads) · file of stack X → its gate in `~/.pi/agent/rules/`.
   User-only skills (suggest in one line): goal unclear → `/skill:grill-me`; larger than one session → `/skill:wayfinder`; settled → `/skill:to-spec` → `/skill:to-tickets` → `/skill:implement`.
2. **Clarify**: ambiguous → ask in the reply and end the turn. Headless → write the assumption where the task says, then continue.
3. **Explore + Ripple**: any add/change/remove → the list of every site the change must reach: text search for the symbol and its string refs (config, templates, dynamic dispatch). Refactor or signature change in an indexed repo → also the code graph's `trace_path` inbound (`## Tools`). "Only used here" is a claim to verify.
4. **Plan**: a plan file: approach + files from step 3 + trade-offs + the check per step; it is the reviewer's contract. Ask for approval in the reply only when the user must decide: the plan narrows or departs from the request, a one-way door, or a risk area. A review-fix round extends the plan file.
   - Each acceptance check runs on its own (command + expected output); the implementer's own tests are never the only check for a behavior.
   - One gate command for lint + typecheck + test + build exists (`pnpm run check` or the stack's equivalent); the plan adds it if missing.
   - One-way door (architecture, library, data model, public contract) not settled by an approved spec/ADR/plan → `oracle` on the plan. A spec you are writing settles nothing yet.
   - Otherwise a risk area (auth/permission, money, migration, concurrency) → `reviewer` reviews the plan. Code starts after findings are in the plan.
5. **Delegate**: per `## Subagents`. A subagent runs steps 3, 6, 7 only. Plan spans ≥2 independent layers and >10 files → one `worker` per layer, plan as contract.
6. **TDD**: each behavior's failing test is seen red before its code, fix rounds included; the `tdd` skill is required only when step 1's track names it. Happy + fail + the edge cases that apply (empty/null/boundary/concurrency/tz/unicode/overflow/permission/network/partial). Pure presentation is checked by eye per the frontend gate. The test lives in the repo's test tree and goes into the same commit as the code; a script in `/tmp` is not a test.
7. **Verify**: the gate command passes; re-run the step 3 search: every site updated; UI change → screenshots per the frontend gate; rendered video → frames per the video gate. Fail → fix root cause.
8. **Review**: after 7 is green; each range reviewed once (a review `/skill:implement` already ran counts; its closing `code-review` covers only commits no earlier review covered).
   - Diff not Small → `reviewer` ← changed files + acceptance criteria (a plan or acceptance file another agent wrote counts as criteria). A spec or ticket a person wrote → `code-review` instead. Last open ticket of a spec → `code-review` on the whole spec range.
   - Untrusted input or auth/secrets → also a security review, whatever the size: a separate `reviewer` call with a security-only task on the same diff (`security-audit` skill as its guide), never folded into the general review.
   - Animation in the diff → also `review-animations`: UI per frontend gate step 6, rendered video per video gate step 5.
   - Model: `reviewer` runs on the tier pi settings `subagents.agentOverrides` pin: opus, thinking no lower than the main session's `defaultThinking` (high in `settings.example.json`), since pi sets no thinking per call; hard to undo (auth/permission, secrets, money, migration) → one level above that. A review that still missed a bug → one tier up.
   - Fix every P0/P1 → back to 7; a P0 was found → one P0-only re-check. Still P0 after 2 rounds → stop and report. A P0/P1 you cannot fix (it needs access, an environment or a decision you lack) stays ✗ in Exit, naming what it needs and from whom. P2 → list in the final reply.

**New gate** for a stack or medium: `rules/<name>.md` in armarium's `claude/common/`; first line names the toolchain skill to load FIRST if the stack has one, then a numbered self-check; add its row to Route.

## Tools
- **Text search**: in a git repo `git grep -n`; else `rg`/`find` through `bash`.
- **Run/read**: one script that prints only the answer. >20 lines of data → `ctx_execute` (`file` for a big file/log), `ctx_batch` for >1 command, `codemode` to chain or filter tool calls. Pass absolute paths and `git -C <repo>`.
- **context-mode** (pi extension) rewrites any tool result over 4 KB into a search pointer: read it with the `ctx_search` call the pointer gives; rerunning the command folds again. A result that feeds a write (a file, an issue, a PR body) goes to a file first and is transformed there by a script: a folded result is the pointer, not the data. A `read` with `offset`/`limit` stays whole; a `read` of a file over 16 KB with no range is denied. `.md` files under `~/.pi/agent` and `~/.agents/skills` are never folded or denied, so a SKILL.md read arrives whole. A tool listed in settings `contextMode.excludeTools` keeps its full output.
- **Code graph (CBM), optional**: `~/.local/bin/codebase-memory-mcp cli <tool>` (flags = schema args in kebab-case); missing → text search.
- **Docs/web**: library/API docs → `web_search`; a page → `fetch_content`; a claim to check → `source_check`.
- **Files**: write with `edit`/`write`, never shell redirects; read a big file with `read` `offset`/`limit`.
- **zsh**: `$cmd` holding "pnpm ci" does not word-split (exit 127); call each command directly or use the repo script.
- **RTK** (pi extension): every `bash` call, `codemode`'s `tools.bash` included, is rewritten to `rtk <cmd>` and condensed; unfiltered → `rtk proxy <cmd>`. `ctx_execute` and `ctx_batch` run raw. Details: `~/.pi/agent/RTK.md`.
- **Hooks** (armarium-pi): a tool call before your `Flow:` line is blocked. A `bash` command that writes a file (`echo`/`printf`/`cat > file`, heredoc into a file, `sed -i`, `perl -i`, `tee`, a python script on stdin) is blocked: use `write`/`edit`; a log redirect (`make check > log 2>&1`) runs. As a `reviewer` or `oracle` subagent, `bash` writes no file at all. A destructive or credential command (drop, kill, `rm -r`, force push, `--no-verify`, credential helper), and a `write` or `edit` into a `.git` directory, waits for the user's yes; with no UI it is blocked, so ask in the reply. In a pi subagent a matched command is always blocked: run it yourself after the user's yes. A final reply with no ✓ or ✗ line, after a `Flow:` row other than `answer directly`, gets one reminder turn. These are pattern checks on your text: "Ask before destructive" still binds you. Head, tail, cat and what the Exit list says are not checked: those rules hold because you keep them.

## Subagents
Main = coordinator: integrates + verifies. Model and thinking per agent live in pi settings `subagents.agentOverrides`.
- **Delegate**: online research, refactor >2 files, summarize >1 file, audit, unknown-repo recon, big log triage. Inline: one chain of dependent steps, work that fits one context.
- **Parallel**: max 3 (`workflow: "parallel"`); serial if dependent or same file; risky parallel writes → `worktree: true`.
- **Wait**: next step needs the result → `async: false`. An async run wakes the session itself: never poll it.
- **Prompt**: self-contained, <500 tok: goal + named files/symbols + constraint + acceptance check + return format. A `subagent` result is not folded (settings `contextMode.excludeTools`); pi-subagents cuts a long one and names the file that holds all of it: `read` that file. A diff goes in as a range the agent runs (`git diff <base> <sha>`; uncommitted work → the SHA `python3 -I ~/.claude/bin/snapshot.py` (Windows: `python`) prints, so later edits leave the range fixed), never pasted. A claim resting on a web page → save the page to the scratchpad and name its path: `reviewer` and `oracle` have no web tool.
- **Pick** by description: `scout` = recon, `worker` = edits and verify-only test runs, `oracle` = decisions (~once per run), `reviewer` = review, `researcher` = web; `evidence-auditor` before a decision rests on `researcher` claims.
- **Report = claim**: check the diff, re-run cited evidence, confirm the acceptance check passed.

## Replies
Plain verbs, concrete nouns, numbers over adjectives. Answer first. Bullets > prose. Mermaid when diagram > prose. Deliverables follow their skill's style.

## Context
After compaction → `ctx_resume`. Long task: checkpoint progress to its plan or report file. Project `AGENTS.md` overrides this file; read it and `architecture.md` before cross-cutting work. Architecture decisions go to the repo's `docs/adr/`.
