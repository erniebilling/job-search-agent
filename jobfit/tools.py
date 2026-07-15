import json

import requests
from agents import function_tool

from jobfit.config import MAX_SCRAPED_CHARS, MAX_SEARCH_RESULTS, OPENSERP_BASE_URL


@function_tool
def search_jobs(query: str, limit: int = MAX_SEARCH_RESULTS) -> str:
    """Search the web for job listings and return compact JSON results."""
    safe_limit = max(1, min(int(limit), MAX_SEARCH_RESULTS))
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
    return json.dumps(results, ensure_ascii=False)


@function_tool
def read_job_page(url: str) -> str:
    """Scrape one job listing URL and return markdown text."""
    try:
        response = requests.get(
            f"{OPENSERP_BASE_URL}/extract",
            params={"url": url, "format": "markdown"},
            timeout=120,
        )
        response.raise_for_status()
    except requests.RequestException:
        return ""
    return response.text[:MAX_SCRAPED_CHARS]
