"""Bonus run: the stronger password requirement R9 with prompts A, B and C.

R9 is R2 with the rules a tester added for better security: upper and lower
case, a special character, no reuse of the current or the last 5 passwords,
and a live checklist where each rule disappears once it is met. It is kept
apart from the main 8 requirements, so the main results do not change.

Run it after Ollama is started. Answers go to outputs/bonus/, and the script
prints, for each prompt, which criteria the tests claim to cover, and every
test, so you can read them.
"""
import json
import os

from generate import HERE, run as generate
from prompts import PROMPTS
from test_format import check

BONUS_FILE = os.path.join(HERE, "bonus_requirement.json")
BONUS_DIR = os.path.join(HERE, "outputs", "bonus")


def main():
    with open(BONUS_FILE, encoding="utf-8") as f:
        requirements = json.load(f)
    generate(requirements, BONUS_DIR)

    for req in requirements:
        print()
        print(f"{req['id']}: {req['title']}")
        for name in PROMPTS:
            with open(os.path.join(BONUS_DIR, f"{req['id']}_{name}.json"), encoding="utf-8") as f:
                result = json.load(f)
            cases, problems = check(result["attempts"][-1]["text"], req)
            print()
            if problems:
                print(f"Prompt {name}: not valid ({problems[0]})")
                continue
            covered = {c for case in cases for c in case["covers"]}
            missing = [c for c in req["criteria"] if c not in covered]
            types = {t: sum(c["type"] == t for c in cases) for t in ("positive", "negative", "boundary")}
            print(f"Prompt {name}: {len(cases)} tests {types}, "
                  f"criteria covered {len(covered)} of {len(req['criteria'])}"
                  + (f", missing {', '.join(missing)}" if missing else ""))
            for case in cases:
                print(f"  [{case['type']}] {case['title']}  (covers {', '.join(case['covers'])})")
                print(f"      expected: {case['expected_result']}")


if __name__ == "__main__":
    main()
