"""CodeCompass server. Implements docs/specs/api-contract.md.

Run:  uvicorn server.main:app --host 127.0.0.1 --port 8000 --reload
"""
import re
import threading
import time
from typing import Literal

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from server.agent import Agent, AgentError, FoundryAgent, RateLimited
from server.agent_output import BadOutput, parse_agent_output
from server.checker import check_rule, load_repos
from server.config import load_settings
from server.storage import Storage

settings = load_settings()

# Questions that try to instruct the assistant instead of asking about the code (docs/specs/api-contract.md: unsafe_input).
INJECTION = re.compile(
    r"ignore (all |any )?(the )?(previous|prior|above) (instructions|prompts)|reveal .{0,30}(system prompt|instructions)|"
    r"(show|print|repeat) .{0,30}(system prompt)|you are now|disregard .{0,20}instructions|jailbreak",
    re.I,
)


class AskRequest(BaseModel):
    question: str


class VerdictRequest(BaseModel):
    id: int
    verdict: Literal["correct", "partial", "wrong"]
    note: str | None = None


def error(status: int, code: str, message: str, retry_after: int | None = None, raw: str | None = None) -> JSONResponse:
    body = {"error": code, "message": message}
    if raw is not None:
        body["raw"] = raw[:4000]  # bad_output only: lets the UI offer "Show raw reply" (rendered as plain text)
    headers = {}
    if retry_after is not None:
        body["retry_after"] = retry_after
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(status_code=status, content=body, headers=headers)


def create_app(agent: Agent | None = None, storage: Storage | None = None, queue_wait_seconds: int | None = None) -> FastAPI:
    app = FastAPI(title="CodeCompass", version="0.1.0")
    app.state.agent = agent or FoundryAgent(settings.project_endpoint, settings.agent_name, settings.agent_timeout_seconds)
    app.state.storage = storage or Storage(settings.log_db_path)
    app.state.slot = threading.Semaphore(1)  # one agent call at a time: each uses 17-45K tokens of the per-minute quota
    app.state.queue_wait = settings.queue_wait_seconds if queue_wait_seconds is None else queue_wait_seconds
    app.state.versions = None  # (agent_version, prompt_version), looked up once, lazily
    repos = load_repos()
    index_commits = {name: r["sha"] for name, r in repos.items()}

    # Only our own web page may call this API from a browser.
    app.add_middleware(CORSMiddleware, allow_origins=[settings.web_origin], allow_methods=["GET", "POST"], allow_headers=["Content-Type"])

    @app.exception_handler(RequestValidationError)
    async def invalid(_: Request, exc: RequestValidationError):
        return error(422, "invalid_input", "Questions can be 1 to 500 characters of plain text." if any("question" in str(e["loc"]) for e in exc.errors()) else "That request is not valid.")

    def versions():
        if app.state.versions is None or app.state.versions == (None, None):
            app.state.versions = app.state.agent.describe()
        return app.state.versions

    @app.get("/api/health")
    def health() -> dict:
        v = app.state.versions or (None, None)
        return {"ok": True, "db": app.state.storage.is_ready(), "agent_version": v[0]}

    @app.post("/api/ask")
    def ask(body: AskRequest):
        question = body.question.strip()
        if not 1 <= len(question) <= settings.max_question_chars:
            return error(422, "invalid_input", f"Questions can be 1 to {settings.max_question_chars} characters.")
        if INJECTION.search(question):
            return error(422, "unsafe_input", "That question looks like an instruction to the assistant, not a question about the code. Please rephrase.")

        log = app.state.storage.save_record
        if not app.state.slot.acquire(timeout=app.state.queue_wait):
            log(question=question, error="busy: another question was still running")
            return error(429, "busy", "Another question is still running. Try again in a moment.", 30)
        try:
            started = time.monotonic()
            agent_version, prompt_version = versions()
            try:
                reply = app.state.agent.ask(question)
            except RateLimited as e:
                log(question=question, error=f"rate_limited: retry after {e.retry_after}s", agent_version=agent_version, prompt_version=prompt_version, index_commits=index_commits)
                return error(429, "rate_limited", "The model is busy. Wait a minute and try again.", e.retry_after)
            except AgentError as e:
                log(question=question, error=f"agent_error: {e}", agent_version=agent_version, prompt_version=prompt_version, index_commits=index_commits)
                return error(502, "agent_error", "The agent could not be reached. Try again in a moment.")
            seconds = round(time.monotonic() - started, 1)
            meta = {"seconds": seconds, "input_tokens": reply.input_tokens, "output_tokens": reply.output_tokens,
                    "agent_version": agent_version, "prompt_version": prompt_version}
            try:
                parsed, warnings = parse_agent_output(reply.text)
            except BadOutput as e:
                log(question=question, meta={**meta, "raw": reply.text[:4000]}, error=f"bad_output: {e}", agent_version=agent_version,
                    prompt_version=prompt_version, index_commits=index_commits)
                return error(502, "bad_output", "The agent returned something unexpected.", raw=reply.text)
            rules = [check_rule(r, repos) for r in parsed["rules"]]
            if warnings:
                meta["warnings"] = warnings
            record_id = log(question=question, answer=parsed["answer"], rules=rules, gaps=parsed["gaps"], meta=meta,
                            agent_version=agent_version, prompt_version=prompt_version, index_commits=index_commits)
            return {"id": record_id, "answer": parsed["answer"], "rules": rules, "gaps": parsed["gaps"], "meta": meta}
        finally:
            app.state.slot.release()

    @app.post("/api/verdict")
    def verdict(body: VerdictRequest):
        if body.note is not None and len(body.note) > 1000:
            return error(422, "invalid_input", "Notes can be up to 1000 characters.")
        if not app.state.storage.save_verdict(body.id, body.verdict, body.note):
            return error(404, "not_found", "No such answer.")
        return {"ok": True}

    @app.get("/api/records")
    def records(limit: int = Query(50, ge=1, le=200), verdict: Literal["correct", "partial", "wrong", "none"] | None = None, since: str | None = None):
        return {"records": app.state.storage.list_records(limit=limit, verdict=verdict, since=since)}

    return app


app = create_app()
