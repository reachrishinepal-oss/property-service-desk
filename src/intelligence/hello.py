"""
PURPOSE: The first model call: the service desk greets a resident.
LAYER:   Intelligence
SESSION: S00
"""
from __future__ import annotations

from src.core.config import get_settings
from src.core.foundry import get_openai_client

INSTRUCTIONS = (
    "You are the resident service desk assistant for Contoso Living, a fictional "
    "property manager in Dubai. Be brief and polite. Reply in the resident's language "
    "(Arabic or English). Never promise a repair date or a cost; say a person will confirm."
)


def first_reply(resident_message: str) -> str:
    """Send one resident message to the chat deployment and return the reply text."""
    settings = get_settings()
    client = get_openai_client()
    # AI-103 2.1.a: one Responses API call; model= takes your deployment name, not the model name.
    response = client.responses.create(
        model=settings.chat_deployment,
        instructions=INSTRUCTIONS,
        input=resident_message,
    )
    return response.output_text
