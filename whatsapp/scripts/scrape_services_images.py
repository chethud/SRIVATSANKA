"""Scrape service-page photos and write dashboard + WhatsApp gallery data."""
from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

PAGES = [
    ("https://srivatsanka.com/services/", "traditional"),
    ("https://srivatsanka.com/catering/", "catering"),
    ("https://srivatsanka.com/services/wedding-decoration/", "decor"),
    ("https://srivatsanka.com/event-ritual-support/", "rituals"),
    ("https://srivatsanka.com/services/wedding-venues/", "venues"),
]

SKIP = re.compile(
    r"logo|favicon|qr-code|sprite|icon|avatar|placeholder|gravatar|semi-white|cta-img|footer-img|\.js$",
    re.I,
)
SIZED = re.compile(r"-\d+x\d+\.")
ABS_IMG = re.compile(r"https?://[^\s\"'<>]+\.(?:jpg|jpeg|png|webp)", re.I)
REL_IMG = re.compile(
    r"""(?:src|data-src|data-lazy-src|data-bg)=["']([^"']+wp-content/uploads[^"']+)""",
    re.I,
)

ROOT = Path(__file__).resolve().parents[2]
WHATSAPP_JSON = ROOT / "whatsapp" / "app" / "data" / "service_photos.json"
FRONTEND_TS = ROOT / "website" / "src" / "data" / "servicePhotos.ts"


def normalize(url: str) -> str:
    url = url.split("?")[0].strip()
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://srivatsanka.com" + url
    return url


def caption_for(url: str, category: str) -> str:
    name = Path(url).stem.replace("-Copy", "").replace("-scaled", "").replace("_", " ")
    name = re.sub(r"-\d+$", "", name)
    name = re.sub(r"\s+", " ", name.replace("-", " ")).strip()
    if name.lower().startswith("img") or name.replace(" ", "").isdigit():
        labels = {
            "catering": "Traditional catering",
            "decor": "Traditional décor",
            "rituals": "Traditional pooja / ritual setup",
            "venues": "Celebration venue",
            "traditional": "Traditional celebration",
        }
        return labels.get(category, "Traditional celebration")
    pretty = name
    pretty = re.sub(r"(?i)^weddings?\s*", "Wedding ", pretty)
    pretty = re.sub(r"(?i)^decors?\s*", "Décor ", pretty)
    pretty = re.sub(r"(?i)^events?\s*", "Venue ", pretty)
    pretty = pretty.replace("img", "").strip() or name
    return pretty[:1].upper() + pretty[1:]


def stem_key(url: str) -> str:
    name = Path(url).name.lower()
    name = re.sub(r"-scaled\.(jpg|jpeg|png|webp)$", r".\1", name)
    name = re.sub(r"\.(jpg|jpeg|png|webp)$", "", name)
    return name


found: dict[str, str] = {}
for page, category in PAGES:
    req = urllib.request.Request(page, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    urls = ABS_IMG.findall(html) + REL_IMG.findall(html)
    for u in urls:
        u = normalize(u)
        if "wp-content/uploads" not in u.lower():
            continue
        if SKIP.search(u) or SIZED.search(u):
            continue
        if not re.search(r"\.(jpg|jpeg|png|webp)$", u, re.I):
            continue
        found.setdefault(u, category)

# Drop webp when a jpg/png of the same stem exists
stems: dict[str, list[str]] = {}
for url in found:
    stems.setdefault(stem_key(url), []).append(url)
keep: list[str] = []
for urls in stems.values():
    preferred = [u for u in urls if not u.lower().endswith(".webp")] or urls
    keep.append(sorted(preferred)[0])

items = []
seen = set()
for url in sorted(keep, key=lambda u: (found[u], u)):
    if url in seen:
        continue
    seen.add(url)
    category = found[url]
    items.append({"url": url, "caption": caption_for(url, category), "category": category})

WHATSAPP_JSON.parent.mkdir(parents=True, exist_ok=True)
WHATSAPP_JSON.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")

lines = [
    "/** Photos scraped from https://srivatsanka.com/services/ and linked service pages. */",
    "export const SERVICE_PHOTOS: { url: string; caption: string; category: string }[] = [",
]
for item in items:
    url = item["url"].replace("'", "\\'")
    cap = item["caption"].replace("'", "\\'")
    cat = item["category"]
    lines.append(f"  {{ url: '{url}', caption: '{cap}', category: '{cat}' }},")
lines.append("];")
lines.append("")
FRONTEND_TS.write_text("\n".join(lines), encoding="utf-8")
print(f"wrote {len(items)} photos")
print(WHATSAPP_JSON)
print(FRONTEND_TS)
