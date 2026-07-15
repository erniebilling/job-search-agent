import logging
import re

log = logging.getLogger(__name__)

_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
_SCORE_RE = re.compile(r"(\d+)")


def _split_row(line: str) -> list[str]:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return cells


def _extract_url(cell: str) -> str:
    match = _LINK_RE.search(cell)
    return match.group(2) if match else ""


def _extract_score(cell: str) -> int | None:
    match = _SCORE_RE.search(cell)
    return int(match.group(1)) if match else None


def _find_table_rows(report_markdown: str, heading: str) -> list[str]:
    lines = report_markdown.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip().startswith(heading))
    except StopIteration:
        return []
    rows = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("|"):
            rows.append(stripped)
    # Drop the header row and the "---" separator row.
    return rows[2:] if len(rows) > 2 else []


def parse_ranked_jobs(report_markdown: str) -> list[dict]:
    entries = []
    for row in _find_table_rows(report_markdown, "## Ranked Jobs"):
        cells = _split_row(row)
        if len(cells) < 6:
            continue
        rank_str, role, company, apply_decision, fit, link = cells[:6]
        entries.append(
            {
                "rank": int(rank_str) if rank_str.isdigit() else None,
                "title": role,
                "company": company,
                "url": _extract_url(link),
                "fit_score": _extract_score(fit),
                "apply_decision": apply_decision,
                "rationale": None,
                "is_rejected": 0,
            }
        )
    return entries


def parse_rejected_jobs(report_markdown: str) -> list[dict]:
    entries = []
    for row in _find_table_rows(report_markdown, "## Rejected Jobs"):
        cells = _split_row(row)
        if len(cells) < 3:
            continue
        title, link, reason = cells[:3]
        entries.append(
            {
                "rank": None,
                "title": title,
                "company": None,
                "url": _extract_url(link),
                "fit_score": None,
                "apply_decision": "Do not apply",
                "rationale": reason,
                "is_rejected": 1,
            }
        )
    return entries


def parse_report(report_markdown: str) -> list[dict]:
    """Best-effort parse of a JobFit AI report into job_entries rows.

    Returns an empty list if the report does not match the expected
    structure; the raw markdown is always preserved separately, so a
    parse failure never loses data.
    """
    try:
        ranked = parse_ranked_jobs(report_markdown)
        rejected = parse_rejected_jobs(report_markdown)
        log.info("Parsed %d ranked and %d rejected job entries", len(ranked), len(rejected))
        return ranked + rejected
    except Exception:
        log.warning("Failed to parse report markdown into job entries", exc_info=True)
        return []
