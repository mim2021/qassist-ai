"""Week 3: train the AI matcher and test it on pages and sites it never saw.

How the matcher works:
1. For an old element, make one row of pair features for every element on
   the changed page (see pair_features.py).
2. A trained classifier gives each row a score: how likely it is the same element.
3. The element with the highest score is the answer.

We test it two ways, and never with a random split of rows:
- unseen page: train on 7 pages, test on the 8th, repeat for every page
- unseen site: train on 2 sites, test on the 3rd (harder, because the 5
  herokuapp pages look alike)

The baselines are scored on exactly the same elements.
"""
import csv
import glob
import json
import os

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from baselines import KINDS, LOCATORS, find_by
from pair_features import FEATURES, pairs_for_file

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
RESULTS_DIR = os.path.join(HERE, "results")

MODELS = {
    # Scaling puts every feature on the same range, so the weights can be compared.
    "logistic regression": lambda: make_pipeline(
        StandardScaler(), LogisticRegression(max_iter=1000)
    ),
    "gradient boosting": lambda: GradientBoostingClassifier(random_state=42),
}


def site_of(page):
    """herokuapp_login -> herokuapp"""
    return page.split("_")[0]


def load_files():
    data = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            data.append(json.load(f))
    return data


def chain(old, after):
    """The best simple locator: try id, then name, then XPath. Many test
    frameworks do something like this."""
    for field in ("id", "name", "xpath"):
        if old.get(field):
            found = find_by(field, old, after)
            if found is not None:
                return found
    return None


def to_matrix(rows, features):
    X = np.array([[r[f] for f in features] for r in rows])
    y = np.array([r["label"] for r in rows])
    return X, y


def match_file(model, d, features):
    """For every old element in one file, the qid the model picks."""
    rows = pairs_for_file(d)
    X, _ = to_matrix(rows, features)
    scores = model.predict_proba(X)[:, 1]
    best = {}
    for r, s in zip(rows, scores):
        if r["old_qid"] not in best or s > best[r["old_qid"]][0]:
            best[r["old_qid"]] = (s, r["new_qid"])
    return {qid: new_qid for qid, (s, new_qid) in best.items()}


def run_split(data, group_of, features, failures=None):
    """Leave one group out. Returns counts[kind][method] = correct, and
    counts[kind]["elements"]."""
    counts = {k: {"elements": 0} for k in KINDS}
    methods = list(LOCATORS) + ["id > name > XPath"] + list(MODELS)
    for k in KINDS:
        for m in methods:
            counts[k][m] = 0

    groups = sorted({group_of(d["page"]) for d in data})
    for test_group in groups:
        train = [d for d in data if group_of(d["page"]) != test_group]
        test = [d for d in data if group_of(d["page"]) == test_group]

        train_rows = [r for d in train for r in pairs_for_file(d)]
        X, y = to_matrix(train_rows, features)
        models = {}
        for name, make in MODELS.items():
            models[name] = make().fit(X, y)

        for d in test:
            c = counts[d["kind"]]
            picks = {name: match_file(m, d, features) for name, m in models.items()}
            after_by_qid = {a["qid"]: a for a in d["after"]}
            for old in d["before"]:
                c["elements"] += 1
                for loc, field in LOCATORS.items():
                    found = find_by(field, old, d["after"])
                    if found is not None and found["qid"] == old["qid"]:
                        c[loc] += 1
                found = chain(old, d["after"])
                if found is not None and found["qid"] == old["qid"]:
                    c["id > name > XPath"] += 1
                for name in MODELS:
                    if picks[name][old["qid"]] == old["qid"]:
                        c[name] += 1
                    elif failures is not None and name == "gradient boosting":
                        failures.append((d, old, after_by_qid[picks[name][old["qid"]]]))
    return counts, methods


def pct(a, b):
    return f"{100 * a / b:.1f}%" if b else "-"


def print_table(title, counts, methods):
    print(title)
    short = {"logistic regression": "AI: LogReg", "gradient boosting": "AI: GBoost"}
    heads = [short.get(m, m) for m in methods]
    print(f"{'change':<8} {'elements':>8} " + " ".join(f"{h:>17}" for h in heads))
    total = {m: 0 for m in methods}
    n = 0
    for k in KINDS:
        c = counts[k]
        n += c["elements"]
        for m in methods:
            total[m] += c[m]
        print(f"{k:<8} {c['elements']:>8} "
              + " ".join(f"{pct(c[m], c['elements']):>17}" for m in methods))
    print(f"{'all':<8} {n:>8} " + " ".join(f"{pct(total[m], n):>17}" for m in methods))
    print()


def save_csv(all_counts, methods):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, "matcher_results.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["split", "change", "method", "correct", "elements", "accuracy"])
        for split, counts in all_counts.items():
            for k in KINDS:
                c = counts[k]
                for m in methods:
                    w.writerow([split, k, m, c[m], c["elements"],
                                round(c[m] / c["elements"], 4)])
    return path


def print_weights(data):
    """The weights of logistic regression trained on all data. A big positive
    weight means 'this feature makes it look like the same element'."""
    rows = [r for d in data for r in pairs_for_file(d)]
    X, y = to_matrix(rows, FEATURES)
    model = MODELS["logistic regression"]().fit(X, y)
    weights = model.named_steps["logisticregression"].coef_[0]
    print("Logistic regression weights (features scaled, trained on all data)")
    for name, wgt in sorted(zip(FEATURES, weights), key=lambda t: -abs(t[1])):
        print(f"  {name:<16} {wgt:>7.2f}")
    print()


def print_failures(failures, limit=8):
    print(f"Gradient boosting mistakes on unseen sites: {len(failures)}. First {limit}:")
    for d, old, wrong in failures[:limit]:
        def show(e):
            return f"<{e['tag']} id='{e['id']}' text='{e['text'][:25]}'>"
        print(f"  {d['page']} {d['kind']} seed {d['seed']}: "
              f"wanted {show(old)}, picked {show(wrong)}")
    print()


if __name__ == "__main__":
    data = load_files()
    print("Files read:", len(data))
    print()

    page_counts, methods = run_split(data, lambda p: p, FEATURES)
    print_table("Unseen page (train on 7 pages, test on the 8th)", page_counts, methods)

    failures = []
    site_counts, _ = run_split(data, site_of, FEATURES, failures)
    print_table("Unseen site (train on 2 sites, test on the 3rd)", site_counts, methods)

    no_order = [f for f in FEATURES if f != "order_diff"]
    print("Check: the same, without the order_diff feature")
    for split, group_of in (("unseen page", lambda p: p), ("unseen site", site_of)):
        counts, _ = run_split(data, group_of, no_order)
        n = sum(counts[k]["elements"] for k in KINDS)
        line = ", ".join(
            f"{m} {pct(sum(counts[k][m] for k in KINDS), n)}" for m in MODELS
        )
        print(f"  {split}: {line}")
    print()

    print_weights(data)
    print_failures(failures)
    print("Saved", save_csv({"unseen page": page_counts, "unseen site": site_counts}, methods))
