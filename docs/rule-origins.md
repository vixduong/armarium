# Rule origins

Why each rule exists: the bug or incident behind it, the evidence, and what the evidence says about keeping it. A reviewer suggested this file after the first public post. Rules are easier to cut safely when you can see what each one was guarding against.

The evidence comes from two runs of the same eval, done in November 2026, on a private Django + React repo. Each run did two tasks (a backend feature slice and an animated login page) twice: once with this config ("full") and once with no user config at all ("bare"). Each run had one sample per cell (n = 1), so a single number here is a hint at most. Both arms passed every hidden test case in both runs; the differences below are in process and cost.

Rules with no recorded origin are not listed yet. Add a row whenever you add or change a rule.

## Changed after the eval

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| Exit: a skill counts only as a `Skill` tool call (`CLAUDE.md` Route, Exit) | A fix agent marked its lead skill ✓ in the final checklist without ever calling it; it had only named the skill in its `Flow:` line | run 2, fix agent of the UI task | Exit now says a name in the `Flow:` line is not a call |
| "Done when" items must point to a command or a `file:line` (`CLAUDE.md` Route) | Two items could be ticked with nothing to show: "reader + purpose named first" and "line budget kept" (no number) | review of the table after a Reddit comment | Both reworded so each names its evidence |
| Ripple: text search, graph only for refactors (`CLAUDE.md` step 3, Tools) | The rule made `index_status` and `trace_path` mandatory; no agent ever called them | 0 of 13 full-arm agents across both runs; 3 graph calls in 28 days of normal use | Graph made optional; listing every site the change reaches stays mandatory |
| `reviewer` for agent-written criteria, `code-review` only for a person's spec (`CLAUDE.md` step 8) | The rule said "spec exists → `code-review`"; every agent with a plan from another agent picked `reviewer` instead | 0 of 4 `code-review` calls | Wording now matches what agents did |
| Security review: check `git remote` first (`CLAUDE.md` step 8) | `security-review` failed in a clone with no remote (it needs `origin/HEAD`); in run 2 the security check was folded into the general review | run 1 and run 2, backend task | Remote → `security-review`; none → a separate security-only `reviewer` call |
| Opus by risk of undo, not by review type (`CLAUDE.md` step 8) | Step 8 sent risky diffs to sonnet and moved to opus only after a missed bug, which contradicted `agent-tuning.md` | a Reddit comment; `agent-tuning.md` line 10 | Auth, secrets, money and migration diffs go to opus whatever their size |
| Agents escalate, never downgrade (`agent-tuning.md`, `hooks/agent-no-downgrade`) | A Reddit commenter's agents handed hard reviews to a cheap model on their own, and they found out only from the bug that got through. My own logs had 10 unlisted drops: `oracle` to opus once, `general-purpose` to sonnet 9 times | 254 local transcripts | Per-call `model` may only go up, except the "Drop when" cells; a hook blocks the rest |
| Settings are opt-in (`settings.example.json`, README Install) | The install command copied `settings.json` without asking on a fresh machine, so a reader who missed the warning got `auto` mode and both permission-skip flags | a Reddit comment | The repo ships `settings.example.json`; the README says to merge the blocks you want |
| Memory holds decisions with a status (`CLAUDE.md` Context, README hooks) | A commenter warned that session-written memory fills with notes that contradict each other. My own project memory had one note that was a session log: its index line said "week stop 0.6", its body said 0.9, and the run used 0.95 | a Reddit comment; my schools project memory | One decision per note with `status: active` or `replaced → <name>`; progress goes to plan files; the README says to gitignore `.claude/memory` |
| `review-animations` for UI motion (`rules/frontend.md` step 6) | The rule lived only in the video gate, which UI work never loads | called 1 of 2 times in run 1, 0 of 2 in run 2 | Moved into the frontend gate; the video gate keeps its own step |
| Shell writes blocked by a hook (`hooks/bash-ban-shell-writes`, `CLAUDE.md` Tools) | The prose rule "write files with Edit/Write only" was followed 5 of 8 times; no hook enforced it. Without the rule, agents wrote 36 and 24 files through heredocs | run 2 full arm, run 1 bare arm | New hook blocks heredoc-into-file, `echo`/`printf`/`cat > file`, `sed -i`, `perl -i`, `tee`, and python on stdin. The prose line now only says what to use instead |
| Lines a hook already enforces removed (`CLAUDE.md` Tools) | "Read big files with offset" and "URL → `ctx_index`" are both blocked by the context-mode plugin's hooks | both blocks seen in normal sessions | Lines deleted |

