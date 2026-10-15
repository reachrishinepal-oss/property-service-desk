"""
PURPOSE: Load the app's settings from environment variables (the .env file on your Mac).
LAYER:   Infrastructure/Operations
SESSION: S00
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

REQUIRED = ("FOUNDRY_PROJECT_ENDPOINT", "CHAT_DEPLOYMENT")


@dataclass(frozen=True)
class Settings:
    project_endpoint: str
    chat_deployment: str
    product_name: str
    judge_endpoint: str = ""


def get_settings() -> Settings:
    """Return validated settings, or explain exactly what is missing."""
    missing = [name for name in REQUIRED if not os.getenv(name) or "<" in os.getenv(name, "")]
    if missing:
        raise RuntimeError(
            "Missing settings in .env: " + ", ".join(missing)
            + ". Copy .env.example to .env in the capstone folder and fill in your values."
        )
    return Settings(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        chat_deployment=os.environ["CHAT_DEPLOYMENT"],
        product_name=os.getenv("PRODUCT_NAME", "Property Service Desk"),
        judge_endpoint=os.getenv("JUDGE_ENDPOINT", ""),
    )


def get_judge_endpoint() -> str:
    """Return JUDGE_ENDPOINT, or explain that it is missing (only the eval runner needs it)."""
    endpoint = get_settings().judge_endpoint
    if not endpoint or "<" in endpoint:
        raise RuntimeError(
            "Missing setting in .env: JUDGE_ENDPOINT. Copy it from .env.example and fill in the judge's endpoint."
        )
    return endpoint
