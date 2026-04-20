"""Configuration centrale : sources RSS, clés API, paramètres."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=True)
LOG_DIR = ROOT_DIR / "logs"
CACHE_FILE = ROOT_DIR / "posted_urls.json"

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_USER_URN = os.getenv("LINKEDIN_USER_URN")

RSS_FEEDS = {
    "cybersecurity": [
        "https://www.bleepingcomputer.com/feed/",
        "https://thehackernews.com/feeds/posts/default",
        "https://krebsonsecurity.com/feed/",
        "https://www.darkreading.com/rss.xml",
    ],
    "ai": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "https://venturebeat.com/category/ai/feed/",
    ],
}

NEWSAPI_QUERIES = [
    "artificial intelligence OR GenAI OR LLM",
    "cybersecurity OR ransomware OR data breach OR zero-day",
]

LOOKBACK_HOURS = 24
MAX_ARTICLES_PER_SOURCE = 15
