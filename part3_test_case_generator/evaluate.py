"""Compare the prompts (A, B and C) on the saved answers in outputs/.

Automatic measures, for each prompt over all 8 requirements:
- valid answers (after at most one retry)
- criteria covered: share of all acceptance criteria that at least one test
  claims to cover ("covers" is the model's own claim, so we also check a
  sample by hand)
- duplicate titles: share of tests whose title repeats an earlier title for
  the same requirement (ignoring case and punctuation)
- number of tests, negative tests and boundary tests

Manual check: for each round in ROUNDS, the first run writes a sheet with
10 test cases from each of its prompts, mixed up and without the prompt name,
so the reader does not know which prompt wrote which. Fill in the yes/no
columns in Excel, save, and run this script again. The prompt names are in
the key file. Round 1 compares A and B. Round 2 came later, for prompt C: it
compares B and C, with B tests that were not in round 1.
"""
import csv
import json
import os
import random
import re

from generate import OUT_DIR, load_requirements
from prompts import PROMPTS
from test_format import check

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(HERE, "results")
# (sheet, key, prompts in the round, random seed)
ROUNDS = [
    ("manual_check.csv", "manual_key.csv", ["A", "B"], 1),
    ("manual_check_2.csv", "manual_key_2.csv", ["B", "C"], 2),
]
MANUAL_COLUMNS = ["sensible", "invents_feature", "covers_correct"]
SAMPLE_PER_PROMPT = 10


def load_answers(requirements):
    """answers[prompt][requirement id] = list of test cases ([] if invalid)."""
    answers = {p: {} for p in PROMPTS}
    info = {p: {"valid": 0, "first_try": 0, "missing": 0} for p in PROMPTS}
    for req in requirements:
        for p in PROMPTS:
            path = os.path.join(OUT_DIR, f"{req['id']}_{p}.json")
            if not os.path.exists(path):
                info[p]["missing"] += 1
                answers[p][req["id"]] = []
                continue
            with open(path, encoding="utf-8") as f:
                result = json.load(f)
            cases, problems = check(result["attempts"][-1]["text"], req)
            if problems:
                answers[p][req["id"]] = []  # an invalid answer counts as a failure
            else:
                answers[p][req["id"]] = cases
                info[p]["valid"] += 1
                info[p]["first_try"] += len(result["attempts"]) == 1
    return answers, info


def normalise(title):
    return re.sub(r"[^a-z0-9 ]", "", title.lower()).strip()


def measures(answers, requirements):
    rows = {}
    total_criteria = sum(len(r["criteria"]) for r in requirements)
    for p, by_req in answers.items():
        covered = tests = duplicates = negative = boundary = 0
        with_negative = with_boundary = 0
        for req in requirements:
            cases = by_req[req["id"]]
            covered += len({c for case in cases for c in case["covers"]})
            seen = set()
            for case in cases:
                t = normalise(case["title"])
                duplicates += t in seen
                seen.add(t)
            tests += len(cases)
            n_neg = sum(c["type"] == "negative" for c in cases)
            n_bnd = sum(c["type"] == "boundary" for c in cases)
            negative += n_neg
            boundary += n_bnd
            with_negative += n_neg > 0
            with_boundary += n_bnd > 0
        rows[p] = {
            "criteria covered": f"{covered} of {total_criteria} ({100 * covered / total_criteria:.0f}%)",
            "tests": tests,
            "duplicate titles": f"{duplicates} ({100 * duplicates / tests:.0f}%)" if tests else "-",
            "negative tests": negative,
            "boundary tests": boundary,
            "requirements with a negative test": f"{with_negative} of {len(requirements)}",
            "requirements with a boundary test": f"{with_boundary} of {len(requirements)}",
        }
    return rows


def excel_safe(value):
    """Stop Excel from running a cell as a formula."""
    value = str(value)
    return "'" + value if value[:1] in ("=", "+", "-", "@") else value


def sampled_before():
    """(prompt, requirement, test id) of every test already in a key file."""
    seen = set()
    for _, key, _, _ in ROUNDS:
        path = os.path.join(RESULTS_DIR, key)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                seen |= {(r["prompt"], r["requirement"], r["test_id"]) for r in csv.DictReader(f)}
    return seen


