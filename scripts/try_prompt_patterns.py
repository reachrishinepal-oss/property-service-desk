"""
PURPOSE: Run the five triage rows the S01 prompt got wrong under four prompts, to see what a system message, few-shot examples and a reasoning line each change.
LAYER:   Intelligence
SESSION: S04
Concept:   prompt engineering: system message with definitions, few-shot examples, delimiters, a reminder at the end, a short reasoning line.
Watch for: which rows flip from wrong to right at which step, and what each step costs in input tokens.
Run:       python scripts/try_prompt_patterns.py
"""
import json

from lab_helpers import DEPLOYMENT, REPO_ROOT, get_openai_client, title

# Try changing:
ROW_IDS = ["T08", "T12", "T14", "T18", "T19"]   # the five rows ai103model1 got wrong in S01 (13 Oct run)
TEMPERATURE = 0                                  # steady answers; use None for a reasoning model (it rejects temperature)

CATEGORIES = "plumbing, electrical, hvac, appliance, pest, noise, access_security, common_area, lease_billing"

# Prompt A: the S01 prompt (v1). A role, the allowed words and a fixed reply shape. No definitions, no examples.
V1 = (
    "You triage resident messages for Contoso Living, a property manager in Dubai.\n"
    "The message may be in English or Arabic.\n"
    f"Choose exactly one category from: {CATEGORIES}\n"
    "Choose exactly one urgency from: emergency, urgent, routine\n"
    "Use these words exactly as written, in lowercase.\n"
    "Reply with only these two lines and nothing else:\nCategory: <category>\nUrgency: <urgency>"
)

# Prompt B: adds what each urgency MEANS (from data/eval/README.md) and a "when unsure" rule.
DEFINITIONS = (
    "Urgency means:\n"
    "- emergency: risk to life or property now\n"
    "- urgent: needs a fix within 24 hours\n"
    "- routine: can wait for the normal service window\n"
    "When the message could fit two urgencies, choose the higher one.\n"
    "Judge the situation described, not the resident's tone."
)
V2 = V1.replace("Use these words exactly", DEFINITIONS + "\nUse these words exactly")

# Prompt C: adds three invented examples (few-shot), fenced with delimiters, and repeats the key rule at the end.
# None of these examples is one of the 20 eval rows: an example that is also a test row would inflate the score.
EXAMPLES = (
    "### Examples\n"
    "Message: The kitchen tap has been dripping since Monday, no rush. Apartment 305.\n"
    "Category: plumbing\nUrgency: routine\n---\n"
    "Message: Smoke is coming from the bedroom socket and it smells of burning. Villa 9.\n"
    "Category: electrical\nUrgency: emergency\n---\n"
    "Message: Both lifts in Tower B have been out since this morning and I have a pram.\n"
    "Category: common_area\nUrgency: urgent\n### End of examples"
)
REMINDER = "\nRemember: use only the allowed words, and when unsure between two urgencies choose the higher one."
V3 = V2 + "\n\n" + EXAMPLES + REMINDER

# Prompt D: C plus one line of reasoning BEFORE the answer (a light chain of thought and self-check).
V4 = V3.replace(
    "Reply with only these two lines and nothing else:\nCategory: <category>\nUrgency: <urgency>",
    "First write one line starting 'Check:' that says which words in the message decide the urgency, "
    "and whether they match a definition above. Then write exactly:\nCategory: <category>\nUrgency: <urgency>",
)

PROMPTS = {"A v1 (S01)": V1, "B + definitions": V2, "C + few-shot + reminder": V3, "D + Check line": V4}

client = get_openai_client()
rows = [json.loads(line) for line in (REPO_ROOT / "data/eval/triage_eval_v1.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
rows = [r for r in rows if r["id"] in ROW_IDS]
totals = {name: [0, 0] for name in PROMPTS}   # right rows, input tokens

for row in rows:
    title(f"{row['id']}  expected {row['expected_category']} / {row['expected_urgency']}")
    for name, prompt in PROMPTS.items():
        kwargs = {} if TEMPERATURE is None else {"temperature": TEMPERATURE}
        # AI-103 2.1.a, 2.4.a: the prompt changes, the call does not. instructions carries the system message.
        response = client.responses.create(model=DEPLOYMENT, instructions=prompt, input=row["text"], **kwargs)
        labels = {}
        for line in response.output_text.splitlines():
            key, _, value = line.partition(":")
            labels[key.strip().lower()] = value.strip().lower()
        ok = labels.get("category") == row["expected_category"] and labels.get("urgency") == row["expected_urgency"]
        totals[name][0] += ok
        totals[name][1] += response.usage.input_tokens
        print(f"   {name:<24} {'RIGHT' if ok else 'wrong':<6} {labels.get('category')} / {labels.get('urgency')}")

title("Totals")
for name, (right, tokens) in totals.items():
    print(f"   {name:<24} {right} of {len(rows)} right   {tokens // len(rows)} input tokens per call")
