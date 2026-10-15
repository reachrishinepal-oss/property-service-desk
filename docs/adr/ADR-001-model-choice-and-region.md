# ADR-001: Model choice and region for the service desk

- **Status:** accepted (owner approved 2026-10-15)
- **Date:** 2026-10-15
- **Session:** S01

## Context

Contoso Living (fictional) wants residents to report problems by chat and get a sorted, routed reply in seconds. The first job is triage: read a resident request and decide its category and urgency. Three models are deployed in one Foundry project (East US 2), all Global Standard, and the service desk needs one default for triage plus a plan for accuracy-critical clients. Constraints: cost per request, response time, accuracy on our own data, model retirement dates, and where a client's data is processed and stored.

## Facts, assumptions, design choice

| Type | Statement | Evidence |
|---|---|---|
| Fact | On our 20-request triage set, gpt-4.1-mini got 15 right, gpt-5-mini 14 and gpt-5 18. | `src/governance/triage_eval.py`, run of 13 Oct 2026 |
| Fact | Time per request was 1.69 s (gpt-4.1-mini), 3.75 s (gpt-5-mini) and 4.33 s (gpt-5). Output tokens per request were 190, 4,128 and 4,335; most of the last two were hidden reasoning tokens. | Same run, first-call latency includes setup |
| Fact | The rule agreed before the run: a challenger replaces the baseline only if it gets at least 2 more rows right, or ties at lower cost. gpt-5-mini lost by 1 row and used more tokens, so it does not replace gpt-4.1-mini. | Rule agreed with the owner on 13 Oct 2026 before the run; run above |
| Fact | In a portal evaluation with the service desk instructions, relevance scored 100% and task completion 25%. | `docs/EVAL_COMPARISON.md`, portal run 2 |
| Fact | In a code evaluation with a judge model on all 20 replies, relevance averaged 3.60, coherence 3.95 and fluency 3.95 out of 5. Rows T18, T19 and T20 scored 2 on relevance; the replies escalated and did not answer a billing or renewal question. | `docs/EVAL_COMPARISON.md`, code run of 15 Oct 2026 |
| Fact | gpt-4.1-mini (version 2025-04-14) is marked Deprecated and retires on 2027-04-14. | Microsoft model retirement schedule, updated 21 Sep 2026, read 13 Oct 2026 |
| Fact | Global Standard may process prompts in any Azure region; data at rest stays in the resource's geography. Data zones are US, EU and Asia Pacific; no Middle East zone is named. | Microsoft "Deployment types" page, updated 2026-08-12, read 15 Oct 2026 |
| Fact | East US 2 offers gpt-4.1-mini, gpt-5-mini and gpt-5 on Global Standard. | Microsoft region availability page, updated 2026-09-04, read 15 Oct 2026 |
| Assumption | 20 rows is enough to rank the models. It is not: one row is 5 points, and the labels are judgement calls. | Check with a larger eval set before any client commitment |
| Assumption | The retirement date of gpt-5 has not been checked. | Read the retirement schedule before relying on it |
| Assumption | Whether the three models exist in a UAE region was not confirmed. | Check the model catalog in the portal if a client needs in-country hosting |
| Assumption | Prices were not checked on the pricing page; cost is judged from tokens and the portal leaderboard only. | Check before quoting a client |
| Assumption | Contoso Living has no rule that data must stay in the UAE. It is a fictional client with synthetic data. | A real client's contract and regulator decide |
| Design choice | Triage default is gpt-4.1-mini (`ai103model1`). gpt-5 (`ai103model3`) is the documented upgrade for clients who weight accuracy over cost. | Owner decision, 15 Oct 2026 |
| Design choice | Keep Global Standard in East US 2 for all deployments. | Owner decision, 15 Oct 2026 |

## Options considered

| Option | For | Against | Measured result |
|---|---|---|---|
| A. gpt-4.1-mini for triage | Cheapest and fastest; text and image input | Deprecated, retires 2027-04-14; 3 fewer rows right than gpt-5 | 15 of 20, 1.69 s |
| B. gpt-5 for triage | Highest accuracy | About 2.5 times slower and about 20 times the output tokens | 18 of 20, 4.33 s |
| C. A now, B as the upgrade (chosen) | Low cost today, a clear path when accuracy matters | Two models to keep tested | See A and B |
| gpt-5-mini | None found | Lost the agreed rule | 14 of 20, 3.75 s |
| Region: Global Standard, East US 2 (chosen) | Cheapest, highest quota, already deployed | Prompts may be processed in any region; data at rest in the US | Not applicable |
| Region: Data Zone Standard | Processing stays in the US zone | Does not keep Dubai data in the UAE | Not tested |
| Region: UAE region | Only option that could meet an in-country rule | Model availability unconfirmed; price and quota unknown | Not tested |

## Decision

Use gpt-4.1-mini for triage and keep gpt-5 as the documented upgrade for accuracy-critical clients. Keep every deployment on Global Standard in East US 2.

## Consequences

This keeps cost and response time low for live chat and keeps the project on one region and one deployment type. It makes the service desk depend on a model that retires on 2027-04-14, so the model choice must be re-run on a newer model before then. Revisit this decision if: a client has a rule that data stays in the UAE or another named place; a larger eval set shows the accuracy gap is real and the client values it; the retirement schedule changes; or prices change. Questions that need lease or billing knowledge (rows T18, T19, T20) were weak on every model and are addressed by retrieval in S06, not by a bigger model.
