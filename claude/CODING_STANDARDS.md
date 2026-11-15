# Coding standards: judgement calls

This file holds only the calls a linter, typechecker, test, or hook cannot make. Anything a machine can check goes in `enforcement.md` instead.
CLAUDE.md points here from **Surgical**. Code review (`code-review` Standards axis, `reviewer`) reads this file as the standard.

## Scope of a change
- **Unrequested refactor or rename**: suggest it in the final reply and keep it out of the diff. (R07; the rule itself stays in CLAUDE.md)
- **Match the existing style** wherever the linter is silent: naming, file layout, error shape, test layout. The surrounding code is the spec. (R08)
- **Orphans**: remove only the imports, functions, and files that your change made dead. Dead code that was already there is reported, never deleted. (R09)
- **Simplest working shape**: inline first. Add an abstraction, option, or config only when a second caller exists now. (R01)

## State and data
- **Derive, don't mirror.** A value computed from props or other state (filtered list, clamped index, total) is computed during render or in a selector, never stored as separate state. Evidence: the Run 1 P1 was an `active` index stored as state that was never clamped after the list shrank (B1.stream.jsonl:375–383).
- **One spelling per concept** across types, JSON keys, test names, and UI copy (`grade` stays `grade`; it never becomes `level` in one layer).

## Trust boundaries
- **Untrusted input** (file, URL, clipboard, network, user text) is validated at the point it enters, with the narrowest shape that works. A JSON parse is not validation.
- **Raw HTML only from a renderer you configured safely.** Before you use `dangerouslySetInnerHTML`/`innerHTML`, name the library that produced the HTML and the option that blocks script or link injection (e.g. KaTeX `trust: false`), in a one-line comment. Then run `security-review` (CLAUDE.md step 8).
- **Choosing the error surface** (inline, toast, `role=alert`) and its wording is a judgement call. That a failed parse keeps the old data is something a machine can check: see `enforcement.md` (AC-09).

## Tests
- **The edge list is a checklist, not a quota.** Pick the cases from CLAUDE.md step 6 that can actually happen for this input. Write one test per case that the code handles differently.
- **A test asserts behavior a user or caller can see.** Use a role, label, or text. Reach for a private field or class name only when nothing visible exists.
- **A reviewer's finding becomes a test first**, seen red, then fixed. That is what Run 1 did for its P1, and it is the pattern to keep.

## Presentation (no test, judged by eye)
- Visual values come from the project's design tokens (`--wb-*` in Run 1). Add a new token only when no existing one fits the meaning. A machine can find a literal value (AC-05 does), but whether to reuse a token or add one is a judgement call.
- Accessibility judgement that linters miss: focus order follows reading order, error text says what to do next, and color is never the only signal. See `~/.claude/rules/frontend.md` items 4–5.
