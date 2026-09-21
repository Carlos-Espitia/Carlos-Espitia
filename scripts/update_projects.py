import os
import re
import base64
import requests
import anthropic
from datetime import datetime

from badges import badge_row

GH_TOKEN = os.environ["GH_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
USERNAME = "Carlos-Espitia"
README_PATH = "README.md"
NUM_PROJECTS = 5

# Hand-picked projects that lead the profile. Descriptions are regenerated from
# each repo's README, file tree and latest commits on every run, so shipping new
# work is enough to update this section -- only the list itself is maintained here.
FEATURED = [
    {
        "repo": "QA-voice-agent-analyzer",
        "title": "QA Voice Agent Analyzer",
        "emoji": "🎙️",
        "tech": ["Python", "FastAPI", "Twilio", "Deepgram", "Claude API", "ElevenLabs"],
    },
    {
        "repo": "SEC-financial-insights",
        "title": "SEC Financial Insights",
        "emoji": "📊",
        "tech": ["Python", "Claude API", "ChromaDB", "LangChain", "Streamlit"],
    },
    {
        # Source is private; the public releases repo is what visitors can open.
        "repo": "jobomatic",
        "link_repo": "jobomatic-releases",
        "title": "Jobomatic",
        "emoji": "🤖",
        "tech": ["Python", "Playwright", "Electron", "React", "Claude API"],
    },
    {
        "repo": "financial-backtester-v2",
        "title": "Quant Research Tool",
        "emoji": "📈",
        "tech": ["Python", "FastAPI", "TypeScript", "React", "Electron", "DuckDB"],
    },
]

gh_headers = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github+json",
}

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def get_repo(full_name):
    resp = requests.get(f"https://api.github.com/repos/{full_name}", headers=gh_headers)
    return resp.json() if resp.status_code == 200 else None


def get_recent_repos():
    url = f"https://api.github.com/users/{USERNAME}/events"
    resp = requests.get(url, headers=gh_headers, params={"per_page": 100})
    resp.raise_for_status()

    seen = {}
    for event in resp.json():
        etype = event["type"]
        is_push = etype == "PushEvent"
        is_create = (
            etype == "CreateEvent"
            and event.get("payload", {}).get("ref_type") == "repository"
        )
        if not (is_push or is_create):
            continue
        repo = event["repo"]
        name = repo["name"]  # format: "owner/repo"
        if name == f"{USERNAME}/{USERNAME}":
            continue
        # Events come newest-first, so the first time we see a repo is its most
        # recent activity (either a push or the repo's creation).
        if name not in seen:
            seen[name] = event["created_at"]

    repo_names = list(seen.keys())[:NUM_PROJECTS]

    repos = []
    for full_name in repo_names:
        repo = get_repo(full_name)
        if repo:
            repos.append(repo)
    return repos


def get_file_tree(full_name, default_branch):
    url = f"https://api.github.com/repos/{full_name}/git/trees/{default_branch}"
    resp = requests.get(url, headers=gh_headers, params={"recursive": "1"})
    if resp.status_code != 200:
        return []
    items = resp.json().get("tree", [])
    return [item["path"] for item in items if item["type"] == "blob"]


