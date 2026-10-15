# Evaluation comparison

Service desk replies scored in the Foundry portal and in code (`scripts/run_judge_eval.py`). Portal scores are the percentages the portal reported; code scores are averages out of 5.

| Method | Data | Answer key | Judge | Relevance | Coherence | Fluency | Cost | Notes |
|---|---|---|---|---|---|---|---|---|
| Portal run 1 | Synthetic | None | | 35% | 85% | 100% | $0.49 | Wrong instructions in both prompt boxes (generation text). OutputQuality 51%. Invalid test, kept as a record. |
| Portal run 2 | Synthetic | None | | 100% | 100% | 100% | $0.24 | Contoso service desk instructions. TaskCompletion 25%, IndirectAttack 75%. |
| Code run, 15 Oct (`scripts/run_judge_eval.py`) | Your 20-row triage set, replies from the service desk | None | Judge deployment (name to confirm) | 3.60 / 5 | 3.95 / 5 | 3.95 / 5 | Not measured | All 20 rows scored after re-judging 5 rows that came back empty on 14 Oct (cause not recorded). 15 of 20 rows scored 4 on relevance; rows T18, T19, T20 scored 2 (billing and renewal questions answered with "escalated" only). Different judge and scale from the portal, so not directly comparable with the percentages above. |
