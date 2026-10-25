# Part 3: Test case generator

By Jannatul Ferdus Mim

## Why I did this

Writing test cases from a requirement is slow, and much of the work follows fixed rules: one test per acceptance criterion, a valid value, the invalid values, and the values right at each limit. I wanted to know whether a small language model running on my own laptop can do this first draft, and whether telling it those testing rules gives better tests than just asking for "test cases".

## The requirements

I wrote 8 short requirements for an imaginary web shop: login, password rules, product search, shopping cart, discount coupon, registration, profile picture upload and order cancellation. Each one has 4 or 5 acceptance criteria (33 in total) with clear limits and exact messages, so a test can be checked against them. They are in [requirements.json](requirements.json). No real product or customer data is used.

## The two prompts

Both prompts get the same requirement text and the same description of the JSON answer format, so the only difference is the test strategy ([prompts.py](prompts.py)).

**Prompt A** just asks: "Write test cases for the following requirement."

**Prompt B** gives the model six rules a tester would follow: at least one test per criterion, equivalence partitions, boundary values (just below, at and just above every limit), at least one negative test, no invented features, and a different title for every test.

## How I tested it

The model is qwen2.5 3B, run locally with Ollama on the CPU ([generate.py](generate.py)). I use temperature 0 and a fixed seed, so a run can be repeated. Ollama is given a JSON schema, so the model is pushed to answer in the right shape, but I still check every answer myself ([test_format.py](test_format.py)): it must be valid JSON, every field must be there, and every criterion id in "covers" must exist for that requirement. If an answer fails the check, the model gets one more try. If it fails again, it counts as a failure.

The automatic measures in [evaluate.py](evaluate.py) count valid answers, how many of the 33 criteria are claimed by at least one test, the number of tests by type, and repeated titles.

"Covers" is the model's own claim, so I also checked a sample by hand. The script picked 10 tests from each prompt at random, mixed them, and hid which prompt wrote which. For each test I answered three questions: does the test make sense, does it test something the requirement does not mention, and does it really check every criterion it claims? I labelled the first 3 tests myself. For the other 17, Claude drafted labels with a short reason, using the same standard, and I reviewed and confirmed them. While reading the code, Claude saw that item 4 came from prompt B; the other drafts were made without the key. The labels and reasons are in [results/manual_check.csv](results/manual_check.csv), and the key is in [results/manual_key.csv](results/manual_key.csv).

## Results

| Measure | Prompt A | Prompt B |
| --- | --- | --- |
| Valid answers | 7 of 8 (7 on the first try) | 7 of 8 (6 on the first try) |
| Criteria covered (claimed) | 25 of 33 (76%) | 25 of 33 (76%) |
| Tests | 42 | 88 |
| Repeated titles | 0 (0%) | 3 (3%) |
| Negative tests | 21 | 42 |
| Boundary tests | 2 | 20 |
| Requirements with a negative test | 7 of 8 | 7 of 8 |
| Requirements with a boundary test | 1 of 8 | 6 of 8 |
| Manual: makes sense | 8 of 10 | 5 of 10 |
| Manual: invents a feature | 1 of 10 | 5 of 10 |
| Manual: covers is correct | 5 of 10 | 5 of 10 |

## What the numbers say

Prompt B does what its rules ask for in shape: twice as many tests, ten times as many boundary tests, and a boundary test for 6 of the 8 requirements instead of 1. If you only counted tests, B would look much better.

The hand check tells a different story. Half of B's sampled tests invent something the requirement does not say, against 1 of 10 for A. The cause is easy to see in the registration requirement. Rule 3 says to test the boundary of every limit, but the requirement has no limits for the email or the password. The model invented them: B wrote 30 tests for registration, including "email just above the limit" and 15 versions of "password that contains only ...". That one answer is a third of all B's tests. Because the sample was drawn from all tests, 4 of B's 10 sampled tests came from it. So the 5 of 10 partly reflects this one answer, but it is still a real failure. Rule 5 ("do not invent features") did not stop it.

Neither prompt is good at "covers". Only half of the sampled tests really check every criterion they claim. A common pattern is one positive test that claims all four criteria but checks only one. So the 76% criteria coverage, which is the same for both prompts, is too optimistic. A tool built on this must not trust the model's own coverage claim.

Several wrong tests have a good input but the wrong expected result. For example, a file just above 5 MB is a good boundary test, but the model expected the "Only JPG and PNG files are allowed" message, which the requirement gives only for the wrong file type. A tester would catch this quickly, but it shows that the output is a draft, not a finished test.

## What went wrong

Both prompts failed on the discount coupon requirement, twice each. The model kept writing more and more coupon tests until it reached the output limit of 4,096 tokens, so the JSON was cut off. Each of these attempts took almost 6 minutes. A larger limit would not help much; the model needs to be told how many tests to write.

The other answers took between 39 seconds and 3.5 minutes each. All 16 together, with retries, took about 41 minutes.

## Limits

The hand check covers only 20 tests, so one or two labels change the result by 10%. The labels were drafted by Claude and confirmed by me, not written independently by two people. All results come from one small model with one seed; a larger model may follow the rules better. The requirements are my own and are cleaner than real ones.

## What I would do next

Tell the model how many tests to write per criterion, to stop runaway answers like the coupon one. Change rule 3 to "for every limit stated in the requirement", so it does not invent limits. Check "covers" automatically, for example by asking a second prompt whether each test really checks the criterion. And repeat the hand check with a larger sample drawn evenly per requirement.

## How to run it

Start Ollama and pull the model (`ollama pull qwen2.5:3b`), then:

```
python generate.py
python evaluate.py
```

`generate.py` skips answers that are already in `outputs/`, so it can be stopped and started again. The first time `evaluate.py` runs, it writes the blind sheet `results/manual_check.csv`. Fill in the yes/no columns, then run it again to add the manual results to `results/results.csv`.
