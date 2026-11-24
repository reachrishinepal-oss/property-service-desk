"""
PURPOSE: Turn sentences into vectors and measure how close their meanings are, to see why vector search finds passages that share no words with the question.
LAYER:   Intelligence
SESSION: S04
Concept:   embeddings and cosine similarity (the retrieval step of RAG); keyword search against vector search.
Watch for: the Microsoft pair that shares no words but scores high, and the English and Arabic pair with the same meaning.
Run:       python scripts/try_embeddings.py   (needs an embedding deployment: see the guide, section 3)
"""
import math
import os

import openai

from lab_helpers import direct_openai_client, title

# Try changing:
EMBEDDING_DEPLOYMENT = os.getenv("EMBEDDING_DEPLOYMENT", "embed-small")   # your deployment name (text-embedding-3-small, created 20 Nov), not the model name
SENTENCES = {
    "A": "The children played joyfully in the park.",
    "B": "Kids happily ran around the playground.",
    "C": "The quarterly invoice is still unpaid.",
    "D": "My air conditioner is not cooling the flat.",
    "E": "المكيف ما يبرد الشقة",
    "F": "I would like to renew my lease for another year.",
}
STOP = {"the", "a", "an", "is", "are", "to", "for", "of", "in", "my", "i", "would", "like", "and", "not", "still"}   # ignored when counting shared words
QUESTION = "The A/C is blowing warm air"
SEARCH = ["Maintenance requests for cooling are handled within 24 hours.", "Pool opening hours are 06:00 to 22:00.", "Lease renewals need 90 days notice."]

client = direct_openai_client()   # embeddings go through the Azure OpenAI endpoint (/openai/v1), the route file_search used in S03


def embed(texts):
    # AI-103 2.1.b: an embedding is a list of numbers that stands for the meaning of a text. One embedding model, one call.
    result = client.embeddings.create(model=EMBEDDING_DEPLOYMENT, input=texts)
    return [item.embedding for item in result.data]


def cosine(a, b):
    # AI-103 2.1.b: cosine similarity is the angle between two vectors: near 1 means very close in meaning.
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


try:
    vectors = dict(zip(SENTENCES, embed(list(SENTENCES.values()))))
except openai.NotFoundError:
    raise SystemExit(f"No deployment named {EMBEDDING_DEPLOYMENT!r}. Create one in the portal (guide, section 3) or set EMBEDDING_DEPLOYMENT in .env.")

title("One embedding")
first = vectors["A"]
print(f"   A has {len(first)} numbers; the first four are {[round(x, 4) for x in first[:4]]}")

title("Cosine similarity between pairs")
for left, right, why in [("A", "B", "same meaning, no shared words"), ("A", "C", "unrelated"), ("D", "E", "same meaning, English and Arabic"),
                         ("D", "F", "both resident requests, different topics")]:
    shared = (set(SENTENCES[left].lower().rstrip(".").split()) & set(SENTENCES[right].lower().rstrip(".").split())) - STOP
    print(f"   {left} and {right}  cosine {cosine(vectors[left], vectors[right]):.3f}   shared words {len(shared)}   ({why})")

title(f"Search: {QUESTION!r}")
question_vector, *passage_vectors = embed([QUESTION] + SEARCH)
ranked = sorted(zip(SEARCH, passage_vectors), key=lambda pair: -cosine(question_vector, pair[1]))
for passage, vector in ranked:
    words = len((set(QUESTION.lower().split()) & set(passage.lower().rstrip(".").split())) - STOP)
    print(f"   cosine {cosine(question_vector, vector):.3f}   shared words {words}   {passage}")
