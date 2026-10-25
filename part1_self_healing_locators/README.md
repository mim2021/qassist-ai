# Part 1: Self-healing locators

By Jannatul Ferdus Mim

## Why I did this

In my job I write UI tests. A test finds a button or an input with a locator, usually its id or its XPath. Then a developer renames an id, or someone adds a banner to the top of the page, and the test goes red. The app still works. Only the locator is broken, and someone has to fix it by hand.

Some test tools promise "self-healing" locators that find the element again on their own. I wanted to see two things for myself. First, how often do the usual locators really break, and after which kind of change? Second, can a small machine-learning model find the same element again on a page it has never seen before?

## The data

I collected the data myself with Selenium and Chrome. I used 8 public practice pages from 3 sites:

| Site | Pages | Elements per page |
| --- | --- | --- |
| the-internet.herokuapp.com | login, checkboxes, dropdown, inputs, forgot password | 4 to 8 |
| saucedemo.com | login | 3 |
| demoqa.com | text box, practice form | 20 and 34 |

I checked each site before using it. The herokuapp site is made by Sauce Labs as an example app for automated testing ([github.com/saucelabs/the-internet](https://github.com/saucelabs/the-internet)). Sauce Labs also uses saucedemo.com in its own Selenium tutorial. For demoqa.com I could not find any terms of use. Many people practise on it, but I found no official statement, so I am saying that here. My script only opens each page a few dozen times.

For every visible element, `build_dataset.py` saves what I call a fingerprint: the tag, id, class, name, type, text, parent tag, full XPath, position and size, plus the page width and height. I skip elements with zero size, because a test cannot click them anyway.

The trick that makes checking possible is a hidden answer key. Before the script changes anything, it gives every element an extra attribute, `data-qid`, with a number. After the change, the same element still carries the same number. The locators and the model never look at this number. I only use it at the end to see if they picked the right element.

Then the script changes the page inside the browser, the way a UI update might. I made six kinds of change so I could look at each one on its own:

| Kind | What the script does |
| --- | --- |
| none | nothing, so I can see the best case |
| rename | adds `-v2` to the id and `new-` to each class (70% of elements) |
| text | makes the text lower case, upper case, or adds " now" (70% of elements) |
| layout | adds a 150 px banner at the top and new margins to half of the elements |
| reorder | moves about 3 in 10 elements to the top of their group, like a new field order |
| mixed | all of the above at once |

Each kind except "none" runs with 5 fixed random seeds, so you get the same files every time. That makes 208 files and 2,184 old elements to find.

## How the matcher works

I first built the simple locators that a normal test would use. Each one looks for the old value on the changed page and takes the first match, the same way `driver.find_element` does. I tried by id, by name and by XPath. I also added one that tries id first, then name, then XPath, because many frameworks fall back like that. That last one is the fair opponent.

The AI matcher works in three steps. For one old element, I pair it with every element on the changed page. For each pair, `pair_features.py` works out 10 numbers that say how alike the two are. Three of them are simple yes/no checks: same tag, same type, same parent tag. Four say how similar the id, name, class and text are, from 0 to 1. For these I count how many 3-letter pieces the two strings share (Jaccard similarity), so "username" and "username-v2" come out as very similar. The last three are about the page itself: how far apart the two elements are (divided by the page diagonal, so the window size matters less), how close their sizes are, and how far the element moved in the page order.

A classifier then learns from these pairs which ones belong to the same element. I tried logistic regression and gradient boosting. For each old element, the pair with the highest score wins.

I was careful about how I tested it. If I had mixed all the rows and split them at random, the model would see the same page in training and in testing, and the result would look better than it is. So I tested in two stricter ways. In the first, I train on 7 pages and test on the 8th, then repeat for every page. In the second, I train on 2 sites and test on the 3rd. The second one is harder, and I trust it more, because the five herokuapp pages look very much alike.

The score is simple: out of all old elements, how many did the method find exactly? If an element has no id, "by id" counts it as a miss, because a test could not have used an id for it.

## Results

This is the main result, testing on a site the model never saw:

| Change | Elements | by id | by name | by XPath | id > name > XPath | Logistic regression | Gradient boosting |
| --- | --- | --- | --- | --- | --- | --- | --- |
| none | 84 | 47.6% | 8.3% | 100% | 97.6% | 100% | 100% |
| rename | 420 | 17.1% | 8.3% | 100% | 96.4% | 95.5% | 92.9% |
| text | 420 | 47.6% | 8.3% | 100% | 97.6% | 100% | 99.0% |
| layout | 420 | 47.6% | 8.3% | 0% | 47.6% | 100% | 94.0% |
| reorder | 420 | 47.6% | 8.3% | 75.2% | 85.5% | 98.3% | 98.6% |
| mixed | 420 | 14.8% | 8.3% | 0% | 21.2% | 94.0% | 90.2% |
| all | 2,184 | 35.4% | 8.3% | 56.8% | 70.7% | 97.7% | 95.1% |

And this is the easier test, on a page the model never saw:

| Change | id > name > XPath | Logistic regression | Gradient boosting |
| --- | --- | --- | --- |
| none | 97.6% | 100% | 94.0% |
| rename | 96.4% | 100% | 95.7% |
| text | 97.6% | 100% | 94.3% |
| layout | 47.6% | 100% | 96.4% |
| reorder | 85.5% | 98.3% | 92.1% |
| mixed | 21.2% | 96.2% | 95.0% |
| all | 70.7% | 98.9% | 94.7% |

The simple locators do not learn anything, so their numbers are the same in both tests.

## What I learned from the numbers

The simple locators broke exactly where I expected. "By id" falls apart when ids are renamed. "By XPath" is perfect until I add one banner to the top of the page, and then it finds nothing at all, because the path of every element changes. It also loses a quarter of the elements when fields are reordered.

What surprised me is that id and name are not perfect even when nothing changes. Only 42 of the 84 elements have an id, and only 9 have a name. On the demoqa form, three elements share the id `subjects-label` and three radio buttons share the name `gender`. So the locator grabs the first one, and that is often the wrong one.

The model earns its place when the structure of the page changes. After layout, reorder and mixed changes, logistic regression found 94% to 100% of the elements on an unseen site. The best simple locator found between 21% and 86%. When nothing changes, or only the text changes, plain XPath is already at 100%, so the model adds nothing there.

I expected gradient boosting to win, because it is the stronger model. It did not. Logistic regression was better in both tests, which I am happy about, because I can explain its weights.

Gradient boosting was also a little worse than a plain XPath when nothing had changed at all (94.0% against 100% on unseen pages). That gives me an idea for a better design: use the normal locator first, and ask the model only when the locator fails. I have not built or tested that yet.

### Is the model just using the page order?

The order difference had the biggest weight in logistic regression, so I wondered if the model was cheating with it. I ran everything again without that feature:

| | With order difference | Without it |
| --- | --- | --- |
| Logistic regression, unseen page | 98.9% | 98.9% |
| Logistic regression, unseen site | 97.7% | 97.3% |
| Gradient boosting, unseen page | 94.7% | 95.6% |
| Gradient boosting, unseen site | 95.1% | 88.7% |

Logistic regression hardly needs it. Gradient boosting does lean on it when it meets a new site.

For anyone curious, these are the logistic regression weights (trained on all the data, with scaled features), largest first: order difference −4.37, same tag 2.50, same parent tag 2.37, class similarity −2.28, text similarity 2.11, id similarity 1.41, same type 0.99, size ratio 0.95, distance −0.69, name similarity 0.04. The negative weight for class similarity looks odd to me. I think it happens because class overlaps with other features like tag and parent, so I do not read it as "the same class means a different element".

## Where it goes wrong

On unseen sites, gradient boosting made 106 mistakes. When I looked at them, most had the same story. In 93 of them, the model picked an element with the same tag and type, usually the one right next to the correct element. For example, it wanted `gender-radio-2` and picked `gender-radio-1`, or wanted `hobbies-checkbox-3` and picked `hobbies-checkbox-2`.

These radio buttons and checkboxes have no text, the same size and the same parent. Their ids differ only in the last digit, and my 3-letter similarity barely notices that. 81 of the 106 mistakes are on the demoqa practice form, 19 on the demoqa text box and 6 on the herokuapp checkboxes.

## What this does not show

The biggest limit is that my own script makes the changes. My rename keeps most of the old name, so `username` becomes `username-v2`. That is easy for the 3-letter similarity. In a real project, a developer might change `btn-login` to something completely different. So these results show that the method works on my changes. They do not show how it would do on a real release.

The data is also small: 8 pages on 3 sites, and most pages have fewer than 10 elements. Picking the right element out of 4 is not hard. I ran gradient boosting with one seed (42) and did not compute confidence intervals. Tag, type and parent never change in my data, so the model learns that they always stay the same, which may not be true on a real site. The matcher always gives an answer, even when it is unsure, and cannot yet say "I could not find it". And I only used Chrome with a maximised window.

## How to run it

You need Python 3, Chrome, and three packages (I used Python 3.14 and the versions in `requirements.txt` in the main folder):

```
pip install selenium scikit-learn numpy
```

Then run these in the `part1_self_healing_locators` folder:

```
python build_dataset.py
python baselines.py
python pair_features.py
python train_matcher.py
```

`build_dataset.py` opens Chrome and saves the 208 files in `data/`. It takes about 12 minutes and needs internet. The files are already in the repository, so you can skip it. `baselines.py` prints the table for the simple locators. `pair_features.py` builds the pairs and prints a quick check that the same-element pairs really look more alike. It also saves `results/pairs.csv`, which is about 5.5 MB, so I do not upload it. `train_matcher.py` trains and tests both models in about a minute and a half, prints the tables above, and saves `results/matcher_results.csv`.

## Files

- `build_dataset.py` collects the fingerprints, adds the answer key and makes the changes
- `baselines.py` has the simple locators
- `pair_features.py` builds the 10 pair features
- `train_matcher.py` trains the models and runs both tests
- `data/` has the 208 data files, and `results/` has the result tables
- `collect_fingerprints.py`, `before_login.json` and `after_login.json` are my first try from week 1. I kept them to show where I started

## Credit

Self-healing locators are not my idea, and several test tools already offer them. I am not claiming a new method. What I did is build a small, open dataset with an answer key, and measure a simple model against the usual locators, one kind of change at a time.
