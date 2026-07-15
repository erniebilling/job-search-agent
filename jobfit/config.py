import os

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
OPENSERP_BASE_URL = os.environ.get("OPENSERP_BASE_URL", "https://openserp.broken-top.com")
DB_PATH = os.environ.get("DB_PATH", "jobfit.db")

MAX_AGENT_TURNS = 25
MAX_SEARCH_RESULTS = 10
MAX_PAGE_READS = 5
MAX_SCRAPED_CHARS = 8000