## Changed after the Code Mode eval

A separate eval on 2026-11-16 compared Code Mode off and on: 5 small synthetic tasks, 2 runs per arm (5 for the `.env` task), 26 interactive Sonnet sessions in auto mode.

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| PreToolUse hook timeouts 15s (`settings.example.json`) | Under Code Mode, a PreToolUse hook that times out refuses the call even without `onFailure`, and every Bash call runs four hooks in series at 5s each | Code Mode docs, "Tool call refused by a hook"; 0 hook failures in 26 sessions at 15s | `timeout` 5 → 15 on the four PreToolUse hooks |
| Code Mode on, ponytail band watched (`settings.example.json` env, `hooks/codemode-ponytail-band`) | Code Mode would not start while ponytail's band mod was registered. With it removed: about 17% lower cost (cache read −33%, output −44%), 3 parallel commands in 18.5s instead of 35.6s, same pass rate. The band removal lives in the plugin cache, so an update undoes it silently | all 5 tasks passed in both arms; smoke runs with and without the band | Env var set; a session-start hook warns when the band is back |
| Report: a `reviewer` re-derives the headline numbers (`CLAUDE.md` Route, Report row) | The eval report nearly shipped with a doubled block count, a denial count stuck at 0, a "30% saving" that was mostly cheap cache reads (about 17% by cost), a wrong cause for the `.env` leak, and a fix that needs a sandbox the config does not enable. The author caught the first two; an outside review caught the rest | `code-mode-v1/results/report.md` before and after | Report row's done-when adds an independent re-derivation |
| Read a file whole with `offset`/`limit` (`CLAUDE.md` Tools, Files) | `humanizer` in file mode must read the whole file. A bare `Read` of a 5.7 KB report came back as a `ctx_search` pointer, with no hint to page it. This is the case the removed line did not cover: the hook stops a big Read but does not say how to get the text when you need all of it | one humanizer run in the same session | One clause added to the Files line |

## Changed after watching one real session

One session on 2026-11-16 built a full slice (plan, backend, frontend, reviews) in a private Django + React repo: sonnet main, 10 subagents, about $12.40 at API prices. The facts come from its transcript, read with the `claude-md-audit` skill's script, and a `reviewer` re-derived the numbers.

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| Code Done-when: test seen red first (`CLAUDE.md` Route) | Step 6 asks for red before code, but no Done-when item named it, so the Exit table never showed a miss. In the session, one app's tests first ran after its code was written; one guard made a test hang instead of fail, another had no red at all | backend worker transcript; its own red list | New item: each behavior's test seen red before its code, else ✗ with the reason |
| UI Done-when: every width and state (`CLAUDE.md` Route) | The Exit marked "screenshots viewed ✓" with no loading-state shot, which frontend gate step 4 asks for | screenshot scripts in the main transcript | The item now names every width and state in step 4; one missing is ✗ |
| `/implement`'s `code-review` covers only unreviewed commits (`CLAUDE.md` step 8) | The skill ends with `code-review` on the whole range, so the backend got an Opus `reviewer` pass and then two `code-review` agents plus a security pass on the same commits | review prompts and their ranges | Step 8 limits the closing `code-review` to commits no earlier review covered |
| `reviewer` knows the `\| head` hook (`agents/reviewer.md`) | A `code-review` agent was blocked twice by `bash-ban-raw-tools` while paging a diff | that agent's transcript | One Scope line: size with `git diff --stat`, then read per file |

## Changed after the 2026-11-17 session audit

