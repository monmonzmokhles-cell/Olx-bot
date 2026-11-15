import os
import re
import sys
import json
import time
import requests
from urllib.parse import quote, unquote

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
BASE = "https://www.dubizzle.com.eg"
SEEN_FILE = "seen_ads.json"

# كلمات البحث
SEARCHES = [
    "Nintendo 3ds",
    "نينتندو",
    "Nintendo new 3ds xl",
    "Nintendo new 3ds",
    "Nintendo new 2ds xl",
    "New 3ds xl",
]

# أي إعلان عنوانه فيه واحدة من الكلمات دي بيتتجاهل (إعلانات "مطلوب")
EXCLUDE = ["مطلوب", "مطلوبة", "wanted", "wtb", "looking for", "ابحث عن", "محتاج"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
}


def search_url(q):
    return f"{BASE}/en/ads/q-{quote(q.strip().replace(' ', '-'))}/"


def is_excluded(title):
    t = title.lower()
    return any(w in t for w in EXCLUDE)


def fetch_ads(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    paths = re.findall(
        r'href="(?:https://www\.dubizzle\.com\.eg)?(/(?:en|ar)/ad/[^"#?]+)"', r.text
    )
    ads = {}
    for p in paths:
        m = re.search(r"ID(\d+)", p)
        key = m.group(1) if m else p
        slug = unquote(p.rstrip("/").split("/")[-1])
        title = re.sub(r"-ID\d+.*$", "", slug).replace(".html", "")
        title = title.replace("-", " ").title()
        if is_excluded(title):
            continue
        ads[key] = {"title": title, "url": BASE + p}
    return ads


def send(text):
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=30,
    )


def main():
    first_run = not os.path.exists(SEEN_FILE)
    seen = set()
    if not first_run:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            seen = set(json.load(f))

    all_ads = {}
    failures = 0
    for q in SEARCHES:
        try:
            ads = fetch_ads(search_url(q))
            print(f"[{q}] {len(ads)} ads")
            all_ads.update(ads)
        except Exception as e:
            failures += 1
            print(f"[{q}] ERROR: {e}")
        time.sleep(2)

    if failures == len(SEARCHES):
        print("All searches failed (maybe blocked).")
        sys.exit(1)

    if not first_run:
        for k, ad in all_ads.items():
            if k not in seen:
                send(f"🎮 إعلان جديد!\n{ad['title']}\n{ad['url']}")
                print("Sent:", ad["title"])

    seen.update(all_ads.keys())
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f)


if __name__ == "__main__":
    main()
