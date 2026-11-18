"""
PURPOSE: Create the vector store for rules search, upload the community rules and the maintenance SLA, and print its id for .env.
LAYER:   Data/Knowledge
SESSION: S03
Run:     python scripts/setup_rules_store.py   (from the capstone folder; run again after a rules file changes, then update .env)
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core.foundry import direct_openai_client  # noqa: E402

RULES_FILES = [REPO_ROOT / "data" / "rules" / "community_rules.md", REPO_ROOT / "data" / "rules" / "maintenance_sla.md"]


def create_rules_store() -> str:
    """Create a vector store holding both rules files, wait until they are indexed, and return its id."""
    # Same route as the chat calls: a vector store made through one endpoint is searched through that endpoint.
    client = direct_openai_client()
    # AI-103 2.1.b: a vector store is the searchable index; file_batches.upload_and_poll uploads the files
    # and waits until they are split into chunks and indexed. A changed file must be uploaded again.
    store = client.vector_stores.create(name="contoso-rules")
    handles = [open(path, "rb") for path in RULES_FILES]
    try:
        batch = client.vector_stores.file_batches.upload_and_poll(vector_store_id=store.id, files=handles)
    finally:
        for handle in handles:
            handle.close()
    if batch.file_counts.completed != len(RULES_FILES):
        raise RuntimeError(f"Only {batch.file_counts.completed} of {len(RULES_FILES)} files were indexed (status {batch.status}).")
    return store.id


if __name__ == "__main__":
    print(f"VECTOR_STORE_ID={create_rules_store()}")
