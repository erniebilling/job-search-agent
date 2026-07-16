import os

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
OPENSERP_BASE_URL = os.environ.get("OPENSERP_BASE_URL", "https://openserp.broken-top.com")
DB_PATH = os.environ.get("DB_PATH", "jobfit.db")

MAX_AGENT_TURNS = 25
MAX_SEARCH_RESULTS = 10
MAX_SEARCH_CALLS = 3
MAX_PAGE_READS = 5
MAX_SCRAPED_CHARS = 8000

# The openai client's default read timeout (600s) is shorter than a single
# prompt-processing pass can legitimately take on this hardware (observed up
# to ~20 min on a long context). llama-server has no way to cancel a request
# once the client stops waiting, so a client-side timeout does not free up
# the slot: the abandoned request keeps running server-side while the retry
# grabs a second slot, and the two compete for the same CPU threads, which
# was the actual cause of the "parallel requests" seen in llama-server logs.
# This is set high enough that a real reply is normally waited out instead
# of triggering a duplicate.
OLLAMA_TIMEOUT_SECONDS = 2400
