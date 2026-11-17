"""
PURPOSE: Shared set-up for the concept labs (scripts/try_*.py): the repo path, your settings, and small print helpers.
LAYER:   Infrastructure/Operations
SESSION: S02 (direct client added in S03)
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core.config import get_settings  # noqa: E402
from src.core.foundry import get_openai_client  # noqa: E402,F401  (the Foundry SDK route your app uses)

SETTINGS = get_settings()
DEPLOYMENT = SETTINGS.chat_deployment  # your deployment name (ai103model1), never the model's name
PROJECT_ENDPOINT = SETTINGS.project_endpoint
RESOURCE = PROJECT_ENDPOINT.split("//")[1].split(".")[0]  # "ai103v1" in https://ai103v1.services.ai.azure.com/...
# The second door into the same resource: the Azure OpenAI endpoint, used by the OpenAI SDK on its own.
OPENAI_ENDPOINT = f"https://{RESOURCE}.openai.azure.com/openai/v1/"
ENTRA_SCOPE = "https://ai.azure.com/.default"


def direct_openai_client():
    """The OpenAI SDK route that Microsoft's exercises use: the Azure OpenAI endpoint with keyless sign-in."""
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import OpenAI

    # AI-103 1.3.d, 2.1.e: a token provider stands where an API key would go, so this is still keyless.
    return OpenAI(base_url=OPENAI_ENDPOINT, api_key=get_bearer_token_provider(DefaultAzureCredential(), ENTRA_SCOPE))


def title(text: str) -> None:
    print("\n" + "=" * 12 + " " + text + " " + "=" * 12)


def show_error(error: Exception) -> None:
    print(f"   ERROR  {type(error).__name__}: {str(error)[:300]}")
