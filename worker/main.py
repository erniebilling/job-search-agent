import asyncio
import sys
import traceback

from jobfit import db
from jobfit.config import OLLAMA_MODEL
from jobfit.report_parser import parse_report
from jobfit.runner import run_jobfit_once


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
        print("Skipped run: profile is missing CV text or preferences.")
        return 1

    run_id = db.create_run(model_name=OLLAMA_MODEL)
    try:
        report_markdown = await run_jobfit_once(profile["cv_text"], profile["preferences"])
        entries = parse_report(report_markdown)
        db.finish_run(run_id, status="success", report_markdown=report_markdown)
        if entries:
            db.save_job_entries(run_id, entries)
        print(f"Run {run_id} succeeded with {len(entries)} parsed job entries.")
        return 0
    except Exception as exc:
        db.finish_run(
            run_id,
            status="failed",
            error_message=f"{exc}\n{traceback.format_exc()}",
        )
        print(f"Run {run_id} failed: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
