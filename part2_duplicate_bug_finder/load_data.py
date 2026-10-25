"""Read one project from data/ and make the test queries.

A test query is a newer report that has at least one older duplicate in the
file. The right answers are those older duplicates. The links in GitBugs go
both ways, so the older report (by Created) is treated as the original.
"""
import os
import re

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

PROJECTS = {
    "hadoop": {
        "reports": "hadoop_bugs.csv",
        "links": "hadoop_bugs-combined.csv",
        "links_column": "Duplicate id",
        "date_format": "%d/%b/%y %H:%M",
    },
    "vscode": {
        "reports": "vscode_bugs.csv",
        "links": "vscode_bugs-combined.csv",
        "links_column": "Duplicates",
        "date_format": None,
    },
}
# How much of the description we use. The same text goes to every method,
# so the comparison is fair.
DESCRIPTION_CHARS = 1000


def remove_template(text):
    """Remove HTML comments such as <!-- Do Not Delete This! bug_report_template -->.
    The GitHub bug template is written in these comments, so the reporter's
    own words are what is left. This is the only cleaning rule, and it was
    fixed before running the experiment."""
    return re.sub(r"<!--.*?-->", " ", text, flags=re.S).strip()


def ids_in(cell):
    """All numbers in a cell: '13547000, 13396667' or "['108599', '114057']"."""
    return [int(x) for x in re.findall(r"\d+", str(cell))]


def load_project(name, clean=False):
    """Return (reports, queries). With clean=True the bug template is removed
    from each description before it is cut to DESCRIPTION_CHARS.

    reports: a table sorted by Created, with columns id, created, title, text.
    queries: a dict {newer report id: set of older duplicate ids}.
    """
    p = PROJECTS[name]
    df = pd.read_csv(os.path.join(DATA_DIR, p["reports"]), low_memory=False)
    df["id"] = df["Issue id"].astype(int)
    df = df.drop_duplicates("id")  # VS Code has one id twice
    if p["date_format"]:
        df["created"] = pd.to_datetime(df["Created"], format=p["date_format"], utc=True)
    else:
        df["created"] = pd.to_datetime(df["Created"], utc=True)
    df["title"] = df["Summary"].fillna("").astype(str)
    description = df["Description"].fillna("").astype(str)
    if clean:
        description = description.map(remove_template)
    description = description.str[:DESCRIPTION_CHARS]
    df["text"] = df["title"] + "\n" + description
    reports = (df[["id", "created", "title", "text"]]
               .sort_values(["created", "id"])
               .reset_index(drop=True))

    created = dict(zip(reports["id"], reports["created"]))
    links = pd.read_csv(os.path.join(DATA_DIR, p["links"]))
    queries = {}
    for left, right in zip(links["Issue id"], links[p["links_column"]]):
        for a in ids_in(left):
            for b in ids_in(right):
                if a == b or a not in created or b not in created:
                    continue
                if created[a] == created[b]:
                    continue  # we cannot tell which one came first
                newer, older = (a, b) if created[a] > created[b] else (b, a)
                queries.setdefault(newer, set()).add(older)
    return reports, queries


if __name__ == "__main__":
    for name in PROJECTS:
        reports, queries = load_project(name)
        answers = sum(len(v) for v in queries.values())
        print(f"{name}: {len(reports)} reports, {len(queries)} test queries, "
              f"{answers} right answers")
