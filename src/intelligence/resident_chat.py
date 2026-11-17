"""
PURPOSE: Send the whole resident conversation to the chat deployment and return the reply and its input tokens.
LAYER:   Intelligence
SESSION: S02
"""
from __future__ import annotations

from pathlib import Path

from src.core.config import get_settings
from src.core.foundry import get_openai_client

SYSTEM_MESSAGE_FILE = Path(__file__).with_name("resident_system_message.md")


def load_system_message() -> str:
    """Read the service desk's system message from its own file."""
    # AI-103 2.3.a: the system message (the rules the assistant follows) lives in one small file so it can be read and changed on its own.
    return SYSTEM_MESSAGE_FILE.read_text(encoding="utf-8")


def reply_to_resident(messages: list[dict]) -> tuple[str, int]:
    """Send the full message list and return (reply text, input tokens for this turn)."""
    settings = get_settings()
    client = get_openai_client()
    # AI-103 2.1.a, 2.1.e: one Responses API call on the deployment ai103model1 (model= takes the deployment name), through the keyless project client.
    # Manual chaining: the app keeps the conversation and resends the whole list every turn (no previous_response_id),
    # and the system message goes in instructions= on every call, apart from the conversation.
    response = client.responses.create(
        model=settings.chat_deployment,
        instructions=load_system_message(),
        input=messages,
    )
    # AI-103 2.1.a: usage.input_tokens counts everything sent this turn (instructions plus the whole history), so it grows each turn.
    return response.output_text, response.usage.input_tokens
