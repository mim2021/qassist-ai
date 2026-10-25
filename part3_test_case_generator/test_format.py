"""The fixed output format for a test case, and a check that an answer follows it.

Ollama is given SCHEMA, so the model is pushed to answer in this shape. We
still check every answer ourselves, because the schema cannot know which
criterion ids exist for a requirement.
"""
import json

TYPES = ["positive", "negative", "boundary"]

SCHEMA = {
    "type": "object",
    "properties": {
        "test_cases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "type": {"type": "string", "enum": TYPES},
                    "preconditions": {"type": "string"},
                    "steps": {"type": "array", "items": {"type": "string"}},
                    "expected_result": {"type": "string"},
                    "covers": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "title", "type", "preconditions", "steps",
                             "expected_result", "covers"],
            },
        }
    },
    "required": ["test_cases"],
}


def check(text, requirement):
    """Return (test_cases, problems). An empty problems list means the answer
    is valid: it is JSON, every field is there with the right type, and every
    id in 'covers' is a real criterion of this requirement."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return [], [f"not JSON: {e.msg}"]
    cases = data.get("test_cases") if isinstance(data, dict) else None
    if not isinstance(cases, list) or not cases:
        return [], ["no test_cases list"]

    problems = []
    real_ids = set(requirement["criteria"])
    for i, c in enumerate(cases, 1):
        if not isinstance(c, dict):
            problems.append(f"test {i}: not an object")
            continue
        for field in ("id", "title", "preconditions", "expected_result"):
            if not isinstance(c.get(field), str) or not c[field].strip():
                problems.append(f"test {i}: '{field}' missing or empty")
        if c.get("type") not in TYPES:
            problems.append(f"test {i}: type '{c.get('type')}' is not one of {TYPES}")
        if not isinstance(c.get("steps"), list) or not c["steps"]:
            problems.append(f"test {i}: no steps")
        covers = c.get("covers")
        if not isinstance(covers, list) or not covers:
            problems.append(f"test {i}: 'covers' is empty")
        else:
            unknown = [x for x in covers if x not in real_ids]
            if unknown:
                problems.append(f"test {i}: covers unknown criteria {unknown}")
    return cases, problems
