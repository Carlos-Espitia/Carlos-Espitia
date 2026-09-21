"""Shared shields.io badge rendering so every section of the README looks alike.

One visual language: coloured logo badges for concrete tech, flat grey badges for
concepts that have no logo (AI engineering, quant research).
"""

from urllib.parse import quote

NEUTRAL_COLOR = "4B5563"

# name -> (hex color, shields logo slug or None, logo color)
TECH = {
    "Python": ("3776AB", "python", "white"),
    "TypeScript": ("3178C6", "typescript", "white"),
    "JavaScript": ("F7DF1E", "javascript", "black"),
    "Java": ("ED8B00", "openjdk", "white"),
    "SQL": ("4479A1", "mysql", "white"),
    "C++": ("00599C", "cplusplus", "white"),
    "PHP": ("777BB4", "php", "white"),
    "CSS": ("1572B6", "css3", "white"),
    "HTML": ("E34F26", "html5", "white"),
    "PowerShell": ("5391FE", "powershell", "white"),
    "FastAPI": ("009688", "fastapi", "white"),
    "React": ("61DAFB", "react", "black"),
    "Node.js": ("339933", "node.js", "white"),
    "Express.js": ("000000", "express", "white"),
    "Electron": ("47848F", "electron", "white"),
    "LangChain": ("1C3C3C", "langchain", "white"),
    "Streamlit": ("FF4B4B", "streamlit", "white"),
    "Playwright": ("2EAD33", "playwright", "white"),
    "Pandas": ("150458", "pandas", "white"),
    "NumPy": ("013243", "numpy", "white"),
    "scikit-learn": ("F7931E", "scikit-learn", "white"),
    "DuckDB": ("FFF000", "duckdb", "black"),
    "MongoDB": ("47A248", "mongodb", "white"),
    "ChromaDB": ("FF6B35", None, "white"),
    "Claude API": ("D97757", "anthropic", "white"),
    "Twilio": ("F22F46", "twilio", "white"),
    "Deepgram": ("13EF93", None, "black"),
    "ElevenLabs": ("000000", "elevenlabs", "white"),
    "WebSockets": ("010101", "socketdotio", "white"),
    "AWS": ("232F3E", "amazon-aws", "white"),
    "Git": ("F05032", "git", "white"),
    "Grafana": ("F46800", "grafana", "white"),
    "Sentry": ("362D59", "sentry", "white"),
    "Jira": ("0052CC", "jira", "white"),
    "Confluence": ("172B4D", "confluence", "white"),
    "Optuna": ("2B6CB0", None, "white"),
    "SSE": ("6B7280", None, "white"),
    "LaTeX": ("008080", "latex", "white"),
}


def _escape(text):
    """shields.io path escaping: '-' -> '--', '_' -> '__', then URL-encode."""
    return quote(text.replace("-", "--").replace("_", "__"), safe="")


def badge(name, color=None, logo=None, logo_color=None):
    """Render one shields.io badge for `name`, looking up known tech by default."""
    known = TECH.get(name)
    if known:
        default_color, default_logo, default_logo_color = known
    else:
        default_color, default_logo, default_logo_color = NEUTRAL_COLOR, None, "white"

    color = color or default_color
    logo = logo if logo is not None else default_logo
    logo_color = logo_color or default_logo_color

    url = f"https://img.shields.io/badge/{_escape(name)}-{color}?style=flat"
    if logo:
        url += f"&logo={quote(logo, safe='')}&logoColor={logo_color}"
    return f"![{name}]({url})"


def badge_row(names, **kwargs):
    """Render a space-joined row of badges."""
    return " ".join(badge(n, **kwargs) for n in names)
