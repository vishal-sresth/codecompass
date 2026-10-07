-- CodeCompass request log (SQLite). Create with:  sqlite3 logs/codecompass.db < docs/specs/storage-schema.sql
-- Every request is logged automatically by the server. A PM verdict updates only the verdict_* columns;
-- the original record is immutable (enforced by the trigger below).

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

CREATE TABLE IF NOT EXISTS queries (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  ts                 TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),   -- UTC ISO-8601
  question           TEXT    NOT NULL CHECK (length(question) BETWEEN 1 AND 500),
  answer             TEXT,                                                              -- agent's plain-English answer; null on error
  rules_json         TEXT    NOT NULL DEFAULT '[]' CHECK (json_valid(rules_json)),      -- rules with citations + verified flags
  gaps_json          TEXT    NOT NULL DEFAULT '[]' CHECK (json_valid(gaps_json)),
  meta_json          TEXT    NOT NULL DEFAULT '{}' CHECK (json_valid(meta_json)),       -- seconds, input_tokens, output_tokens
  agent_version      INTEGER,                                                           -- Foundry agent version, null if unknown
  prompt_version     TEXT,                                                              -- e.g. 'system_v1', or 'unknown'
  index_commits_json TEXT    NOT NULL DEFAULT '{}' CHECK (json_valid(index_commits_json)), -- {"hyperswitch": "<sha>", "active_merchant": "<sha>"}
  error              TEXT,                                                              -- error code + message if the request failed
  verdict            TEXT    CHECK (verdict IS NULL OR verdict IN ('correct', 'partial', 'wrong')),
  verdict_note       TEXT    CHECK (verdict_note IS NULL OR length(verdict_note) <= 1000),
  verdict_ts         TEXT,
  CHECK ((verdict IS NULL) = (verdict_ts IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_queries_ts      ON queries (ts DESC);
CREATE INDEX IF NOT EXISTS idx_queries_verdict ON queries (verdict) WHERE verdict IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_queries_version ON queries (prompt_version, agent_version);

-- The original record can never be rewritten, only judged.
CREATE TRIGGER IF NOT EXISTS queries_original_is_immutable
BEFORE UPDATE OF ts, question, answer, rules_json, gaps_json, meta_json, agent_version, prompt_version, index_commits_json, error
ON queries
BEGIN
  SELECT RAISE(ABORT, 'original record is immutable; only verdict columns may change');
END;

-- Storage interface (server/storage.py):
--   save_record(question, answer, rules, gaps, meta, agent_version, prompt_version, index_commits, error) -> id
--       INSERT INTO queries (...) VALUES (...);  returns last_insert_rowid()
--   save_verdict(id, verdict, note) -> bool
--       UPDATE queries SET verdict=?, verdict_note=?, verdict_ts=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?;  false if no row changed
--   list_records(limit, verdict=None, since=None) -> rows
--       SELECT ... FROM queries [WHERE verdict=? AND ts>=?] ORDER BY ts DESC LIMIT ?;
