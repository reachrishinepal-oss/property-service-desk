# Property Service Desk (working name)

An AI service desk for residential property managers in the GCC, built on Microsoft Foundry. Residents report problems by chat, voice or photo in Arabic or English; AI agents triage the issue, check the lease, raise and approve work orders, and keep the resident updated.

**Status:** v0.1 released. Built in public, one release per sprint.
**Demo client:** Contoso Living, a fictional property manager in Dubai. All data in this repository is synthetic.

## The problem (demo scenario)

Residents report leaks, AC faults and noise through calls, chat apps, email and the front desk, in two languages, often with photos. Staff re-type each request, check the lease to see who pays, call contractors for quotes and chase approvals by email. Requests get lost and residents repeat themselves.

## What it does now

- v0.1: a resident says hello and the service desk answers through a model deployed in Microsoft Foundry.

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
