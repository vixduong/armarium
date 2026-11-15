# Agent tuning

Read before changing an agent's `model`/`effort` or overriding it for one call. Current values live in each `agents/*.md` frontmatter; this file holds the why and the triggers.

## Tiers (cheapest first)
| Tier | For | Budget |
|---|---|---|
| `haiku` | recon, lookup, running known commands — a mistake is cheap to spot, loops are short | main pool |
| `sonnet` | well-scoped implementation against a spec; routine review | main pool |
| `opus` | judgment: review of a risk area; work that stays hard even with a clear spec (migration, perf) | main pool |
| `fable` | one-way doors: major refactor or migration, architecture; long unattended runs; Opus at `high` still falls short | own weekly limit, ~1 call per run |

Effort (`low` → `medium` → `high` → `xhigh` → `max`) buys depth, not knowledge: `xhigh` is waste where `low` answers. Routine work stays in the main pool to protect the Fable limit.

## Result not good enough → escalate in this order
1. Give the agent a way to verify its own work: a test, a build, a script.
2. Raise effort one level.
3. Move one model up, starting at a lower effort than the smaller model used.

Checkable batch → run everything at `low`, re-run only the failures at `high`. Past `high`, one more effort level can cost as much as the next model: test the next model at a lower effort first (Opus past `high` → Fable at `high`).

## Per agent
| Agent | Default | Why | Raise when | Drop when |
|---|---|---|---|---|
| `explorer` | haiku / medium | recon is collection, not judgment | sonnet / high: area spans generated or vendored code and the map will be trusted for a write | low: parent already named the exact files and symbols |
| `researcher` | haiku / medium | lookup, not judgment | sonnet / high: answer decides an architecture, dependency, or migration; or sources conflict and must be weighed | — |
| `tester` | haiku / medium | runs a known command, reads output | sonnet / high: must design the missing test, not just run one | — |
| `worker` | sonnet / medium | only agent that writes product code | fable: parent flagged the change as architecturally risky | haiku / medium: mechanical, fully specified edits that a test or build checks |
| `evidence-auditor` | sonnet / medium | checks claims against sources | opus / high: claim decides architecture, security, or licensing | — |
| `reviewer` | sonnet / high | review is a well-defined, repeated task; the agent's evidence rule (file, line, proof) checks its own findings. `medium` rated a real crash P2 where `high` rated it P1, for +$0.11 (reviewer-cmp, 2026-11-12) | opus / high: a sonnet/high review missed a bug, or the diff touches auth/permission, money, migration, concurrency. fable / xhigh: security review, major data migration, final pre-merge re-check | — |
| `oracle` | fable / medium | judgment with no tool output to lean on; `medium` is enough for a scoped question; the one agent that spends Fable — decisions, not lookups | — | sonnet / high when the Fable limit is exhausted; say so in the report |
