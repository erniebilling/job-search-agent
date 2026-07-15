# JobFit AI

JobFit AI reads a candidate CV and job preferences, then runs a local Qwen3 agent (through Ollama and the OpenAI Agents SDK) that searches the web with OpenSERP and produces a ranked Markdown job-fit report.

It runs as a scheduled service: a **Kubernetes CronJob** searches for jobs once a day and stores results in a SQLite database, and a small always-on **Gradio web app** lets you update your CV/preferences and browse the latest and historical reports. The whole thing is designed to run on a home **k3s cluster on a Raspberry Pi**, built and deployed by an in-cluster **Tekton pipeline**.

The default preferences target AI, data science, technical writing, technical content, curriculum, and developer education roles, and can be changed for other job searches.

## Architecture

```
jobfit/    shared library: CV reading, prompts, agent/tools, DB access, report parsing
worker/    CronJob entrypoint (python -m worker.main) - runs the agent once, writes to SQLite
web/       always-on Gradio app (python -m web.app) - edit profile, browse reports
k8s/       Kubernetes manifests for the jobfit namespace
tekton/    Tekton Pipeline/Task resources that build the image and deploy it in-cluster
```

Both `worker` and `web` are packaged in the **same container image** with different entrypoints, and both mount the same PVC-backed SQLite database, so a profile edit made in the web app is immediately visible to the next scheduled run.

### Data flow

1. Open the web app, upload a CV PDF and job preferences, click **Save Profile**. This is stored in the `profile` table (single row - this is a single-user app).
2. Once a day, the `jobfit-worker` CronJob starts a pod, loads the saved profile, runs the JobFit AI agent (Ollama + OpenSERP, unchanged from the original app's logic), and writes a `runs` row plus parsed `job_entries` rows.
3. The web app's **Latest Report** and **History** tabs read directly from the same database.

## Local Development

Install dependencies:

```bash
pipenv install
```

JobFit AI runs its agent against a local [Ollama](https://ollama.com) instance instead of a hosted API, so no API key is required. Install Ollama, then pull the model:

```bash
ollama pull qwen3:8b
```

Make sure the Ollama server is running (`ollama serve`, or the Ollama desktop app). By default the app looks for Ollama at `http://localhost:11434/v1`. If it runs elsewhere, or you want a different model, set:

```bash
export OLLAMA_BASE_URL="http://localhost:11434/v1"
export OLLAMA_MODEL="qwen3:8b"
```

JobFit AI also needs a running [OpenSERP](https://github.com/karust/openserp) instance for web search and page extraction. Start one locally with Docker:

```bash
docker run --rm -p 127.0.0.1:7000:7000 karust/openserp:latest serve -a 0.0.0.0 -p 7000
```

By default the app looks for OpenSERP at `http://localhost:7000`. If it runs elsewhere, set `OPENSERP_BASE_URL`:

```bash
export OPENSERP_BASE_URL="http://localhost:7000"
```

By default the SQLite database is created at `jobfit.db` in the working directory. Override with `DB_PATH`.

### Run the web app

```bash
python -m web.app
```

Open `http://127.0.0.1:7860`, go to the **Profile** tab, upload a CV PDF, enter job preferences, and click **Save Profile**.

### Run the worker once

```bash
python -m worker.main
```

This reads the saved profile, runs the agent once, and stores the result. Reopen the web app's **Latest Report** or **History** tab to see it.

## Deploying to k3s

These manifests assume a single-node k3s cluster (e.g. on a Raspberry Pi) with Tekton Pipelines already installed, and OpenSERP/Ollama reachable from the cluster (adjust `k8s/configmap.yaml` for their actual addresses).

1. Apply the base resources:

   ```bash
   kubectl apply -f k8s/namespace.yaml
   kubectl apply -f k8s/pvc-data.yaml -f k8s/configmap.yaml -f k8s/secret.yaml
   kubectl apply -f k8s/service-web.yaml
   ```

2. Apply the Tekton build/deploy pipeline:

   ```bash
   kubectl apply -f tekton/rbac.yaml
   kubectl apply -f tekton/registry-pvc.yaml -f tekton/registry-deployment.yaml -f tekton/registry-service.yaml
   kubectl apply -f tekton/pvc-workspace.yaml
   kubectl apply -f tekton/task-git-clone.yaml -f tekton/task-kaniko-build.yaml -f tekton/task-deploy.yaml
   kubectl apply -f tekton/pipeline-build-deploy.yaml
   ```

   The in-cluster registry (`registry.jobfit.svc.cluster.local:5000`) is plain HTTP. Configure k3s's containerd to treat it as an insecure registry (`/etc/rancher/k3s/registries.yaml` with `mirrors`/`configs` for that host and `insecure_skip_verify: true`), then restart k3s, so the cluster's own image pulls succeed. The Kaniko build Task already passes `--insecure`/`--skip-tls-verify` for pushes.

3. Since `k8s/deployment-web.yaml` and `k8s/cronjob-worker.yaml` reference an image that doesn't exist yet, trigger the pipeline first to build and push it, *then* apply those two manifests:

   ```bash
   # Edit tekton/pipelinerun-template.yaml with your repo URL, or use tkn:
   tkn pipeline start jobfit-build-deploy -n jobfit \
     -p git-url=https://github.com/<you>/JobFit-AI.git \
     -p git-revision=main \
     -p image-tag=latest \
     -w name=source,claimName=jobfit-pipeline-workspace \
     --serviceaccount=jobfit-pipeline

   kubectl apply -f k8s/deployment-web.yaml -f k8s/cronjob-worker.yaml
   ```

4. Trigger a run manually to validate before waiting for the schedule:

   ```bash
   kubectl create job --from=cronjob/jobfit-worker jobfit-worker-manual-1 -n jobfit
   ```

5. Open the web app at `http://<pi-host>:30786` (the `NodePort` set in `k8s/service-web.yaml`).

For subsequent code changes, re-trigger the pipeline (with a new `image-tag`, or `latest` again) - it rebuilds the image and redeploys both the web Deployment and worker CronJob.

### Notes for the Raspberry Pi environment

- Everything in `jobfit/`, `worker/`, and `web/` uses only pure-Python dependencies (`gradio`, `pypdf`, `openai`, `openai-agents`, stdlib `sqlite3`) with arm64 wheels, and the `Dockerfile` builds on `python:3.13-slim`.
- The daily worker run's `activeDeadlineSeconds` (in `k8s/cronjob-worker.yaml`) is set generously to account for a local 8B model running on Pi-class CPU; treat the first few real runs as a timing calibration and adjust if needed.
- `k8s/pvc-data.yaml` uses `ReadWriteOnce`, which only works because the web Deployment and worker CronJob land on the same single node - this does not generalize to a multi-node cluster without an RWX-capable StorageClass.
