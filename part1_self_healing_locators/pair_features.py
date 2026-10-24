"""Pair features for the AI matcher (week 2: first half).

For every old element and every element on the changed page we make one row:
numbers that say how alike the two are, and a label (1 = same element,
0 = different), taken from the hidden data-qid. In week 3 a classifier learns
from these rows which numbers matter.

The label is only used as the answer. No feature looks at data-qid.
"""
import csv
import glob
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
OUT_FILE = os.path.join(HERE, "results", "pairs.csv")

FEATURES = [
    "same_tag", "same_type", "same_parent_tag",
    "id_sim", "name_sim", "class_sim", "text_sim",
    "dist", "size_ratio", "order_diff",
]


def trigrams(s):
    """The set of 3-letter pieces of a string, for example 'login' ->
    {'  l', ' lo', 'log', 'ogi', 'gin', 'in '}. Spaces at the ends let short
    words count too."""
    s = "  " + (s or "").lower() + " "
    return {s[i:i + 3] for i in range(len(s) - 2)}


def similarity(a, b):
    """How alike two strings are, from 0 (nothing shared) to 1 (same).
    It is the share of 3-letter pieces they have in common (Jaccard).
    'username' and 'username-v2' share most pieces, so they score high.
    If both are empty we return 0, because there is nothing to compare."""
    if not a and not b:
        return 0.0
    ta, tb = trigrams(a), trigrams(b)
    return len(ta & tb) / len(ta | tb)


def centre(e):
    return e["x"] + e["width"] / 2, e["y"] + e["height"] / 2


def pair_features(old, new, old_index, new_index, n_old, n_new):
    """All feature numbers for one (old element, new element) pair."""
    (ox, oy), (nx, ny) = centre(old), centre(new)
    # Divide by the page diagonal, so a small and a large window give
    # comparable numbers.
    diagonal = math.hypot(old["page_w"], old["page_h"])
    old_area = old["width"] * old["height"]
    new_area = new["width"] * new["height"]
    return {
        "same_tag": int(old["tag"] == new["tag"]),
        "same_type": int((old["type"] or "") == (new["type"] or "")),
        "same_parent_tag": int(old["parent_tag"] == new["parent_tag"]),
        "id_sim": similarity(old["id"], new["id"]),
        "name_sim": similarity(old["name"], new["name"]),
        "class_sim": similarity(old["class"], new["class"]),
        "text_sim": similarity(old["text"], new["text"]),
        "dist": math.hypot(ox - nx, oy - ny) / diagonal,
        "size_ratio": min(old_area, new_area) / max(old_area, new_area),
        # Where the element sits in the page order (0 = first, 1 = last).
        "order_diff": abs(old_index / max(n_old - 1, 1) - new_index / max(n_new - 1, 1)),
    }


def pairs_for_file(d):
    """One row for every (old, new) pair in one data file."""
    rows = []
    before, after = d["before"], d["after"]
    for i, old in enumerate(before):
        for j, new in enumerate(after):
            row = {"page": d["page"], "kind": d["kind"], "seed": d["seed"],
                   "old_qid": old["qid"], "new_qid": new["qid"]}
            row.update(pair_features(old, new, i, j, len(before), len(after)))
            row["label"] = int(old["qid"] == new["qid"])
            rows.append(row)
    return rows


def build_all():
    rows = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            rows.extend(pairs_for_file(json.load(f)))
    return rows


def save(rows):
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def print_check(rows):
    """A quick check: same-element pairs should look more alike than others."""
    same = [r for r in rows if r["label"] == 1]
    other = [r for r in rows if r["label"] == 0]
    print("Pairs:", len(rows), "| same element:", len(same), "| different:", len(other))
    print()
    print(f"{'feature':<16} {'same (avg)':>11} {'different (avg)':>16}")
    for name in FEATURES:
        a = sum(r[name] for r in same) / len(same)
        b = sum(r[name] for r in other) / len(other)
        print(f"{name:<16} {a:>11.3f} {b:>16.3f}")


if __name__ == "__main__":
    rows = build_all()
    save(rows)
    print_check(rows)
    print()
    print("Saved", OUT_FILE)
