import json
import logging

import requests
from agents import RunContextWrapper, function_tool

from jobfit.config import MAX_PAGE_READS, MAX_SCRAPED_CHARS, MAX_SEARCH_CALLS, MAX_SEARCH_RESULTS, OPENSERP_BASE_URL
from jobfit.context import JobFitRunContext

log = logging.getLogger(__name__)


def _search_jobs_enabled(ctx: RunContextWrapper[JobFitRunContext], agent) -> bool:
    """Remove search_jobs from the model's toolset once the cap is hit, instead
    of just returning an error. A blocking error message alone was not enough:
    a real run kept calling search_jobs 19 times after being told to stop,
    burning its whole turn budget on the same blocked call instead of pivoting
    to read_job_page, and never wrote a report. A tool it cannot see cannot be
    retried.

    Also disabled once read_job_page is capped: two real runs read 5 good
    pages, then used their remaining search budget to gather more urls they
    could no longer read, and on discovering read_job_page gone wrote
    <tool_call> XML as plain text instead of the report. Once reading is
    capped there is nothing left to do with more search results, so search is
    capped too, leaving write-the-report as the only option."""
    return ctx.context.search_call_count < MAX_SEARCH_CALLS and ctx.context.read_call_count < MAX_PAGE_READS


@function_tool(is_enabled=_search_jobs_enabled)
def search_jobs(ctx: RunContextWrapper[JobFitRunContext], query: str, limit: int = MAX_SEARCH_RESULTS) -> str:
    """Search the web for job listings and return compact JSON results."""
    if ctx.context.search_call_count >= MAX_SEARCH_CALLS:
        # Defense in depth in case is_enabled is ever bypassed; should not be reachable.
        log.warning(
            "search_jobs blocked: already called %d times (limit %d); forcing read_job_page instead",
            ctx.context.search_call_count,
            MAX_SEARCH_CALLS,
        )
        return json.dumps(
            {
                "error": (
                    f"search_jobs has already been called {ctx.context.search_call_count} times. "
                    "No more searching is allowed. Call read_job_page on one of the urls already "
                    "returned by search_jobs, then write the report."
                )
            }
        )
    ctx.context.search_call_count += 1
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
    ctx.context.seen_urls.update(r["url"] for r in results)
    log.info("search_jobs query=%r returned %d usable results (of %d raw)", query, len(results), len(links))
    return json.dumps(results, ensure_ascii=False)


def _read_job_page_enabled(ctx: RunContextWrapper[JobFitRunContext], agent) -> bool:
    """Remove read_job_page from the model's toolset once the count cap is
    hit, for the same reason search_jobs is disabled above: a blocking error
    message alone did not stop a real run from calling it 24+ times (ping-
    ponging between the same two thin urls) until MaxTurnsExceeded killed it.
    Kept enabled while under the cap even if some urls have already been
    read, since it may still be called validly on a different url; the
    per-url repeat check inside the tool handles that case."""
    return ctx.context.read_call_count < MAX_PAGE_READS


@function_tool(is_enabled=_read_job_page_enabled)
def read_job_page(ctx: RunContextWrapper[JobFitRunContext], url: str) -> str:
    """Scrape one job listing URL and return markdown text."""
    if url in ctx.context.read_urls:
        log.warning("read_job_page blocked: url already read this run: %s", url)
        return json.dumps(
            {
                "error": (
                    "This url has already been read. Re-reading it will not return new "
                    "content. Call read_job_page on a different url, or stop and write the report."
                )
            }
        )
    if ctx.context.read_call_count >= MAX_PAGE_READS:
        # Defense in depth in case is_enabled is ever bypassed; should not be reachable.
        log.warning(
            "read_job_page blocked: already called %d times (limit %d); forcing report instead",
            ctx.context.read_call_count,
            MAX_PAGE_READS,
        )
        return json.dumps(
            {
                "error": (
                    f"read_job_page has already been called {ctx.context.read_call_count} times. "
                    "No more reading is allowed. Stop using tools and write the report now."
                )
            }
        )
    log.info("read_job_page url=%s", url)
    ctx.context.read_call_count += 1
    ctx.context.read_urls.add(url)
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
    ctx.context.seen_urls.add(url)
    log.info("read_job_page url=%s fetched %d chars (truncated to %d)", url, len(response.text), len(text))
    return text
