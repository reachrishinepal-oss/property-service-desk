"""
PURPOSE: Send the same two messages under each tool_choice setting, to show who decides whether a tool is called.
LAYER:   Orchestration/Action
SESSION: S03
Concept:   tool_choice: auto, required, none, or one named function.
Watch for: "required" forces a call even for a thank-you; "none" blocks the call even when the question needs it.
Run:       python scripts/try_tool_choice.py
"""
from lab_helpers import DEPLOYMENT, get_openai_client, title

# Try changing:
MESSAGES = ["Who lives in unit 1204?", "Thanks, that is all for today."]

TOOLS = [{
    "type": "function",
    "name": "get_resident",
    "description": "Look up the resident of a unit in the Contoso Living work-order system.",
    "parameters": {
        "type": "object",
        "properties": {"unit": {"type": "string", "description": "The unit number, for example 1204"}},
        "required": ["unit"],
        "additionalProperties": False,
    },
    "strict": True,
}]

CHOICES = {
    "auto (the default: the model decides)": "auto",
    "required (must call a tool)": "required",
    "none (must not call a tool)": "none",
    "a named function (must call this one)": {"type": "function", "name": "get_resident"},
}

client = get_openai_client()
for message in MESSAGES:
    title(message)
    for label, choice in CHOICES.items():
        # AI-103 2.1.c: tool_choice overrides the default, in which the model decides for itself.
        response = client.responses.create(model=DEPLOYMENT, input=message, tools=TOOLS, tool_choice=choice)
        calls = [item for item in response.output if item.type == "function_call"]
        if calls:
            print(f"{label:<40} -> asked to call {calls[0].name}({calls[0].arguments})")
        else:
            print(f"{label:<40} -> answered in text: {response.output_text[:70]!r}")
