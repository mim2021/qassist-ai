"""Find the 5 earlier reports most like a new bug report.

Example (in this folder):
    ..\\.venv\\Scripts\\python find_duplicates.py vscode "Terminal opens in wrong folder" "In a multi-root workspace the new terminal starts in the first folder."

It uses the embedding method, which did best on VS Code in my tests. The
report vectors are read from data/ (made by embeddings.py), so only the new
report has to be embedded.
"""
import argparse

from embeddings import MODEL_NAME, MODELS_DIR, embed
from load_data import DESCRIPTION_CHARS, PROJECTS, load_project

LINKS = {"vscode": "https://github.com/microsoft/vscode/issues/{}",
         "thunderbird": "https://bugzilla.mozilla.org/show_bug.cgi?id={}"}


def find(project, title, description, top=5):
    from sentence_transformers import SentenceTransformer
    reports, _ = load_project(project)
    vectors = embed(project, reports["text"])
    model = SentenceTransformer(MODEL_NAME, device="cpu", cache_folder=MODELS_DIR)
    # The same text recipe as for the stored reports.
    text = title + "\n" + description[:DESCRIPTION_CHARS]
    query = model.encode([text], normalize_embeddings=True)[0]
    scores = vectors @ query
    best = scores.argsort()[::-1][:top]
    return reports.iloc[best].assign(score=scores[best])


def main():
    parser = argparse.ArgumentParser(description="Find possible duplicates of a new bug report.")
    parser.add_argument("project", choices=list(PROJECTS))
    parser.add_argument("title")
    parser.add_argument("description", nargs="?", default="")
    args = parser.parse_args()

    found = find(args.project, args.title, args.description)
    print()
    print(f"Top {len(found)} similar {args.project} reports (score 1.0 = same meaning):")
    print()
    for i, r in enumerate(found.itertuples(), 1):
        link = LINKS.get(args.project, "issue id {}").format(r.id)
        print(f"{i}. score {r.score:.2f}  {r.created:%Y-%m-%d}  {r.title[:80]}")
        print(f"   {link}")
    print()
    print("These are suggestions. A person still decides if it is really the same bug.")


if __name__ == "__main__":
    main()
