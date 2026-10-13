# Build rules for this repository

For Claude Code in VS Code and for the AI-103 Studio tutor. Read this before writing any code here.

## What this is

Property Service Desk (working name): an AI service desk for Contoso Living, a fictional property manager in Dubai. Residents report problems by chat, voice, call, photo or video in Arabic or English; agents triage, check the lease, raise and approve work orders, dispatch contractors and reply.

It is also the capstone of Rishi's AI-103 course. Every feature exercises an exam skill. The course plan lives outside this repo in `../course/` (`SYLLABUS.md`, `CAPSTONE.md`, `EXAM_MAP.md`); read the current session's block there before building.

## How Rishi uses you

He vibe-codes the scaffold with you. Each session the AI-103 Studio tutor gives him a scaffold brief (what to build, which files, constraints, and the learner zones to leave empty); he pastes it here. Build exactly that, keep changes small and reviewable, then summarise what changed file by file so he can review the diff before committing.

## The learner-zone contract (the most important rule)

Rishi is learning. Code splits into two kinds:

1. **Scaffold, which you write** complete and runnable: UI, mock systems, synthetic data, configuration, logging, glue code, tests, scripts, docs.
2. **Learner zones, which he writes:** any code that exercises an AI-103 skill. That means Foundry and Azure SDK clients and authentication, model and agent calls, prompts and instructions, tool schemas and tool loops, agent and workflow definitions, retrieval and index queries, Language, Speech, Translator, Vision, Content Understanding and Document Intelligence calls, evaluation runs, and safety settings.

Rules:
- Leave the `Decision:` and `Predict:` lines exactly as in the template; Rishi fills them in.
- Never write code inside a learner zone. Leave the block with its header and `raise NotImplementedError("LZ-xx.n")`.
- Exception: when Rishi's message says `translate my steps in LZ-xx.n` and the zone's `Steps:` comment holds his own plain-English steps, write code that implements exactly those steps and nothing more: no extra validation, no prompt wording and no parameters he did not state. Keep his `Steps:` comment above the code. If the steps are empty or too vague to code, do not fill the gaps; ask him one plain-language question instead. After writing, list each line of the zone with a one-sentence meaning and ask him to explain them back.
- Never solve a zone indirectly, for example in a helper function the zone would then call.
- Solve a zone only when Rishi says "solve LZ-xx.n", then explain it line by line.
- When new scaffold needs an AI call, create a new learner zone for it (the next free number in the current session) instead of writing the call.
- The scaffold must run with zones unfinished: catch `NotImplementedError` at the UI edge and show "Next step: LZ-xx.n".

Learner-zone block (Python):

```python
    # ── LEARNER ZONE LZ-02.1 ──────────────────────────────────────────────
    # Goal:    what the code must achieve, in one or two lines
    # Inputs:  names available at this point
    # Return:  what to return
    # Concept: S02 <concept> | Exam: <skill IDs from EXAM_MAP.md>
    # Steps:    (Rishi, before coding: your plain-English steps, one per line)
    # Decision: (Rishi, before coding: which client, endpoint, parameter or service, and why)
    # Predict:  (Rishi, before running: the output or error you expect)
    # Stuck?   Ask the tutor: "hint LZ-02.1"
    raise NotImplementedError("LZ-02.1")
    # ── END LEARNER ZONE ─────────────────────────────────────────────────
```

Numbering: `LZ-<session>.<n>`, for example `LZ-06.2`. Portal steps are `PZ-<session>.<n>`; they live in the session notes, not in code.

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
  docs/            ARCHITECTURE.md, adr/, demo/, SERVICE_CHOICES.md and FAILURE_MODES.md (Rishi writes these; never fill them in)
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
- No learner zone was filled.
- The README's "What it does now" is still true.
