"""Holds the checker to docs/specs/citation-checker-cases.json (16 cases from real lines in the pinned repos)."""
import json
import subprocess
from pathlib import Path

import pytest

from server.checker import ROOT, check_citation, check_rule, load_repos

CASES = json.loads((ROOT / "docs" / "specs" / "citation-checker-cases.json").read_text(encoding="utf-8"))["cases"]
REPOS = load_repos()

pytestmark = pytest.mark.skipif(
    not all((r["path"] / ".git").exists() or r["path"].exists() for r in REPOS.values()),
    reason="source repos not present; run scripts/setup_repos.sh",
)


def test_fixtures_are_not_empty():
    # a test that loads zero cases would pass for the wrong reason
    assert len(CASES) >= 16


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_fixture(case):
    result = check_citation({k: case[k] for k in ("repo", "file", "line_start", "line_end", "evidence")}, REPOS)
    expect = case["expect"]
    assert result.verified == expect["verified"], result
    assert result.top_note == expect["first_note"], result
    if "found_lines" in expect:
        assert result.found_lines == expect["found_lines"]


def test_pinned_commits_match_repos_json():
    """A repo checked out at the wrong commit would make every citation result suspect."""
    for name, repo in REPOS.items():
        if not (repo["path"] / ".git").exists():
            pytest.skip(f"{name} is not a git checkout")
        head = subprocess.run(["git", "-C", str(repo["path"]), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        assert head == repo["sha"], f"{name}: checked out {head}, repos.json pins {repo['sha']}"


def test_rule_without_citations_is_never_verified():
    out = check_rule({"rule": "something", "citations": []}, REPOS)
    assert out["all_verified"] is False
    assert out["verify_text"] == "Could not verify: the rule has no citation"


def test_rule_needs_every_citation_verified():
    good = {"repo": "active_merchant", "file": "lib/active_merchant/billing/gateways/stripe.rb", "line_start": 31, "line_end": 31, "evidence": "self.default_currency = 'USD'"}
    bad = {**good, "evidence": "self.default_currency = 'EUR'"}
    assert check_rule({"rule": "r", "citations": [good]}, REPOS)["all_verified"] is True
    assert check_rule({"rule": "r", "citations": [good, bad]}, REPOS)["all_verified"] is False


def test_found_elsewhere_text_names_the_real_lines():
    case = next(c for c in CASES if c["id"] == "C05_found_elsewhere_bitpay")
    out = check_rule({"rule": "r", "citations": [{k: case[k] for k in ("repo", "file", "line_start", "line_end", "evidence")}]}, REPOS)
    assert "lines 1003-1004" in out["citations"][0]["verify_text"]


def test_malformed_citation_does_not_crash():
    for citation in ({}, {"repo": "hyperswitch"}, {"repo": "hyperswitch", "file": "config/development.toml", "line_start": "x", "line_end": None, "evidence": "abcdefgh"}):
        assert check_citation(citation, REPOS).verified is False


def _cite(case_id):
    case = next(c for c in CASES if c["id"] == case_id)
    return {k: case[k] for k in ("repo", "file", "line_start", "line_end", "evidence")}


def test_verified_citation_reads_plainly_but_keeps_the_detail():
    out = check_rule({"rule": "r", "citations": [_cite("C02_prefix_stripped_airwallex"), _cite("C04_off_by_one")]}, REPOS)
    for c in out["citations"]:
        assert c["verify_text"] == "Citation verified"
    assert "prefix_stripped" in out["citations"][0]["verify_notes"] and "range_off_by_1" in out["citations"][1]["verify_notes"]


def test_source_lines_are_the_real_lines_of_the_pinned_file():
    out = check_rule({"rule": "r", "citations": [_cite("C13_multiline_evidence")]}, REPOS)
    lines = out["citations"][0]["source_lines"]
    assert [l["n"] for l in lines] == [595, 596]
    assert lines[0]["text"].strip() == "[pm_filters.coinbase]" and lines[1]["text"].lstrip().startswith("crypto_currency")


def test_long_lines_are_shortened_for_display():
    out = check_rule({"rule": "r", "citations": [_cite("C15_part_marker")]}, REPOS)
    (line,) = out["citations"][0]["source_lines"]
    assert line["n"] == 653 and line["text"].endswith("\u2026") and len(line["text"]) <= 202
    assert "[part" not in line["text"]  # no index formatting leaks into what the PM sees


def test_unverified_citation_shows_where_the_text_really_is():
    out = check_rule({"rule": "r", "citations": [_cite("C05_found_elsewhere_bitpay")]}, REPOS)
    c = out["citations"][0]
    assert c["verified"] is False and [l["n"] for l in c["source_lines"]] == [1003, 1004]


def test_source_lines_are_capped():
    big = {"repo": "active_merchant", "file": "lib/active_merchant/billing/gateways/stripe.rb", "line_start": 30, "line_end": 31, "evidence": "self.supported_countries = %w(AE AT AU"}
    assert len(check_rule({"rule": "r", "citations": [big]}, REPOS)["citations"][0]["source_lines"]) <= 12
