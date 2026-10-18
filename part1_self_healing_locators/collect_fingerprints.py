import json
from selenium import webdriver
from selenium.webdriver.common.by import By

URL = "https://the-internet.herokuapp.com/login"

driver = webdriver.Chrome()
driver.maximize_window()
driver.get(URL)

elements = driver.find_elements(
    By.CSS_SELECTOR, "a, button, input, select, textarea, label, h1, h2, h3"
)

fingerprints = []
for el in elements:
    parent = el.find_element(By.XPATH, "..")
    fingerprints.append({
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
    })

driver.quit()

with open("fingerprints_login.json", "w", encoding="utf-8") as f:
    json.dump(fingerprints, f, indent=2)

print("Saved", len(fingerprints), "elements")