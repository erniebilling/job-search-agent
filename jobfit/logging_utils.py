import contextlib
import io
import logging

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


@contextlib.contextmanager
def capture_run_logs(level=logging.INFO):
    """Configure root logging for the duration of a worker run and capture it as text.

    Logs still go to stderr (so `docker logs`/`kubectl logs` show them live) and are
    simultaneously collected into a string for storage in runs.log_text.
    """
    buffer = io.StringIO()
    formatter = logging.Formatter(LOG_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    buffer_handler = logging.StreamHandler(buffer)
    buffer_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(stream_handler)
    root.addHandler(buffer_handler)
    try:
        yield buffer
    finally:
        root.removeHandler(stream_handler)
        root.removeHandler(buffer_handler)
