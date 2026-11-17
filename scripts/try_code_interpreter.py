"""
PURPOSE: Ask for a calculation over a small ticket table without and with the code_interpreter tool, and check both.
LAYER:   Orchestration/Action
SESSION: S03
Concept:   code_interpreter, which the model knows as "the python tool".
Watch for: the answer without the tool is an estimate; with the tool the model writes code, runs it and reports the result.
Cost:      one Code Interpreter session.
Run:       python scripts/try_code_interpreter.py
"""
import statistics
from collections import Counter

from lab_helpers import DEPLOYMENT, direct_openai_client, title

# Try changing:
QUESTION = "How many tickets are there per category, and what is the population standard deviation of days_open, to 3 decimals?"

TICKETS = """category,days_open
plumbing,3.5
hvac,1.25
electrical,7.75
plumbing,0.5
noise,12.0
hvac,2.75
plumbing,9.25
appliance,4.0
hvac,6.5
electrical,1.0
pest,15.5
plumbing,2.25
hvac,0.75
noise,3.0
appliance,8.5
plumbing,5.75
electrical,2.5
hvac,11.0
pest,6.25
plumbing,1.5"""

rows = [line.split(",") for line in TICKETS.splitlines()[1:]]
prompt = f"{QUESTION}\n\n{TICKETS}"
client = direct_openai_client()

title("1  Without the tool: the model works it out in its head")
print(client.responses.create(model=DEPLOYMENT, input=prompt).output_text)

title("2  With code_interpreter")
# AI-103 2.1.c: the tool gives the model a sandboxed Python runtime (no network). "container: auto" lets the service create it.
response = client.responses.create(
    model=DEPLOYMENT,
    instructions="Use the python tool for every calculation.",
    input=prompt,
    tools=[{"type": "code_interpreter", "container": {"type": "auto"}}],
)
print(response.output_text)

title("3  The code the model wrote and ran")
for item in response.output:
    if item.type == "code_interpreter_call":
        print(item.code)

title("4  The true values, computed here on your Mac")
print(dict(Counter(category for category, _ in rows)))
print(f"standard deviation: {statistics.pstdev(float(days) for _, days in rows):.3f}")
