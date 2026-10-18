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
SEEDS = [1, 2, 3, 4, 5]
SELECTOR = "a, button, input, select, textarea, label, h1, h2, h3"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


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


def mutate(driver, seed):
    """Change the page a little, like a real UI update."""
    random.seed(seed)
    for el in driver.find_elements(By.CSS_SELECTOR, "[data-qid]"):
        try:
            old_id = el.get_attribute("id")
            if old_id and random.random() < 0.5:
                driver.execute_script(
                    "arguments[0].id = arguments[1];", el, old_id + "-v2"
                )

            old_class = el.get_attribute("class")
            if old_class and random.random() < 0.5:
                driver.execute_script(
                    "arguments[0].className = arguments[1];", el, "new-" + old_class
                )

            old_name = el.get_attribute("name")
            if old_name and random.random() < 0.5:
                driver.execute_script(
                    "arguments[0].setAttribute('name', arguments[1]);",
                    el,
                    old_name + "_v2",
                )

            old_text = el.text.strip()
            if old_text and el.tag_name != "input" and random.random() < 0.5:
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

            if random.random() < 0.3:
                driver.execute_script("arguments[0].style.marginTop = '12px';", el)
        except WebDriverException:
            continue


def count_changed(before, after):
    """How many elements had id, class, name or text changed."""
    after_by_qid = {a["qid"]: a for a in after}
    changed = 0
    for b in before:
        a = after_by_qid.get(b["qid"])
        if a and any(a[k] != b[k] for k in ("id", "class", "name", "text")):
            changed += 1
    return changed


def run():
    os.makedirs(DATA_DIR, exist_ok=True)
    driver = webdriver.Chrome()
    driver.maximize_window()

    failed = []
    rows = []
    for name, url in PAGES.items():
        for seed in SEEDS:
            try:
                load_page(driver, url)
                add_labels(driver)
                before = collect(driver)
                mutate(driver, seed)
                after = collect(driver)
            except WebDriverException as e:
                failed.append(f"{name} seed {seed}: {str(e.msg).splitlines()[0]}")
                continue

            data = {"page": name, "url": url, "seed": seed,
                    "before": before, "after": after}
            file_path = os.path.join(DATA_DIR, f"{name}_seed{seed}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            rows.append((name, seed, len(before), len(after),
                         count_changed(before, after)))
            print(f"{name} seed {seed}: before={len(before)} after={len(after)} "
                  f"changed={rows[-1][4]}")

    driver.quit()

    print()
    print("Files saved:", len(rows), "of", len(PAGES) * len(SEEDS))
    if failed:
        print("Failed:")
        for line in failed:
            print("  ", line)


if __name__ == "__main__":
    run()