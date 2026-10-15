# Build rules for this repository

For Claude Code in VS Code and for the AI103 Agent (Rishi's course tutor). Read this before writing any code here.

## What this is

Property Service Desk (working name): an AI service desk for Contoso Living, a fictional property manager in Dubai. Residents report problems by chat, voice, call, photo or video in Arabic or English; agents triage, check the lease, raise and approve work orders, dispatch contractors and reply.

It is also the capstone of Rishi's AI-103 course. Every feature exercises an exam skill. The course plan lives outside this repo in `../course/` (`SYLLABUS.md`, `CAPSTONE.md`, `EXAM_MAP.md`); read the current session's block there before building.

## How Rishi uses you

Rishi is the product owner and solution designer; you are the developer. He writes his own instructions to you, feature by feature, and the product is built from scratch from them. You write all of the code, including the AI calls: Foundry and Azure SDK clients, model and agent calls, prompts, tool schemas, retrieval, evaluations and safety settings. He runs it, reads your summary, and explains the feature in his own words to the tutor. He does not write or fill in code, and you never ask him what a line of code should be.

## Rules

- **Build exactly what he asked, small.** The least code that does it, about 150 lines of new code without tests unless he says otherwise. No extra options, flags, thresholds, reports or abstractions; tests only for real logic. If the request seems to need more, say so before building.
- **Use the approach he names.** If he says gpt-4.1-mini, keyless sign-in, the project endpoint or hybrid search, use exactly that; don't swap in your own preference. If his instruction leaves a real design choice open (which service, model, parameter or approach), ask him one plain question before building rather than choosing silently.
- **Setup and Azure are his.** Never edit `.env`, create or change Azure or Foundry resources, assign roles or run `az` commands that change anything. When something is missing (an endpoint, a deployment, a role), tell him exactly what is needed and where in the portal, and wait.
- **Tag every AI-103 concept in the code.** Directly above each piece of code that uses an exam skill, add one comment line: `# AI-103 <skill id>: <what this does and why, in plain English>`, for example `# AI-103 1.3.d: sign in with your Azure identity (no API key); the Foundry User role allows the call`. Skill IDs come from `../course/EXAM_MAP.md`. Keep each such piece in one clearly named function so it can be pointed at.
- **Readable over clever.** Plain functions, clear names, short files. Rishi reads code at the level of "what does this function do", not line by line.
- **Finish every change with a plain-English summary** in this shape, with no jargon left unexplained:
  1. What it does now, in two sentences a client would understand.
  2. AI-103 concepts used: skill ID, one-line meaning, and where (file and function).
  3. How to run it: the exact command, and what he should see.
  4. Any design choice you made yourself that the brief didn't settle (a parameter, a default, a threshold), so he can confirm or change it.
  5. Files changed, one line each.
- Older functions keep Rishi's `Steps:`, `Decision:` and `Predict:` comments under their `# AI-103` tag; leave them as they are.
- The app must keep running while a feature is half-built: catch errors at the UI edge and show a plain message.

## File header (every Python file)

```python
"""
PURPOSE: what this file does, in one sentence.
LAYER:   one of the nine layers: Intelligence; Data/Knowledge; Context/Retrieval;
         Memory/State; Orchestration/Action; Integration/Experience;
         Evaluation/Reliability; Security/Controls; Infrastructure/Operations
SESSION: the session that introduced it (S00 to S17)
"""
```

## Stack

- Python 3.13 (the Microsoft labs are tested on it; not 3.14). Streamlit for the UI. SQLite for mock systems. FastAPI only where an HTTP API is needed (OpenAPI tool, MCP over HTTP, A2A).
- Microsoft only for AI: the Foundry SDK (`azure-ai-projects`), the OpenAI SDK against Foundry, Microsoft Agent Framework, the Azure AI service SDKs, `azure-identity`. No LangChain, LlamaIndex or other vendors' agent platforms.
- Check current package names and APIs against the Microsoft lab for the session (linked in `../course/SYLLABUS.md`) or the official docs before writing scaffold that depends on them. Pin versions in `requirements.txt`.

## Layout

```
capstone/
  src/
    core/          settings, Foundry clients, logging       Infrastructure/Operations, Security/Controls
    ui/            Streamlit pages: resident, staff, studio  Integration/Experience
    intelligence/  prompts, model calls, structured output   Intelligence
    knowledge/     ingestion, AI Search, Foundry IQ          Data/Knowledge, Context/Retrieval
    agents/        agent definitions, workflows, orchestration  Orchestration/Action, Memory/State
    tools/         function tools, MCP server, A2A contractor   Orchestration/Action, Integration/Experience
    perception/    language, speech, vision, documents, media   Intelligence (Foundry Tools)
    governance/    guardrails, evaluation, tracing, PII         Evaluation/Reliability, Security/Controls
  mock_systems/    work-order system (SQLite + API), contractor service
  data/            synthetic buildings, leases, rules, media (safe to publish)
  data/eval/       evaluation sets; run results in data/eval/results/
  tests/
  scripts/         setup check, upload and rebuild scripts
  docs/            ARCHITECTURE.md, adr/, demo/, SERVICE_CHOICES.md and FAILURE_MODES.md (content comes from Rishi; you may type it up when he asks)
```

Folders appear when the session that needs them arrives. Don't create empty ones ahead of time.

## Security and hygiene (this repo is public)

- Keyless authentication with `DefaultAzureCredential` by default. Secrets only in `.env`, which is never committed.
- Synthetic data and fictional names only. No real personal data in photos, audio or documents.
- Public docs (README, release notes, ADRs): no em dashes; no claim without a number, a name or an artefact behind it.
- Git lives in this folder only. Never run `git init` in the parent course folder.

## Run it

```bash
cd capstone
source .venv/bin/activate
python scripts/check_setup.py   # local setup check; keep it working as the stack grows
streamlit run src/ui/app.py
```

## Before you finish a change

- Changed Python files compile (`python -m py_compile <file>`); start the app if the UI changed.
- Every AI-103 concept in the change has its `# AI-103` tag line, and the summary lists them.
- The README's "What it does now" is still true.
