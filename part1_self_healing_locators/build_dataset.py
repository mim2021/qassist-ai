import json
import os
import random
import time

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

PAGES = {
    "herokuapp_login": "https://the-internet.herokuapp.com/login",
    "herokuapp_checkboxes": "https://the-internet.herokuapp.com/checkboxes",
    "herokuapp_dropdown": "https://the-internet.herokuapp.com/dropdown",
    "herokuapp_inputs": "https://the-internet.herokuapp.com/inputs",
    "herokuapp_forgot_password": "https://the-internet.herokuapp.com/forgot_password",
    "saucedemo_login": "https://www.saucedemo.com/",
    "demoqa_text_box": "https://demoqa.com/text-box",
    "demoqa_practice_form": "https://demoqa.com/automation-practice-form",
}
# The kinds of UI change. "none" changes nothing, so it shows the best a
# locator can do on an unchanged page.
KINDS = ["none", "rename", "text", "layout", "reorder", "mixed"]
SEEDS = [1, 2, 3, 4, 5]
SELECTOR = "a, button, input, select, textarea, label, h1, h2, h3"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Builds the full XPath of an element, for example /html/body/div[2]/form/input[1].
XPATH_JS = """
let el = arguments[0], parts = [];
while (el && el.nodeType === 1) {
    let i = 1, sib = el.previousElementSibling;
    while (sib) { if (sib.tagName === el.tagName) i++; sib = sib.previousElementSibling; }
    parts.unshift(el.tagName.toLowerCase() + '[' + i + ']');
    el = el.parentElement;
}
return '/' + parts.join('/');
"""


def load_page(driver, url):
    """Open the page and wait until it has elements."""
    driver.get(url)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, SELECTOR))
    )
    time.sleep(1)


def add_labels(driver):
    """Give every visible element with a real size a secret number (the answer key)."""
    count = 0
    for el in driver.find_elements(By.CSS_SELECTOR, SELECTOR):
        try:
            size = el.size
            if el.is_displayed() and size["width"] > 0 and size["height"] > 0:
                driver.execute_script(
                    "arguments[0].setAttribute('data-qid', arguments[1]);",
                    el,
                    str(count),
                )
                count += 1
        except WebDriverException:
            continue
    return count


def collect(driver):
    """Save the fingerprint of every labelled element."""
    page_w = driver.execute_script("return window.innerWidth;")
    page_h = driver.execute_script("return window.innerHeight;")
    result = []
    for el in driver.find_elements(By.CSS_SELECTOR, "[data-qid]"):
        try:
            parent = el.find_element(By.XPATH, "..")
            result.append({
                "qid": el.get_attribute("data-qid"),
                "tag": el.tag_name,
                "id": el.get_attribute("id"),
                "class": el.get_attribute("class"),
                "name": el.get_attribute("name"),
                "type": el.get_attribute("type"),
                "text": el.text.strip(),
                "parent_tag": parent.tag_name,
                "xpath": driver.execute_script(XPATH_JS, el),
                "x": el.location["x"],
                "y": el.location["y"],
                "width": el.size["width"],
                "height": el.size["height"],
                "page_w": page_w,
                "page_h": page_h,
            })
        except WebDriverException:
            continue
    return result


def rename(driver, el):
    """Rename the id and every class, like a developer refactoring the code."""
    old_id = el.get_attribute("id")
    if old_id and random.random() < 0.7:
        driver.execute_script("arguments[0].id = arguments[1];", el, old_id + "-v2")

    old_class = el.get_attribute("class")
    if old_class and random.random() < 0.7:
        new_class = " ".join("new-" + c for c in old_class.split())
        driver.execute_script("arguments[0].className = arguments[1];", el, new_class)


