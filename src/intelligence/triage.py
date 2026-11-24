"""
PURPOSE: Classify one resident message into a triage category and urgency with a model deployment (prompt v1 or v2).
LAYER:   Intelligence
SESSION: S01 (triage prompt v2 and the shared triage policy added in S04)
"""
from __future__ import annotations

from pathlib import Path

from src.core.foundry import get_openai_client

POLICY_FILE = Path(__file__).with_name("triage_policy.md")

# Same values as scripts/validate_eval_set.py and data/eval/README.md.
CATEGORIES = (
    "plumbing", "electrical", "hvac", "appliance", "pest",
    "noise", "access_security", "common_area", "lease_billing",
)
URGENCIES = ("emergency", "urgent", "routine")

# Prompt v1 (S01): a role, the allowed words and a fixed reply shape. No definitions, no examples.
PROMPT_V1 = (
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

# Four invented few-shot examples for prompt v2. None copies a row of either eval set:
# an example that is also a test row would inflate the score.
EXAMPLES_V2 = (
    "### Examples\n"
    "Message: ما في ماي حار في الشقة من أمس الصبح، طفيت السخان وشغلته مرة ثانية وما في فايدة. شقة 1102، كونتوسو هايتس A.\n"
    "Check: 'no hot water' is listed under urgent; nothing suggests a safety risk.\n"
    "Category: plumbing\nUrgency: urgent\n---\n"
    "Message: Third time I'm reporting this and nobody ever comes, pathetic service. The burning smell from the "
    "electrics cupboard outside my door came back last night. It's stopped now but I'm fed up. Villa 31, Contoso Gardens.\n"
    "Check: 'burning smell' is always emergency; it has stopped but no technician has checked it, so it keeps its level.\n"
    "Category: electrical\nUrgency: emergency\n---\n"
    "Message: My statement shows AED 400 for a plumber call-out, but the leak was in the flat above me and your "
    "plumber only worked up there. Please remove this charge. Unit 608, Contoso Arta 2.\n"
    "Check: the resident asks us to remove a charge; the repair is only mentioned, and no risk is described.\n"
    "Category: lease_billing\nUrgency: routine\n---\n"
    "Message: The remote for the bedroom A/C stopped working. The A/C still cools fine from the wall panel, "
    "so whenever you have time. Unit 1407, Contoso Arta.\n"
    "Check: the A/C works and nobody is at risk, so the normal window applies.\n"
    "Category: hvac\nUrgency: routine\n"
    "### End of examples"
)


def load_triage_policy() -> str:
    """Read the shared triage policy (urgency and category rules) used by prompt v2, the chat and the ticket card."""
    # AI-103 2.3.a: one policy file is the single source for urgency and category rules, so the three prompts cannot disagree.
    return POLICY_FILE.read_text(encoding="utf-8").strip()


def build_prompt_v2() -> str:
    """Triage prompt v2: definitions from the policy file, few-shot examples, delimiters, a Check line and a reminder at the end."""
    # AI-103 2.3.a: prompt engineering. The call stays the same as v1; only the system message changes:
    # definitions (the shared policy), few-shot examples, ### delimiters around each part, and a reminder at the end (recency).
    # AI-103 2.3.b: the Check line asks for one short line of reasoning before the answer (a light chain of thought and self-check).
    return (
        "You triage resident messages for Contoso Living, a property manager in Dubai.\n"
        "The message may be in English or Arabic.\n"
        "\n"
        f"Choose exactly one category from: {', '.join(CATEGORIES)}\n"
        f"Choose exactly one urgency from: {', '.join(URGENCIES)}\n"
        "\n"
        "### Triage policy\n"
        f"{load_triage_policy()}\n"
        "### End of triage policy\n"
        "\n"
        "Judge the situation described, not the resident's tone.\n"
        "Use the category and urgency words exactly as written, in lowercase.\n"
        "\n"
        "First write one line starting 'Check:' that says which words in the message decide the urgency, "
        "and whether they match the policy above. Then write exactly:\n"
        "Category: <category>\n"
        "Urgency: <urgency>\n"
        "\n"
        f"{EXAMPLES_V2}\n"
        "\n"
        "Remember: use only the allowed words, apply the triage policy, and when unsure between two urgencies "
        "and a safety risk is possible, choose the higher one."
    )


def parse_labels(reply: str) -> dict:
    """Read 'Check:', 'Category:' and 'Urgency:' lines out of a reply; the Check line is kept apart so the labels still parse."""
    labels = {}
    for line in reply.splitlines():
        name, _, value = line.partition(":")
        name = name.strip().strip("*").lower()
        if name in ("check", "category", "urgency"):
            labels[name] = value.strip() if name == "check" else value.strip().strip("*").strip().lower()
    return labels


def classify_request(deployment: str, text: str, prompt: str = "v1") -> dict:
    """Ask one deployment for the category and urgency of one resident message, with prompt v1 or v2."""
    # AI-103 1.1.a, 2.1.d: ask one deployment to label a resident message, so models can be compared on the same answer key; token counts give the cost.
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
    client = get_openai_client()
    instructions = PROMPT_V1 if prompt == "v1" else build_prompt_v2()
    response = client.responses.create(model=deployment, instructions=instructions, input=text)
    labels = parse_labels(response.output_text)
    usage = response.usage
    details = usage.output_tokens_details
    return {
        "category": labels["category"],
        "urgency": labels["urgency"],
        "check": labels.get("check", ""),
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "reasoning_tokens": (details.reasoning_tokens if details else 0) or 0,
    }
