"""Shared helpers: load .env and build a Foundry client."""
import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def project_client():
    load_env()
    return AIProjectClient(endpoint=os.environ["PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
