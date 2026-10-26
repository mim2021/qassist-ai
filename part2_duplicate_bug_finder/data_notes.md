# Data notes for Part 2

These are my notes from opening the GitBugs files, before building anything.

## Source and licence

- GitBugs by Avinash Patil: <https://github.com/av9ash/gitbugs>, paper: arXiv:2504.09651 (2025).
- Licence: the repository README says the project is released under Creative Commons Attribution 4.0 (CC BY 4.0). Anyone who reuses it must cite the paper. GitHub itself shows no licence file for the repo, so the README is the only statement.
- The README table lists 9 projects and 192,387 reports in total. The paper's abstract says "over 150,000", so I quote the per-project numbers from the table instead of a total.

## Files I use

| Project | Tracker | Reports file | Duplicate links file |
| --- | --- | --- | --- |
| Hadoop | Jira | `hadoop/hadoop_bugs.csv` (2.7 MB) | `hadoop/hadoop_bugs-combined.csv` |
| VS Code | GitHub issues | `ms_vscode_bugs/vscode_bugs.csv.zip` (10.7 MB, 41 MB unzipped) | `ms_vscode_bugs/vscode_bugs-combined.csv` |

Hadoop also has small `-train.csv` and `-test.csv` files with a split made by the dataset author. I do not use them, because I split by time.

## Fields

Hadoop reports (2,503 rows, created 1 Jan 2020 to 31 Dec 2024):

| Column | Notes |
| --- | --- |
| Summary | the title, never empty |
| Issue id | a number such as 13404344, unique |
| Status | Resolved, Open, Patch Available, In Progress, Reopened |
| Priority | Major, Minor, Critical, Blocker, Trivial |
| Resolution | Fixed, Duplicate, Won't Fix and others; empty for 770 rows |
| Created | text like `30/Sep/21 17:20` |
| Resolved | same format; empty for 770 rows |
| Affects Version/s | empty for 741 rows |
| Description | the body text, Jira markup; empty for 143 rows |

VS Code reports (32,829 rows, created 13 Nov 2015 to 25 Jul 2024):

| Column | Notes |
| --- | --- |
| Issue id | the GitHub issue number; one number (51135) appears twice |
| Summary | the title |
| Created | text like `2024-07-25 14:34:59+00:00` |
| Resolved | empty for 2,684 rows |
| Description | the body text, Markdown; empty for 226 rows |
| Resolution | completed, not_planned, reopened; empty for 2,592 rows. There is no "duplicate" value |

Duplicate links:

- Hadoop: columns `Issue id`, `Duplicate id`. Some cells hold two ids, like `"13547000, 13396667"`.
- VS Code: columns `Issue id`, `Duplicates`, where `Duplicates` is a list written as text, like `['108599', '114057']`. Some ids have extra spaces.
- The links go both ways (A lists B and B lists A), so they do not say which report is the original. I take the older report (by Created) as the original.

## What the links really give me

| | Hadoop | VS Code |
| --- | --- | --- |
| Duplicate pairs in the links file | 66 | 17,353 |
| Pairs where both reports are in the reports file | 66 | 375 |
| Test queries (a newer report whose older duplicate is in the file) | 66 | 355 |

For VS Code, most links point to issues that are not in the reports file, so only 355 queries can be used. (My first count was 358. Three pairs were created in the same second, so I cannot tell which report came first, and I skip them.) For Hadoop, 151 reports have Resolution "Duplicate", but only 59 of them appear in any link. So the labels are incomplete, and some "misses" may be real duplicates that nobody linked.

Test queries per year: Hadoop 2020: 15, 2021: 11, 2022: 25, 2023: 8, 2024: 7. VS Code 2020: 26, 2021: 130, 2022: 94, 2023: 85, 2024: 23 (counted before skipping the three same-second pairs).

## Privacy

These are public bug reports, but the text can contain people's names, user names or log lines. I do not copy report text into the README, only ids and short summaries where needed.

## Thunderbird (added later as a check)

- Files: `thunderbird/Thunderbird_bugs.csv` (13.8 MB) and `thunderbird/Thunderbird_bugs-combined.csv`.
- Reports: 15,192 rows, created 1 Jan 2020 to 5 Mar 2025, the same columns as Hadoop, and no repeated ids. `Created` looks like `2020-01-01 01:58:36+00:00`. The description is empty for 181 rows, and only 21 descriptions contain an HTML comment.
- Links: 4,288 rows with columns `Issue id` and `Duplicate id`, one id in each. 3,214 reports have Resolution "DUPLICATE".
- Test queries: 1,917, with 1,974 right answers.
