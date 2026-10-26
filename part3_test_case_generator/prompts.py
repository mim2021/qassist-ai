"""The prompts. All get the same requirement and the same format
description, so the only difference between them is the test strategy."""

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

# Prompt C is prompt B after the first results: B invented limits that the
# requirement does not have, wrote the wrong message for a case without one,
# claimed criteria it did not check, and ran into the output limit. Rules 1
# and 3 change and rules 7 and 8 are new; the others are the same as in B.
PROMPT_C = """You are a careful software tester. Write test cases for the requirement below.

Follow these rules:
1. Write 1 to 3 tests for every acceptance criterion. Do not write more.
2. Use equivalence partitions: test one valid value and the invalid groups of values.
3. Only for a number or limit that an acceptance criterion states, test the boundary values: just below, exactly at, and just above the limit. Mark these tests "boundary". Do not make up limits that the requirement does not state.
4. Write at least one negative test (wrong input or a forbidden action).
5. Only test what the requirement says. Do not invent features.
6. Give every test a different title.
7. In the expected result, use the exact message from the requirement. If the requirement gives no message for a case, write only that the input is rejected.
8. In "covers", list only the criteria whose expected result the test really checks.

{requirement}

""" + FORMAT

PROMPTS = {"A": PROMPT_A, "B": PROMPT_B, "C": PROMPT_C}


def requirement_text(req):
    """The requirement as plain text, the same for both prompts."""
    lines = [f"Requirement {req['id']}: {req['title']}", req["description"], "Acceptance criteria:"]
    lines += [f"{cid}: {text}" for cid, text in req["criteria"].items()]
    return "\n".join(lines)
