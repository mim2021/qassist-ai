# Part 3: Test case generator

By Jannatul Ferdus Mim

## Why I did this

Writing test cases from a requirement takes time, and a lot of it follows fixed rules. You write one test per acceptance criterion, try a valid value and the invalid ones, and test the values right at each limit. I wanted to know if a small language model on my own laptop can write that first draft. I also wanted to know if it helps to tell the model those testing rules, or if just asking for "test cases" is enough.

## The requirements

I wrote 8 short requirements for an imaginary web shop: login, password rules, product search, shopping cart, discount coupon, registration, profile picture upload and order cancellation. Each one has 4 or 5 acceptance criteria, 33 in total. I gave them clear limits and exact messages, so a test can be checked against them. They are in [requirements.json](requirements.json). There is no real product or customer data in them.

## The prompts

All prompts get the same requirement text and the same description of the JSON answer, so the only difference is what they say about testing ([prompts.py](prompts.py)).

**Prompt A** just says "Write test cases for the following requirement."

**Prompt B** gives the model six rules that a tester would follow: at least one test per criterion, equivalence partitions, boundary values (just below, at and just above every limit), at least one negative test, no invented features, and a different title for every test.

**Prompt C** came later. I wrote it after I saw what went wrong with B (see below). It is B with four changes: write 1 to 3 tests per criterion and no more, test boundaries only for limits the requirement states and never make up a limit, use the exact message from the requirement or just say the input is rejected, and only list a criterion in "covers" if the test really checks it.

## How I tested it

The model is qwen2.5 3B, run with Ollama on my laptop's CPU ([generate.py](generate.py)). I use temperature 0 and a fixed seed, so the same run gives the same answer. I checked that: running R1 again gave word-for-word the same answers.

Ollama gets a JSON schema, which pushes the model to answer in the right shape. I still check every answer myself ([test_format.py](test_format.py)). It has to be valid JSON with every field filled in, and every criterion in "covers" has to exist for that requirement. If an answer fails, the model gets one more try. If that fails too, it counts as a failure. In practice the retry hardly helped. At temperature 0 the model almost always picks the same words again, so 5 of the 6 retries gave exactly the same answer as the first try. Only one (prompt B on order cancellation) came out different and passed. A retry would need some randomness to be useful.

[evaluate.py](evaluate.py) counts the valid answers, how many of the 33 criteria at least one test claims to cover, the number of tests of each type, and repeated titles.

"Covers" is only the model's own claim, so I also read a sample of tests by hand. For each test I asked three things. Does it make sense? Does it invent a feature? Does it really check every criterion it claims? The script picks the tests at random, mixes them up and hides which prompt wrote which.

There were two rounds. Round 1 compared A and B, 10 tests each. Round 2 compared B and C, again 10 each, with B tests that were not in round 1. I labelled the first 3 tests of round 1 myself. Claude drafted the other 37 labels with a short reason for each, without looking at the key, and I went through them.

The drafts first counted a test as "inventing" when it checked a rule the requirement doesn't state, like a length limit for the login email. I decided against that. A tester tries things like that anyway, so for me nothing there is new, it is all part of testing. So no test counts as inventing a feature, and the tests that were marked not sensible only for that reason now count as sensible. That includes four B tests that try a limit the requirement never gives, like "email just above the boundary", or a made-up rounding of quantity 10.99 to 10. Tests whose expected result goes against what the requirement says are still not sensible. All labels and reasons are in `results/manual_check.csv` and `results/manual_check_2.csv`, and the keys are next to them.

## Results

| Measure | Prompt A | Prompt B | Prompt C |
| --- | --- | --- | --- |
| Valid answers | 7 of 8 | 7 of 8 | 5 of 8 |
| Criteria covered (claimed) | 25 of 33 (76%) | 25 of 33 (76%) | 19 of 33 (58%) |
| Tests | 42 | 88 | 23 |
| Repeated titles | 0 | 3 | 0 |
| Negative tests | 21 | 42 | 9 |
| Boundary tests | 2 | 20 | 2 |
| Requirements with a negative test | 7 of 8 | 7 of 8 | 5 of 8 |
| Requirements with a boundary test | 1 of 8 | 6 of 8 | 2 of 8 |

The hand check, by round:

| | A (round 1) | B (round 1) | B (round 2) | C (round 2) |
| --- | --- | --- | --- | --- |
| Makes sense | 8 of 10 | 9 of 10 | 9 of 10 | 7 of 10 |
| Covers is correct | 5 of 10 | 5 of 10 | 3 of 10 | 7 of 10 |

With my rule, no test invents a feature, so that column is 0 for every prompt and I leave it out here.

`results/results.csv` adds both rounds together for B, so it shows 20 tests for B there.

## What the numbers say

If you only count tests, prompt B looks like the winner. It wrote twice as many as A, ten times as many boundary tests, and had a boundary test for 6 of the 8 requirements instead of 1.

Reading the tests makes it less clear. In round 1, A made sense 8 times out of 10 and B 9 times. With only 10 tests each, that one test is not a real difference, so B gives more tests of about the same quality, which is a good result for B.

B does go beyond the requirement a lot, though. Rule 3 says to test the boundaries of every limit, and on registration, which has no limits for the email or the password, the model tested limits anyway. It wrote 30 tests for registration, with things like "email just above the limit" and 15 versions of "password that contains only ...". That one answer is a third of all B's tests. In round 2 it did the same for login. I count these as normal testing, but someone still has to find out what the real limits are before such a test can pass or fail, because the requirement doesn't say.

