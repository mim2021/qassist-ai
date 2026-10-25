"""Download the Hadoop and VS Code files from GitBugs into data/.

GitBugs: https://github.com/av9ash/gitbugs (CC BY 4.0, cite arXiv:2504.09651).
The files are too big to upload to GitHub through the website, so they are
not in this repository. Run this once instead. It needs internet.
"""
import os
import urllib.request
import zipfile

BASE = "https://raw.githubusercontent.com/av9ash/gitbugs/main/"
FILES = [
    "hadoop/hadoop_bugs.csv",
    "hadoop/hadoop_bugs-combined.csv",
    "ms_vscode_bugs/vscode_bugs.csv.zip",
    "ms_vscode_bugs/vscode_bugs-combined.csv",
]
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def download(path):
    target = os.path.join(DATA_DIR, os.path.basename(path))
    if os.path.exists(target):
        print("Already there:", os.path.basename(path))
        return target
    print("Downloading", path, "...")
    urllib.request.urlretrieve(BASE + path, target)
    return target


def run():
    os.makedirs(DATA_DIR, exist_ok=True)
    for path in FILES:
        target = download(path)
        if target.endswith(".zip"):
            with zipfile.ZipFile(target) as z:
                # Take only the CSV, not the extra __MACOSX folder in the zip.
                z.extract("vscode_bugs.csv", DATA_DIR)
            print("Unzipped vscode_bugs.csv")
    print()
    print("Files in data/:")
    for name in sorted(os.listdir(DATA_DIR)):
        size = os.path.getsize(os.path.join(DATA_DIR, name)) / 1e6
        print(f"  {name:<32} {size:6.1f} MB")


if __name__ == "__main__":
    run()
