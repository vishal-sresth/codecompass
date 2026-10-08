"""The Foundry agent behind a small interface, so the API flow can be tested with a fake agent (no Azure calls).

Real calls use the Responses API with an agent_reference; auth is `az login` (DefaultAzureCredential)."""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parent.parent


class AgentError(Exception):
    """Foundry unreachable, timed out, or returned an error other than rate limiting."""


class RateLimited(Exception):
    def __init__(self, retry_after: int = 60):
        super().__init__("rate limited")
        self.retry_after = retry_after


@dataclass
class AgentReply:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class Agent(Protocol):
    def ask(self, question: str) -> AgentReply: ...
    def describe(self) -> tuple[int | None, str | None]:
        """(agent_version, prompt_version). prompt_version is the prompts/*.md file whose text equals the agent's instructions."""


class FoundryAgent:
    def __init__(self, project_endpoint: str, agent_name: str, timeout_seconds: int = 90):
        self.project_endpoint, self.agent_name, self.timeout = project_endpoint, agent_name, timeout_seconds
        self._project = None
        self._client = None

    def _ensure(self):
        if self._client is None:
            from azure.ai.projects import AIProjectClient
            from azure.identity import DefaultAzureCredential

            if not self.project_endpoint:
                raise AgentError("PROJECT_ENDPOINT is not set (see .env.example)")
            self._project = AIProjectClient(endpoint=self.project_endpoint, credential=DefaultAzureCredential())
            self._client = self._project.get_openai_client()
        return self._client

    def ask(self, question: str) -> AgentReply:
        import openai

        try:
            response = self._ensure().responses.create(
                input=question,
                extra_body={"agent_reference": {"name": self.agent_name, "type": "agent_reference"}},
                timeout=self.timeout,
            )
        except openai.RateLimitError as e:
            retry = 60
            try:
                retry = int(e.response.headers.get("retry-after", 60))
            except Exception:
                pass
            raise RateLimited(retry) from e
        except AgentError:
            raise
        except Exception as e:  # network, auth, timeout, service errors
            raise AgentError(f"{type(e).__name__}: {str(e)[:200]}") from e
        usage = getattr(response, "usage", None)
        return AgentReply(
            text=response.output_text or "",
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )

    def describe(self) -> tuple[int | None, str | None]:
        try:
            self._ensure()
            latest = self._project.agents.get(self.agent_name).as_dict()["versions"]["latest"]
            instructions = (latest.get("definition") or {}).get("instructions", "").strip()
            prompt = next((p.stem for p in sorted((ROOT / "prompts").glob("*.md")) if p.read_text(encoding="utf-8").strip() == instructions), "unknown")
            return int(latest["version"]), prompt
        except Exception:
            return None, None
