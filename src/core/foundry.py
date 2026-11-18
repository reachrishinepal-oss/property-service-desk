"""
PURPOSE: Create the clients that connect this app to your Microsoft Foundry project.
LAYER:   Infrastructure/Operations, Security/Controls (keyless sign-in)
SESSION: S00 (direct Azure OpenAI client moved here from scripts/lab_helpers.py in S03)
"""
from __future__ import annotations

from functools import lru_cache
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI

from src.core.config import get_settings


@lru_cache(maxsize=1)
def get_project_client():
    """One Foundry project client for the whole app."""
    settings = get_settings()
    # AI-103 1.3.d, 2.1.f: connect to your Foundry project by its endpoint and sign in with your Azure identity (keyless; the Foundry User role allows the calls).

    return AIProjectClient(endpoint=settings.project_endpoint, credential=DefaultAzureCredential())

@lru_cache(maxsize=1)
def get_openai_client():
    """An OpenAI-compatible client for calling your model deployments."""
    project = get_project_client()
    # AI-103 2.1.e: the Foundry SDK hands out an OpenAI-compatible client that calls your deployments with the Responses API.
    return project.get_openai_client()


ENTRA_SCOPE = "https://ai.azure.com/.default"


def openai_endpoint() -> str:
    """The Azure OpenAI endpoint of the same resource as the project, for example https://<resource>.openai.azure.com/openai/v1/."""
    resource = get_settings().project_endpoint.split("//")[1].split(".")[0]
    return f"https://{resource}.openai.azure.com/openai/v1/"


@lru_cache(maxsize=1)
def direct_openai_client():
    """The OpenAI SDK on the Azure OpenAI endpoint with keyless sign-in: the route Microsoft's exercises use for vector stores."""
    # AI-103 1.3.d, 2.1.e: a token provider stands where an API key would go, so this is still keyless.
    return OpenAI(base_url=openai_endpoint(), api_key=get_bearer_token_provider(DefaultAzureCredential(), ENTRA_SCOPE))
