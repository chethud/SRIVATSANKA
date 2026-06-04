import re
import urllib.request

h = urllib.request.urlopen("https://kannansharangapani.com/", timeout=20).read().decode("utf-8", "ignore")
urls = sorted(set(re.findall(r"https?://[^\s\"'<>]+\.(?:jpg|jpeg|png|webp)", h, re.I)))
for u in urls[:25]:
    print(u)
