import json

import pytest

from server.agent_output import BadOutput, parse_agent_output

GOOD = {
    "answer": "Stripe supports 41 countries.",
    "rules": [{"rule": "Stripe supports these merchant countries.", "category": "technical",
               "citations": [{"repo": "active_merchant", "file": "lib/x.rb", "line_start": 30, "line_end": 30, "evidence": "self.supported_countries = %w(AE AT)"}],
               "reasoning": "It is declared in the class."}],
    "gaps": [{"looked_in": ["stripe.rb"], "not_found": "no overrides", "suggested_follow_up": "ask engineering"}],
}


def test_plain_json():
    result, warnings = parse_agent_output(json.dumps(GOOD))
    assert result["answer"] == GOOD["answer"] and result["rules"][0]["citations"][0]["line_start"] == 30
    assert warnings == []


def test_code_fence_is_removed():
    result, _ = parse_agent_output("```json\n" + json.dumps(GOOD) + "\n```")
    assert len(result["rules"]) == 1


def test_text_around_json_is_ignored():
    result, _ = parse_agent_output("Here you go:\n" + json.dumps(GOOD) + "\nHope that helps!")
    assert result["answer"] == GOOD["answer"]


def test_braces_inside_strings_do_not_confuse_extraction():
    tricky = {**GOOD, "answer": "Uses } and { inside text, and a \"quote\"."}
    result, _ = parse_agent_output("prefix " + json.dumps(tricky) + " suffix")
    assert result["answer"] == tricky["answer"]


def test_playground_markers_are_removed_everywhere():
    marked = json.loads(json.dumps(GOOD).replace("Stripe", "Stri[[1]]pe").replace("stripe.rb", "stri[[2]]pe.rb"))
    result, _ = parse_agent_output(json.dumps(marked))
    assert "[[" not in json.dumps(result) and result["answer"].startswith("Stripe")


def test_unknown_category_becomes_unknown_with_warning():
    bad = json.loads(json.dumps(GOOD)); bad["rules"][0]["category"] = "legal"
    result, warnings = parse_agent_output(json.dumps(bad))
    assert result["rules"][0]["category"] == "unknown" and any("category" in w for w in warnings)


def test_missing_gaps_is_empty_with_warning():
    no_gaps = {k: v for k, v in GOOD.items() if k != "gaps"}
    result, warnings = parse_agent_output(json.dumps(no_gaps))
    assert result["gaps"] == [] and warnings


def test_invalid_line_numbers_are_kept_visible_for_the_checker():
    bad = json.loads(json.dumps(GOOD)); bad["rules"][0]["citations"][0]["line_start"] = "thirty"
    result, _ = parse_agent_output(json.dumps(bad))
    assert result["rules"][0]["citations"][0]["line_start"] == 0  # the checker will report range_invalid


def test_empty_rules_is_valid():
    result, _ = parse_agent_output(json.dumps({"answer": "I could not find it.", "rules": [], "gaps": [GOOD["gaps"][0]]}))
    assert result["rules"] == [] and len(result["gaps"]) == 1


def test_extra_fields_are_ignored():
    result, _ = parse_agent_output(json.dumps({**GOOD, "confidence": 0.9}))
    assert "confidence" not in result


@pytest.mark.parametrize("raw", ["", "   ", "not json at all", '{"answer": "x"', '["a", "list"]',
                                 json.dumps({"answer": "", "rules": [], "gaps": []}),
                                 json.dumps({"answer": "x", "rules": "nope", "gaps": []}),
                                 json.dumps({"rules": [], "gaps": []})])
def test_bad_output_is_rejected(raw):
    with pytest.raises(BadOutput):
        parse_agent_output(raw)
