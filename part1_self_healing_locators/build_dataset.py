import json
import random
from selenium import webdriver
from selenium.webdriver.common.by import By

URL = "https://the-internet.herokuapp.com/login"
SELECTOR = "a, button, input, select, textarea, label, h1, h2, h3"


def add_labels(driver):
    """Give every visible element a secret number (the answer key)."""
    count = 0
    for el in driver.find_elements(By.CSS_SELECTOR, SELECTOR):
        if el.is_displayed():
            driver.execute_script(
                "arguments[0].setAttribute('data-qid', arguments[1]);", el, str(count)
            )
            count += 1


def collect(driver):
    """Save the fingerprint of every labelled element."""
    page_w = driver.execute_script("return window.innerWidth;")
    page_h = driver.execute_script("return window.innerHeight;")
    result = []
    for el in driver.find_elements(By.CSS_SELECTOR, "[data-qid]"):
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
    return result


def mutate(driver, seed=1):
    """Change the page a little, like a real UI update."""
    random.seed(seed)
    for el in driver.find_elements(By.CSS_SELECTOR, "[data-qid]"):
        old_id = el.get_attribute("id")
        if old_id and random.random() < 0.5:
            driver.execute_script("arguments[0].id = arguments[1];", el, old_id + "-v2")

        old_class = el.get_attribute("class")
        if old_class and random.random() < 0.5:
            driver.execute_script(
                "arguments[0].className = arguments[1];", el, "new-" + old_class
            )

        old_name = el.get_attribute("name")
        if old_name and random.random() < 0.5:
            driver.execute_script(
                "arguments[0].setAttribute('name', arguments[1]);", el, old_name + "_v2"
            )

        old_text = el.text.strip()
        if old_text and el.tag_name != "input" and random.random() < 0.5:
            new_text = random.choice(
                [old_text.lower(), old_text.upper(), old_text + " now"]
            )
            driver.execute_script("arguments[0].textContent = arguments[1];", el, new_text)

        if random.random() < 0.3:
            driver.execute_script("arguments[0].style.marginTop = '12px';", el)


driver = webdriver.Chrome()
driver.maximize_window()
driver.get(URL)

add_labels(driver)
before = collect(driver)

mutate(driver)
after = collect(driver)

driver.quit()

with open("before_login.json", "w", encoding="utf-8") as f:
    json.dump(before, f, indent=2)
with open("after_login.json", "w", encoding="utf-8") as f:
    json.dump(after, f, indent=2)

print("Before:", len(before), "elements | After:", len(after), "elements")
print()
for b, a in zip(before, after):
    print(
        f"#{b['qid']} <{b['tag']}> "
        f"id: '{b['id']}' -> '{a['id']}' | text: '{b['text']}' -> '{a['text']}'"
    )