"""Unit checks for eval/score_hs.py on synthetic replies. Citations get their verified flags from the real citation checker,
so the scorer is exercised exactly as it will be on live answers. Run: python -m pytest eval/test_score_hs.py -q"""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from score_hs import Source, load_questions, score_all, summarise  # noqa: E402
from server.checker import check_rule, load_repos  # noqa: E402

REPOS = load_repos()
pytestmark = pytest.mark.skipif(not (ROOT / "hyperswitch" / "config" / "development.toml").exists(), reason="run scripts/setup_repos.sh")
Q = load_questions()
SRC = Source()
DEV, PROD = "config/development.toml", "config/deployments/production.toml"


def line_text(rel, n):
    return (ROOT / "hyperswitch" / rel).read_text(encoding="utf-8").splitlines()[n - 1]


def reply(*cites, rules_extra=(), answer="ok"):
    """cites: (file, first_line, last_line, evidence-or-None). Evidence defaults to the real text of those lines."""
    rules = []
    for f, a, b, ev in cites:
        evidence = ev if ev is not None else "\n".join(line_text(f, n) for n in range(a, b + 1))
        rules.append(check_rule({"rule": "r", "category": "commercial", "reasoning": "",
                                 "citations": [{"repo": "hyperswitch", "file": f, "line_start": a, "line_end": b, "evidence": evidence}]}, REPOS))
    rules += list(rules_extra)
    return {"answer": answer, "rules": rules, "gaps": []}


def ans(qid, response, status=200):
    return {"id": qid, "status": status, "response": response}


def one(qid, response, status=200):
    return score_all([ans(qid, response, status)], Q, SRC)[qid]


def test_ground_truth_lines_are_what_the_questions_say():
    # R7: MB Way on Adyen, development.toml line 716 (verified when the file was built)
    assert "mb_way" in line_text(DEV, 716)


def test_correct_citation_passes():
    r = one("R7", reply((DEV, 716, 716, None)))
    assert r["verdict"] == "PASS" and r["matched"][0]["line"] == 716


def test_same_fact_from_production_also_passes():
    prod_line = next(e["line"] for e in Q["R7"][1]["environments"] if e["file"] == PROD)
    assert one("R7", reply((PROD, prod_line, prod_line, None)))["verdict"] == "PASS"


def test_range_that_includes_a_neighbouring_line_still_passes():
    r = one("R7", reply((DEV, 715, 716, None)))  # the cited range starts one line above the entry
    assert r["verdict"] == "PASS" and r["matched"][0]["line"] == 716


def test_off_by_one_citation_still_scores_via_found_lines():
    r = one("R7", reply((DEV, 717, 717, line_text(DEV, 716))))  # evidence is on 716, cited 717
    assert r["verdict"] == "PASS"


def test_wrong_connector_does_not_pass():
    # a stripe entry offered for an Adyen question: R11 is affirm on Adyen, dev:718; stripe affirm is dev:654
    assert one("R11", reply((DEV, 654, 654, None)))["verdict"] != "PASS"


def test_different_payment_method_is_a_miss():
    assert one("R7", reply((DEV, 720, 720, None)))["verdict"] == "MISS"  # pay_bright on Adyen


def test_same_connector_and_method_but_different_values_is_partial():
    q = copy.deepcopy(Q)
    q["R7"][1]["countries"] = ["PT", "ES"]
    r = score_all([ans("R7", reply((DEV, 716, 716, None)))], q, SRC)["R7"]
    assert r["verdict"] == "PARTIAL" and r["different_values"][0]["countries"] == ["PT"]


def test_unverified_citation_is_never_counted():
    r = one("R7", reply((DEV, 716, 716, 'mb_way = { country = "ZZ", currency = "EUR" }')))
    assert r["verdict"] == "MISS" and r["unverified_citations"] == 1


def test_extra_rules_are_counted_not_penalised():
    r = one("R7", reply((DEV, 716, 716, None), (DEV, 720, 720, None)))
    assert r["verdict"] == "PASS" and r["rules"] == 2 and r["rules_not_matching"] == 1


def test_trick_passes_only_with_no_rules():
    assert one("D-T1", {"answer": "not found", "rules": [], "gaps": [{"not_found": "x"}]})["verdict"] == "PASS"
    failed = one("D-T1", reply((DEV, 716, 716, None)))
    assert failed["verdict"] == "FAIL" and failed["rules"] == 1


def test_trick_without_gaps_still_passes_but_is_flagged():
    r = one("D-T1", {"answer": "none", "rules": [], "gaps": []})
    assert r["verdict"] == "PASS" and r["gaps_present"] is False


def test_near_miss_is_always_manual():
    assert one("D-T2", {"answer": "global max_age 365", "rules": [], "gaps": []})["verdict"] == "MANUAL"


def test_errors_never_pass_and_missing_questions_are_not_run():
    assert one("R7", {"error": "rate_limited"}, status=429)["verdict"] == "ERROR"
    assert one("R7", "garbage")["verdict"] == "ERROR"
    res = score_all([ans("R7", reply((DEV, 716, 716, None)))], Q, SRC)
    assert res["R1"]["verdict"] == "NOT RUN"


def test_accepts_the_smoke_test_format_and_matches_by_question_text():
    item = {"question": Q["R7"][1]["question"], "status": 200, "result": reply((DEV, 716, 716, None))}
    assert score_all([item], Q, SRC)["R7"]["verdict"] == "PASS"


def test_summary_counts():
    answers = [ans("R7", reply((DEV, 716, 716, None))), ans("R8", reply((DEV, 716, 716, None))),  # pass, miss
               ans("D-T1", {"answer": "n", "rules": [], "gaps": []}), ans("D-T3", reply((DEV, 716, 716, None))),  # pass, fail
               ans("D-T2", {"answer": "n", "rules": [], "gaps": []})]
    s = summarise(score_all(answers, Q, SRC))
    assert s["answerable"]["pass"] == 1 and s["answerable"]["miss"] == 1 and s["answerable"]["run"] == 2 and s["answerable"]["total"] == 12
    assert s["trick"]["pass"] == 1 and s["trick"]["fail"] == 1 and s["near_miss"]["manual_review"] == 1


def test_every_answerable_question_scores_pass_on_its_own_ground_truth_line():
    """Positive control for the whole file: feed each item its own verified development.toml entry; all 12 must PASS."""
    q = json.loads((ROOT / "eval" / "hs_questions.json").read_text(encoding="utf-8"))
    dev_lines = {}
    for item in q["answerable"]:
        env = next(e for e in item["environments"] if e["file"] == DEV)
        dev_lines[item["id"]] = env["line"]
    answers = [ans(i, reply((DEV, n, n, None))) for i, n in dev_lines.items()]
    s = summarise(score_all(answers, Q, SRC))
    assert s["answerable"]["pass"] == 12 and s["answerable"]["total"] == 12