One `/implement` session on 2026-11-17 in a private Spring/Oracle workspace: sonnet main and one `reviewer`, $4.10 at the audit script's prices. A `reviewer` re-derived the numbers from the transcript. Report: `claude-evals/session-6a542f78/report.md` (local).

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| Gate must run the changed tests (`CLAUDE.md` Route, Code Done-when) | The Exit marked the gate ✓ with `skipped=124`; per the session's final reply, the skips were the e2e classes it edited, because Docker was down | transcript: final reply table; `docker ps` failure | Done-when now reads "gate command green and it ran the changed tests (skip count stated)" |
| P0-only re-check after a P1 fix (`CLAUDE.md` Route, Code Done-when) | Step 8 asks for it; the agent skipped it and still marked "step 8 reviews ran ✓" with a footnote | transcript: final reply table | Done-when now reads "every P0/P1 fixed, then the P0-only re-check ran" |
| Deviation from the contract is recorded, not edited in (`CLAUDE.md` step 1) | The agent changed an error code in the spec it was implementing, to match its code, without asking | transcript: `Edit` on `specs/sibft-sim.md` | One sentence: record the deviation in code and the final reply; edit the contract only after the user agrees |
| REPL file helpers and the context-mode cap (`CLAUDE.md` Tools, Files) | `file().text()` and `edit()` on files over 2 KB were refused or silently matched nothing; seen in the audited session and the audit session itself | transcripts of both sessions | One sentence: read with `file().slice()` or `sed -n`, edit with `tools.Edit` |

## Changed after the 51f24d34 session audit

A second `/implement` session on 2026-11-17 (same workspace, sonnet main, $5.40) ran under the rules from the section above. A `reviewer` re-derived the numbers. Report: `claude-evals/session-51f24d34/report.md` (local).

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| Reviewer model follows step 8 inside `code-review` (`skills/code-review` step 4, not in this repo) | A `DROP TABLE` migration was reviewed by `/implement`'s `code-review`, whose two reviewers ran sonnet with no `model`; step 8 asks for opus on a migration, and the Exit still said "Review ✓" | transcript: the two `Agent` calls, the Exit table | One sentence in the skill: each reviewer takes the `model` step 8 gives the diff |
| Lead skills named in `Flow:` must be called (`hooks/flow-skill-check`, Stop) | The Flow line named `lean-build` + `tdd`; neither was called, and the Exit had no lead-skill row | transcript: `Skill` calls (only `code-review`) | A Stop hook blocks once until the skill is called or listed as ✗ |
| Contract edits need the user's agreement even when the contract is wrong (`CLAUDE.md` step 1) | Under the new rule the agent recorded the deviation but still edited the gateway spec, judging the spec itself wrong | transcript: two `Edit` calls on `specs/sibft-gateway-core.md` | Sentence extended: "also when the contract itself is wrong" |

## Changed after the 2026-11-17 config review

A static read of the repo against the installed `~/.claude`, done with the `writing-for-agents` skill.

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| The model can call `review-animations` (`hooks/skill-model-invocable`, `settings.example.json` SessionStart) | Upstream ships the skill with `disable-model-invocation: true`, so the model could never call it, and `flow-skill-check` would block a `Flow:` line naming it. `skillOverrides` can only hide a skill, not unlock it, and `npx skills update` restores the line | the skill's frontmatter; the `skillOverrides` schema | A SessionStart hook removes the line from each skill it names; the steps in `CLAUDE.md` and `rules/` stay as they were |
| Dead references removed (`CODING_STANDARDS.md`) | It pointed at `enforcement.md`, R01/R07–R09, AC-05/AC-09, "Run 1" and `--wb-*`, none of which exist here | `ls` and `grep` over the repo and `~/.claude` | References cut, rules kept; the "Derive" example kept without its file path |
| `reviewer` at least on the author's tier (`CLAUDE.md` step 8, `agent-tuning.md` reviewer row) | The main session ran on opus and wrote the code; the reviewer and the security pass on it ran on the sonnet default, a weaker model checking a stronger one. With `settings.example.json` (main on haiku) sonnet is already above the author, so the default stays | `~/.claude/settings.json` `"model": "opus"`; this session's two review calls resolved to sonnet | Step 8 sets the reviewer's floor at the author's tier capped at opus (a fable author would otherwise spend the Fable budget on every review), opus for hard-to-undo diffs; per-call raises pass `agent-no-downgrade` |
| Code graph line trimmed (`CLAUDE.md` Tools) | The `search_graph` → `trace_path` → `get_code_snippet` order is also injected every session by `cbm-session-reminder` and the MCP server instructions | session start context | Kept only the load and fallback steps |

