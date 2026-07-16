from dataclasses import dataclass, field


@dataclass
class JobFitRunContext:
    """Tracks URLs the agent actually observed, so the report can be checked
    against ground truth instead of trusting the model's transcription."""

    seen_urls: set[str] = field(default_factory=set)
