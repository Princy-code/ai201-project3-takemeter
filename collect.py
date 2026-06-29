"""collect.py - gather ~250 public r/LocalLLaMA posts + comments into a CSV."""
import csv, html, os, re, time, requests

SUB = "LocalLLaMA"
UA = {"User-Agent": "takemeter:v0.1 (course project)"}
TARGET = 250
MIN_WORDS, MAX_WORDS = 5, 200
seen = {}

def clean(t):
    t = html.unescape(t or "")
    t = re.sub(r"http\S+", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def add(text):
    text = clean(text)
    if not text:
        return
    n = len(text.split())
    if n < MIN_WORDS or n > MAX_WORDS:
        return
    key = text.lower()[:120]
    if key not in seen:
        seen[key] = text

def get(url, params=None):
    for attempt in range(4):
        r = requests.get(url, headers=UA, params=params, timeout=25)
        if r.status_code == 200:
            return r.json()
        print(f"  [{r.status_code}] retrying...")
        time.sleep(3 * (attempt + 1))
    return None

permalinks = []
for sort, t in [("top", "year"), ("top", "month"), ("hot", None), ("new", None), ("rising", None)]:
    after = None
    for _ in range(3):
        params = {"limit": 100}
        if t: params["t"] = t
        if after: params["after"] = after
        data = get(f"https://www.reddit.com/r/{SUB}/{sort}.json", params)
        if not data:
            break
        d = data["data"]
        after = d.get("after")
        for ch in d["children"]:
            p = ch["data"]
            body = p.get("title", "")
            if p.get("selftext"):
                body += ". " + p["selftext"]
            add(body)
            if p.get("permalink"):
                permalinks.append(p["permalink"])
        if not after:
            break
        time.sleep(2)
    if len(seen) >= TARGET:
        break

for link in permalinks[:40]:
    if len(seen) >= TARGET:
        break
    data = get(f"https://www.reddit.com{link}.json", {"limit": 15, "depth": 1})
    if not data or len(data) < 2:
        continue
    for ch in data[1]["data"]["children"]:
        c = ch.get("data", {})
        if c.get("body"):
            add(c["body"])
    time.sleep(1.5)

os.makedirs("data", exist_ok=True)
out = "data/raw_posts.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["text", "label", "notes"])
    for text in seen.values():
        w.writerow([text, "", ""])

print(f"\nDone. Collected {len(seen)} examples -> {out}")
if len(seen) < 200:
    print("Got fewer than 200. Re-run in a minute, or tell Claude to switch to PRAW.")
