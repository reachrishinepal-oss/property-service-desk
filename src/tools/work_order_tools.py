"""
PURPOSE: Two function tools on the mock work-order system (get_resident, create_ticket), rules search (file_search), the checks before tools run, and the tool-call loop.
LAYER:   Orchestration/Action, Context/Retrieval (rules search)
SESSION: S03 (guardrail outcomes checked on every call in S04)
"""
from __future__ import annotations

import json
import time

from mock_systems import work_orders
from src.core.config import get_settings
from src.core.foundry import direct_openai_client
from src.governance.filter_outcomes import call_with_filter_check
from src.intelligence.resident_chat import load_system_message
from src.intelligence.triage import CATEGORIES, URGENCIES

MAX_ROUNDS = 5

# AI-103 2.1.c: two strict function tools. strict=True makes the model's arguments match the schema exactly, which needs
# every property in "required" and additionalProperties false; enums hold category and urgency to the S01 labels.
# No example values in any description: a forced call once copied an example unit from a description (FAILURE_MODES, S03).
# A unit is two values, building and unit_number; the building is an enum, so the model picks a name and never decodes an id.
UNIT_PROPERTIES = {
    "building": {
        "type": "string",
        "enum": list(work_orders.BUILDINGS),
        "description": "The building the resident lives in. Match what the resident says to one building; "
                       "if more than one building could match, or none does, ask the resident instead of choosing.",
    },
    "unit_number": {
        "type": "string",
        "description": "The unit number exactly as the resident gave it, including any letters.",
    },
}
TOOLS = [
    {
        "type": "function",
        "name": "get_resident",
        "description": "Check that a unit exists in the Contoso Living work-order system. "
                       "Returns the unit's building only, never who lives there.",
        "parameters": {
            "type": "object",
            "properties": UNIT_PROPERTIES,
            "required": ["building", "unit_number"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "create_ticket",
        "description": "Raise a maintenance ticket in the Contoso Living work-order system. "
                       "Use only once the building, the unit number and a clear description of the problem are known. "
                       "Returns the ticket id.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": list(CATEGORIES), "description": "The kind of problem."},
                "urgency": {"type": "string", "enum": list(URGENCIES), "description": "How urgent the problem is."},
                **UNIT_PROPERTIES,
                "summary": {"type": "string", "description": "One or two sentences describing the problem, in English."},
            },
            "required": ["category", "urgency", "building", "unit_number", "summary"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def unknown_unit_error(building: str, unit_number: str) -> dict:
    return {"error": f"No unit '{unit_number}' in {building} in the work-order system. "
                     "Ask the resident to confirm their building and unit number."}


def get_resident(building: str, unit_number: str) -> dict:
    """Return the unit's building only (never a name, rent, lease or payment details), or an error for an unknown unit."""
    # AI-103 2.1.c: the app checks the argument against the work-order system before acting; strict makes it well formed, not true.
    # Only the building goes back to the model: the chat has no sign-in, so it cannot know whose unit is being asked about.
    # The pair (building, unit_number) is looked up exactly as given; nothing is split or decoded from text.
    resident = work_orders.find_resident(building, unit_number.strip())
    return {"building": resident["building"]} if resident else unknown_unit_error(building, unit_number)


def create_ticket(category: str, urgency: str, building: str, unit_number: str, summary: str) -> dict:
    """Write a ticket and return its id, or return an error to the model instead of acting."""
    # AI-103 2.1.c: validate every argument before anything is written; an error goes back to the model to reason about.
    unit_number = unit_number.strip()
    if category not in CATEGORIES:
        return {"error": f"Unknown category '{category}'. Use one of: {', '.join(CATEGORIES)}."}
    if urgency not in URGENCIES:
        return {"error": f"Unknown urgency '{urgency}'. Use one of: {', '.join(URGENCIES)}."}
    if not summary.strip():
        return {"error": "The summary is empty. Ask the resident to describe the problem."}
    if building not in work_orders.BUILDINGS:
        return {"error": f"Unknown building '{building}'. Ask the resident which building they live in."}
    if work_orders.find_resident(building, unit_number) is None:
        return unknown_unit_error(building, unit_number)
    ticket_id = work_orders.insert_ticket(building, unit_number, category, urgency, summary.strip())
    # The building and unit go back with the id, so the reply can name them and the resident can correct a mistake.
    return {"ticket_id": ticket_id, "building": building, "unit_number": unit_number}


FUNCTIONS = {"get_resident": get_resident, "create_ticket": create_ticket}


def run_tool_call(name: str, arguments: str, log: list[dict]) -> dict:
    """Run one function the model asked for, in this app, and log its name, arguments, result and seconds."""
    started = time.perf_counter()
    try:
        result = FUNCTIONS[name](**json.loads(arguments))
    except (KeyError, TypeError, ValueError) as error:  # unknown tool or unreadable arguments: tell the model, do not act
        result = {"error": f"Could not run {name}: {error}"}
    log.append({"name": name, "arguments": arguments, "result": result,
                "seconds": round(time.perf_counter() - started, 3)})
    return result


def rules_search_tool(vector_store_id: str) -> dict:
    """The file_search tool over the vector store with the community rules and the maintenance SLA."""
    # AI-103 2.1.b: file_search runs in Microsoft's cloud: the model writes search queries, the service finds
    # matching passages in the vector store, and the model answers from them.
    return {"type": "file_search", "vector_store_ids": [vector_store_id]}


def read_rules_searches(output: list) -> list[dict]:
    """Collect the queries the model wrote and each retrieved passage (file name, score, first 200 characters)."""
    searches = []
    for item in output:
        if item.type == "file_search_call":
            passages = [{"file": result.filename, "score": round(result.score, 3), "text": result.text[:200]}
                        for result in item.results or []]
            searches.append({"queries": item.queries, "passages": passages})
    return searches


def reply_with_tools(messages: list[dict], vector_store_id: str | None = None) -> tuple[str, list[dict], list[dict], int]:
    """Answer the resident, running any tool calls the model asks for. Returns the reply, the tool log, the rules searches and the input tokens.

    vector_store_id replaces the rules store from .env (the red-team run uses it for a poisoned copy).
    Raises FilterStop when a guardrail or a length limit stopped a call; the caller shows its message."""
    settings = get_settings()
    store_id = vector_store_id or settings.vector_store_id
    # The Azure OpenAI route, the same one that created the vector store (scripts/setup_rules_store.py).
    client = direct_openai_client()
    tools = TOOLS + ([rules_search_tool(store_id)] if store_id else [])
    conversation = list(messages)  # this turn's tool calls and outputs are added here, not to the saved chat
    log: list[dict] = []
    searches: list[dict] = []
    input_tokens = 0
    for _ in range(MAX_ROUNDS):
        # AI-103 2.1.b, 2.1.c: the function tools and file_search go in one tools list on one call; tool_choice "auto"
        # lets the model decide which, if any, it needs. include asks for the retrieved passages, so they can be shown.
        # AI-103 1.4.a: every call goes through the filter check, so a blocked prompt or a cut reply becomes a FilterStop.
        response = call_with_filter_check(lambda: client.responses.create(
            model=settings.chat_deployment,
            instructions=load_system_message(),
            input=conversation,
            tools=tools,
            tool_choice="auto",
            include=["file_search_call.results"] if store_id else [],
        ))
        input_tokens += response.usage.input_tokens
        searches += read_rules_searches(response.output)
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            return response.output_text, log, searches, input_tokens
        conversation += response.output  # keep the model's requests so it can match the results to them
        for call in calls:
            # AI-103 2.1.c: the model never runs the function. The app runs it and sends the result back
            # as a function_call_output with the same call_id, so the model can match result to request.
            result = run_tool_call(call.name, call.arguments, log)
            conversation.append({"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result)})
    return (f"Sorry, I could not finish this request: I stopped after {MAX_ROUNDS} rounds of tool calls. "
            "Please try again.", log, searches, input_tokens)
