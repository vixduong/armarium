# Plan: stop CLAUDE.md growing, then test a general version

Contract: the six proposals of the 2026-11-28 retro (session 3822f333), in dependency order. Growth stops first because it is cheap and changes no behaviour. The kit measures next. `CLAUDE.md` itself changes last, by the kit's verdict.

Baseline (2026-11-28, commit `108b9e3`): `claude/common/CLAUDE.md` 16,812 bytes, 88 lines, 13 Route rows, 31 Done-when items; `pi/AGENTS.md` 17,160 bytes. `docs/rule-origins.md`: 96 rows under "## Changed" headings, 1 row under "## Removed".

Gate: `bin/check` from the repo root. Kit gate: `python3 -I scripts/fixtures.py selftest && python3 -I scripts/measure.py selftest` from the kit directory.

Non-goals: no rewrite of the live `CLAUDE.md` before the kit's verdict; no edit to a third-party plugin's own files (context-mode, rtk); no new agent or skill; issues #20 and #21 stay separate kits (one variable per kit).

One-way doors: none. Every step is one commit that `git revert` undoes; on Windows a revert also needs `claude/windows/install.ps1 -Apply`.

Reviewed: `reviewer` (opus, high) read this plan on 2026-11-28 and returned 0 P0, 9 P1, 12 P2. All are folded in below; the main session re-ran the cited evidence for the P1s.

| Step | Retro item | Depends on | Size |
|---|---|---|---|
| 1 Size cap in `bin/check` | 2 | none | Small |
| 2 Audit skill proposes removals | 3 | none | Agent docs |
| 3 Kit `lean-config-v1` | 1 | 1 and 2 merged, so the batch runs on a tree that stays still | Big, in `armarium-audits` |
| 4 Owner runs the kit | 1 | 3 | `/eval-kit`, user-only |
| 5 Apply the verdict | 1, 4, 6 | 4 | Big |
| 6 A loaded skill counts | 5 | after the batch of step 4 ends, because it edits a hook both arms run | gate edit, optional |

## Step 1: size cap in `bin/check`

Behaviour: `bin/check` reports a problem when `claude/common/CLAUDE.md` or `pi/AGENTS.md` is larger than its cap. Size is counted in bytes after `\r` is removed, so a CRLF checkout and an LF checkout give the same number (the repo has no `.gitattributes`, and `claude/windows/install.ps1:41` already allows for CRLF). A file that is absent is skipped: the base fixture of `bin/test_check.py` has no `pi/AGENTS.md`. The caps are two constants in `bin/check`: 16,900 and 17,200. A sentence added to either file then needs one merged or removed, or a cap edit that shows in the diff.

Files: `bin/check` (constants, one check block, one docstring line), `bin/test_check.py` (three cases), `docs/rule-origins.md` (one row).

Seam: `bin/check` as a process, through the `fixture()` helper of `bin/test_check.py`. The cases read the cap from the constant in `bin/check`'s source and build one-line content with no newline, so Windows text mode adds nothing.
- Red first: `claude/common/CLAUDE.md` one byte over the cap gives a problem line naming the file, its size and the cap. It fails today because no such check exists.
- A file exactly at the cap passes.
- A file at the cap with CRLF line endings passes.

Acceptance checks, independent of those tests:
- In a throwaway `git worktree`, append 300 bytes to `claude/common/CLAUDE.md`, run `bin/check --repo-only` there and expect `check: 1 problem(s)`; remove the worktree; `bin/check` in the main tree prints `check: ok`. The live file is never edited for the test, because it is symlinked into `~/.claude`.
- With the owner's consent, `gh workflow run check.yml --ref <branch>` then `gh run watch` is green on `windows-latest`.

Owner decides: the cap values. Recommended: the two above, so the cap bites on the next addition.

## Step 2: the audit skill proposes removals

Behaviour: `/claude-md-audit` reports what to take out as well as what to add.

