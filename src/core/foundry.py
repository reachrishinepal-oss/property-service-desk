"""
PURPOSE: Create the clients that connect this app to your Microsoft Foundry project.
LAYER:   Infrastructure/Operations, Security/Controls (keyless sign-in)
SESSION: S00
"""
from __future__ import annotations

from functools import lru_cache
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from src.core.config import get_settings


@lru_cache(maxsize=1)
def get_project_client():
    """One Foundry project client for the whole app."""
    settings = get_settings()
    # ── LEARNER ZONE LZ-00.1 ──────────────────────────────────────────────
    # Goal:    Return a Foundry project client for settings.project_endpoint,
    #          signed in WITHOUT an API key (Microsoft Entra ID, keyless).
    # Inputs:  settings.project_endpoint
    # Return:  the project client object
    # You need: the project client class from the Foundry SDK and an Azure
    #          Identity credential that picks up your `az login` session.
    # Concept: S00 keyless authentication | Exam: 1.3.d, 2.1.f
    # Stuck?   Ask the tutor: "hint LZ-00.1"

    return AIProjectClient(endpoint=settings.project_endpoint, credential=DefaultAzureCredential())

@lru_cache(maxsize=1)
def get_openai_client():
    """An OpenAI-compatible client for calling your model deployments."""
    project = get_project_client()
    # ── LEARNER ZONE LZ-00.2 ──────────────────────────────────────────────
    # Goal:    From the project client, get an OpenAI-compatible client that
    #          can call your deployments with the Responses API.
    # Inputs:  project (the client from LZ-00.1)
    # Return:  the OpenAI-compatible client
    # You need: the project client's method that returns an OpenAI-compatible
    #          client (hint H2 names it for the current SDK version).
    # Concept: S00 ways into Foundry | Exam: 2.1.e, 2.1.f
    # Stuck?   Ask the tutor: "hint LZ-00.2"
    return project.get_openai_client()
    # ── END LEARNER ZONE ─────────────────────────────────────────────────
