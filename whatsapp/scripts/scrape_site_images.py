"""Scrape image URLs from the official marketing site."""
import re
import urllib.request

SITE = "https://srivatsanka.com/"
html = urllib.request.urlopen(SITE, timeout=30).read().decode("utf-8", "ignore")
urls = sorted(set(re.findall(r"https?://[^\s\"'<>]+\.(?:jpg|jpeg|png|webp)", html, re.I)))
uploads = [
    u
    for u in urls
    if "wp-content/uploads" in u.lower()
    and "srivatsanka.com" in u.lower()
    and not re.search(r"-\d+x\d+\.", u)
    and "logo" not in u.lower()
    and "favicon" not in u.lower()
    and "qr-code" not in u.lower()
]
print(f"full-size uploads from {SITE}: {len(uploads)}")
for u in uploads:
    print(u)