Files: `claude/common/skills/claude-md-audit/SKILL.md`, `docs/rule-origins.md` (one row).
- Step 6 gains one fix type: a fix that adds a sentence names the sentence it merges with or replaces. A rule is a removal candidate when its row sits in a `## Changed after …` section of `docs/rule-origins.md` with one session as evidence, 5 or more audit sections follow that one, and no report under `/Users/Shared/claude-evals/session-*/report.md` written after it names the rule.
- Step 7's report gains the section "what to remove" after "findings". An empty section says so.
- The "Never triggered" check feeds that section.

Lead skill: `writing-for-agents`. Done-when is the Agent docs row: pointer targets exist, `wc -l` no higher than 74 or the growth stated, the diff removes only intended lines.

Acceptance check: `bin/check` green, and the first audit run after the merge has the section in its report. The second half cannot be checked at merge time; if the section is missing, this step reopens.

Owner decides: the number of audits before a rule expires. Recommended: 5.

## Step 3: kit `lean-config-v1`

Question: does a general `CLAUDE.md` of about 30 lines, with the same hooks, rules, skills, agents and plugins, cost less than today's file without losing correctness? The tasks are code and scene work only, so the kit says nothing about the Report, Writing, Research, Agent docs or Git rows.

Location: `~/projects/armarium-audits/evals/lean-config-v1/` with `PLAN.md` (Question, Arms, Tasks, Running, Decision, all written before any run), `scripts/` (`run.py`, `fixtures.py`, `measure.py`, `batch.sh`) and `arms/lean/CLAUDE.md`.

Reuse:
- `evals/context-mode-v1/scripts/run.py`, `measure.py`, `batch.sh`: session driver, metrics, batch loop.
- `~/projects/claude-md-eval-island/`: `base/`, `PROMPT.md`, `FIX.md`, `RUBRIC.md`, `scripts/score.mjs`, `scripts/persist.mjs`, and `scripts/make-cfg.sh`, which builds a `CLAUDE_CONFIG_DIR` whose `CLAUDE.md` is a draft and whose other entries are symlinks to `~/.claude`.

Arms. Both are built by `make-cfg.sh`, so they differ in one file:
- `full`: draft = the installed `CLAUDE.md`.
- `lean`: draft = `arms/lean/CLAUDE.md`. It holds three rules (state the check that can fail before starting; no claim of done without evidence produced in this turn; above the Big threshold or in a risk area an independent `reviewer` sees the diff), the Trivial, Small and Big tiers, the `## Tools` and `## Subagents` sections unchanged, and pointers to the existing `rules/*.md`. It keeps the `Flow:` line (code work names `Code flow`, interface work adds `UI`) and an Exit list of ✓ and ✗ items with evidence. It has no Route table, no per-row Done-when and no numbered Code flow.
- Why the Flow line stays: `flow-skill-check` and `reviewer-gate` act only on a turn that has one, and `pi/armarium-pi/index.ts:16` blocks tool calls until it is written. Without it the Stop hooks would block only the `full` arm, and the verdict would measure the hooks. With it, the lean file is the file step 5a would ship.
- Arm check: the `loaded` entry of `session_audit.py` for `CLAUDE.md` equals the arm file's length in characters (the script stores `len(content)`, not bytes).
- Still tree: `run.py` writes the armarium `HEAD` SHA into each run's `meta.json`, and `batch.sh` stops when it differs from the first run's. Steps 5 and 6 wait until the batch ends.
- Both arms get permission to run headless Chrome. In the 2026-11-28 comparison the bare run was refused 5 commands and could not open its own page.

Edits to the copied `run.py`, settled by one smoke session per arm before any other kit code:
- `CLAUDE_CONFIG_DIR` joins the env whitelist (line 74 passes only `HOME`, `PATH`, `USER`).
- `--model` comes from `PLAN.md` (line 77 hard-codes `sonnet`).
- `HARD_TIMEOUT_S` (900 at line 28) becomes a per-task value from `PLAN.md`.
- `transcript_for` (line 41) reads `~/.claude/projects`; it keeps working because `make-cfg.sh` symlinks `projects/`. The smoke run confirms it.
- Each task workspace is a git repository with one base commit, so `reviewer-gate` can see the edits a REPL makes.
- Both prompts say that questions are barred, and the smoke run confirms that no arm waits on `AskUserQuestion` or plan mode.
If a smoke session cannot log in or fails the arm check, stop and report.

