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
| `review-animations` for UI motion (`rules/frontend.md` step 6) | The rule lived only in the video gate, which UI work never loads | called 1 of 2 times in run 1, 0 of 2 in run 2 | Moved into the frontend gate; the video gate keeps its own step |
| Shell writes blocked by a hook (`hooks/bash-ban-shell-writes`, `CLAUDE.md` Tools) | The prose rule "write files with Edit/Write only" was followed 5 of 8 times; no hook enforced it. Without the rule, agents wrote 36 and 24 files through heredocs | run 2 full arm, run 1 bare arm | New hook blocks heredoc-into-file, `echo`/`printf`/`cat > file`, `sed -i`, `perl -i`, `tee`, and python on stdin. The prose line now only says what to use instead |
| Lines a hook already enforces removed (`CLAUDE.md` Tools) | "Read big files with offset" and "URL → `ctx_index`" are both blocked by the context-mode plugin's hooks | both blocks seen in normal sessions | Lines deleted |

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

## Still open

- `explorer`, `tester` and `evidence-auditor` also show 0 calls. `explorer` stays, because it is meant to keep code search cheap; the reason it is never picked is not known yet.
- The cost of the full config: about 1.2× (backend task) to 1.6× (UI task) the bare cost in run 2, down from 1.9× in run 1.
- Not measured: whether skipping the graph misses call sites in a large refactor, and whether three reviewers on every commit (another commenter's setup) catch more than one reviewer on big diffs.
