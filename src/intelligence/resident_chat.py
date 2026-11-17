"""
PURPOSE: Send the whole resident conversation to the chat deployment and stream the reply back, with its input tokens at the end.
LAYER:   Intelligence
SESSION: S02
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from src.core.config import get_settings
from src.core.foundry import get_openai_client

SYSTEM_MESSAGE_FILE = Path(__file__).with_name("resident_system_message.md")


def load_system_message() -> str:
    """Read the service desk's system message from its own file."""
    # AI-103 2.3.a: the system message (the rules the assistant follows) lives in one small file so it can be read and changed on its own.
    return SYSTEM_MESSAGE_FILE.read_text(encoding="utf-8")


def stream_reply_to_resident(messages: list[dict], result: dict) -> Iterator[str]:
    """Send the full message list and yield the reply piece by piece; puts the input tokens in result["input_tokens"] at the end."""
    settings = get_settings()
    client = get_openai_client()
    # AI-103 2.1.a, 2.1.e: one Responses API call on the deployment ai103model1 (model= takes the deployment name), through the keyless project client.
    # Manual chaining: the app keeps the conversation and resends the whole list every turn (no previous_response_id),
    # and the system message goes in instructions= on every call, apart from the conversation.
    # Streaming: stream=True sends the reply as events while it is being written, so the resident sees text straight away.
    stream = client.responses.create(
        model=settings.chat_deployment,
        instructions=load_system_message(),
        input=messages,
        stream=True,
    )
    for event in stream:
        # AI-103 2.1.a: each response.output_text.delta event carries the next piece of the reply.
        if event.type == "response.output_text.delta":
            yield event.delta
        # AI-103 2.1.a: response.completed is the final event; its usage.input_tokens counts everything sent this turn
        # (instructions plus the whole history), so it grows each turn. Streaming changes what the resident feels, not the cost.
        elif event.type == "response.completed":
            result["input_tokens"] = event.response.usage.input_tokens
    if "input_tokens" not in result:
        raise RuntimeError("The reply stopped before it finished (no response.completed event).")
