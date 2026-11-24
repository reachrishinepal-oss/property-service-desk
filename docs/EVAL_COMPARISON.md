# Evaluation comparison

Service desk replies scored in the Foundry portal and in code (`scripts/run_judge_eval.py`). Portal scores are the percentages the portal reported; code scores are averages out of 5.

| Method | Data | Answer key | Judge | Relevance | Coherence | Fluency | Cost | Notes |
|---|---|---|---|---|---|---|---|---|
| Portal run 1 | Synthetic | None | | 35% | 85% | 100% | $0.49 | Wrong instructions in both prompt boxes (generation text). OutputQuality 51%. Invalid test, kept as a record. |
| Portal run 2 | Synthetic | None | | 100% | 100% | 100% | $0.24 | Contoso service desk instructions. TaskCompletion 25%, IndirectAttack 75%. |
| Code run, 15 Oct (`scripts/run_judge_eval.py`) | Your 20-row triage set, replies from the service desk | None | Judge deployment (name to confirm) | 3.60 / 5 | 3.95 / 5 | 3.95 / 5 | Not measured | All 20 rows scored after re-judging 5 rows that came back empty on 14 Oct (cause not recorded). 15 of 20 rows scored 4 on relevance; rows T18, T19, T20 scored 2 (billing and renewal questions answered with "escalated" only). Different judge and scale from the portal, so not directly comparable with the percentages above. |

## v1 against v2

Triage prompt v1 (S01) against triage prompt v2 (S04: shared triage policy, four few-shot examples, delimiters, a Check line and a reminder at the end), on `ai103model1` with the guardrail `contoso-strict` assigned, 24 Nov 2026. `triage_eval_v1.jsonl` is the S01 answer key; `triage_eval_v2.jsonl` is a held-out set that was not opened while the v2 examples were written. One run each, 20 rows per file, so one row is 5 points. Command: `python scripts/run_triage_eval.py --deployments ai103model1 --prompt v1|v2 --eval-file <file>`.

| Eval file | Prompt | Rows right | Cat | Urg | Both | Input tokens (20 calls) | Mean seconds per call | Errors | Results file |
|---|---|---|---|---|---|---|---|---|---|
| triage_eval_v1 | v1 | 15 of 20 | 90% | 80% | 75% | 3,095 | 1.58 | 0 | `run_20261124_155613_v1_triage_eval_v1.jsonl` |
| triage_eval_v1 | v2 | 16 of 20 | 95% | 85% | 80% | 14,675 | 1.75 | 0 | `run_20261124_155649_v2_triage_eval_v1.jsonl` |
| triage_eval_v2 | v1 | 15 of 20 | 80% | 90% | 75% | 2,913 | 1.53 | 0 | `run_20261124_155720_v1_triage_eval_v2.jsonl` |
| triage_eval_v2 | v2 | 17 of 20 | 90% | 95% | 85% | 14,493 | 1.54 | 0 | `run_20261124_155752_v2_triage_eval_v2.jsonl` |

Rows that changed from v1 to v2 (expected, then v1's answer, then v2's answer):

- triage_eval_v1: T08 wrong to right (hvac/emergency: v1 hvac/urgent). T19 wrong to right (lease_billing/routine: v1 hvac/urgent). T16 right to wrong (access_security/urgent: v2 access_security/emergency). Net +1 row.
- triage_eval_v2: T27 wrong to right (lease_billing/routine: v1 pest/urgent). T30 wrong to right (plumbing/emergency: v1 plumbing/urgent). T38 wrong to right (common_area/routine: v1 electrical/routine). T33 right to wrong (appliance/urgent: v2 appliance/emergency). Net +2 rows.

Still wrong under both prompts: T12, T14, T18 (triage_eval_v1); T21, T37 (triage_eval_v2). The v2 input tokens are about 4.7 times v1 (about 730 against 150 per call).
