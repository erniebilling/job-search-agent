import asyncio
import logging
import sys
import traceback

from jobfit import db
from jobfit.config import OLLAMA_MODEL
from jobfit.logging_utils import capture_run_logs
from jobfit.report_parser import parse_report
from jobfit.runner import run_jobfit_once

log = logging.getLogger(__name__)


async def run() -> int:
    db.init_db()
    profile = db.get_profile()

    if profile is None or not (profile["cv_text"] or "").strip() or not (profile["preferences"] or "").strip():
        run_id = db.create_run(model_name=OLLAMA_MODEL)
        db.finish_run(
            run_id,
            status="failed",
            error_message="No CV/preferences saved yet. Set them in the web app before the next scheduled run.",
        )
        log.warning("Skipped run: profile is missing CV text or preferences.")
        return 1

    run_id = db.create_run(model_name=OLLAMA_MODEL)
    with capture_run_logs() as log_buffer:
        log.info("Starting run %s with model %s", run_id, OLLAMA_MODEL)
        log.info("CV file used for this run: %s", profile["cv_filename"])
        try:
            report_markdown, seen_urls = await run_jobfit_once(profile["cv_text"], profile["preferences"])
            entries = parse_report(report_markdown, seen_urls)
            if not entries:
                log.warning("Report parsed to zero job entries; report may not match the expected structure")
            db.finish_run(
                run_id,
                status="success",
                report_markdown=report_markdown,
                log_text=log_buffer.getvalue(),
            )
            if entries:
                db.save_job_entries(run_id, entries)
            log.info("Run %s succeeded with %d parsed job entries", run_id, len(entries))
            return 0
        except Exception as exc:
            log.error("Run %s failed: %s", run_id, exc, exc_info=True)
            db.finish_run(
                run_id,
                status="failed",
                error_message=f"{exc}\n{traceback.format_exc()}",
                log_text=log_buffer.getvalue(),
            )
            return 1


def main() -> None:
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
