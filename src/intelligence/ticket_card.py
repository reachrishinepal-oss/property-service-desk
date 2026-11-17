"""
PURPOSE: Read the whole resident conversation and fill the four-field triage card (category, urgency, unit, summary).
LAYER:   Intelligence
SESSION: S02
"""
from __future__ import annotations

import json

from src.core.config import get_settings
from src.core.foundry import get_openai_client
from src.intelligence.triage import CATEGORIES, URGENCIES

CARD_INSTRUCTIONS = (
    "You fill a triage card for Contoso Living, a property manager in Dubai, from a resident conversation "
    "that may be in English or Arabic. Use everything said so far.\n"
    "category: the one category that best fits the problem.\n"
    "urgency: emergency, urgent or routine.\n"
    "unit: the unit number exactly as the resident gave it, or unknown if the resident has not given one.\n"
    "summary: one short sentence in English describing the problem."
)

# The card's shape: four required fields, two of them limited to the S01 labels, and nothing extra allowed.
CARD_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": list(CATEGORIES)},
        "urgency": {"type": "string", "enum": list(URGENCIES)},
        "unit": {"type": "string", "description": "The unit number, or unknown if not given yet."},
        "summary": {"type": "string"},
    },
    "required": ["category", "urgency", "unit", "summary"],
    "additionalProperties": False,
}


def fill_ticket_card(messages: list[dict]) -> tuple[dict, int]:
    """Send the whole conversation and return (the card as a dict, input tokens for this call)."""
    settings = get_settings()
    client = get_openai_client()
    # AI-103 2.1.a, 2.1.e: structured outputs: a second Responses API call on ai103model1 (keyless client) with a json_schema
    # in text.format and strict=True, so the reply must have exactly these four fields and only the allowed labels.
    # json_schema is used, not json_object: json_object only promises valid JSON, not these fields.
    response = client.responses.create(
        model=settings.chat_deployment,
        instructions=CARD_INSTRUCTIONS,
        input=messages,
        text={"format": {"type": "json_schema", "name": "triage_card", "schema": CARD_SCHEMA, "strict": True}},
    )
    # AI-103 2.1.a: this call also reads the whole conversation, so its input tokens grow each turn too.
    return json.loads(response.output_text), response.usage.input_tokens
