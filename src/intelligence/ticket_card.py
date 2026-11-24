"""
PURPOSE: Read the whole resident conversation and fill the triage card (category, urgency, building, unit_number, summary).
LAYER:   Intelligence
SESSION: S02 (shared triage policy, building and unit_number, and the filter check added in S04)
"""
from __future__ import annotations

import json

from src.core.config import get_settings
from mock_systems.work_orders import BUILDINGS
from src.core.foundry import get_openai_client
from src.governance.filter_outcomes import call_with_filter_check
from src.intelligence.triage import CATEGORIES, URGENCIES, load_triage_policy


def card_instructions() -> str:
    """The card's instructions, with category and urgency decided by the shared triage policy."""
    return (
        "You fill a triage card for Contoso Living, a property manager in Dubai, from a resident conversation "
        "that may be in English or Arabic. Use everything said so far.\n"
        "category and urgency: decide them with the triage policy below.\n"
        "building: the building the resident named, or unknown if they have not named one or it is unclear.\n"
        "unit_number: the unit number exactly as the resident gave it, or unknown if they have not given one.\n"
        "summary: one short sentence in English describing the problem.\n"
        "\n### Triage policy\n" + load_triage_policy() + "\n### End of triage policy"
    )


# The card's shape: five required fields, like the tickets; category, urgency and building are limited to known values.
CARD_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(CATEGORIES)},
        "urgency": {"type": "string", "enum": list(URGENCIES)},
        "building": {"type": "string", "enum": [*BUILDINGS, "unknown"]},
        "unit_number": {"type": "string", "description": "The unit number as the resident gave it, or unknown if not given yet."},
        "summary": {"type": "string"},
    },
    "required": ["category", "urgency", "building", "unit_number", "summary"],
    "additionalProperties": False,
}


def fill_ticket_card(messages: list[dict]) -> tuple[dict, int]:
    """Send the whole conversation and return (the card as a dict, input tokens for this call). Raises FilterStop if a guardrail stopped it."""
    settings = get_settings()
    client = get_openai_client()
    # AI-103 2.1.a, 2.1.e: structured outputs: a second Responses API call on ai103model1 (keyless client) with a json_schema
    # in text.format and strict=True, so the reply must have exactly these five fields and only the allowed labels.
    # json_schema is used, not json_object: json_object only promises valid JSON, not these fields.
    # AI-103 1.4.a: the same filter check as the chat, so a blocked prompt or cut reply is a FilterStop, not a crash.
    response = call_with_filter_check(lambda: client.responses.create(
        model=settings.chat_deployment,
        instructions=card_instructions(),
        input=messages,
        text={"format": {"type": "json_schema", "name": "triage_card", "schema": CARD_SCHEMA, "strict": True}},
    ))
    # AI-103 2.1.a: this call also reads the whole conversation, so its input tokens grow each turn too.
    return json.loads(response.output_text), response.usage.input_tokens
