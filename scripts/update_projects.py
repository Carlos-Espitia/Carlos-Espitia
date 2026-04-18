import os
import re
import requests
import anthropic
from datetime import datetime, timezone

GH_TOKEN = os.environ["GH_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
USERNAME = "Carlos-Espitia"
README_PATH = "README.md"
NUM_PROJECTS = 5

gh_headers = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
}


def get_recent_repos():
    url = "https://api.github.com/user/repos"
    params = {"sort": "pushed", "per_page": 20, "affiliation": "owner"}
    resp = requests.get(url, headers=gh_headers, params=params)
    resp.raise_for_status()
    repos = [r for r in resp.json() if r["name"] != USERNAME]
    return repos[:NUM_PROJECTS]


def get_file_tree(repo_name, default_branch):
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/git/trees/{default_branch}"
    resp = requests.get(url, headers=gh_headers, params={"recursive": "1"})
    if resp.status_code != 200:
        return []
    items = resp.json().get("tree", [])
    return [item["path"] for item in items if item["type"] == "blob"]


def get_recent_commits(repo_name, count=3):
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/commits"
    resp = requests.get(url, headers=gh_headers, params={"per_page": count})
    if resp.status_code != 200:
        return []
    commits = []
    for c in resp.json():
        msg = c["commit"]["message"].split("\n")[0]
        date_str = c["commit"]["author"]["date"]
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        commits.append({"message": msg, "date": dt})
    return commits


def relative_date(dt):
    now = datetime.now(timezone.utc)
    delta = now - dt
    days = delta.days
    if days == 0:
        hours = delta.seconds // 3600
        return f"{hours}h ago" if hours > 0 else "just now"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days}d ago"
    if days < 30:
        return f"{days // 7}w ago"
    return dt.strftime("%b %d, %Y")


def generate_description(repo_name, language, file_paths):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    tree_text = "\n".join(file_paths[:60]) if file_paths else "No files found."
    prompt = f"""You are writing a short project description for a GitHub profile README.

Repo: {repo_name}
Primary language: {language or "unknown"}
File tree:
{tree_text}

Write ONE concise sentence (max 12 words) describing what this project does based on the repo name and file structure. Be specific, not generic. No quotes."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=60,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def build_section(repos):
    lines = ["| Project | Stack | Description | Recent Commits |", "|---|---|---|---|"]
    for repo in repos:
        name = repo["name"]
        language = repo["language"] or "—"
        private = repo["private"]
        url = repo["html_url"]
        branch = repo.get("default_branch", "main")

        file_paths = get_file_tree(name, branch)
        description = generate_description(name, language, file_paths)
        commits = get_recent_commits(name)

        project_cell = f"🔒 {name}" if private else f"[{name}]({url})"

        if commits:
            commits_cell = "<br>".join(
                f"`{c['message'][:50]}` · {relative_date(c['date'])}"
                for c in commits
            )
        else:
            commits_cell = "—"

        lines.append(f"| {project_cell} | {language} | {description} | {commits_cell} |")

    return "\n".join(lines)


def update_readme(section_md):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    new_block = f"<!-- PROJECTS:START -->\n{section_md}\n<!-- PROJECTS:END -->"
    updated = re.sub(
        r"<!-- PROJECTS:START -->.*?<!-- PROJECTS:END -->",
        new_block,
        content,
        flags=re.DOTALL,
    )

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(updated)

    print("README updated.")


if __name__ == "__main__":
    repos = get_recent_repos()
    section = build_section(repos)
    update_readme(section)
