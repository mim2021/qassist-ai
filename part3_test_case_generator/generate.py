"""Ask the local model for test cases: every requirement with prompt A and B.

It uses Ollama on this computer (http://localhost:11434), model qwen2.5 3B,
on the CPU only (the GPU setup on my laptop crashed). Most answers take
under 2 minutes, but an answer that runs into the output limit takes almost
6, so all 16 with retries took about 41 minutes. Answers are saved in
outputs/, and a finished answer is not asked again, so you can stop and
start the script.

If an answer is not valid, the model is asked once more. If it is still not
valid, it counts as a failure (the answer is kept for reading).
"""
import json
import os
import time
import urllib.request

from prompts import PROMPTS, requirement_text
from test_format import SCHEMA, check

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "outputs")
MODEL = "qwen2.5:3b"
URL = "http://localhost:11434/api/chat"
# temperature 0 and a fixed seed, so a run can be repeated. num_gpu 0 = CPU only.
OPTIONS = {"temperature": 0, "seed": 42, "num_gpu": 0, "num_predict": 4096}


def load_requirements():
    with open(os.path.join(HERE, "requirements.json"), encoding="utf-8") as f:
        return json.load(f)


def ask(prompt, seed):
    body = {"model": MODEL, "stream": False, "format": SCHEMA,
            "options": dict(OPTIONS, seed=seed),
            "messages": [{"role": "user", "content": prompt}]}
    request = urllib.request.Request(URL, json.dumps(body).encode("utf-8"),
                                     {"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=1800) as response:
        return json.load(response)


def run():
    os.makedirs(OUT_DIR, exist_ok=True)
    for req in load_requirements():
        for name, template in PROMPTS.items():
            path = os.path.join(OUT_DIR, f"{req['id']}_{name}.json")
            if os.path.exists(path):
                print(f"{req['id']} prompt {name}: already done")
                continue
            # replace, not format(): the JSON example in the prompt has { } in it
            prompt = template.replace("{requirement}", requirement_text(req))
            attempts = []
            for attempt, seed in enumerate((42, 43), 1):  # first try, then one retry
                start = time.time()
                reply = ask(prompt, seed)
                text = reply["message"]["content"]
                cases, problems = check(text, req)
                attempts.append({"attempt": attempt, "seconds": round(time.time() - start),
                                 "output_tokens": reply.get("eval_count"),
                                 "problems": problems, "text": text})
                if not problems:
                    break
            result = {"requirement": req["id"], "prompt": name, "model": MODEL,
                      "options": OPTIONS, "valid": not attempts[-1]["problems"],
                      "attempts": attempts}
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            last = attempts[-1]
            print(f"{req['id']} prompt {name}: {'valid' if result['valid'] else 'INVALID'}, "
                  f"{len(attempts)} attempt(s), {last['seconds']} s")


if __name__ == "__main__":
    run()
