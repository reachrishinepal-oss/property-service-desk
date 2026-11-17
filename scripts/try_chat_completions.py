"""
PURPOSE: Ask the same question through the Responses API and the ChatCompletions API, then test which one remembers.
LAYER:   Intelligence
SESSION: S02
Concept:   Responses API against ChatCompletions API.
Watch for: where the reply text sits in each, and what ChatCompletions answers when the history is not resent.
Run:       python scripts/try_chat_completions.py
"""
from lab_helpers import DEPLOYMENT, get_openai_client, title

# Try changing:
RULES = "You are a property service desk assistant. Answer in one short sentence."
FIRST = "My unit is 1204 and my kitchen tap is leaking."
SECOND = "Which unit did I say?"

client = get_openai_client()

title("Responses API: instructions + input, text in output_text")
# AI-103 2.1.a: responses.create takes the rules in instructions and the message in input.
response = client.responses.create(model=DEPLOYMENT, instructions=RULES, input=FIRST)
print(f"response.output_text                 -> {response.output_text}")

title("ChatCompletions API: one list of messages, text in choices[0].message.content")
# AI-103 2.1.a: chat.completions.create takes a list of messages; the rules are a message with the role "system".
history = [{"role": "system", "content": RULES}, {"role": "user", "content": FIRST}]
completion = client.chat.completions.create(model=DEPLOYMENT, messages=history)
first_answer = completion.choices[0].message.content
print(f"completion.choices[0].message.content -> {first_answer}")

title("Second question to ChatCompletions, history NOT resent")
alone = client.chat.completions.create(
    model=DEPLOYMENT, messages=[{"role": "system", "content": RULES}, {"role": "user", "content": SECOND}]
)
print(alone.choices[0].message.content)

title("Second question to ChatCompletions, history resent by the app")
# ChatCompletions keeps no state: the app appends every message and sends the whole list each turn.
history += [{"role": "assistant", "content": first_answer}, {"role": "user", "content": SECOND}]
remembered = client.chat.completions.create(model=DEPLOYMENT, messages=history)
print(remembered.choices[0].message.content)
