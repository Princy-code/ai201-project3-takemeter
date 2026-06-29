"""prelabel.py - Groq suggests a label per post to speed your review. You fix every wrong one."""
import csv, os, time
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MODEL = "llama-3.3-70b-versatile"

SYSTEM = """You classify a single r/LocalLLaMA post into exactly one label.

analysis = a structured argument backed by specific, verifiable evidence
  (benchmarks, numbers, configs, technical reasoning). The evidence would still
  support the point even if the opinion framing were removed.
hot_take = a bold, confident opinion stated WITHOUT real evidence; it asserts
  rather than argues. Includes posts that drop one cherry-picked stat for effect.
reaction = an immediate emotional response to an event (a release, a leak, a
  paper drop); little to no argument.

Reply with ONLY one word: analysis, hot_take, or reaction."""

def label_one(text):
    for attempt in range(3):
        try:
            r = client.chat.completions.create(
                model=MODEL, temperature=0, max_tokens=4,
                messages=[{"role": "system", "content": SYSTEM},
                          {"role": "user", "content": text[:1500]}],
            )
            out = r.choices[0].message.content.strip().lower()
            for lab in ("analysis", "hot_take", "reaction"):
                if lab in out:
                    return lab
            return "reaction"
        except Exception as e:
            print("  retry:", e)
            time.sleep(8)
    return ""

rows = list(csv.DictReader(open("data/raw_posts.csv", encoding="utf-8")))
with open("data/to_label.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["text", "label", "suggested", "notes"])
    for i, row in enumerate(rows, 1):
        s = label_one(row["text"])
        w.writerow([row["text"], s, s, ""])
        if i % 20 == 0:
            print(f"  {i}/{len(rows)}")
        time.sleep(1.0)

print("\nDone -> data/to_label.csv")
print("NOW REVIEW: open it, read each post, fix any wrong 'label'.")