Neither A nor B is good at "covers". Only about half of their tests really check every criterion they claim. A common case is one positive test that claims all four criteria and checks one. So the 76% coverage is too optimistic, and a tool built on this shouldn't trust the model's own coverage claim.

Several wrong tests have a good input and the wrong expected result. A file just above 5 MB is a good boundary test, but the model expected the "Only JPG and PNG files are allowed" message, which the requirement only gives for the wrong file type.

## Prompt C: better tests, but not reliable

C fixed part of what it was meant to fix. Its tests stay close to the requirement, and 7 of 10 claim the right criteria, which is better than A or B. They did not make sense more often, though: 7 of 10, against 9 of 10 for B in the same round. And it brought two new problems.

First, it broke down on 3 requirements. On password rules, product search and picture upload, the model ignored "1 to 3 tests per criterion" and kept writing until it hit the output limit of 4,096 tokens. One password answer reached 49 tests before it was cut off. All three have number limits in them, so my guess is that the boundary rule pulled it into listing more and more values. The cart and coupon requirements have limits too and didn't break, though, so I'm not sure.

Second, where it worked, it wrote too little. It wrote only 23 tests in total, often 3 for a requirement with 4 criteria, so some criteria got no test at all. Coverage dropped to 58%.

So the rules that kept the tests close to the requirement also made the model unstable. With a 3B model, I don't think more rules in the prompt is the answer. A better way may be to ask for the tests one criterion at a time, so each answer is short.

## What went wrong along the way

A and B both failed on the discount coupon requirement, twice each, in the same way as C did later on other requirements. The model kept adding coupon tests until the JSON was cut off. Each of those tries took almost 6 minutes. A larger output limit wouldn't help much, because the model needs a reason to stop. Prompt C did get the coupon one right, with 3 short tests.

Most answers took under 2 minutes. The 16 A and B answers took about 41 minutes in total. The C runs that broke down took 6 to 10 minutes per try, but the laptop was busy with Part 2 for part of that time, so I don't compare those times.

## Bonus: a stronger password rule

While I was checking the tests by hand, I noticed that R2 is weaker than the password rules I test in real life. So I wrote a stricter version, R9 ([bonus_requirement.json](bonus_requirement.json)). It keeps the 8 to 64 characters and the "Password updated" message, and adds three rules. The password needs an uppercase letter, a lowercase letter, a digit and a special character. It can't be the current password or any password the user has used before ("You cannot reuse a recent password"). And a live checklist under the field shows every rule that isn't met yet, where each rule disappears as soon as the password meets it. I kept R9 apart from the main 8 requirements, so it doesn't change the results above.

I ran all three prompts on it once ([bonus.py](bonus.py)). All three answers were valid JSON:

| | Prompt A | Prompt B | Prompt C |
| --- | --- | --- | --- |
| Tests | 10 | 9 | 13 |
| Criteria covered (claimed) | 4 of 5 | 4 of 5 | 3 of 5 |
| A separate test for each character type | yes, but some twice | no | yes, but only positive |
| Tries an old password | only the current one | yes | yes |
| Tests the live checklist (AC4) | no | no | no |
| Expected results right | no | too vague | partly |

Prompt A wrote a test for every missing character type, which is good, but it repeated two of them, and every negative test expects "You cannot reuse a recent password", even a password that is just too short. Prompt B claimed the checklist in three tests, but its expected results only say "shows error message", so you can't tell what should happen, and it made up "a recent password just below the boundary", which means nothing. Prompt C was the only one with the right message for a reused password, but it expects "Password updated" for a password that is too short or too long.

No prompt really tested the checklist, for example typing one uppercase letter and checking that only that line disappears. That is the rule that needs the most care from a tester, and it is the one the model skipped.

I also ran R9 once before with a slightly different rule 3 ("the last 5 passwords" instead of "any password used before"). That first run gave 5, 10 and 3 tests and was weaker overall. Changing a few words in one rule changed the answers a lot, so one run says little about any single prompt. This is one requirement, so it is only an example. But it fits the main results: the more rules a requirement has, the less reliably this small model tests them, and the tester's extra rules are the part it handles worst.

## Limits

The hand check is small: 10 tests per prompt per round, so one label moves a result by 10%. Most labels were drafted by Claude and then checked by me, so they are not two independent opinions. Whether a test "invents" something depends on the rule you choose. With a stricter rule (only what the requirement says), Claude's drafts counted about half of B's tests as inventing, against 1 in 10 for A and C. I sampled from all tests, so a prompt that writes many tests for one requirement gets more of its tests picked from it. All of this comes from one small model with one seed, and a bigger model may follow the rules much better. The requirements are my own and cleaner than real ones.

## What I would do next

Ask for tests one criterion at a time, so a runaway answer can't happen. Check "covers" automatically, for example with a second prompt that asks if a test really checks a criterion. And try a larger model, to see if the rules work when the model can actually follow them.

## How to run it

Start Ollama and pull the model (`ollama pull qwen2.5:3b`), then run:

```
..\.venv\Scripts\python generate.py
..\.venv\Scripts\python evaluate.py
```

`generate.py` skips answers that are already in `outputs/`, so you can stop and start it. For the bonus run, `..\.venv\Scripts\python bonus.py` asks for R9 with all three prompts, saves the answers in `outputs/bonus/`, and prints every test. When all answers for a round are there, `evaluate.py` writes the blind sheet for that round. Fill in the yes/no columns and run it again, and the hand check is added to `results/results.csv`.
