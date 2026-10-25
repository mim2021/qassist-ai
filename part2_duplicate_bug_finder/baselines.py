"""Two classic search methods for duplicate bug reports: TF-IDF and BM25.

The test is "rolling": every test query searches only the reports created
before it, like a tester searching on the day the bug was reported. The word
statistics (how rare a word is) are also counted only on those older reports,
so nothing from the future leaks in.

A query is a hit at k if one of its true older duplicates is in the top k.
"""
import csv
import os

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer

from load_data import PROJECTS, load_project

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
KS = [1, 5, 10]


class Index:
    """Word counts for every report, in date order. CountVectorizer only
    makes the word list here; how often a word appears is always counted
    on the older reports for each query."""

    def __init__(self, reports):
        self.vec = CountVectorizer(stop_words="english")
        self.counts = self.vec.fit_transform(reports["text"]).tocsr().astype(np.float64)
        self.by_column = self.counts.tocsc()
        self.present = (self.counts > 0).astype(np.float64)
        self.lengths = np.asarray(self.counts.sum(axis=1)).ravel()
        self.created = reports["created"].values
        self.row_of = {rid: i for i, rid in enumerate(reports["id"])}

    def pool_size(self, row):
        """Number of reports created strictly before the query report."""
        return int(np.searchsorted(self.created, self.created[row], side="left"))

    def doc_freq(self, n):
        """In how many of the first n reports each word appears."""
        return np.asarray(self.present[:n].sum(axis=0)).ravel()


def tfidf_scores(index, row, n):
    """Cosine similarity between the query and each of the n older reports.
    tf = 1 + log(count), idf = log((1 + n) / (1 + df)) + 1, like scikit-learn."""
    idf = np.log((1 + n) / (1 + index.doc_freq(n))) + 1
    pool = index.counts[:n].copy()
    pool.data = 1 + np.log(pool.data)
    query = index.counts[row].toarray().ravel()
    query[query > 0] = 1 + np.log(query[query > 0])
    q = query * idf
    dot = pool @ (q * idf)
    pool_norm = np.sqrt(pool.power(2) @ (idf ** 2))
    q_norm = np.linalg.norm(q)
    with np.errstate(divide="ignore", invalid="ignore"):
        scores = dot / (pool_norm * q_norm)
    return np.nan_to_num(scores)


def bm25_scores(index, row, n, k1=1.2, b=0.75):
    """BM25 score of each of the n older reports for the query words."""
    words = index.counts[row].indices
    if len(words) == 0:
        return np.zeros(n)
    df = index.doc_freq(n)[words]
    idf = np.log((n - df + 0.5) / (df + 0.5) + 1)
    tf = index.by_column[:, words][:n].toarray()
    dl = index.lengths[:n]
    avgdl = dl.mean() if n else 1.0
    part = tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl[:, None] / avgdl))
    return part @ idf


METHODS = {"TF-IDF": tfidf_scores, "BM25": bm25_scores}


def rank_of_answer(scores, answer_rows):
    """Rank (1 = top) of the best-placed true duplicate. On a tie we count
    the tied reports as above it, so a tie never helps the method."""
    best = None
    for r in answer_rows:
        s = scores[r]
        rank = int((scores > s).sum() + (scores == s).sum())
        best = rank if best is None else min(best, rank)
    return best


def evaluate(name):
    reports, queries = load_project(name)
    index = Index(reports)
    ranks = {m: {} for m in METHODS}
    pools = []
    for qid, answers in queries.items():
        row = index.row_of[qid]
        n = index.pool_size(row)
        pools.append(n)
        answer_rows = [index.row_of[a] for a in answers]
        for m, score in METHODS.items():
            ranks[m][qid] = rank_of_answer(score(index, row, n), answer_rows)
    return ranks, pools


def summary(r):
    r = np.array(list(r.values()))
    row = {f"Recall@{k}": float((r <= k).mean()) for k in KS}
    row["MRR"] = float((1 / r).mean())
    return row


def run():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    table = []
    all_ranks = []
    for name in PROJECTS:
        ranks, pools = evaluate(name)
        print(f"{name}: {len(pools)} test queries, each searched "
              f"{min(pools)} to {max(pools)} older reports (median {int(np.median(pools))})")
        for m in METHODS:
            row = {"project": name, "method": m, "queries": len(pools)}
            row.update(summary(ranks[m]))
            table.append(row)
            all_ranks += [(name, m, qid, rk) for qid, rk in ranks[m].items()]
    print()
    print(f"{'project':<8} {'method':<7} {'queries':>7} "
          + " ".join(f"{'Recall@' + str(k):>10}" for k in KS) + f" {'MRR':>7}")
    for row in table:
        print(f"{row['project']:<8} {row['method']:<7} {row['queries']:>7} "
              + " ".join(f"{100 * row['Recall@' + str(k)]:>9.1f}%" for k in KS)
              + f" {row['MRR']:>7.3f}")

    with open(os.path.join(RESULTS_DIR, "baselines.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)
    # One row per query, so we can read the failures by hand later.
    with open(os.path.join(RESULTS_DIR, "baseline_ranks.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["project", "method", "query_id", "rank_of_true_duplicate"])
        w.writerows(all_ranks)
    print()
    print("Saved results/baselines.csv and results/baseline_ranks.csv")


if __name__ == "__main__":
    run()
