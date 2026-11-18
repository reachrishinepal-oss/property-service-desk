"""
PURPOSE: Ask the same question through the three clients the exam compares, then walk into the classic endpoint trap.
LAYER:   Infrastructure/Operations
SESSION: S02
Concept:   two endpoints (project, Azure OpenAI) and three clients (Foundry SDK's client, OpenAI, AzureOpenAI).
Watch for: which address each client talks to, and the error when a client is given the other one's address.
Run:       python scripts/try_three_clients.py
"""
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI, OpenAI

from lab_helpers import (DEPLOYMENT, ENTRA_SCOPE, OPENAI_ENDPOINT, PROJECT_ENDPOINT, RESOURCE, get_openai_client,
                         show_error, title)

# Try changing:
QUESTION = "Reply with the single word: hello"

credential = DefaultAzureCredential()

title("A  Foundry SDK: AIProjectClient(...).get_openai_client()   <- what your app uses")
try:
    # AI-103 2.1.e, 2.1.f: the project client knows the project endpoint and hands out an OpenAI-compatible client.
    client = get_openai_client()
    print(f"   talks to  {client.base_url}")
    print(f"   reply     {client.responses.create(model=DEPLOYMENT, input=QUESTION).output_text}")
except Exception as error:
    show_error(error)

title("B  OpenAI SDK on its own: OpenAI(base_url=<Azure OpenAI endpoint>, api_key=<token provider>)")
try:
    # AI-103 1.3.d: keyless sign-in for the OpenAI client: a token provider stands where an API key would go.
    client = OpenAI(base_url=OPENAI_ENDPOINT, api_key=get_bearer_token_provider(credential, ENTRA_SCOPE))
    print(f"   talks to  {client.base_url}")
    print(f"   reply     {client.responses.create(model=DEPLOYMENT, input=QUESTION).output_text}")
except Exception as error:
    show_error(error)

title("C  AzureOpenAI(azure_endpoint=..., api_version=...)   <- only when you must pin an API version")
try:
    # AI-103 2.1.e: AzureOpenAI needs an api_version; the older dated versions predate the Responses API,
    # so this call uses ChatCompletions.
    client = AzureOpenAI(
        azure_endpoint=f"https://{RESOURCE}.openai.azure.com",
        api_version="2024-10-21",
        azure_ad_token_provider=get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default"),
    )
    print(f"   talks to  {client.base_url}")
    answer = client.chat.completions.create(model=DEPLOYMENT, messages=[{"role": "user", "content": QUESTION}])
    print(f"   reply     {answer.choices[0].message.content}")
except Exception as error:
    show_error(error)

title("D  The trap: the OpenAI client given the PROJECT endpoint as if it were the OpenAI endpoint")
try:
    client = OpenAI(base_url=PROJECT_ENDPOINT, api_key=get_bearer_token_provider(credential, ENTRA_SCOPE))
    print(f"   talks to  {client.base_url}")
    print(f"   reply     {client.responses.create(model=DEPLOYMENT, input=QUESTION).output_text}")
except Exception as error:
    show_error(error)
    print("   That is the exam trap: the endpoint and the client have to match.")
