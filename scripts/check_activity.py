import os
import sys
import requests
from datetime import datetime

GH_TOKEN = os.environ["GH_TOKEN"]
LAST_RUN_UTC = sys.argv[1] if len(sys.argv) > 1 else "1970-01-01T00:00:00Z"
USERNAME = "Carlos-Espitia"

resp = requests.get(
    f"https://api.github.com/users/{USERNAME}/events",
    headers={"Authorization": f"Bearer {GH_TOKEN}", "Accept": "application/vnd.github+json"},
    params={"per_page": 30},
)
resp.raise_for_status()

last_run = datetime.fromisoformat(LAST_RUN_UTC.replace("Z", "+00:00"))

changed = False
for event in resp.json():
    if event["type"] != "PushEvent":
        continue
    if event["repo"]["name"] == f"{USERNAME}/{USERNAME}":
        continue
    created = datetime.fromisoformat(event["created_at"].replace("Z", "+00:00"))
    if created > last_run:
        changed = True
        break

print("true" if changed else "false")