def write_manual_sheet(answers, requirements, sheet, key, prompts, seed):
    """10 test cases from each prompt, mixed up, without the prompt name."""
    rng = random.Random(seed)
    skip = sampled_before()
    criteria_text = {r["id"]: " | ".join(f"{k}: {v}" for k, v in r["criteria"].items())
                     for r in requirements}
    picked = []
    for p in prompts:
        pool = [(p, rid, case) for rid, cases in answers[p].items() for case in cases
                if (p, rid, case["id"]) not in skip]
        picked += rng.sample(pool, min(SAMPLE_PER_PROMPT, len(pool)))
    rng.shuffle(picked)

    with open(os.path.join(RESULTS_DIR, sheet), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["item", "requirement", "criteria", "title", "type", "steps",
                    "expected_result", "covers"] + MANUAL_COLUMNS + ["note"])
        for i, (p, rid, case) in enumerate(picked, 1):
            w.writerow([i, rid, criteria_text[rid], excel_safe(case["title"]), case["type"],
                        excel_safe(" / ".join(case["steps"])), excel_safe(case["expected_result"]),
                        ", ".join(case["covers"]), "", "", "", ""])
    with open(os.path.join(RESULTS_DIR, key), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["item", "prompt", "requirement", "test_id"])
        for i, (p, rid, case) in enumerate(picked, 1):
            w.writerow([i, p, rid, case["id"]])


def read_manual_sheet(sheet, key, counts):
    """Add the answers in one sheet to counts[prompt][column] = [yes, answered]."""
    with open(os.path.join(RESULTS_DIR, key), encoding="utf-8") as f:
        prompt_of = {row["item"]: row["prompt"] for row in csv.DictReader(f)}
    with open(os.path.join(RESULTS_DIR, sheet), encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            for c in MANUAL_COLUMNS:
                answer = row.get(c, "").strip().lower()
                if answer in ("yes", "y", "no", "n"):
                    counts[prompt_of[row["item"]]][c][1] += 1
                    counts[prompt_of[row["item"]]][c][0] += answer in ("yes", "y")


def run():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    requirements = load_requirements()
    answers, info = load_answers(requirements)
    if any(info[p]["missing"] for p in PROMPTS):
        print("Note: some answers are missing. Run generate.py first.", info)

    table = {}
    for p in PROMPTS:
        table[p] = {"valid answers": f"{info[p]['valid']} of {len(requirements)} "
                                     f"({info[p]['first_try']} on the first try)"}
        table[p].update(measures(answers, requirements)[p])

    # Every round adds to the same counts, so B is counted over both rounds.
    counts = {p: {c: [0, 0] for c in MANUAL_COLUMNS} for p in PROMPTS}
    for sheet, key, prompts, seed in ROUNDS:
        if os.path.exists(os.path.join(RESULTS_DIR, sheet)):
            read_manual_sheet(sheet, key, counts)
        elif not any(info[p]["missing"] for p in prompts):
            write_manual_sheet(answers, requirements, sheet, key, prompts, seed)
            print(f"Wrote results/{sheet}: fill in the yes/no columns, then run this script again.")
            print()
    if any(n for p in counts.values() for _, n in p.values()):
        for p in PROMPTS:
            for c in MANUAL_COLUMNS:
                yes, n = counts[p][c]
                table[p][f"manual: {c.replace('_', ' ')}"] = f"{yes} of {n}" if n else "-"

    names = list(next(iter(table.values())))
    width = max(len(n) for n in names)
    print(f"{'measure':<{width}}" + "".join(f"  {'prompt ' + p:>22}" for p in PROMPTS))
    for n in names:
        print(f"{n:<{width}}" + "".join(f"  {str(table[p][n]):>22}" for p in PROMPTS))

    with open(os.path.join(RESULTS_DIR, "results.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["measure"] + [f"prompt {p}" for p in PROMPTS])
        for n in names:
            w.writerow([n] + [table[p][n] for p in PROMPTS])
    print()
    print("Saved results/results.csv")


if __name__ == "__main__":
    run()
