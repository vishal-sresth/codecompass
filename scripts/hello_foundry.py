"""Smoke test: can we reach the Foundry project and see our agent?"""
import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# tiny .env loader (no extra package needed)
for line in (Path(__file__).resolve().parent.parent / ".env").read_text().splitlines():
    if line.strip() and not line.startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

project = AIProjectClient(endpoint=os.environ["PROJECT_ENDPOINT"], credential=DefaultAzureCredential())
print("connected to:", os.environ["PROJECT_ENDPOINT"])
for agent in project.agents.list():
    print("agent:", agent.name)