def get_readme(full_name, limit=4000):
    resp = requests.get(f"https://api.github.com/repos/{full_name}/readme", headers=gh_headers)
    if resp.status_code != 200:
        return ""
    content = resp.json().get("content", "")
    try:
        return base64.b64decode(content).decode("utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def get_languages(full_name):
    url = f"https://api.github.com/repos/{full_name}/languages"
    resp = requests.get(url, headers=gh_headers)
    if resp.status_code != 200:
        return []
    # Returns {"Python": bytes, "HTML": bytes, ...}; sort by bytes descending
    # so the dominant language comes first.
    langs = resp.json()
    return sorted(langs, key=langs.get, reverse=True)


def get_recent_commits(full_name, count=3):
    url = f"https://api.github.com/repos/{full_name}/commits"
    resp = requests.get(url, headers=gh_headers, params={"per_page": count, "author": USERNAME})
    if resp.status_code != 200:
        return []
    commits = []
    for c in resp.json():
        msg = c["commit"]["message"].split("\n")[0]
        date_str = c["commit"]["author"]["date"]
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        commits.append({"message": msg, "date": dt})
    return commits


def format_date(dt):
    return dt.strftime("%b %d, %Y")


def ask_claude(prompt, max_tokens):
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def generate_description(repo_name, stack, file_paths):
    tree_text = "\n".join(file_paths[:60]) if file_paths else "No files found."
    prompt = f"""You are writing a short project description for a GitHub profile README.

    Repo: {repo_name}
    Languages used: {stack or "unknown"}
    File tree:
    {tree_text}

    Write ONE concise sentence describing what this project does based on the repo name and file structure. Be specific, not generic. No quotes."""
    return ask_claude(prompt, max_tokens=60)


def generate_featured_blurb(title, tech, readme, file_paths, commits):
    tree_text = "\n".join(file_paths[:80]) if file_paths else "No files found."
    commit_text = "\n".join(f"- {c['message']}" for c in commits) or "No commits found."
    prompt = f"""You are writing the blurb for a featured project on a software engineer's GitHub profile README. This is portfolio copy aimed at recruiters and engineers.

    Project: {title}
    Stack: {", ".join(tech)}

    The project's README:
    ---
    {readme or "No README available."}
    ---

    File tree:
    {tree_text}

    Most recent commits:
    {commit_text}

    Write 2-3 sentences (max 65 words) describing what this project does and what is technically impressive about it. Lead with the substance, not the name. Preserve any concrete numbers from the README (accuracy rates, counts, latency) exactly as stated -- never invent metrics. Plain prose, no markdown, no bullet points, no quotes."""
    return ask_claude(prompt, max_tokens=220)


def build_featured():
    blocks = []
    for entry in FEATURED:
        full_name = f"{USERNAME}/{entry['repo']}"
        repo = get_repo(full_name)
        if repo is None:
            continue

        branch = repo.get("default_branch", "main")
        readme = get_readme(full_name)
        file_paths = get_file_tree(full_name, branch)
        commits = get_recent_commits(full_name)
        blurb = generate_featured_blurb(entry["title"], entry["tech"], readme, file_paths, commits)

        # A private repo 404s for visitors: link an explicit public mirror if the
        # entry names one, otherwise show the title unlinked with a lock.
        link_repo = entry.get("link_repo")
        if link_repo:
            link = f"https://github.com/{USERNAME}/{link_repo}"
            heading = f"**{entry['emoji']} [{entry['title']}]({link})**"
        elif repo["private"]:
            heading = f"**{entry['emoji']} {entry['title']}** 🔒"
        else:
            heading = f"**{entry['emoji']} [{entry['title']}]({repo['html_url']})**"

        blocks.append(f"{heading}  \n{badge_row(entry['tech'])}  \n{blurb}")

    return "\n\n".join(blocks)


def build_section(repos):
    lines = ["| Project | Stack | Description | Recent Commits |", "|---|---|---|---|"]
    for repo in repos:
        name = repo["name"]
        private = repo["private"]
        url = repo["html_url"]
        branch = repo.get("default_branch", "main")

        full_name = repo["full_name"]
        languages = get_languages(full_name)
        stack = ", ".join(languages) if languages else (repo["language"] or "—")

        file_paths = get_file_tree(full_name, branch)
        description = generate_description(name, stack, file_paths)
        commits = get_recent_commits(full_name)

        # Private repos 404 for visitors, so name them without a link.
        project_cell = f"🔒 {name}" if private else f"[{name}]({url})"

        if commits:
            commits_cell = "<br>".join(
                f"`{c['message'][:50]}` · {format_date(c['date'])}"
                for c in commits
            )
        else:
            commits_cell = "—"

        lines.append(f"| {project_cell} | {stack} | {description} | {commits_cell} |")

    return "\n".join(lines)


def replace_block(content, marker, body):
    return re.sub(
        rf"<!-- {marker}:START -->.*?<!-- {marker}:END -->",
        f"<!-- {marker}:START -->\n{body}\n<!-- {marker}:END -->",
        content,
        flags=re.DOTALL,
    )


def update_readme(featured_md, section_md):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    content = replace_block(content, "FEATURED", featured_md)
    content = replace_block(content, "PROJECTS", section_md)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("README updated.")


if __name__ == "__main__":
    featured = build_featured()
    repos = get_recent_repos()
    section = build_section(repos)
    update_readme(featured, section)
