# Part 2: Duplicate bug finder

By Jannatul Ferdus Mim

## Why I did this

The same bug often gets reported more than once. Different people hit it, describe it in their own words, and file a new report. Somebody then has to read each one and realise it is already known. That is slow, and when it goes wrong, the same bug is fixed twice or tracked in two places.

So I asked a simple question. When a new bug report comes in, can a tool show the five older reports most likely to be the same bug? And does an AI method that compares meaning do better than the classic methods that compare words?

## The data

I used GitBugs, a public collection of bug reports with duplicate labels made by Avinash Patil ([github.com/av9ash/gitbugs](https://github.com/av9ash/gitbugs)). Its README says it is released under CC BY 4.0, and it asks users to cite the paper (see Credit below). I did not use any company tickets.

I picked two projects on purpose, because they use different trackers and different kinds of reporters:

| Project | Tracker | Reports | Created |
| --- | --- | --- | --- |
| Hadoop | Jira | 2,503 | Jan 2020 to Dec 2024 |
| VS Code | GitHub issues | 32,828 | Nov 2015 to Jul 2024 |

For each report I use the title and the first 1,000 characters of the description. Every method gets exactly the same text.

Opening the files gave me my first surprise. The GitBugs table says VS Code has 9,238 duplicates, so I expected thousands of test cases. But most duplicate links in the VS Code file point to issues that are not in the reports file. Only 375 pairs have both reports in it. Hadoop has 66 pairs. The links also go both ways (A lists B and B lists A), so I treat the older report as the original. A test query is then a newer report whose older duplicate is in the file. That gives 66 queries for Hadoop and 355 for VS Code. (I skipped a few pairs created in the same second, because I cannot tell which came first.)

The labels are also incomplete. In Hadoop, 151 reports are marked "Duplicate", but only 59 of them appear in any link. So when a method "misses", it may sometimes have found a real duplicate that nobody linked. My full notes on the files are in [data_notes.md](data_notes.md).

## How I tested it

The paper "Duplicate Bug Report Detection: How Far Are We?" (Zhang et al., TOSEM 2023) warns that old benchmarks give biased results, that results differ between trackers, and that a simple method beat newer deep-learning tools on recent data. I took three things from that: test on two trackers, respect time, and treat the simple methods as serious opponents.

To respect time, every query searches only the reports created before it, like a tester searching on the day the bug came in. I first planned one fixed cut-off date, but that would have left Hadoop with only 15 test queries, so I chose this rolling test instead. It keeps all the queries and never lets a method see the future. For TF-IDF and BM25, even the word statistics (how rare each word is) are counted only on those older reports.

I score each method with the usual measures. Recall@k is the share of queries where the true duplicate is in the top k results. MRR (mean reciprocal rank) is the average of 1 divided by the rank of the true duplicate, so it rewards finding it near the top. When several reports have the same score, I count the tied ones as ranked above the true duplicate, so a tie never helps a method.

## The four methods

**TF-IDF** and **BM25** are the classic word-based methods. They give a high score to older reports that share many words with the new one, especially rare words. I wrote both myself on top of scikit-learn's word counter, and I checked that my TF-IDF scores are the same as scikit-learn's own TF-IDF.

**Embeddings** is the AI method. A small pre-trained language model, all-MiniLM-L6-v2 (Apache-2.0 licence), turns each report into 384 numbers that stand for its meaning. Two reports that say the same thing in different words get similar numbers, and I compare them with cosine similarity. The model was not trained on my data, so it cannot have learned the answers. It reads at most 256 word pieces, so the end of a long text is cut off.

**Hybrid** mixes BM25 and embeddings with reciprocal rank fusion. Each method ranks the older reports, and each report gets 1/(60 + rank) from both lists added together. A report that is high in both lists wins.

## Results

| Project | Method | Recall@1 | Recall@5 | Recall@10 | MRR |
| --- | --- | --- | --- | --- | --- |
| Hadoop (66 queries) | TF-IDF | 53.0% | 78.8% | 84.8% | 0.633 |
| | BM25 | 47.0% | 72.7% | 80.3% | 0.592 |
| | Embeddings | 48.5% | 80.3% | 84.8% | 0.617 |
| | Hybrid | 51.5% | 80.3% | 89.4% | 0.648 |
| VS Code (355 queries) | TF-IDF | 8.2% | 16.9% | 21.1% | 0.124 |
| | BM25 | 9.6% | 15.8% | 17.7% | 0.129 |
| | Embeddings | 16.9% | 31.8% | 36.9% | 0.240 |
| | Hybrid | 13.0% | 25.4% | 32.1% | 0.198 |

## What the numbers say

On VS Code, the AI method clearly helps. Embeddings put the true duplicate in the top 5 for 31.8% of queries, almost twice as often as TF-IDF (16.9%). That fits the problem: VS Code reports come from thousands of different users, and they describe the same bug in different words.

On Hadoop, the four methods are close. TF-IDF is best at the very top (Recall@1), and the hybrid is best at Recall@10 and MRR. With only 66 queries, one query is about 1.5%, so I would not call any of these a clear winner. The simple word method is a serious opponent here, just as the paper above found.

Mixing methods is not always better. On VS Code the hybrid is worse than embeddings alone, because BM25 is weak there and pulls the result down.

The two projects are very different in difficulty. A Hadoop query searches about 1,300 older reports (the median), and a VS Code query about 24,000. Hadoop duplicates are also often filed by developers who use the same technical words, though not by copying: only 6 of the 66 have exactly the same title as their original.

## Five failures I read by hand

I picked four VS Code queries and one Hadoop query where embeddings did not find the true duplicate in the top 10, and read them.

1. **The bug template drowns the real text.** A report about the terminal ignoring the working directory with a different profile in a multi-folder workspace. Its true duplicate is a report about the "selected working directory" being ignored for a "non-default profile" in a "multi-folder workspace". It is the same bug in different words, but the new report's description starts with the GitHub bug template (`<!-- Do Not Delete This! bug_report_template -->` and more). So the top picks were other terminal reports with the same template, at similarity 0.86. The true duplicate was ranked 258th.
2. **The label may be too narrow.** A report about drag and drop in notebooks causing unexpected scrolling. Its labelled duplicate is about focus and scroll position jumping to the top on many operations. The model's top picks were "Drag and drop Notebook cells broken" and "Cell drag and drop doesn't work". These look at least as close to me, so this may be a duplicate that nobody linked rather than a real mistake.
3. **Same cause, different symptom.** "git diff doesn't work in root of a drive" against an older report about source control showing an empty file when the project is on a remote share. A developer can see that both come from the same path handling, but the words and the symptoms are different. Neither embeddings (rank 439) nor TF-IDF (rank 8,911) came close. Both reports start with the template too.
4. **Same cause, different feature.** A report about `@link` making a Windows path inside a Dev Container, against an older one about JSDoc links in remote sources opening on the host system. Again it is one root cause described from two sides, and both descriptions start with the template.
5. **Symptom against cause (Hadoop).** "Fix compilation error of ITUseHadoopCodecs with -DskipShade" is linked to a report saying lz4-java and snappy-java should be excluded from relocation in the shaded libraries. One describes the build error and the other describes its cause. The model's second pick, "hadoop-client-integration-tests doesn't work when building with skipShade", looks closely related to me.

Two lessons came out of this. First, about 17% of VS Code descriptions start with the bug template, and in three of my four VS Code failures it was there. So I tried removing it, as a separate experiment (next section). Second, many duplicates are linked by a shared root cause, not by a shared description. Text similarity alone cannot find those.

## Experiment: removing the bug template

The GitHub bug template is written inside HTML comments (`<!-- ... -->`). I decided on one cleaning rule before running anything: remove every HTML comment from the description, then take the first 1,000 characters as before. Nothing else changed. All four methods get the same cleaned text, and the queries and the rolling test are exactly the same.

10,876 of the 32,828 VS Code descriptions contain an HTML comment somewhere. In Hadoop it is only 5 of 2,503, so the Hadoop numbers did not change at all, which is what I expected.

VS Code, before and after removing the template:

| Method | Recall@1 | Recall@5 | Recall@10 | MRR |
| --- | --- | --- | --- | --- |
| TF-IDF | 8.2% → 10.1% | 16.9% → 21.1% | 21.1% → 26.2% | 0.124 → 0.158 |
| BM25 | 9.6% → 12.4% | 15.8% → 20.8% | 17.7% → 24.5% | 0.129 → 0.173 |
| Embeddings | 16.9% → 17.5% | 31.8% → 36.3% | 36.9% → 44.2% | 0.240 → 0.267 |
| Hybrid | 13.0% → 16.6% | 25.4% → 35.5% | 32.1% → 41.7% | 0.198 → 0.257 |

Every method got better, so the template was hurting all of them, not only the AI. Embeddings are still the best, and now find the true duplicate in the top 10 for 44.2% of VS Code queries. The hybrid gained the most and is now close to embeddings, because BM25 improved too.

I want to be clear about one thing. The idea came from reading test failures, so this is not a clean, untouched test. I kept it as fair as I could: one rule, decided before the run, applied to every method alike, and the original numbers stay in the main table above. The real check would be a third project that I have not looked at. `find_duplicates.py` still uses the original text.

## Try it on a new report

`find_duplicates.py` takes a project, a title and an optional description, and prints the five most similar older reports with their scores. It uses the embedding method. For example:

```
..\.venv\Scripts\python find_duplicates.py vscode "Terminal opens in wrong folder" "In a multi-root workspace the new terminal starts in the first folder instead of the selected one."
```

The top result was "Terminal fails to open after setting terminal.integrated.cwd in multi-root workspace", with a score of 0.70, and the third was "'Split Terminal' in workspace is opening incorrect directory". Each VS Code result has a link to the GitHub issue. A search takes about 25 seconds, mostly to load the model. The tool only suggests reports. A person still has to decide whether it is really the same bug.

## What this does not show

The duplicate labels come from the project maintainers and are incomplete, so some "misses" may be real duplicates that nobody linked. Two projects are not all projects, and the Hadoop result rests on only 66 queries. VS Code has fewer usable queries than its size suggests, because most links point outside the file. I used one embedding model with no fine-tuning, the first 1,000 characters of each description, and no confidence intervals. And the results are about finding a report that was later linked as a duplicate, not about how much triage time a team would really save.

## How to run it

The packages are listed in `requirements.txt` in the main folder. I use a virtual environment there (`.venv`), so the large AI packages stay on the E drive. Run these in the `part2_duplicate_bug_finder` folder:

```
..\.venv\Scripts\python download_data.py
..\.venv\Scripts\python baselines.py
..\.venv\Scripts\python embeddings.py
..\.venv\Scripts\python find_duplicates.py vscode "your title" "your description"
```

To repeat the template experiment, run `..\.venv\Scripts\python embeddings.py --clean`. It embeds the cleaned text once more (about 9 minutes) and saves `results/all_methods_clean.csv`.

`download_data.py` downloads about 13 MB from GitBugs into `data/`. The data is not in this repository, because the VS Code file is 41 MB. `baselines.py` runs TF-IDF and BM25 (about 30 seconds). `embeddings.py` downloads the model (about 90 MB) into `models/` the first time, embeds every report once (about 11 minutes on my CPU), saves the vectors in `data/`, and prints the table above. The next runs take seconds.

## Files

- `download_data.py` gets the GitBugs files
- `load_data.py` reads a project and builds the test queries
- `baselines.py` has TF-IDF, BM25 and the rolling test
- `embeddings.py` has the embedding and hybrid methods and prints all four
- `find_duplicates.py` is the tool for a new report
- `data_notes.md` has my notes on the data files
- `results/` has the result tables, including the rank of the true duplicate for every query

## Credit

Finding duplicate bug reports is a well-studied problem, and I am not claiming a new method. I compared known methods on public data, with a test that respects time.

- A. Patil, "GitBugs: Bug Reports for Duplicate Detection, Retrieval Augmented Generation, Triage, and More", arXiv:2504.09651, 2025. Data licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
- T. Zhang, D. Han, V. Vinayakarao, I. C. Irsan, B. Xu, F. Thung, D. Lo and L. Jiang, "Duplicate Bug Report Detection: How Far Are We?", ACM Transactions on Software Engineering and Methodology 32(4), 2023. [doi:10.1145/3576042](https://doi.org/10.1145/3576042)
- The embedding model is sentence-transformers/all-MiniLM-L6-v2 from Hugging Face (Apache-2.0).
