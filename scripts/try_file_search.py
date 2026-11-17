"""
PURPOSE: Ask a question about community rules without and with the file_search tool, and show the passages it retrieved.
LAYER:   Context/Retrieval
SESSION: S03
Concept:   file_search over a vector store.
Watch for: without the tool the model cannot know the rules; with it, the answer comes from the passages listed in step 4.
Cost:      a few file-search tool calls and a tiny vector store (under the free first gigabyte), deleted at the end.
Run:       python scripts/try_file_search.py
"""
import tempfile
from pathlib import Path

from lab_helpers import DEPLOYMENT, direct_openai_client, title

# Try changing:
QUESTION = "Until what time can I use the gym, and what does a lost access card cost?"
KEEP_STORE = False  # True leaves the vector store in your resource (it then counts as stored data)

RULES = """Contoso Living community rules (synthetic document for a course experiment)

Gym: open every day from 05:30 to 23:00. Residents under 16 must be with an adult.
Pool: open from 07:00 to 21:00. No glass in the pool area.
Quiet hours: 22:00 to 07:00 on weekdays, 23:00 to 08:00 on Fridays and Saturdays.
Access cards: a lost access card is replaced for a fee of AED 150, payable at the community office.
Move-in and move-out: book the service lift 48 hours ahead. Moves are allowed from 09:00 to 18:00.
Maintenance: emergency repairs are attended within 4 hours, urgent repairs within 24 hours, routine repairs within 5 working days.
"""
INSTRUCTIONS = "You answer residents of Contoso Living. If you do not know a rule, say that you do not know."

# Microsoft's exercise uses the Azure OpenAI endpoint for vector stores, so this experiment does too.
client = direct_openai_client()

title("1  Without file_search")
print(client.responses.create(model=DEPLOYMENT, instructions=INSTRUCTIONS, input=QUESTION).output_text)

title("2  Create a vector store and upload the rules")
rules_file = Path(tempfile.gettempdir()) / "contoso_community_rules.txt"
rules_file.write_text(RULES, encoding="utf-8")
# AI-103 2.1.b: a vector store is the searchable index; upload_and_poll waits until the file has been indexed.
store = client.vector_stores.create(name="try-file-search-rules")
with open(rules_file, "rb") as handle:
    stored = client.vector_stores.files.upload_and_poll(vector_store_id=store.id, file=handle)
print(f"vector store {store.id}, file status: {stored.status}")

try:
    title("3  With file_search")
    # AI-103 2.1.b: the tool names the vector store to search; include asks for the retrieved passages as well.
    response = client.responses.create(
        model=DEPLOYMENT,
        instructions=INSTRUCTIONS,
        input=QUESTION,
        tools=[{"type": "file_search", "vector_store_ids": [store.id]}],
        include=["file_search_call.results"],
    )
    print(response.output_text)

    title("4  What it searched for and what it retrieved")
    for item in response.output:
        if item.type == "file_search_call":
            print(f"queries the model wrote: {item.queries}")
            for result in item.results or []:
                print(f"  score {result.score:.2f}  {result.filename}: {result.text[:100]!r}")
finally:
    title("5  Clean up")
    if KEEP_STORE:
        print(f"Kept vector store {store.id}. Delete it in the portal when you are done.")
    else:
        client.vector_stores.delete(store.id)
        client.files.delete(stored.id)
        print("Vector store and file deleted.")
