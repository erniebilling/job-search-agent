FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    gradio \
    openai \
    openai-agents \
    pypdf \
    requests

COPY jobfit/ jobfit/
COPY worker/ worker/
COPY web/ web/

ENV DB_PATH=/data/jobfit.db
VOLUME ["/data"]

EXPOSE 7860

# Overridden by k8s: CronJob runs `python -m worker.main`,
# Deployment runs `python -m web.app`.
CMD ["python", "-m", "web.app"]
