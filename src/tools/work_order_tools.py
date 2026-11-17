"""
PURPOSE: Two function tools on the mock work-order system (get_resident, create_ticket), the checks before they run, and the tool-call loop.
LAYER:   Orchestration/Action
SESSION: S03
"""
from __future__ import annotations

import json
import time

from mock_systems import work_orders
from src.core.config import get_settings
from src.core.foundry import get_openai_client
from src.intelligence.resident_chat import load_system_message
from src.intelligence.triage import CATEGORIES, URGENCIES

MAX_ROUNDS = 5

# AI-103 2.1.c: two strict function tools. strict=True makes the model's arguments match the schema exactly, which needs
# every property in "required" and additionalProperties false; enums hold category and urgency to the S01 labels.
# No example values in any description: a forced call once copied an example unit from a description (FAILURE_MODES, S03).
UNIT_PROPERTY = {
    "type": "string",
    "description": "The unit id: the building letter (A for Contoso Heights A, B for Contoso Heights B, "
                   "G for Contoso Gardens), a hyphen, then the unit number the resident gave.",
}
TOOLS = [
    {
        "type": "function",
        "name": "get_resident",
        "description": "Look up who lives in a unit in the Contoso Living work-order system. "
                       "Returns the resident's name and building only.",
        "parameters": {
            "type": "object",
            "properties": {"unit": UNIT_PROPERTY},
            "required": ["unit"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "create_ticket",
        "description": "Raise a maintenance ticket in the Contoso Living work-order system. "
                       "Use only once the unit and a clear description of the problem are known. Returns the ticket id.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "enum": list(CATEGORIES), "description": "The kind of problem."},
                "urgency": {"type": "string", "enum": list(URGENCIES), "description": "How urgent the problem is."},
                "unit": UNIT_PROPERTY,
                "summary": {"type": "string", "description": "One or two sentences describing the problem, in English."},
            },
            "required": ["category", "urgency", "unit", "summary"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def unknown_unit_error(unit: str) -> dict:
    return {"error": f"No unit '{unit}' in the work-order system. Ask the resident for their building and unit number."}


def get_resident(unit: str) -> dict:
    """Return the resident's name and building only (never rent, lease or payment details), or an error for an unknown unit."""
    # AI-103 2.1.c: the app checks the argument against the work-order system before acting; strict makes it well formed, not true.
    resident = work_orders.find_resident(unit.strip().upper())
    return resident if resident else unknown_unit_error(unit)


def create_ticket(category: str, urgency: str, unit: str, summary: str) -> dict:
    """Write a ticket and return its id, or return an error to the model instead of acting."""
    # AI-103 2.1.c: validate every argument before anything is written; an error goes back to the model to reason about.
    unit = unit.strip().upper()
    if category not in CATEGORIES:
        return {"error": f"Unknown category '{category}'. Use one of: {', '.join(CATEGORIES)}."}
    if urgency not in URGENCIES:
        return {"error": f"Unknown urgency '{urgency}'. Use one of: {', '.join(URGENCIES)}."}
    if not summary.strip():
        return {"error": "The summary is empty. Ask the resident to describe the problem."}
    if work_orders.find_resident(unit) is None:
        return unknown_unit_error(unit)
    return {"ticket_id": work_orders.insert_ticket(unit, category, urgency, summary.strip())}


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


def reply_with_tools(messages: list[dict]) -> tuple[str, list[dict], int]:
    """Answer the resident, running any tool calls the model asks for. Returns the reply, the tool log and the input tokens."""
    settings = get_settings()
    client = get_openai_client()
    conversation = list(messages)  # this turn's tool calls and outputs are added here, not to the saved chat
    log: list[dict] = []
    input_tokens = 0
    for _ in range(MAX_ROUNDS):
        # AI-103 2.1.c: send the tools with every call; tool_choice "auto" lets the model decide whether it needs one.
        response = client.responses.create(
            model=settings.chat_deployment,
            instructions=load_system_message(),
            input=conversation,
            tools=TOOLS,
            tool_choice="auto",
        )
        input_tokens += response.usage.input_tokens
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            return response.output_text, log, input_tokens
        conversation += response.output  # keep the model's requests so it can match the results to them
        for call in calls:
            # AI-103 2.1.c: the model never runs the function. The app runs it and sends the result back
            # as a function_call_output with the same call_id, so the model can match result to request.
            result = run_tool_call(call.name, call.arguments, log)
            conversation.append({"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result)})
    return (f"Sorry, I could not finish this request: I stopped after {MAX_ROUNDS} rounds of tool calls. "
            "Please try again.", log, input_tokens)
