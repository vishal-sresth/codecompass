"""SQLite request log (docs/specs/storage-schema.sql, reused as the single source of truth for the schema).

Every request is logged by the server. A verdict updates only the verdict columns; the original record is immutable
(enforced by a trigger in the schema, and tested in server/tests/test_storage.py).
Interface (so the store can be swapped later): save_record, save_verdict, list_records.
"""
import json
import sqlite3
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = ROOT / "docs" / "specs" / "storage-schema.sql"
VERDICTS = ("correct", "partial", "wrong")


class Storage:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.executescript(SCHEMA_FILE.read_text(encoding="utf-8"))  # idempotent: CREATE ... IF NOT EXISTS

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=10)  # one short-lived connection per call: safe across request threads
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def is_ready(self) -> bool:
        try:
            with closing(self._connect()) as db:
                return db.execute("PRAGMA user_version").fetchone()[0] >= 1
        except sqlite3.Error:
            return False

    def save_record(self, *, question: str, answer: str | None = None, rules: list | None = None, gaps: list | None = None,
                    meta: dict | None = None, agent_version: int | None = None, prompt_version: str | None = None,
                    index_commits: dict | None = None, error: str | None = None) -> int:
        with closing(self._connect()) as db, db:
            cur = db.execute(
                """INSERT INTO queries (question, answer, rules_json, gaps_json, meta_json, agent_version,
                                        prompt_version, index_commits_json, error)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (question, answer, json.dumps(rules or []), json.dumps(gaps or []), json.dumps(meta or {}),
                 agent_version, prompt_version, json.dumps(index_commits or {}), error),
            )
            return cur.lastrowid

    def save_verdict(self, record_id: int, verdict: str, note: str | None = None) -> bool:
        """False if there is no such record. Raises ValueError for an invalid verdict or a note over 1000 characters."""
        if verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}")
        if note is not None and len(note) > 1000:
            raise ValueError("note is limited to 1000 characters")
        with closing(self._connect()) as db, db:
            cur = db.execute(
                """UPDATE queries SET verdict = ?, verdict_note = ?, verdict_ts = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                   WHERE id = ?""",
                (verdict, note, record_id),
            )
            return cur.rowcount == 1

    def list_records(self, limit: int = 50, verdict: str | None = None, since: str | None = None) -> list[dict]:
        """Newest first. verdict may be correct|partial|wrong, or 'none' for records without a verdict."""
        where, args = [], []
        if verdict == "none":
            where.append("verdict IS NULL")
        elif verdict:
            where.append("verdict = ?")
            args.append(verdict)
        if since:
            where.append("ts >= ?")
            args.append(since)
        sql = "SELECT * FROM queries" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY ts DESC, id DESC LIMIT ?"
        with closing(self._connect()) as db:
            rows = db.execute(sql, (*args, max(1, min(int(limit), 200)))).fetchall()
        return [self._row(r) for r in rows]

    @staticmethod
    def _row(r: sqlite3.Row) -> dict:
        return {
            "id": r["id"], "ts": r["ts"], "question": r["question"], "answer": r["answer"],
            "rules": json.loads(r["rules_json"]), "gaps": json.loads(r["gaps_json"]), "meta": json.loads(r["meta_json"]),
            "agent_version": r["agent_version"], "prompt_version": r["prompt_version"],
            "index_commits": json.loads(r["index_commits_json"]), "error": r["error"],
            "verdict": r["verdict"], "verdict_note": r["verdict_note"], "verdict_ts": r["verdict_ts"],
        }
