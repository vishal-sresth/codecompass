import sqlite3

import pytest

from server.storage import Storage


@pytest.fixture
def store(tmp_path):
    return Storage(tmp_path / "logs" / "test.db")  # also proves the folder is created


def test_ready_after_init(store):
    assert store.is_ready()


def test_save_and_list_round_trip(store):
    rid = store.save_record(question="q1", answer="a1", rules=[{"rule": "r"}], gaps=[{"not_found": "x"}],
                            meta={"seconds": 1.5}, agent_version=4, prompt_version="system_v1",
                            index_commits={"hyperswitch": "abc"})
    (row,) = store.list_records()
    assert row["id"] == rid and row["question"] == "q1" and row["answer"] == "a1"
    assert row["rules"] == [{"rule": "r"}] and row["meta"] == {"seconds": 1.5}
    assert row["agent_version"] == 4 and row["verdict"] is None


def test_failures_are_logged_too(store):
    rid = store.save_record(question="q", error="rate_limited: busy")
    row = store.list_records()[0]
    assert row["id"] == rid and row["answer"] is None and row["error"].startswith("rate_limited")


def test_verdict_updates_only_verdict_columns(store):
    rid = store.save_record(question="q", answer="original")
    assert store.save_verdict(rid, "partial", "needs the connector named") is True
    row = store.list_records()[0]
    assert (row["verdict"], row["verdict_note"]) == ("partial", "needs the connector named")
    assert row["verdict_ts"] and row["answer"] == "original"
    assert store.save_verdict(rid, "correct") is True  # may change their mind; the original stays
    assert store.list_records()[0]["verdict"] == "correct"


def test_unknown_id_and_bad_values(store):
    assert store.save_verdict(999, "correct") is False
    rid = store.save_record(question="q")
    with pytest.raises(ValueError):
        store.save_verdict(rid, "maybe")
    with pytest.raises(ValueError):
        store.save_verdict(rid, "wrong", "x" * 1001)


def test_original_record_is_immutable(store):
    rid = store.save_record(question="q", answer="original")
    with sqlite3.connect(store.db_path) as db, pytest.raises(sqlite3.DatabaseError, match="immutable"):
        db.execute("UPDATE queries SET answer = 'rewritten' WHERE id = ?", (rid,))
    assert store.list_records()[0]["answer"] == "original"


def test_schema_rejects_bad_input(store):
    with pytest.raises(sqlite3.IntegrityError):
        store.save_record(question="")
    with pytest.raises(sqlite3.IntegrityError):
        store.save_record(question="x" * 501)


def test_filters_and_limit(store):
    a, b, c = (store.save_record(question=f"q{i}") for i in range(3))
    store.save_verdict(a, "correct")
    store.save_verdict(b, "wrong")
    assert [r["id"] for r in store.list_records(verdict="wrong")] == [b]
    assert [r["id"] for r in store.list_records(verdict="none")] == [c]
    assert len(store.list_records(limit=2)) == 2
    assert [r["id"] for r in store.list_records()] == [c, b, a]  # newest first


def test_init_twice_keeps_data(tmp_path):
    path = tmp_path / "x.db"
    first = Storage(path)
    first.save_record(question="keep me")
    assert Storage(path).list_records()[0]["question"] == "keep me"
