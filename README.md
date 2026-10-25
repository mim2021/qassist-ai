# qassist-ai

By Jannatul Ferdus Mim

Three small experiments on where AI can help in software testing. Each part asks one question, builds a simple tool, and measures it against the usual way of doing the job, on data with a known answer. Each folder has its own README with the full method, results and limits.

## The three parts

**[Part 1: Self-healing locators](part1_self_healing_locators/README.md).** When a UI changes, can a small model find the same element again after the usual locators break? On 8 public practice pages, with changes made by my own script, logistic regression found 97.7% of the elements on a site it had never seen. The best simple locator (id, then name, then XPath) found 70.7%. The model helps most after layout and order changes, where XPath fails.

**[Part 2: Duplicate bug finder](part2_duplicate_bug_finder/README.md).** When a new bug report comes in, can a tool show the older reports most likely to be the same bug? On public GitBugs data, sentence embeddings put the true duplicate in the top 5 for 31.8% of VS Code queries, almost twice as often as TF-IDF. On Hadoop, the classic word methods were just as good. Removing the GitHub bug template from the text helped every method.

**[Part 3: Test case generator](part3_test_case_generator/README.md).** Can a small local language model write useful first-draft test cases from a requirement, and does a prompt with testing rules help? The rules gave twice as many tests and many more boundary tests, but in a hand check half of them tested features the requirement does not have. Neither prompt's claims about which criteria it covers can be trusted.

## Setup

I use Python 3.14 on Windows, with a virtual environment in this folder:

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Part 1 also needs Chrome, but only to collect the data again; the data files are already in the repository. Part 2 downloads its data and the embedding model the first time (see its README). Part 3 needs [Ollama](https://ollama.com) with the model `qwen2.5:3b`, and no extra packages.

## Data

No company or customer data is used anywhere. Part 1 uses public practice pages, Part 2 uses the public GitBugs dataset (CC BY 4.0), and Part 3 uses requirements I wrote for an imaginary web shop. The credits are in each part's README.
