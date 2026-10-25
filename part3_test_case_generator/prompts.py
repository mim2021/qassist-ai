"""The two prompts. Both get the same requirement and the same format
description, so the only difference between A and B is the test strategy."""

FORMAT = """Answer only with JSON in this form:
{"test_cases": [{"id": "TC1", "title": "...", "type": "positive | negative | boundary",
"preconditions": "...", "steps": ["...", "..."], "expected_result": "...",
"covers": ["AC1"]}]}
In "covers", list the ids of the acceptance criteria that the test checks."""

PROMPT_A = """Write test cases for the following requirement.

{requirement}

""" + FORMAT

PROMPT_B = """You are a careful software tester. Write test cases for the requirement below.

Follow these rules:
1. Write at least one test for every acceptance criterion.
2. Use equivalence partitions: test one valid value and the invalid groups of values.
3. For every number or limit, test the boundary values: just below, exactly at, and just above the limit. Mark these tests "boundary".
4. Write at least one negative test (wrong input or a forbidden action).
5. Only test what the requirement says. Do not invent features.
6. Give every test a different title.

{requirement}

""" + FORMAT

PROMPTS = {"A": PROMPT_A, "B": PROMPT_B}


def requirement_text(req):
    """The requirement as plain text, the same for both prompts."""
    lines = [f"Requirement {req['id']}: {req['title']}", req["description"], "Acceptance criteria:"]
    lines += [f"{cid}: {text}" for cid, text in req["criteria"].items()]
    return "\n".join(lines)
