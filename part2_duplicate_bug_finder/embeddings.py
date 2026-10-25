"""The AI methods: sentence embeddings, and a hybrid of embeddings and BM25.

Embeddings: a small pre-trained model (all-MiniLM-L6-v2) turns each report
into 384 numbers that stand for its meaning. Two reports that say the same
thing in different words get similar numbers. We compare them with cosine
similarity. The model is not trained on our data, so it cannot learn the
answers.

Hybrid: BM25 and embeddings each rank the older reports. Reciprocal rank
fusion adds 1 / (60 + rank) from both lists, so a report that is high in
both lists wins.

The test is the same rolling test as in baselines.py, on the same queries,
so all four methods can be compared directly.
"""
import csv
import os
import sys
import time

import numpy as np

from baselines import KS, METHODS, Index, bm25_scores, rank_of_answer, summary
from load_data import DATA_DIR, PROJECTS, load_project

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
# The model is kept inside the project (not in the user folder on drive C).
# It is downloaded here the first time, about 90 MB.
MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
MODEL_NAME = "all-MiniLM-L6-v2"
RRF_K = 60


def embed(name, texts, clean=False):
    """Embed every report once and save the vectors in data/. The next run
    reads them from disk."""
    path = os.path.join(DATA_DIR, f"{name}_minilm{'_clean' if clean else ''}.npy")
    if os.path.exists(path):
        vectors = np.load(path)
        if len(vectors) == len(texts):
            return vectors

    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME, device="cpu", cache_folder=MODELS_DIR)
    texts = list(texts)

    # Time the first 1,000 reports, so we know how long the rest will take.
    start = time.time()
    first = model.encode(texts[:1000], batch_size=64, normalize_embeddings=True)
    seconds = time.time() - start
    print(f"{name}: 1,000 reports took {seconds:.0f} s, so all {len(texts)} "
          f"should take about {seconds * len(texts) / 1000 / 60:.1f} min")
    rest = model.encode(texts[1000:], batch_size=64, normalize_embeddings=True,
                        show_progress_bar=True) if len(texts) > 1000 else np.empty((0, first.shape[1]))
    vectors = np.vstack([first, rest]).astype(np.float32)
    np.save(path, vectors)
    return vectors


def ranks_from_scores(scores):
    """Turn scores into ranks: 1 for the highest score."""
    order = np.argsort(-scores, kind="stable")
    ranks = np.empty(len(scores), dtype=np.int64)
    ranks[order] = np.arange(1, len(scores) + 1)
    return ranks


def evaluate(name, clean=False):
    reports, queries = load_project(name, clean)
    index = Index(reports)
    vectors = embed(name, reports["text"], clean)

    methods = list(METHODS) + ["Embeddings", "Hybrid"]
    ranks = {m: {} for m in methods}
    for qid, answers in queries.items():
        row = index.row_of[qid]
        n = index.pool_size(row)
        answer_rows = [index.row_of[a] for a in answers]

        scores = {m: score(index, row, n) for m, score in METHODS.items()}
        # Vectors are normalised, so the dot product is the cosine similarity.
        scores["Embeddings"] = vectors[:n] @ vectors[row]
        scores["Hybrid"] = (1 / (RRF_K + ranks_from_scores(scores["BM25"]))
                            + 1 / (RRF_K + ranks_from_scores(scores["Embeddings"])))
        for m in methods:
            ranks[m][qid] = rank_of_answer(scores[m], answer_rows)
    return ranks, methods


def run(clean=False):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    suffix = "_clean" if clean else ""
    print("Text:", "bug template removed" if clean else "as in the data")
    table = []
    all_ranks = []
    for name in PROJECTS:
        ranks, methods = evaluate(name, clean)
        for m in methods:
            row = {"project": name, "method": m, "queries": len(ranks[m])}
            row.update(summary(ranks[m]))
            table.append(row)
            all_ranks += [(name, m, qid, rk) for qid, rk in ranks[m].items()]

    print()
    print(f"{'project':<8} {'method':<11} {'queries':>7} "
          + " ".join(f"{'Recall@' + str(k):>10}" for k in KS) + f" {'MRR':>7}")
    for row in table:
        print(f"{row['project']:<8} {row['method']:<11} {row['queries']:>7} "
              + " ".join(f"{100 * row['Recall@' + str(k)]:>9.1f}%" for k in KS)
              + f" {row['MRR']:>7.3f}")

    with open(os.path.join(RESULTS_DIR, f"all_methods{suffix}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(table[0].keys()))
        w.writeheader()
        w.writerows(table)
    with open(os.path.join(RESULTS_DIR, f"all_ranks{suffix}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["project", "method", "query_id", "rank_of_true_duplicate"])
        w.writerows(all_ranks)
    print()
    print(f"Saved results/all_methods{suffix}.csv and results/all_ranks{suffix}.csv")


if __name__ == "__main__":
    # python embeddings.py          -> the text as it is in the data
    # python embeddings.py --clean  -> the same test with the bug template removed
    run(clean="--clean" in sys.argv)
