---
name: eval-kit
description: "Run an A/B eval kit from armarium-audits (gate, smoke, batch, measure) and judge it by the kit's PLAN.md."
disable-model-invocation: true
argument-hint: "[kit, default context-mode-v1] [smoke|batch|measure]"
---

Runs one kit under `~/projects/armarium-audits/evals/<kit>/` (private repo `vixduong/armarium-audits`). The kit's
`evals/<kit>/PLAN.md` is the contract: its arms, its arm check, its pass rule and its decision rule, all written before any run.
Every verdict you give comes from that file and the kit's own scripts, never from a rule of your own.

## Steps

1. **Locate.** Missing clone → `git clone https://github.com/vixduong/armarium-audits.git ~/projects/armarium-audits`;
   otherwise `git -C ~/projects/armarium-audits pull --ff-only`. Read `evals/<kit>/PLAN.md` and `scripts/batch.sh`.
   Done when you can name the arms, the arm check, the session count of a batch and the decision rule.

2. **Gate**, from the kit dir: `python3 -I scripts/fixtures.py selftest && python3 -I scripts/measure.py selftest`.
   Red → stop and report the failing line.

3. **Smoke** (skip with `measure`): `python3 -I scripts/run.py <control task> on 0`, then the same with `off`. Rep 0 is
   left out of the summary. Check the PLAN's arm check on both transcripts with `measure.metrics(<transcript>)`
   (context-mode-v1: `cm_rows` above 0 in on, 0 in off). A run directory that already exists makes `run.py` refuse:
   ask before deleting `runs/<id>` and its workspace. Done when both arms pass the arm check; else stop and report.

4. **Batch** (only with `batch` or no mode): tell the user the session count and model from the PLAN first, since
   each session spends their quota. Start `scripts/batch.sh` in the background
   (`await $\`scripts/batch.sh\`.timeout(5000)` from the kit dir) and wait on its output file until `batch done`.
   It skips finished runs, so a stopped batch resumes by starting it again.

5. **Measure**: `python3 -I scripts/measure.py` writes `results/runs.tsv` and `results/summary.md` in the kit. For every run that
   failed, read its `runs/<id>/meta.json` (`check`, `timed_out`) and say why.

6. **Judge**: apply each line of the PLAN's decision rule to `results/summary.md`, task by task. Report the summary
   table, each rule line with its numbers, and the verdict. Done when every number in the reply is a cell of
   `results/summary.md` or `results/runs.tsv`.

Committing `results/` to armarium-audits is a separate step the user asks for.