Tasks, fixed seed, n = 3 per arm. Each task has a list of boolean checks in `PLAN.md`, and `fixtures.py selftest` proves every check on one seeded good answer (passes) and one seeded bad answer (fails):
1. the island build (`PROMPT.md`). `score.mjs` records fps, buttons, errors and screenshots and has no pass or fail today, so its checks are written new: 0 console errors, each of the 4 buttons changes the frame, 30 fps or more, one file, three.js r170, no other network request.
2. the island fix (`FIX.md`): the `checks` object of `persist.mjs`.
3. one feature on the shared base that parses untrusted input, with a new hidden check for the unbounded-restore bug the Floating Island eval found.

Metrics per run:
- cost in USD: the session total of `session_audit.py`, main plus subagents (`measure.py` has no cost code);
- checks passed; a run that times out fails all its checks and its cost still counts;
- P1 count from one fixed post-hoc `reviewer` prompt run on every output;
- report only, used by no rule: wall time, Stop-hook blocks per arm, and for task 1 a blind pairwise preference judged twice (a single judge moved up to 3 points between passes in the earlier eval).

Decision rule, approved by the owner before the batch and then frozen in `PLAN.md`. A check passes for an arm when at least 2 of its 3 runs pass it. The rules apply in this order:
1. keep `full` when any check on any task passes in `full` and fails in `lean`;
2. adopt `lean` when, on every task, its median cost is at most 80% of `full`'s and its mean post-hoc P1 count is at most 1 higher;
3. otherwise keep `full` and go to step 5b.

Tests: `fixtures.py selftest` and `measure.py selftest`, each new check and metric seen red on testdata before its code.

Cost: 18 sessions. The one full-config scene build measured so far cost 18.58 USD on Fable 5.2 and hit the 5-hour limit, so 6 such builds plus 12 smaller runs take several quota windows. Smaller option: tasks 2 and 3 only, 12 sessions, at the price of no scene evidence. Owner decides the model, n and the task list before the batch. Recommended model: the one the owner uses daily, since the verdict replaces the file for that model.

## Step 4: the owner runs the kit

`/eval-kit lean-config-v1` (user-only). Its step 6 applies the decision rule to `results/summary.md`. The kit's verdict settles the general-versus-detailed question: `claude-md-audit` step 6 sends a fix whose gain and cost only a run can weigh to a kit.

Result, 2026-11-28: 18 of 18 sessions scored. The session ran the batch itself on the owner's instruction, without `/eval-kit`. Rule 1: no check lost. Rule 2 failed on task `u` (median 2.03 against 2.42 USD, ratio 0.84). Verdict: rule 3, so step 5b. Done from 5b: issue #12 (`tester` and `evidence-auditor` cut, `explorer` kept) and issue #4 (`humanizer` for over one paragraph; a report's `reviewer` for over 40 lines or more than one source). Both went into one change and each twin file grew 25 bytes, so the caps stayed: a deviation from 5b's "one decision at a time, lowering the cap with each". `## Tools` waits on issues #15, #16 and #19.

## Step 5: apply the verdict

5a, `lean` adopted. Order on the live tree: readers first, then the file.
1. Readers of the old wording accept both versions, each with a test seen red:
   - `bin/check:214-217`: the Names check takes lead skills from column 3 of the Route table. With no table it would check nothing, so it reads the skill names of the lean file's pointers instead.
   - `claude/common/hooks/reviewer-gate`: `CODE_ROW` (line 21) and `PROSE_ROWS` (line 22) match Route row names.
   - `claude/common/hooks/flow-skill-check`: the `UI` name; the Flow line and ✓/✗ items stay.
   - `pi/armarium-pi/index.ts`: lines 16, 180 and 187 (Flow line, the chat row by name, the Exit items), with `pi/test_armarium_pi.py`.
   - `claude/common/skills/claude-md-audit/SKILL.md:45-53` (the Flow check group: Route, Exit honesty, Missing Done-when) and `scripts/session_audit.py:46,198` with `test_session_audit.py`.
   - `claude/common/rules/video.md:14` cites Code flow steps 4 and 6 by number; `rules/scene.md` and `rules/frontend.md` are re-read for the same.
   - `claude/windows/install.ps1:9-14` patches three `## Tools` lines and throws when one is missing; `bin/verify_windows_install.py:38-41` asserts the result. They hold as long as `## Tools` is unchanged.
