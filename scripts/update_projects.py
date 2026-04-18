import os
import re
import requests
import anthropic

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
    url = f"https://api.github.com/user/repos"
    params = {"sort": "pushed", "per_page": 20, "affiliation": "owner"}
    resp = requests.get(url, headers=gh_headers, params=params)
    resp.raise_for_status()
    repos = [r for r in resp.json() if r["name"] != USERNAME]
    return repos[:NUM_PROJECTS]


def get_recent_commits(repo_name, count=5):
    url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/commits"
    params = {"per_page": count}
    resp = requests.get(url, headers=gh_headers, params=params)
    if resp.status_code != 200:
        return []
    return [c["commit"]["message"].split("\n")[0] for c in resp.json()]


def generate_description(repo_name, language, commits):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    commits_text = "\n".join(f"- {c}" for c in commits) if commits else "No recent commits."
    prompt = f"""You are writing a short project description for a GitHub profile README.

Repo: {repo_name}
Primary language: {language or "unknown"}
Recent commits:
{commits_text}

Write ONE concise sentence (max 12 words) describing what this project does based on the repo name and commits. Be specific, not generic. No quotes."""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=60,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def build_table(repos):
    rows = ["| Project | Description | Stack |", "|---|---|---|"]
    for repo in repos:
        name = repo["name"]
        language = repo["language"] or "—"
        private = repo["private"]
        url = repo["html_url"]

        commits = get_recent_commits(name)
        description = generate_description(name, language, commits)

        if private:
            project_cell = f"🔒 {name}"
        else:
            project_cell = f"[{name}]({url})"

        rows.append(f"| {project_cell} | {description} | {language} |")

    return "\n".join(rows)


def update_readme(table_md):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    new_block = f"<!-- PROJECTS:START -->\n{table_md}\n<!-- PROJECTS:END -->"
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
    table = build_table(repos)
    update_readme(table)