## Changed after the 2026-11-17 retro

A `/retro` on the config-review session above (session 28008295, $4.45).

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| Repo gate (`bin/check`, `.githooks/pre-commit`, root `CLAUDE.md`) | The repo had no CI, no pre-commit and no check script. A dead `enforcement.md` pointer, a user-only skill the model was told to call, and a hook missing from the install were all found by reading | `ls .git/hooks` held only samples; `bin/check` on `HEAD` flags `enforcement.md` | `bin/check` runs every self-test plus the settings, pointer and user-only-skill checks; the pre-commit hook runs it |
| New repo files reach `~/.claude` (`hooks/armarium-links`) | Per-file symlinks still missed new files: `skill-model-invocable` had to be linked by hand | the session's `ln -sfn` call | A SessionStart hook links tracked files `~/.claude` lacks and reports copies |
| A ✗ counts in any reply (`hooks/flow-skill-check`, `CLAUDE.md` Route) | A skill named in an early `Flow:` line was blocked again at every later stop, because only the last reply was searched for its ✗ | two Stop blocks for `review-animations` in one session | ✗ in any reply of the session clears the name; the Flow line backticks only skills you will call |
| `git grep` for ripple (`CLAUDE.md` Tools) | `grep -rn --include=*.md` died on a zsh glob ("no matches found") and the miss went unnoticed | the session's script 8 | Text search in a git repo starts with `git grep -n` |
| A diff goes to an agent as a range (`CLAUDE.md` Subagents) | A pasted `git diff` reached the security sub-task cut to 359 characters by an output hook | the session's script 29 stderr | Prompt line: pass `git diff <base>` for the agent to run |
| Removed lines checked (`CLAUDE.md` Route, Agent docs row) | An edit fused two bullets; the drop from 28 to 27 lines was reported as a win under "`wc -l` no higher" | `CODING_STANDARDS.md:7` before the fix | Done-when adds "`git diff` removes only lines you meant to remove" |

## Changed after the 6d6d184a session audit

An audit of three chat questions asked before `/claude-md-audit` (session 6d6d184a, $0.23 for the questions). Report: `/Users/Shared/claude-evals/session-6d6d184a/report-qa.md`.

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| A question answered in chat has its own row (`CLAUDE.md` Route) | No row fitted a question, so replies had no Flow line and nothing asked for a source. Turn 3 said the prompt cache lives 5 minutes and cache reads cost 1/10 of input; the session wrote 1h cache and Sonnet 5.5 reads cost 1/20. Turn 1 put the wrong cause first | transcript lines 53, 76, 83 (`ephemeral_1h`), 101 (cache hit after 16.7 min idle), 84 (the claims); `claude-api` price table | The row drops Flow and Exit for chat answers and sends any fact a source holds (repo code, library, version, price, Claude) to that source first; general knowledge is answered directly |
| A `/skill` command counts as the call (`hooks/flow-skill-check`, `CLAUDE.md` Exit) | A skill started with `/claude-md-audit` has no `Skill` tool call, so the Stop hook blocked a Flow line that named it | the audit session's Stop block | The hook also reads `<command-name>/x</command-name>` from plain-string user records; tool results do not count |

## Changed after the 3d60fcff session audit

