import os

OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
# Used to write the final report after search_agent hands off. Report writing
# is one large generation over the full accumulated context (all search
# results plus every scraped page), the single most expensive turn in the
# whole run, where raw throughput matters more than the extra judgment a
# bigger model brings to picking search queries and urls one at a time.
# Defaults to OLLAMA_MODEL so a single model is used end to end unless this is
# set explicitly.
OLLAMA_REPORT_MODEL = os.environ.get("OLLAMA_REPORT_MODEL", OLLAMA_MODEL)
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1")
OPENSERP_BASE_URL = os.environ.get("OPENSERP_BASE_URL", "https://openserp.broken-top.com")
DB_PATH = os.environ.get("DB_PATH", "jobfit.db")

MAX_AGENT_TURNS = 25
MAX_SEARCH_RESULTS = 10
MAX_SEARCH_CALLS = 3
MAX_PAGE_READS = 5
MAX_SCRAPED_CHARS = 8000

# A model can keep retrying read_job_page on a url it has already read,
# getting the "already read" block every time without ever hitting
# MAX_PAGE_READS (that only counts successful new reads). One real run did
# this 15 times in a row until MaxTurnsExceeded killed it. After this many
# consecutive repeat-url blocks, read_job_page is disabled the same way it is
# once MAX_PAGE_READS is reached, since keeping it available is not leading
# anywhere new.
MAX_CONSECUTIVE_REPEAT_READ_BLOCKS = 2

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
