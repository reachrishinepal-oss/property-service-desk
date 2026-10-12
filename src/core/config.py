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
    )
