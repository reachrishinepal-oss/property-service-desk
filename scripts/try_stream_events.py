"""
PURPOSE: Show every event a streamed reply sends, in order, so the event names stop being hidden inside the app.
LAYER:   Intelligence
SESSION: S02
Concept:   streaming (stream=True) and its events.
Watch for: the order of the event types, how many are text deltas, and that the token count only arrives in the last event.
Run:       python scripts/try_stream_events.py
"""
from collections import Counter

from lab_helpers import DEPLOYMENT, get_openai_client, title

# Try changing:
QUESTION = "In two sentences, what should a resident do first if a pipe bursts?"
SHOW_TEXT = True  # False prints only the event types, which makes the pattern easier to see

client = get_openai_client()
# AI-103 2.1.a: stream=True makes the Responses API send the reply as a series of events while it is being written.
stream = client.responses.create(model=DEPLOYMENT, input=QUESTION, stream=True)

title("Events, in the order they arrived")
counts = Counter()
final = None
for number, event in enumerate(stream, start=1):
    counts[event.type] += 1
    # AI-103 2.1.a: response.output_text.delta carries the next piece of text in event.delta.
    if event.type == "response.output_text.delta" and SHOW_TEXT:
        print(f"{number:>4}  {event.type:<32} {event.delta!r}")
    else:
        print(f"{number:>4}  {event.type}")
    # AI-103 2.1.a: response.completed is the last event; it holds the whole response, including its id and usage.
    if event.type == "response.completed":
        final = event.response

title("How many of each")
for event_type, how_many in counts.items():
    print(f"{how_many:>4}  {event_type}")

title("What only the last event knows")
print(f"response id   {final.id}")
print(f"input tokens  {final.usage.input_tokens}")
print(f"output tokens {final.usage.output_tokens}")
