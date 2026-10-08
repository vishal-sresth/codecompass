"""Clean and validate the agent's reply (docs/specs/agent-output-contract.md).

The agent should return one JSON object {answer, rules[], gaps[]}. Models sometimes wrap it in a code fence, add text
around it, or leave citation markers like [[1]] in strings. We repair only those known problems; anything else is
BadOutput and the caller returns 502 bad_output (the raw text is kept in the log).
"""
import json
import re

CATEGORIES = {"regulatory", "commercial", "technical", "unknown"}
MARKER = re.compile(r"\[\[\d+\]\]")
FENCE = re.compile(r"^```[a-zA-Z]*\s*\n?(.*?)\n?```\s*$", re.S)


class BadOutput(Exception):
    """The agent's reply cannot be turned into the contract's shape."""


def _first_json_object(text: str) -> str:
    """The first balanced {...} object, respecting strings and escapes."""
    start = text.find("{")
    if start == -1:
        raise BadOutput("no JSON object found")
    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise BadOutput("JSON object is not closed")


def _clean_strings(value):
    if isinstance(value, str):
        return MARKER.sub("", value)
    if isinstance(value, list):
        return [_clean_strings(v) for v in value]
    if isinstance(value, dict):
        return {k: _clean_strings(v) for k, v in value.items()}
    return value


def _as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def parse_agent_output(raw: str) -> tuple[dict, list[str]]:
    """Returns (result, warnings). result = {answer, rules, gaps}. Raises BadOutput."""
    if not isinstance(raw, str) or not raw.strip():
        raise BadOutput("empty reply")
    text = raw.strip()
    fenced = FENCE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        try:
            data = json.loads(_first_json_object(text))
        except json.JSONDecodeError as e:
            raise BadOutput(f"invalid JSON: {e.msg}") from e
    if not isinstance(data, dict):
        raise BadOutput("top level is not an object")

    data = _clean_strings(data)
    warnings: list[str] = []

    answer = data.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise BadOutput("missing answer")

    raw_rules = data.get("rules")
    if not isinstance(raw_rules, list):
        raise BadOutput("rules must be a list")
    rules = []
    for item in raw_rules:
        if not isinstance(item, dict) or not isinstance(item.get("rule"), str) or not item["rule"].strip():
            warnings.append("dropped a rule without text")
            continue
        category = item.get("category")
        if category not in CATEGORIES:
            warnings.append(f"category {category!r} replaced by 'unknown'")
            category = "unknown"
        citations = []
        for c in item.get("citations") or []:
            if not isinstance(c, dict):
                continue
            start, end = _as_int(c.get("line_start")), _as_int(c.get("line_end"))
            citations.append({
                "repo": str(c.get("repo", "")), "file": str(c.get("file", "")),
                # invalid numbers are kept as 0 so the citation checker reports range_invalid instead of hiding the citation
                "line_start": start if start is not None else 0, "line_end": end if end is not None else 0,
                "evidence": str(c.get("evidence", "")),
            })
        rules.append({"rule": item["rule"].strip(), "category": category, "citations": citations,
                      "reasoning": str(item.get("reasoning", ""))})

    raw_gaps = data.get("gaps")
    if raw_gaps is None:
        warnings.append("gaps missing; treated as empty")
        raw_gaps = []
    if not isinstance(raw_gaps, list):
        raise BadOutput("gaps must be a list")
    gaps = []
    for g in raw_gaps:
        if not isinstance(g, dict):
            continue
        looked = g.get("looked_in") or []
        gaps.append({"looked_in": [str(x) for x in looked] if isinstance(looked, list) else [str(looked)],
                     "not_found": str(g.get("not_found", "")), "suggested_follow_up": str(g.get("suggested_follow_up", ""))})

    return {"answer": answer.strip(), "rules": rules, "gaps": gaps}, warnings