A self-audit of a session with seven deliverables ($21.22). Report: `/Users/Shared/claude-evals/session-3d60fcff/report.md`.

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| Skill evidence follows the Flow line (`CLAUDE.md` Exit, `hooks/flow-skill-check`) | The post's Exit marked `humanizer` ✓ by citing a call made an hour earlier for another deliverable; the hook accepted any call in the session | transcript lines 459 (call) and 1181 (the post's Flow line, no call after it) | A call counts only after the last Flow line naming it; a `/skill` command counts only for the task it started; only this turn's Flow lines are checked |
| One owner for Video lead skills (`CLAUDE.md` Route, `rules/video.md`) | Three places listed different leads: `ui-ux-pro-max` ran after the first code write, `lean-build` and `tdd` never ran and no Exit showed them as ✗ | lines 1342, 1463, 2084, 2028 | The Video row owns the list; `video.md` points to it |
| The Stop hook reads the final reply (`hooks/flow-skill-check`) | A reply with the right ✗ line was blocked in the same second it was written | lines 612 to 615 | The hook also reads `last_assistant_message` from its input |
| A turn with a Flow line ends on an Exit list (`hooks/flow-skill-check`, `CLAUDE.md` Exit) | Three final replies in session `0fb097b2` listed no Done-when item, so a skipped intake note went unseen; the hook passed all three because the named skills had been called. Session `f3410d1d` also had no ✓ or ✗ in any reply | lines 1287, 1930, 2275; `~/claude-evals/session-0fb097b2/report.md` F2 | The hook blocks once when this turn's final reply has no ✓ or ✗ line outside a Flow line |
| The Stop hook decodes its input as UTF-8 (`hooks/flow-skill-check`) | On Windows, Python read stdin as cp1252, so a ✓ or ✗ in `last_assistant_message` never matched: the new Exit check blocked a reply that had both, and a ✗ sent on stdin had never cleared a skill. The self-test sent `\u2713` escapes, so it could not see this | the Stop block on the reply that shipped the Exit check | The hook reads `sys.stdin.buffer` as UTF-8; the self-test sends raw UTF-8 |
| Long `$` output in REPL scripts (`CLAUDE.md` Tools) | context-mode folded `$` output over 2 KB four times, and `| head` was blocked twice | the report's finding 5 | Send it to a scratchpad log and read with `file().slice()` |

## Changed after the 68085871 session audit

A ticket session on 2026-11-18 in the Spring/Oracle workspace, which spans several git repos: sonnet main, one opus `reviewer`, $10.50. A `reviewer` re-derived the numbers. Report: `claude-evals/session-68085871/report.md` (local).

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| A P0/P1 the agent cannot fix stays ✗ (`CLAUDE.md` step 8) | The reviewer found 2 P1s that needed core DB access and a working e2e stack; the Exit marked review ✓ with "no P0" | transcript lines 2786 (handback) and 2987 (final reply) | One sentence: it stays ✗ in Exit, naming what it needs and from whom |
| Security review keys on `origin/HEAD` in the cwd (`CLAUDE.md` step 8, `claude-md-audit` Reviews check) | The cwd was a root repo without a remote, the code sat in sub-repos with one; `security-review` failed on `origin/HEAD` and no security-only `reviewer` followed | lines 2775 and 2776 | Test `git rev-parse origin/HEAD` in the cwd; fall back to the security-only `reviewer` also when the skill fails. The audit skill points to step 8 instead of restating it |
| Plan Done-when names the step 4 gates (`CLAUDE.md` Route, Plan row) | A money-path plan with a data model and a core-schema join went out with neither `reviewer` nor `oracle`; no Done-when item showed it | lines 364 (Flow) and 727 (plan reply) | New item: risk area → `reviewer` on the plan; one-way door → `oracle`, or the approved doc cited |
| An item with any exception is ✗ (`CLAUDE.md` Exit) | ✓ lines carried caveats: "red first" listed a never-red test as an exception, "gate ran the changed tests" listed 3 skipped new tests. The 2026-11-17 audit saw the same "✓ with a footnote" | line 2987; the 2026-11-17 row on the P0-only re-check | Exit: an item with any exception is ✗, the exception its reason |

## Changed after the 999024f4 session audit

