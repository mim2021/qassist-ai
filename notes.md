## Week 1 notes
- Collected element "fingerprints" with Selenium (tag, id, class, name, type, text, parent, position, size).
- Each element gets a hidden number (data-qid) as the answer key. The AI never sees it.
- Simulated a UI update (changed id, class, name, text, margin). Random seed fixed, so results are repeatable.
- Saved page width and height, because positions change with window size (x of username input: 34 in a small window, 284 in a large one).
- Known flaw: elements with zero size are not useful. To skip them.