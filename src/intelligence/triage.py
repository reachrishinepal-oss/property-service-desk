"""
PURPOSE: Classify one resident message into a triage category and urgency with a model deployment.
LAYER:   Intelligence
SESSION: S01
"""
from __future__ import annotations

from src.core.foundry import get_openai_client

# Same values as scripts/validate_eval_set.py and data/eval/README.md.
CATEGORIES = (
    "plumbing", "electrical", "hvac", "appliance", "pest",
    "noise", "access_security", "common_area", "lease_billing",
)
URGENCIES = ("emergency", "urgent", "routine")


def classify_request(deployment: str, text: str) -> dict:
    """Ask one deployment for the category and urgency of one resident message."""
    # ── LEARNER ZONE LZ-01.1 ──────────────────────────────────────────────
    # Goal:    Send one resident message to the given deployment with the
    #          Responses API and return the category and urgency it chooses
    #          (one of CATEGORIES and URGENCIES), plus token usage.
    # Inputs:  client (src.core.foundry.get_openai_client()), deployment, text,
    #          CATEGORIES, URGENCIES
    # Return:  a dict with keys category (str), urgency (str), input_tokens (int),
    #          output_tokens (int), reasoning_tokens (int, 0 if the response
    #          gives none)
    # Concept: S01 model choice evaluation | Exam: 1.1.a, 2.1.a, 2.1.d
    # Steps:    1. Give the model the resident's message plus the allowed categories and urgencies.
    #            2. Call the service through the existing client, with the deployment name in the
    #               model= slot so the right model answers.
    #            3. Ask for a fixed, labelled reply (category and urgency, nothing extra, using the
    #               exact words from the allowed lists) and read those two values out of it.
    #            4. Read the token counts the service reports (in, out, thinking) and return them
    #               with the two labels.
    # Decision: Send the resident message with the deployment name of the model from my resource.
    #           (Client: the project's OpenAI client; the deployment name goes in model=.)
    # Predict:  ai103model1 answers a fixed reply: Category: plumbing, Urgency: emergency
    # Stuck?   Ask the tutor: "hint LZ-01.1"
    client = get_openai_client()
    instructions = (
        "You triage resident messages for Contoso Living, a property manager in Dubai.\n"
        "The message may be in English or Arabic.\n"
        "\n"
        f"Choose exactly one category from: {', '.join(CATEGORIES)}\n"
        f"Choose exactly one urgency from: {', '.join(URGENCIES)}\n"
        "Use these words exactly as written, in lowercase.\n"
        "\n"
        "Reply with only these two lines and nothing else:\n"
        "Category: <category>\n"
        "Urgency: <urgency>"
    )
    response = client.responses.create(model=deployment, instructions=instructions, input=text)
    labels = {}
    for line in response.output_text.splitlines():
        name, _, value = line.partition(":")
        labels[name.strip().lower()] = value.strip()
    usage = response.usage
    details = usage.output_tokens_details
    return {
        "category": labels["category"],
        "urgency": labels["urgency"],
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "reasoning_tokens": (details.reasoning_tokens if details else 0) or 0,
    }
    # ── END LEARNER ZONE ─────────────────────────────────────────────────
