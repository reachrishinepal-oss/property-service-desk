"""
PURPOSE: Time the same questions sent one after another and all at once, to show what AsyncOpenAI is for.
LAYER:   Intelligence
SESSION: S02
Concept:   the asynchronous client (AsyncOpenAI) against the normal one (OpenAI).
Watch for: the two times. Async does not make one call faster; it lets several calls wait at the same time.
Run:       python scripts/try_async_vs_sync.py
"""
import asyncio
import time

from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential

from lab_helpers import DEPLOYMENT, PROJECT_ENDPOINT, get_openai_client, title

# Try changing:
HOW_MANY = 5  # try 1 (async gives no gain) and 10 (the gap grows)
QUESTIONS = [
    "Name one cause of low water pressure.",
    "Name one cause of a tripping breaker.",
    "Name one cause of a noisy AC unit.",
    "Name one cause of a jammed door lock.",
    "Name one cause of a leaking tap.",
] * 2


def one_after_another(questions: list[str]) -> float:
    client = get_openai_client()  # the normal client: each call blocks until its reply is back
    start = time.perf_counter()
    for question in questions:
        client.responses.create(model=DEPLOYMENT, input=question, max_output_tokens=40)
    return time.perf_counter() - start


async def all_at_once(questions: list[str]) -> float:
    credential = DefaultAzureCredential()
    project = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)
    # AI-103 2.1.e: the async project client hands out an AsyncOpenAI client; every call on it is awaited.
    client = project.get_openai_client()
    start = time.perf_counter()
    # asyncio.gather starts all the calls, then waits for them together.
    await asyncio.gather(
        *[client.responses.create(model=DEPLOYMENT, input=question, max_output_tokens=40) for question in questions]
    )
    seconds = time.perf_counter() - start
    await client.close()
    await project.close()
    await credential.close()
    return seconds


questions = QUESTIONS[:HOW_MANY]
title(f"{len(questions)} questions")
slow = one_after_another(questions)
print(f"one after another (OpenAI client)      {slow:5.1f} seconds")
fast = asyncio.run(all_at_once(questions))
print(f"all at once (AsyncOpenAI client)       {fast:5.1f} seconds")
print(f"\nSame questions, same model, same tokens. Only the waiting changed: about {slow / fast:.1f} times faster.")
