"""Three simple locators that a normal test uses: by id, by name and by XPath.

For every element on the old page, each locator tries to find it on the changed
page. The hidden data-qid tells us if it found the right one. The locators
never look at data-qid themselves.
"""
import csv
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
RESULTS_DIR = os.path.join(HERE, "results")
KINDS = ["none", "rename", "text", "layout", "reorder", "mixed"]


def find_by(field, old, after):
    """Return the first new element whose field equals the old value, like
    driver.find_element does. Return None if the old element has no value
    (then a test could not use this locator at all) or nothing matches."""
    value = old.get(field)
    if not value:
        return None
    for new in after:
        if new.get(field) == value:
            return new
    return None


# Each locator and the field it uses.
LOCATORS = {"by id": "id", "by name": "name", "by XPath": "xpath"}


def load_files():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.json")))
    data = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            data.append(json.load(f))
    return data


def evaluate(data):
    """Count, for each kind of change and each locator, how many elements
    were found correctly, and how many could use that locator at all."""
    counts = {k: {"elements": 0} for k in KINDS}
    for k in KINDS:
        for loc in LOCATORS:
            counts[k][loc] = 0
            counts[k][loc + " usable"] = 0

    for d in data:
        c = counts[d["kind"]]
        for old in d["before"]:
            c["elements"] += 1
            for loc, field in LOCATORS.items():
                if old.get(field):
                    c[loc + " usable"] += 1
                found = find_by(field, old, d["after"])
                if found is not None and found["qid"] == old["qid"]:
                    c[loc] += 1
    return counts


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "-"


def print_table(counts):
    print("Top-1 accuracy out of ALL elements")
    print("(an element with no id cannot be found by id, so it counts as a miss)")
    print()
    print(f"{'change':<8} {'elements':>8} " + " ".join(f"{loc:>9}" for loc in LOCATORS))
    for k in KINDS:
        c = counts[k]
        print(f"{k:<8} {c['elements']:>8} "
              + " ".join(f"{pct(c[loc], c['elements']):>9}" for loc in LOCATORS))

    print()
    print("Top-1 accuracy out of the elements that HAVE that attribute")
    print()
    print(f"{'change':<8} " + " ".join(f"{loc:>15}" for loc in LOCATORS))
    for k in KINDS:
        c = counts[k]
        cells = []
        for loc in LOCATORS:
            cells.append(f"{pct(c[loc], c[loc + ' usable']):>7} of {c[loc + ' usable']:>4}")
        print(f"{k:<8} " + " ".join(f"{cell:>15}" for cell in cells))


def save_csv(counts):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, "baselines.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["change", "elements", "locator", "correct", "usable",
                    "accuracy_all", "accuracy_usable"])
        for k in KINDS:
            c = counts[k]
            for loc in LOCATORS:
                w.writerow([k, c["elements"], loc, c[loc], c[loc + " usable"],
                            round(c[loc] / c["elements"], 4) if c["elements"] else "",
                            round(c[loc] / c[loc + " usable"], 4) if c[loc + " usable"] else ""])
    return path


if __name__ == "__main__":
    data = load_files()
    print("Files read:", len(data))
    print()
    counts = evaluate(data)
    print_table(counts)
    print()
    print("Saved", save_csv(counts))
