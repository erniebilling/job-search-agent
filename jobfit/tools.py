import json
import logging

import requests
from agents import function_tool

from jobfit.config import MAX_SCRAPED_CHARS, MAX_SEARCH_RESULTS, OPENSERP_BASE_URL

log = logging.getLogger(__name__)


@function_tool
def search_jobs(query: str, limit: int = MAX_SEARCH_RESULTS) -> str:
    """Search the web for job listings and return compact JSON results."""
    safe_limit = max(1, min(int(limit), MAX_SEARCH_RESULTS))
    log.info("search_jobs query=%r limit=%d", query, safe_limit)
    response = requests.get(
        f"{OPENSERP_BASE_URL}/mega/search",
        params={"text": query, "limit": safe_limit},
        timeout=60,
    )
    response.raise_for_status()
    links = response.json().get("results", [])[:safe_limit]
    results = [
        {"title": item.get("title", "Untitled"), "url": item.get("url"), "description": item.get("snippet", "")}
        for item in links
        if isinstance(item, dict) and item.get("url")
    ]
    log.info("search_jobs query=%r returned %d usable results (of %d raw)", query, len(results), len(links))
    return json.dumps(results, ensure_ascii=False)


@function_tool
def read_job_page(url: str) -> str:
    """Scrape one job listing URL and return markdown text."""
    log.info("read_job_page url=%s", url)
    try:
        response = requests.get(
            f"{OPENSERP_BASE_URL}/extract",
            params={"url": url, "format": "markdown"},
            timeout=120,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        log.warning("read_job_page failed url=%s error=%s", url, exc)
        return ""
    text = response.text[:MAX_SCRAPED_CHARS]
    log.info("read_job_page url=%s fetched %d chars (truncated to %d)", url, len(response.text), len(text))
    return text
