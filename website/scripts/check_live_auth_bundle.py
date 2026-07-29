from pathlib import Path
import re

html = Path("/home/ubuntu/srivatsanka/website/dist/index.html").read_text()
print(html)
m = re.search(r"/assets/(index-[^\"]+\.js)", html)
print("bundle", m.group(1) if m else None)
if m:
    t = (Path("/home/ubuntu/srivatsanka/website/dist/assets") / m.group(1)).read_text(errors="ignore")
    print("has_project_host", "hlzndlmcvpmsxzkawsbz" in t)
    print("has_supabase_account_copy", "Sign in with your Supabase account" in t)
    print("has_dashboard_copy", "SRIVATSANKA EVENTS dashboard" in t)
