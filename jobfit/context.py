from dataclasses import dataclass, field


@dataclass
class JobFitRunContext:
    """Tracks URLs the agent actually observed, so the report can be checked
    against ground truth instead of trusting the model's transcription. Also
    tracks how many times search_jobs has been called, so a model that keeps
    re-searching instead of reading pages (observed running 19 searches in a
    row for over an hour without ever calling read_job_page) can be cut off
    in code rather than relying on it following an advisory prompt rule."""

    seen_urls: set[str] = field(default_factory=set)
    search_call_count: int = 0
