"""Server settings. Non-secret values only; they come from environment variables, with .env as a convenience.
Authentication to Azure is `az login` (DefaultAzureCredential); no keys live here."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    env_file = ROOT / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()  # allow trailing comments
        if "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    web_origin: str
    log_db_path: Path
    max_question_chars: int
    agent_timeout_seconds: int
    queue_wait_seconds: int
    project_endpoint: str
    agent_name: str


def load_settings() -> Settings:
    _load_dotenv()
    env = os.environ.get
    return Settings(
        web_origin=env("WEB_ORIGIN", "http://localhost:3000"),
        log_db_path=ROOT / env("LOG_DB_PATH", "logs/codecompass.db"),
        max_question_chars=int(env("MAX_QUESTION_CHARS", "500")),
        agent_timeout_seconds=int(env("AGENT_TIMEOUT_SECONDS", "90")),
        queue_wait_seconds=int(env("QUEUE_WAIT_SECONDS", "60")),
        project_endpoint=env("PROJECT_ENDPOINT", ""),
        agent_name=env("AGENT_NAME", "Codecompass-agent"),
    )