def change_text(driver, el):
    """Change the visible text, like a new wording on a button or label."""
    old_text = el.text.strip()
    if old_text and el.tag_name != "input" and random.random() < 0.7:
        new_text = random.choice(
            [old_text.lower(), old_text.upper(), old_text + " now"]
        )
        # Do not change text if the element holds another labelled element,
        # because that would delete the inner element.
        driver.execute_script(
            "if (!arguments[0].querySelector('[data-qid]')) "
            "{ arguments[0].textContent = arguments[1]; }",
            el,
            new_text,
        )


def add_banner(driver):
    """Put a new banner at the top of the page. Everything moves down, and the
    full XPath of many elements changes, because body gets a new first child."""
    driver.execute_script(
        "let b = document.createElement('div');"
        "b.textContent = 'New banner';"
        "b.style.height = '150px';"
        "document.body.insertBefore(b, document.body.firstChild);"
    )


def shift(driver, el):
    """Move one element a little, like a new spacing in the design."""
    if random.random() < 0.5:
        driver.execute_script(
            "arguments[0].style.marginTop = arguments[1] + 'px';"
            "arguments[0].style.marginLeft = arguments[2] + 'px';",
            el,
            random.randint(5, 30),
            random.randint(0, 30),
        )


def move_up(driver, el):
    """Move the element's block to the top of its group, like a new field
    order in a form. Many inputs sit alone inside a wrapper div, so we go up
    until we reach a block that has siblings, and move that block. The page
    order of the element (and of the elements it passes) changes."""
    if random.random() < 0.3:
        driver.execute_script(
            "let b = arguments[0];"
            "while (b.parentElement && b.parentElement !== document.body"
            "       && b.parentElement.children.length < 2) { b = b.parentElement; }"
            "let p = b.parentElement;"
            "if (p && p !== document.body && p.firstElementChild !== b)"
            "{ p.insertBefore(b, p.firstElementChild); }",
            el,
        )


def mutate(driver, kind, seed):
    """Change the page in one kind of way, like a real UI update."""
    random.seed(seed)
    if kind in ("layout", "mixed"):
        add_banner(driver)
    for el in driver.find_elements(By.CSS_SELECTOR, "[data-qid]"):
        try:
            if kind in ("rename", "mixed"):
                rename(driver, el)
            if kind in ("text", "mixed"):
                change_text(driver, el)
            if kind in ("layout", "mixed"):
                shift(driver, el)
            if kind in ("reorder", "mixed"):
                move_up(driver, el)
        except WebDriverException:
            continue


def count_changed(before, after):
    """How many elements had id, class, name, text, XPath or position changed."""
    after_by_qid = {a["qid"]: a for a in after}
    changed = 0
    for b in before:
        a = after_by_qid.get(b["qid"])
        if a and any(a[k] != b[k] for k in ("id", "class", "name", "text", "xpath", "x", "y")):
            changed += 1
    return changed


def run():
    os.makedirs(DATA_DIR, exist_ok=True)
    driver = webdriver.Chrome()
    driver.maximize_window()

    failed = []
    saved = 0
    expected = 0
    for name, url in PAGES.items():
        for kind in KINDS:
            # "none" is the same for every seed, so one seed is enough.
            for seed in ([1] if kind == "none" else SEEDS):
                expected += 1
                try:
                    load_page(driver, url)
                    add_labels(driver)
                    before = collect(driver)
                    mutate(driver, kind, seed)
                    after = collect(driver)
                except WebDriverException as e:
                    failed.append(f"{name} {kind} seed {seed}: {str(e.msg).splitlines()[0]}")
                    continue

                data = {"page": name, "url": url, "kind": kind, "seed": seed,
                        "before": before, "after": after}
                file_path = os.path.join(DATA_DIR, f"{name}_{kind}_seed{seed}.json")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)

                saved += 1
                print(f"{name} {kind} seed {seed}: before={len(before)} "
                      f"after={len(after)} changed={count_changed(before, after)}")

    driver.quit()

    print()
    print("Files saved:", saved, "of", expected)
    if failed:
        print("Failed:")
        for line in failed:
            print("  ", line)


if __name__ == "__main__":
    run()
