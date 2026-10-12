"""
PURPOSE: One command that checks your local setup before you ask for help.
LAYER:   Infrastructure/Operations
SESSION: S00 (run it again whenever something feels broken)
Run:     python scripts/check_setup.py   (from the capstone folder, virtual environment active)

It never prints secrets. Paste its output into the tutor chat after "stuck:".
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from importlib import metadata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MINIMUMS = {
    "streamlit": "1.65.0",
    "python-dotenv": "1.2.4",
    "azure-identity": "1.26.0",
    "azure-ai-projects": "2.8.0",
    "openai": "3.26.0",
}
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))


def as_tuple(version: str) -> tuple[int, ...]:
    parts = []
    for piece in version.split(".")[:3]:
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


# 1. Python version
v = sys.version_info
check("Python 3.13", (v.major, v.minor) == (3, 13), f"found {v.major}.{v.minor}.{v.micro}")

# 2. Virtual environment
in_venv = sys.prefix != sys.base_prefix
check("Virtual environment active", in_venv, sys.prefix if in_venv else "run: source .venv/bin/activate")

# 3. Packages
for package, minimum in MINIMUMS.items():
    try:
        found = metadata.version(package)
        check(f"{package} >= {minimum}", as_tuple(found) >= as_tuple(minimum), f"found {found}")
    except metadata.PackageNotFoundError:
        check(f"{package} >= {minimum}", False, "not installed: pip install -r requirements.txt")

# 4. .env file (values are never printed)
env_path = REPO_ROOT / ".env"
check(".env exists", env_path.exists(), str(env_path) if env_path.exists() else "run: cp .env.example .env")
if env_path.exists():
    try:
        from dotenv import dotenv_values

        values = dotenv_values(env_path)
    except ImportError:
        values = {}
    endpoint = values.get("FOUNDRY_PROJECT_ENDPOINT") or ""
    shape_ok = endpoint.startswith("https://") and "/api/projects/" in endpoint and "<" not in endpoint
    check("Project endpoint format", shape_ok, "ok" if shape_ok else "expected https://<resource>.services.ai.azure.com/api/projects/<project>")
    deployment = values.get("CHAT_DEPLOYMENT") or ""
    check("Chat deployment name set", bool(deployment) and "<" not in deployment, "ok" if deployment and "<" not in deployment else "set CHAT_DEPLOYMENT")

# 5. .env ignored by Git
if shutil.which("git") and (REPO_ROOT / ".git").exists():
    ignored = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=REPO_ROOT).returncode == 0
    check(".env ignored by Git", ignored, "ok" if ignored else "add .env to .gitignore before committing")
else:
    check("Git repository", False, "not a Git repo yet (S00 creates it)")

# 6. Azure CLI sign-in (shows the subscription name, not any token)
if shutil.which("az"):
    out = subprocess.run(["az", "account", "show", "-o", "json"], capture_output=True, text=True)
    if out.returncode == 0:
        account = json.loads(out.stdout)
        check("Azure CLI signed in", True, f"subscription: {account.get('name')}")
    else:
        check("Azure CLI signed in", False, "run: az login")
else:
    check("Azure CLI installed", False, "install: brew install azure-cli")

width = max(len(name) for name, _, _ in results)
for name, ok, detail in results:
    print(f"{'OK ' if ok else 'FIX'}  {name.ljust(width)}  {detail}")
failed = sum(1 for _, ok, _ in results if not ok)
print(f"\n{len(results) - failed} of {len(results)} checks passed.")
sys.exit(1 if failed else 0)
