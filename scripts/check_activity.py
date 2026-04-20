import os
import sys
import requests
from datetime import datetime, timezone

GH_TOKEN = os.environ["GH_TOKEN"]
LAST_RUN_UTC = sys.argv[1] if len(sys.argv) > 1 else "1970-01-01T00:00:00Z"
USERNAME = "Carlos-Espitia"

resp = requests.get(
    f"https://api.github.com/users/{USERNAME}/repos",
    headers={"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"},
    params={"sort": "pushed", "per_page": 10},
)
resp.raise_for_status()

repos = [r for r in resp.json() if r["name"] != USERNAME]
pushed_at = repos[0]["pushed_at"] if repos else "1970-01-01T00:00:00Z"

last_run = datetime.fromisoformat(LAST_RUN_UTC.replace("Z", "+00:00"))
pushed = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))

print("true" if pushed > last_run else "false")