A feature session on 2026-11-18 in the same Spring/Oracle workspace, two rounds on one branch, sonnet main, six sonnet reviewers, then an in-session self-audit: $6.60 in total. A second audit ran from a new session; an opus `reviewer` re-derived its numbers. Report: `claude-evals/session-999024f4/report-v2.md` (local).

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| Red means a failed assertion (`CLAUDE.md` Route, Code row) | "✓ seen red before code" rested on three compile errors ("method is undefined", "cannot find symbol") and one real red; the old wording "the failure names the missing behavior" let a compile error pass | transcript lines 688, 1013, 1830, 2022; reply 2112 | Red = the test ran and failed an assertion; a compile error or a run with no test is not red |
| Plan acceptance checks in the Code Done-when (`CLAUDE.md` Route, Code row) | Plan check 4 (replay case 924 through sim) never ran, and neither final reply said so | plan file line 30; no sim command in the transcript | New item: every acceptance check the plan lists ran, else ✗ |
| Reviewer model owned by step 8 (`agent-tuning.md` reviewer row) | The tuning row put every security review on fable and listed concurrency for opus; step 8 had neither. The agent reads tuning only when it changes a model, so all 7 reviewer calls ran sonnet | lines 1379, 1381, 1654, 1934, 1936, 2091, 2677 | The row defers to step 8 for opus; fable no longer covers security review (owner's choice: cost stays as is) |
| Audit from a new session (`claude-md-audit` step 2) | The in-session audit cost $1.95 (29.5%) at a median 309k context per request against 173k during the work, and its own cost table left that out | report-v2 cost table | The current session as target → ask for a run from a new session |
| Checks table in the audit report (`claude-md-audit` step 7) | The self-audit gave no verdict for Models, Plan gates or Verification and so missed the model conflict above | `report.md` against report-v2 | Report gets one row per check with its verdict |
| Reviewer reads hunks, then the file (`agents/reviewer.md`) | 3 of 6 reviewers said their `git diff` output was folded | the three reviewer reports | `git diff -U0` per file, then `Read` the changed lines |

## Changed after the 2026-11-18 doctor scan

A `/doctor` run over the 50 newest sessions (2026-11-10 to 2026-11-18, every project). Local data: `claude-evals/doctor-20261118/`.

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| Docs/web: library/API docs → context7 first (`CLAUDE.md` Tools) | The line pointed at a plugin that no session used; the scan found the plugin's tools called 0 times, against 285 for `context-mode` and 63 for `codebase-memory-mcp`. It had 2 uses since install, the last on 2026-11-05 | `transcripts.txt` MCP counts; `pluginUsage` in `~/.claude.json` | Plugin set to `false` in both `settings.example.json` files and marked off by default in the README; the line now says WebSearch |

## Changed after the b672aeb0 session audit

A wayfinder + bug-fix session on 2026-11-19 in a private Spring workspace ($11.18, opus main, 3 `reviewer` calls). Local data: `claude-evals/session-b672aeb0/`.

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| Read-only agents cannot write from Bash (`hooks/bash-ban-shell-writes`) | `reviewer` has no Write/Edit, but its Bash is unrestricted: one spec review ran 20 redirects into 28+ files under the project's `.scratch/`. Its `.md` says "never run anything that writes"; the hook allowed log redirects for every caller | main transcript line 1446 (the prompt that asked for it); only that reviewer of 3 got the instruction and only it wrote | For `agent_type` `reviewer`/`oracle` the hook blocks file redirects (`>`, `2>`, `&>`), `mkdir/rm/mv/cp/touch`, git write subcommands, and ignores the unlock file. Live probe from a `reviewer`: redirect blocked, `\| sed -n` ran |
| Read-only agents read long output in slices (`CLAUDE.md` Tools, Files) | The parent copied "send long output to a scratchpad log" into the reviewer's prompt, overriding `reviewer.md`; it gave the same line to both research agents | same transcript, lines 405-424 and 1446 | One sentence: a `reviewer`/`oracle` prompt asks for `\| sed -n` or `git grep -n` instead |

## Kept, with evidence

| Rule | Evidence | Note |
|---|---|---|
| Test seen red before its code (`CLAUDE.md` step 6) | full arm 7 of 9 turns, bare 0 of 8; one full-arm fix left a regression test the bare fix did not | Changes process; no hidden case caught the difference yet |
| Big diff → `reviewer` (`CLAUDE.md` step 8) | in run 2, each review led to a commit that fixed 3 real bugs | Review was also the largest single cost in the full arm |
| `Flow:` line and Exit checklist (`CLAUDE.md` Route) | full arm 17 of 17 agents, bare 0 of 16 | Makes grading fast; see the Exit change above for its limit |
| `oracle` on one-way doors (`CLAUDE.md` step 4) | run 1: not called; run 2: called once, and the plan was fixed after it | n = 2 |

## Removed

| What | Why |
|---|---|
| `agents/codebase-memory.md`, `-auditor.md`, `-scout.md` | 0 calls in 254 local session transcripts |

## Changed after the Floating Island eval

Sonnet 5.5 at medium effort built a single-file three.js app (n = 3 per config) and then did a fix plus a feature on a shared base. There were four configs: this file ("with"), no CLAUDE.md ("without"), design skills removed from routing ("noskill"), and a draft with a Stop hook ("v2"). Report: `~/projects/claude-md-eval-island/REPORT-v2.md` (local).

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| Review on Big diffs (`hooks/reviewer-gate`, step 8) | With the rule only in text, `reviewer` ran in 1 of 3 "with" builds and 2 of 3 "noskill" builds, though every diff was over 200 lines. With the Stop hook it ran in 3 of 3. Each review found 3 P1s, and the agent fixed them | Stop-feedback lines in `logs/v2-b*/seg0.jsonl` | New Stop hook: it blocks once when a turn with a Flow line changed over 200 lines or more than 3 files and no review ran. It also counts files git sees changed since the prompt, so REPL and subagent writes count |
| Design skills are optional (Route UI and Video rows, `rules/frontend.md`, `rules/video.md`) | Forcing `ui-ux-pro-max` and `hallmark` did not raise blind scores: with 7.0, noskill 6.7, v2 5.7, and one judge's score for the same build moved by up to 3 points between passes. Once the UI row lost its lead skill, one run routed a 3D app in a repo as an Artifact and skipped the 375 px shots | `logs/judge-v2.md`, v2-b3 final reply | The UI row names "page, component, canvas or WebGL app" and has no lead skill. The Artifact row says "published with the Artifact tool, no repo". Video toolchain skills move to `video.md`, which now owns that list and replaces the "Video row owns the list" change above |
| Tests live in the repo (step 6) | In the fix task, "with" and "without" left 0 of 6 tests in the repo: the tests sat in `/tmp` or did not exist. With this sentence, 3 of 3 v2 runs committed a test that failed first | fix table in the report, `git log --stat` of each app | One sentence in step 6 |
| Small tier (Code flow) | Every fix run passed the hidden checks except one "without" run, which shipped broken persistence and never opened a browser. v2 took 6.0 min (median) where "without" took 1.0 | `logs/score/without-f2/persist.json` | Small: at most 2 files and 80 lines, with no Big, untrusted-input or secrets trigger. It runs steps 1 to 3, 6 and 7, so it keeps a test and a look |
| P0-only re-check (Code Done-when, step 8) | No review across 6 runs found a P0, and no run did the re-check | the final replies of the reviewed runs | The re-check runs only after a P0. This replaces the 2026-11-17 wording above |
| Untrusted input (Code flow) | v2-f1 restored `localStorage` with no validation or cap. Only v2-f3 ran a security review, which found that the restore loop had no upper bound | v2-f1 `index.html:599`, v2-f3 commit `52e7ce9` | Now defined by source and sink, for any stack. It includes browser storage, LLM output, and a loop or allocation sized by the input |

## Changed after the 7f560b1a session audit

Sonnet main with opus workers built two feature slices on the same private Django + React repo (18 commits, $45.72 with advisor calls). Local data: `claude-evals/session-7f560b1a/report.md`.

| Rule (where) | What happened | Evidence | Change |
|---|---|---|---|
| Security branch of step 8 (`hooks/reviewer-gate`) | Main wrote "no `origin/HEAD`" and sent a security-only reviewer prompt twice, without running the check; `origin/HEAD` had resolved since 2026-11-11. Second session with this error (999024f4) | report finding 1; no `rev-parse origin/HEAD` command in any of 24 transcripts | The Stop hook blocks once when a security-only reviewer ran, `origin/HEAD` resolves in cwd, and `security-review` was not called |
| Exit: an item with any exception is ✗ (`hooks/flow-skill-check`) | Two ✓ for "red before code" carried "trừ trigger và SQL". Third session after the sentence entered Exit (68085871, 999024f4) | report finding 2, main transcript lines 4530 and 5368 | The Stop hook blocks once when a ✓ item, on its line or an indented sub-bullet, holds except/but/unless/apart from/trừ/nhưng/chưa. "only" is left out: the Git row's Done-when says it |
| Red-run evidence (`agents/worker.md` Output format) | Main copied the worker's summary into its ✓; Part A had models, a migration and `average_data.py` written before their tests | worker a670192a, 14:25:02 to 14:27:18 | Workers report each behavior's red run: test id, command, failing assertion, first code file written after it |
| UI row for UI files (`hooks/flow-skill-check`) | Both slices with a page wrote only "Code flow", so no Done-when asked for loading and long-content states. Second session with missing states (4f71e73c) | report finding 3; screenshots read by workers a7a7aa0e, acb4ae5a, abeed048 | The Stop hook blocks once when files matching `rules/frontend.md` `paths:` were committed since the prompt, or are dirty and touched since, and the Flow line has no `UI` |
| Advisor cost (`skills/claude-md-audit/scripts/session_audit.py`) | The script reported $34.97; 19 advisor calls sit in `usage.iterations[]` and cost $10.74 more | the audit's reviewer re-derived the total from raw usage | Each `advisor_message` iteration is priced at its own model and counted in its agent's total and the cost mix |

## Still open

- From the 7f560b1a audit, one session each; re-check them alongside later evals:
  - Main said "I start items 1 and 2 now" and ended the turn. One prompt held a git op plus three tasks and got only `Flow: Git`. Candidate Done-when line: "a reply that says work continues ends with that work started".
  - 9 of 10 workers got a per-call `opus` with no "Raise when" cell for it ($28.12 with advisor, 62%); every opus slice still drew P1s. A reviewer ran on its sonnet default over opus-written commits, which `agent-no-downgrade` cannot see. Candidates: a worker "Raise when" cell, and a reviewer-below-author check.
  - The Exit Stop hook also blocks a turn that only waits for a background agent (L4525), which forced an Exit on unfinished work. Candidate: skip a turn whose last `Agent` call is still running.
  - 60 of 188 main requests were Poll-only ($1.63, 26% of main) against 5 to 6% in review-20261123. Candidate line in `## Subagents` Wait: in Code Mode, end the turn while a background agent runs.
  - Concurrent pytest runs on one test database deadlocked 4 times. Fix lives in the schools repo (`flock` around `backend-check` and `backend-test`), not here.
  - A local command such as `/reload-plugins` starts a new turn for `flow-skill-check` and `reviewer-gate`, so a task's Exit after it goes unchecked (line 4535 of 7f560b1a).

- `explorer`, `tester` and `evidence-auditor` also show 0 calls. `explorer` stays, because it is meant to keep code search cheap; the reason it is never picked is not known yet.
- The cost of the full config: about 1.2× (backend task) to 1.6× (UI task) the bare cost in run 2, down from 1.9× in run 1.
- Not re-run yet: the Small tier and the new UI and Video wording (November eval above).
- Not measured: whether skipping the graph misses call sites in a large refactor, and whether three reviewers on every commit (another commenter's setup) catch more than one reviewer on big diffs.
