"""
PURPOSE: Run one prompt under different generation settings to see what temperature, top_p and max_output_tokens do.
LAYER:   Intelligence
SESSION: S02
Concept:   generation parameters.
Watch for: how alike the three replies are at each setting, and what the response reports when a reply is cut off.
Run:       python scripts/try_parameters.py
"""
from lab_helpers import DEPLOYMENT, get_openai_client, title

# Try changing:
PROMPT = "Write one sentence welcoming a new resident to Contoso Living."
RUNS = 3
SETTINGS = {
    "temperature 0   (steady)": {"temperature": 0},
    "temperature 1.5 (varied)": {"temperature": 1.5},
    "top_p 0.1       (narrow word choice)": {"top_p": 0.1},
}
CUT_OFF_AT = 20  # max_output_tokens for the last test

client = get_openai_client()
for name, setting in SETTINGS.items():
    title(name)
    for run in range(1, RUNS + 1):
        # AI-103 2.3.a: temperature (0 to 2) and top_p both control variety; change one of them, not both.
        print(f"{run}. {client.responses.create(model=DEPLOYMENT, input=PROMPT, **setting).output_text}")

title(f"max_output_tokens = {CUT_OFF_AT}")
# AI-103 2.3.a: max_output_tokens caps the reply; a capped reply comes back with status "incomplete".
cut = client.responses.create(
    model=DEPLOYMENT, input="Explain in detail how central air conditioning works.", max_output_tokens=CUT_OFF_AT
)
print(f"reply             {cut.output_text!r}")
print(f"status            {cut.status}")
print(f"incomplete reason {cut.incomplete_details}")
print(f"output tokens     {cut.usage.output_tokens}")
