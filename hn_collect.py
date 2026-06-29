"""hn_collect.py - collect ~250 Hacker News comments via the free Algolia API. No auth."""
import csv, html, re, time, requests

URL = "https://hn.algolia.com/api/v1/search_by_date"
MIN_W, MAX_W = 5, 200
TARGET = 260
seen = {}

def clean(t):
    t = html.unescape(t or "")
    t = re.sub(r"<[^>]+>", " ", t)     # strip HTML tags
    t = re.sub(r"http\S+", "", t)      # strip urls
    t = re.sub(r"\s+", " ", t).strip()
    return t

def add(t):
    t = clean(t)
    if not t:
        return
    n = len(t.split())
    if n < MIN_W or n > MAX_W:
        return
    k = t.lower()[:120]
    if k not in seen:
        seen[k] = t

# mix of topical queries + general recent comments for varied discourse
queries = ["AI", "LLM", "open source", "Rust", "startup", "model", "Python", "Apple", ""]
for q in queries:
    for page in range(2):
        params = {"tags": "comment", "hitsPerPage": 100, "page": page}
        if q:
            params["query"] = q
        try:
            r = requests.get(URL, params=params, timeout=25)
            if r.status_code != 200:
                print(f"  [{r.status_code}] skip {q!r} p{page}")
                continue
            for h in r.json().get("hits", []):
                add(h.get("comment_text"))
        except Exception as e:
            print("  err:", e)
        time.sleep(1)
    if len(seen) >= TARGET:
        break

import os
os.makedirs("data", exist_ok=True)
out = "data/raw_posts.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["text", "label", "notes"])
    for text in seen.values():
        w.writerow([text, "", ""])

print(f"\nDone. Collected {len(seen)} comments -> {out}")
