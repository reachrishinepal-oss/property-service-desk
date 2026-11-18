"""
PURPOSE: Show the other way to keep a conversation going: the service holds the history and each call passes previous_response_id.
LAYER:   Memory/State
SESSION: S02
Run:     python scripts/try_previous_response_id.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.core.foundry import get_openai_client  # noqa: E402 - needs the repo root on sys.path

DEPLOYMENT = "ai103model1"


def first_turn(client):
    """Turn 1: the rule goes in instructions, with the resident's first message."""
    # AI-103 2.1.a, 2.3.a: one Responses API call on ai103model1 with a rule in instructions; the service stores the response so a later call can point back to it.
    return client.responses.create(
        model=DEPLOYMENT,
        instructions="End every reply with the word DONE",
        input="My unit is 1204 and my kitchen tap is leaking.",
    )


def second_turn(client, previous_id):
    """Turn 2: only the new message and the id of turn 1; no instructions, on purpose."""
    # AI-103 2.1.e: previous_response_id lets the service supply the earlier conversation, so the app sends only the new message.
    return client.responses.create(
        model=DEPLOYMENT,
        previous_response_id=previous_id,
        input="Which unit did I say?",
    )


def main() -> None:
    client = get_openai_client()
    turn1 = first_turn(client)
    print(f"Turn 1 reply: {turn1.output_text}")
    print(f"Turn 1 input tokens: {turn1.usage.input_tokens}\n")
    turn2 = second_turn(client, turn1.id)
    print(f"Turn 2 reply: {turn2.output_text}")
    print(f"Turn 2 input tokens: {turn2.usage.input_tokens}")

    # AI-103 2.1.a: responses.retrieve fetches a stored response again by its id.
    again = client.responses.retrieve(turn1.id)
    print(f"\nTurn 1 fetched again with responses.retrieve: {again.output_text}")

    # store=False: the service keeps nothing, so there is no chain to continue from.
    unsaved = client.responses.create(model=DEPLOYMENT, input="My unit is 1204.", store=False)
    try:
        client.responses.create(model=DEPLOYMENT, previous_response_id=unsaved.id, input="Which unit did I say?")
        print("\nContinuing from a store=False response worked (not expected).")
    except Exception as error:
        print(f"\nContinuing from a store=False response failed: {type(error).__name__}: {str(error)[:200]}")


if __name__ == "__main__":
    main()
