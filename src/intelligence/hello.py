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
    # ── LEARNER ZONE LZ-00.3 ──────────────────────────────────────────────
    # Goal:    Send resident_message to your chat deployment with the
    #          Responses API, using INSTRUCTIONS, and return the reply text.
    # Inputs:  client, settings.chat_deployment, INSTRUCTIONS, resident_message
    # Return:  the reply as a plain string
    # Watch:   the `model` argument takes your DEPLOYMENT name.
    # Concept: S00 first call; S02 goes deeper | Exam: 2.1.a, 2.1.e
    # Stuck?   Ask the tutor: "hint LZ-00.3"
    response = client.responses.create(
        model=settings.chat_deployment,
        instructions=INSTRUCTIONS,
        input=resident_message,
    )
    return response.output_text
    # ── END LEARNER ZONE ─────────────────────────────────────────────────
