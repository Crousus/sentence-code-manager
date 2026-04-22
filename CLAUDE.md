# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **political manifesto classification system** — a Master's thesis research project that classifies "quasi-sentences" from political party manifestos across multiple policy dimensions using Google Vertex AI (Gemini).

The system has two layers:
- **`rlang/`** — legacy standalone scripts (read-only reference, do not modify)
- **`sol_projekt/`** — the active full-stack dashboard: FastAPI backend + Next.js frontend, deployable via Docker Compose

See @ARCHITECTURE.md for a full description of the system design.

## Running the Dashboard

```bash
# Docker (recommended)
cd /home/control/sol_projekt
docker compose up --build

# Or locally without Docker
source /home/control/rlang/venv/bin/activate
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
cd ../frontend && npm run dev
```

Dashboard: http://localhost:3000 — API docs: http://localhost:8000/docs

## Running Legacy Models (rlang/ only)

```bash
source /home/control/rlang/venv/bin/activate
cd /home/control/rlang
python3 Model<dimension>.py
```

## Architecture Summary

- **`backend/config.py`** — 18 built-in dimension configs (`_DEFAULT_DIMENSIONS`) + `load_dimensions()` which reads `data/dimensions.json` at import time, falling back to defaults. Both `main.py` and `classifier.py` subprocesses use this. Exports `refine_input_path(dim, batch)` → `data/input_{dim}_{batch}.json`.
- **`backend/main.py`** — FastAPI app. Maintains `_dimensions` (mutable in-memory dict) and `_runtime_config` (project_id, location, gcs_bucket). Writes to `data/dimensions.json` on any create/update/refine. All batch loops use `_dim_batches(dim_id)` which returns the dimension's custom `"batches"` list or the global `BATCHES`. Jobs have a `mode` field ("singular" or "batch") that determines which classifier subprocess to spawn.
- **`backend/classifier.py`** — Subprocess per `(dimension, batch)` job in **singular mode** (one sentence at a time). Uses `_get_input_file(dimension, batch)` which prefers `data/input_{dim}_{batch}.json` (refine input) over the rlang sentence files.
- **`backend/batch_classifier.py`** — Subprocess per `(dimension, batch)` job in **batch prediction mode**. Builds JSONL, uploads to GCS, submits to Google Cloud Batch Prediction API, polls for completion, downloads and parses results. Requires a GCS bucket configured in ⚙ Config. Supports `--max-sentences` to limit how many sentences to process. On SIGTERM the remote job is **not** cancelled — a tracking file (`data/.batch_state_{dim}_{batch}.json`) persists so the next run re-attaches to the still-running Google Cloud job.
- **`backend/fix_errors.py`** — Subprocess that scans ALL output files for a dimension, collects `Code == "ERROR"` entries across all batches, reprocesses them (singular or batch mode), and writes fixed results back into the original output files. Triggered by "Fix Errors" button on dimension cards. Job key: `{dimension}:fix-errors`. In batch mode, same re-attach behaviour as `batch_classifier.py` (tracking file: `data/.batch_state_{dim}_fix_errors.json`).
- **`data/dimensions.json`** — Persisted dimension config. Refine dimensions include `"refine_of": "<parent_id>"` and `"batches": [1, ...]`. Bind-mounted in Docker.
- **`data/input_{dim}_{batch}.json`** — Auto-generated input files for refine dimensions (non-99 sentences from parent results). Created by `POST /api/dimensions/{id}/refine`.
- **`frontend/components/DimensionFormDrawer.tsx`** — Create / edit / duplicate / refine dimensions from the UI.
- **`frontend/components/JobStartDialog.tsx`** — Modal dialog shown when starting a job or fixing errors. Lets the user choose processing mode (singular vs batch prediction) and configure max sentences for batch mode. In fix-errors mode, shows error count across all batches.

## Data Format

**Input** (`/home/control/rlang/sentences_part_N.json`):
```json
[{"ID": 1234, "QuasiSentence": "..."}]
```

**Output** (`data/output_<dimension>_N.json`):
```json
[{"ID": 1234, "QuasiSentence": "...", "Code": 1}]
```

## Coding Scheme

- `1` — Conservative position
- `0` — Neutral
- `-1` — Liberal position
- `99` — Not relevant to the variable
- `"ERROR"` — Permanent API failure after all retries

## Key Constraints

- **Do not modify anything in `rlang/`** — legacy/reference code only.
- `data/` is bind-mounted in Docker — output files, `dimensions.json`, and refine input files (`input_{dim}_{batch}.json`) all persist on the host.
- Per-dimension model names (`gemini-3-flash-preview`, `gemini-2.5-flash`) are set in `config.py` and editable via the dashboard UI.
- Refine dimensions cannot be further refined (one level only). They use a custom `"batches"` list (≤7000 sentences per batch, equally distributed) instead of the global 1–6.
- `project_id` / `location` / `gcs_bucket` are runtime-configurable via the ⚙ Config panel without restarting. `gcs_bucket` is required for batch prediction mode.
- Two processing modes: **singular** (one sentence at a time, streaming progress) and **batch** (Google Cloud Batch Prediction API, faster for large volumes). Mode is chosen per-job from the UI.
- **Fix Errors**: Each dimension card shows a "Fix N Errors" button when ERROR entries exist. This spawns `fix_errors.py` which scans all batch output files, collects errors, reprocesses them (singular or batch mode), and replaces ERROR entries in-place in the original output files. Resume is implicit (re-scan finds only remaining errors).
- Whenever there is an update/change/addition to the project update the @ARCHITECTURE.md at the end