2. One commit flips `claude/common/CLAUDE.md` and `pi/AGENTS.md` and lowers both caps. `README.md`, `docs/hooks.md`, `docs/requirements.md` name `CLAUDE.md` rules and are re-read in that commit.
3. Each Route row then moves to an on-demand file or is dropped, the owner's call row by row: Git, Plan, Artifact, Report, Writing, Agent docs, Research, Question, Settings. UI, Scene and Video already have `rules/*.md`. The kit gives evidence for the Code, UI and Scene rows only.
4. `docs/rule-origins.md`: one section citing the kit's `results/summary.md`.
5. Windows CI on a branch, with the owner's consent.

5b, `full` kept: prune one decision at a time, lowering the cap with each.
- Issue #4: the size below which a report skips `reviewer` and prose skips `humanizer` (Report and Writing rows, both files).
- Issue #12: reword or cut `explorer`, `tester`, `evidence-auditor`. A cut touches `claude/common/agents/{explorer,tester,evidence-auditor}.md`, `claude/common/agent-tuning.md`, the `## Subagents` line in both files, `pi/settings.example.json`, `claude/common/hooks/test_agent_no_downgrade.py`, `bin/test_check.py`.
- `## Tools`: 18 of its 34 sentences describe a plugin, hook or shell quirk. A sentence leaves only when its cause is gone, which waits on issues #15, #16 and #19. A cut of the zsh, RTK or `codebase-memory-mcp` line also edits `claude/windows/install.ps1:9-14` and `bin/verify_windows_install.py:38-41`. Nothing moves to an on-demand file: the fold applies to any read over 4 KB, so the agent needs those sentences in most Code Mode sessions.

Either branch runs the Code flow with its own review at step 8; a hook edit is developed on scratchpad copies and written to the live file once (project `CLAUDE.md`).

## Step 6: a skill loaded earlier in the session counts (optional)

Measured gain is small: in session 3822f333, 4 of 5 repeat calls of `writing-for-agents` returned a one-line "already loaded" stub, and 2 calls of `humanizer` with new arguments reprinted about 7k tokens each. Recommended: skip this step unless a later audit shows the reprint in a second session.

If it is done:
- `claude/common/CLAUDE.md` line 23 and its twin in `pi/AGENTS.md`: a `Skill` call earlier in the session counts as evidence, unless a compaction came after it. The added clause passes the step 1 cap only with a merge elsewhere or a cap edit in `bin/check`.
- `claude/common/hooks/flow-skill-check`: accept a call made before the last Flow line when no compaction follows it. The parser keeps only `user` and `assistant` records today, so the `{"type":"system","subtype":"compact_boundary"}` record needs a new event kind. The `isCompactSummary` user record that follows each boundary already counts as a prompt and resets the turn. A partial compaction keeps a `preservedSegment`; a call inside it is treated as lost, the safe side.
- `test_flow_skill_check.py`, with fixtures that hold both records: "called earlier, no compaction, passes" is the red case; "never called blocks" and "called before a compaction blocks" block today and are regression cases.
- `bin/hook-diff` replays Bash rows only and does not apply to a Stop hook.
- Windows shares the hook, so with the owner's consent CI runs once on a branch.
- Acceptance check: the hook reads a JSON object on stdin with `transcript_path` and `last_assistant_message`, and always exits 0. A real transcript from `~/.claude/projects` with an early `Skill` call and a later Flow line prints nothing; a copy with a `compact_boundary` record and its summary record inserted after the call prints `"decision": "block"`.

## Owner decisions, in order

1. Cap values (step 1) and expiry count (step 2).
2. Kit model, n, task list and the decision rule (step 3), before the batch.
3. After the verdict: the per-row calls of 5a, or the thresholds and cuts of 5b.
4. Whether step 6 is done at all.
