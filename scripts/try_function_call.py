"""
PURPOSE: Show a function tool call end to end: what the model returns, what the app must do, and what the model does with the result.
LAYER:   Orchestration/Action
SESSION: S03
Concept:   the function tool and the call_id loop.
Watch for: in step 2 there is no answer text, only a request to call your function. The same call_id goes out and comes back.
Run:       python scripts/try_function_call.py
"""
import json
import sys

from lab_helpers import DEPLOYMENT, get_openai_client, title

# Try changing:
QUESTION = "Hello"  # try "Hello" (no tool needed) and unit 9999 (not found)
SEND_OUTPUT_BACK = True  # False stops after step 2, to show what the resident would get if the app did nothing

RESIDENTS = {  # a stand-in for the work-order system; all data is invented
    "1204": {"name": "Layla R.", "building": "Contoso Heights A", "rent_paid": True},
    "0307": {"name": "Omar K.", "building": "Contoso Gardens", "rent_paid": False},
}


def get_resident(unit: str) -> dict:
    """The real function. It runs in YOUR app, never inside the model."""
    return RESIDENTS.get(unit, {"error": f"No resident found for unit {unit}"})


# AI-103 2.1.c: a function tool is a name, a description and a schema for its arguments. strict=True makes the
# arguments follow the schema exactly; a strict schema lists every property in "required" and forbids extras.
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

client = get_openai_client()
messages = [{"role": "user", "content": QUESTION}]

title("1  The app sends the question and its list of tools")
print(f"question: {QUESTION}")
print(f"tools:    {[tool['name'] for tool in TOOLS]}")
first = client.responses.create(model=DEPLOYMENT, input=messages, tools=TOOLS)

title("2  What the model sent back")
print(f"output_text: {first.output_text!r}")
calls = [item for item in first.output if item.type == "function_call"]
for call in calls:
    # AI-103 2.1.c: the model returns a function_call item. It has run nothing; it is asking the app to.
    print(f"function_call: name={call.name}  arguments={call.arguments}  call_id={call.call_id}")
if not calls:
    sys.exit("No function call: the model answered on its own, because the question needed no tool.")
if not SEND_OUTPUT_BACK:
    sys.exit("Stopped here on purpose. Nothing ran and nothing was answered: the model never runs your function.")

title("3  The app runs the function itself")
messages += first.output  # keep the model's request in the conversation
for call in calls:
    result = get_resident(**json.loads(call.arguments))
    print(f"get_resident({call.arguments}) -> {result}")
    # AI-103 2.1.c: the result goes back as a function_call_output with the SAME call_id.
    messages.append({"type": "function_call_output", "call_id": call.call_id, "output": json.dumps(result)})

title("4  The app calls the model again, and now it can answer")
final = client.responses.create(model=DEPLOYMENT, input=messages, tools=TOOLS)
print(final.output_text)
print(f"\ninput tokens: first call {first.usage.input_tokens}, second call {final.usage.input_tokens} (two calls for one answer)")
