# Property Service Desk (working name)

An AI service desk for residential property managers in the GCC, built on Microsoft Foundry. Residents report problems by chat, voice or photo in Arabic or English; AI agents triage the issue, check the lease, raise and approve work orders, and keep the resident updated.

**Status:** v0.1 released. Built in public, one release per sprint.
**Demo client:** Contoso Living, a fictional property manager in Dubai. All data in this repository is synthetic.

## The problem (demo scenario)

Residents report leaks, AC faults and noise through calls, chat apps, email and the front desk, in two languages, often with photos. Staff re-type each request, check the lease to see who pays, call contractors for quotes and chase approvals by email. Requests get lost and residents repeat themselves.

## What it does now

- v0.2: a resident chats with the service desk over several turns through a model deployed in Microsoft Foundry; each reply streams in and shows the input tokens for that turn, and a ticket preview card beside the chat (category, urgency, building, unit number, summary since S04) updates after every reply.
- v0.2 (S03): the assistant can check a unit exists (it never reveals who lives there) and raise a real ticket in a mock work-order system (SQLite, 5 invented buildings, 60 units, each unit identified by its building and unit number). The app checks every argument before anything is written, and each reply lists its tool calls in a "Tool calls" panel. Replies no longer stream while tools are in use.
- v0.2 (S03): community-rules and repair-time questions are answered from two synthetic documents (`data/rules/`) through file_search, and each reply shows the queries and retrieved passages with their scores in a "Rules searched" panel. Rules search is off until `VECTOR_STORE_ID` is set (run `python scripts/setup_rules_store.py`).
- v0.2 (S03): a "Manager question" box in the sidebar (demo, no sign-in yet) answers questions over the synthetic tickets with code_interpreter, shows the Python the model ran, and for the built-in test question shows the true values computed in plain pandas beside it.
- v0.2 (S04): triage prompt v2 reads one shared triage policy (`src/intelligence/triage_policy.md`), also used by the chat and the ticket card; on ai103model1 it scored 16 of 20 against 15 for v1 on the S01 answer key, and 17 of 20 against 15 on a held-out set (`docs/EVAL_COMPARISON.md`). When the guardrail blocks a message or cuts a reply, the resident sees a plain fallback message instead of an error. Twelve red-team prompts and their results are in `docs/RED_TEAM_LOG.md` (`python scripts/run_redteam.py --guardrail contoso-strict`).

## Roadmap

| Release | Adds |
|---|---|
| v0.1 Hello resident | The app talks to a Foundry model deployment with keyless sign-in |
| v0.2 Answers residents | Multi-turn chat, triage card, tools on a mock work-order system, cited rules, guardrails, evaluation |
| v0.3 Agents that act | Foundry agents, lease search with citations, MCP and A2A, approval workflow, multi-agent handoff |
| v0.4 Speaks Arabic and English | PII redaction, tone escalation, voice notes, translation, a real-time voice line |
| v0.5 Sees and shows | Photo and video triage, invoice and lease extraction, listing images and teaser videos with AI disclosure |
| v1.0 Portfolio ready | Tracing, agent evaluation in CI, demo video, architecture and decision records |

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Run it locally

Requirements: Python 3.13, the Azure CLI, and access to a Microsoft Foundry project with a chat model deployment.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env      # then fill in your project endpoint and deployment name
az login
python scripts/check_setup.py   # every line should say OK
streamlit run src/ui/app.py
```

## Built with (so far)

Microsoft Foundry, the Foundry SDK, Azure Identity, Streamlit. Each release adds to this list.
