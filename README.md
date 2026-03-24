# Manifesto Classifier Dashboard

A full-stack web dashboard for automated classification of political manifesto quasi-sentences across multiple policy dimensions using Google Vertex AI (Gemini).

Built as part of a Master's thesis research project.

---

## Overview

The system classifies short text fragments ("quasi-sentences") from political party manifestos on a scale of **conservative (1) / neutral (0) / liberal (-1) / not relevant (99)** for each policy dimension. Classification runs via the Gemini API on Google Vertex AI with structured JSON output and automatic retry logic.

The dashboard lets you launch, monitor, and manage classification jobs across all dimensions and batches from a browser — no command line required during normal operation.

---

## Features

- **Live dashboard** — per-dimension progress bars, batch-level status cells, code distribution bars
- **Job management** — start, stop, and resume classification jobs per batch
- **Live logs** — SSE-streamed log output per job
- **Results browser** — paginated view of classified sentences per dimension
- **Dimension management** — create, edit, and duplicate dimensions with custom prompts from the UI
- **Refinement workflow** — create a refined sub-dimension from any base dimension, automatically filtering out code-99 sentences and splitting into optimally-sized batches
- **Persistent config** — dimension configs saved to `data/dimensions.json`, accessible outside Docker
- **Docker Compose** — single command to build and run everything

---

## Quick Start

### With Docker (recommended)

```bash
# 1. Copy and fill in your GCP project ID
cp .env.example .env
# edit .env: GOOGLE_CLOUD_PROJECT=your-gcp-project-id

# 2. Build and start
docker compose up --build
```

Dashboard: http://localhost:3000
API docs: http://localhost:8000/docs

### Without Docker

```bash
# Backend
source /home/control/rlang/venv/bin/activate
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (separate terminal)
cd frontend && npm run dev
```

---

## Configuration

### Environment

Copy `.env.example` to `.env` and set your GCP project:

```
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
```

Docker Compose reads this automatically. The GCP project can also be changed at runtime from the **⚙ Config** panel in the dashboard without restarting.

### GCP Authentication

The backend requires Application Default Credentials. Docker mounts `~/.config/gcloud` read-only into the container — run `gcloud auth application-default login` on the host before starting.

### Vertex AI location

Defaults to `global`. Change via the **⚙ Config** panel or `PATCH /api/config`.

---

## Project Structure

```
sol_projekt/
├── backend/
│   ├── config.py        # Built-in dimension configs + dynamic loader
│   ├── classifier.py    # Subprocess: classifies one (dimension, batch)
│   ├── main.py          # FastAPI app
│   ├── migrate.py       # One-time migration from legacy rlang/ outputs
│   └── requirements.txt
├── frontend/
│   ├── app/page.tsx     # Main dashboard
│   ├── components/      # UI components
│   └── lib/api.ts       # API client
├── data/                # Output files + dimension config (bind-mounted)
├── .env.example
├── docker-compose.yml
└── start.sh             # Non-Docker start script
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for a full technical description.

---

## Data

### Input sentences

```
/home/control/rlang/sentences_part_{1..6}.json
```

Each file: `[{"ID": int, "QuasiSentence": str}, ...]`

### Classification output

```
data/output_{dimension}_{batch}.json
```

Each file: `[{"ID": int, "QuasiSentence": str, "Code": 1|0|-1|99|"ERROR"}, ...]`

### Coding scheme

| Code | Meaning |
|------|---------|
| `1` | Conservative |
| `0` | Neutral |
| `-1` | Liberal |
| `99` | Not relevant |
| `"ERROR"` | API failure after all retries |

---

## Refinement Workflow

A **refine dimension** re-classifies the non-99 results of a base dimension with a modified prompt — useful for iterating on coding decisions without re-processing irrelevant sentences.

1. Click **↺** on any base dimension card
2. Edit the ID, label, and prompt in the form
3. Click **Create refinement** — the backend filters out code-99 sentences, splits them into batches of ≤7000, and creates the new dimension
4. The refine card appears below its parent with a violet border

---

## Migrating Legacy Results

If you have existing output files from the legacy `rlang/` scripts:

```bash
source /home/control/rlang/venv/bin/activate
python backend/migrate.py
```

This merges all `output_*` files from `rlang/` into `data/`, deduplicating by ID and preferring non-ERROR results.
