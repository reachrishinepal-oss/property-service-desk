"""
PURPOSE: Send one resident message three ways (plain text, json_object, json_schema) to show what each one guarantees.
LAYER:   Intelligence
SESSION: S02
Concept:   structured outputs. json_object promises valid JSON; json_schema promises your exact fields and labels.
Watch for: the field names. With json_object the model invents them; with json_schema they are always your four.
Run:       python scripts/try_json_object_vs_schema.py
"""
import json

from lab_helpers import DEPLOYMENT, get_openai_client, title

# Try changing:
MESSAGE = "Hi, the AC in 1204 has been dripping onto the bedroom floor since last night and the carpet is soaked."
RUNS = 2  # more runs make the drift in json_object field names easier to see

ASK = f"Turn this resident message into a triage card as JSON.\n\nResident message: {MESSAGE}"  # names no fields on purpose

CARD_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": ["plumbing", "electrical", "hvac", "appliance", "pest", "noise",
                                                "access_security", "common_area", "lease_billing"]},
        "urgency": {"type": "string", "enum": ["emergency", "urgent", "routine"]},
        "unit": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["category", "urgency", "unit", "summary"],
    "additionalProperties": False,
}

WAYS = {
    "1 plain text (no format)": None,
    # AI-103 4.1.a: json_object only promises that the reply is valid JSON. The fields are whatever the model picks.
    "2 json_object": {"format": {"type": "json_object"}},
    # AI-103 4.1.a: json_schema with strict=True promises exactly these fields and only these labels.
    "3 json_schema": {"format": {"type": "json_schema", "name": "triage_card", "schema": CARD_SCHEMA, "strict": True}},
}

client = get_openai_client()
for name, text_format in WAYS.items():
    title(name)
    for run in range(1, RUNS + 1):
        extra = {"text": text_format} if text_format else {}
        reply = client.responses.create(model=DEPLOYMENT, input=ASK, **extra).output_text
        try:
            fields = ", ".join(json.loads(reply).keys())
            print(f"run {run}: valid JSON, fields: {fields}")
        except (ValueError, AttributeError):
            print(f"run {run}: NOT valid JSON on its own. It starts: {reply[:80]!r}")
