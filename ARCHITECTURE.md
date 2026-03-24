# Architecture — Manifesto Classifier Dashboard

## Overview

A full-stack web dashboard for running and monitoring automated classification of political manifesto quasi-sentences across 18 policy dimensions using Google Vertex AI (Gemini).

```
Browser ──► Next.js (port 3000) ──► FastAPI (port 8000) ──► Vertex AI
                  │                       │
              /api/* proxy           sol_projekt/data/
              (rewrites)            output_{dim}_{batch}.json
```

---

## Directory Structure

```
sol_projekt/
├── backend/
│   ├── config.py          # Built-in dimension configs + GCP settings + dynamic loader
│   ├── classifier.py      # Subprocess: classifies one (dimension, batch)
│   ├── main.py            # FastAPI app — job management & API
│   ├── migrate.py         # One-time migration: rlang/ → data/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   └── page.tsx       # Main dashboard page
│   ├── components/
│   │   ├── ConfigPanel.tsx        # GCP project / location editor
│   │   ├── CodeDistBar.tsx        # Stacked code distribution bar
│   │   ├── DimensionFormDrawer.tsx  # Create / edit / duplicate dimension
│   │   ├── LogDrawer.tsx          # SSE live log viewer
│   │   ├── ResultsDrawer.tsx      # Paginated results browser
│   │   └── StatusBadge.tsx        # Colour-coded status pill
│   ├── lib/
│   │   └── api.ts         # Typed fetch wrappers (all calls → /api/*)
│   ├── next.config.ts     # Rewrite proxy + allowedDevOrigins
│   ├── .env.local         # BACKEND_URL=http://localhost:8000
│   └── Dockerfile
├── data/                  # Output files + live dimension config
│   ├── output_{dim}_{batch}.json
│   └── dimensions.json    # Persisted dimension config (created on first edit)
├── docker-compose.yml     # Builds + runs backend & frontend with bind mounts
├── start.sh               # Starts backend + frontend (non-Docker)
└── ARCHITECTURE.md        # This file
```

---

## Backend (`backend/`)

### `config.py`

Contains built-in defaults for all 18 dimensions and the dynamic loader.

**Central GCP settings** (apply to all jobs unless overridden at runtime):
```python
PROJECT_ID = "masterarbeit-485518"   # GCP project
LOCATION   = "global"                # Vertex AI location
```

**Per-dimension settings** (18 entries in `_DEFAULT_DIMENSIONS` dict):
```python
"childcare": {
    "label":           "Childcare & Parental Leave",
    "model":           "gemini-3-flash-preview",
    "prompt_template": "...",
}
```

**Dynamic loading** — at import time, `config.py` calls `load_dimensions()` which reads `data/dimensions.json` if present, falling back to `_DEFAULT_DIMENSIONS`. This means `classifier.py` subprocesses always see the latest saved config without a restart.

**Batch helpers**:
```python
BATCHES = [1, 2, 3, 4, 5, 6]          # global default for base dimensions
input_path(batch)                       # → /home/control/rlang/sentences_part_{batch}.json
output_path(dim, batch)                 # → sol_projekt/data/output_{dim}_{batch}.json
refine_input_path(dim, batch)           # → sol_projekt/data/input_{dim}_{batch}.json
```

Refine dimensions store a `"batches"` list in their config entry that overrides the global `BATCHES`. `classifier.py` auto-detects which input file to use via `_get_input_file(dimension, batch)` — prefers `data/input_{dim}_{batch}.json` if present, otherwise falls back to the rlang sentences.

### `classifier.py`

Standalone subprocess script — one invocation = one (dimension, batch) job.

```
python classifier.py --dimension childcare --batch 2 [--project-id ...] [--location ...]
```

Execution flow:
1. Auto-detect input: uses `data/input_{dim}_{batch}.json` if present (refine dim), else `rlang/sentences_part_{batch}.json`
2. Load existing `output_{dim}_{batch}.json` → build `processed_ids` set (resume logic)
3. For each unprocessed sentence: call Vertex AI with structured JSON output (`Classification` Pydantic schema, `temperature=0.0`)
4. Up to 6 retries with linear backoff on failure; permanent failures → `Code: "ERROR"`
5. Save full output list to disk after every sentence (incremental)

**Structured log protocol** (parsed by `main.py`):
| Line | Meaning |
|------|---------|
| `TOTAL:{n}` | sentences in input file |
| `RESUME:{n}` | already processed, skipping |
| `PROCESSING:{id}` | starting sentence |
| `SUCCESS:{id}:{code}` | classified OK |
| `RETRY:{id}:{attempt}:{err}` | transient failure |
| `FAILED:{id}` | permanent failure |
| `PROGRESS:{n}` | cumulative saved count |
| `COMPLETE` | all done |
| `ERROR:{msg}` | fatal startup error |

### `main.py` — FastAPI

**Job lifecycle**:
- Jobs are keyed by `(dimension, batch)` — batch list is per-dimension (refine dims may have fewer batches)
- Each job spawns `classifier.py` as an async subprocess
- Stdout is streamed line-by-line, parsed for structured progress updates
- Job state is in-memory (lost on restart); file state (output JSONs) is persistent

**Runtime config** (`_runtime_config`): holds `project_id` and `location`, changeable via `PATCH /api/config` without restarting.

**Dimension registry** (`_dimensions`): mutable in-memory dict initialised from `data/dimensions.json` at startup (falls back to `_DEFAULT_DIMENSIONS`). Written to disk on every create/update so `classifier.py` subprocesses and Docker restarts always see the latest config.

**API endpoints**:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dimensions` | All dims with per-batch status + aggregate stats |
| GET | `/api/dimensions/{id}/config` | Full config (label, model, prompt_template) for one dim |
| POST | `/api/dimensions` | Create a new dimension |
| PUT | `/api/dimensions/{id}` | Update label / model / prompt_template |
| POST | `/api/dimensions/{id}/refine` | Create a refinement dimension from a parent |
| GET | `/api/stats` | Global totals (sentences, jobs, progress) |
| POST | `/api/jobs` | Start a `{dimension, batch}` job |
| GET | `/api/jobs` | List all jobs |
| GET | `/api/jobs/{id}` | Job detail + last 200 log lines |
| GET | `/api/jobs/{id}/logs` | Paginated logs |
| GET | `/api/jobs/{id}/stream` | SSE live log stream |
| POST | `/api/jobs/{id}/stop` | Terminate job process |
| GET | `/api/config` | Current runtime GCP config |
| PATCH | `/api/config` | Update `project_id` / `location` |
| GET | `/api/results/{dim}` | Paginated results merged across all batches |

---

## Frontend (`frontend/`)

Next.js 16 app (App Router, TypeScript, Tailwind CSS).

### Networking

All API calls use relative paths (`/api/...`). `next.config.ts` proxies these server-side to FastAPI:

```ts
rewrites: [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }]
```

This eliminates CORS entirely — the browser only ever talks to the Next.js origin.

### Data flow

```
page.tsx
  └─ polls /api/dimensions + /api/stats every 3s
  └─ renders DimensionCards sorted: each base dim followed by its refinements
       └─ N BatchCells per card (6 for base dims, 1–N for refine dims)
            └─ click idle/partial → POST /api/jobs
            └─ click running / "■ Stop B{n}" button → POST /api/jobs/{id}/stop
       └─ ↺ Refine button (base dims only) → fetches config → DimensionFormDrawer (refine mode)
       └─ ✎ Edit button → DimensionFormDrawer (edit mode)
       └─ ⎘ Duplicate button → fetches config → DimensionFormDrawer (create mode, pre-filled)
       └─ "Logs" → LogDrawer (SSE stream via EventSource)
       └─ "Results" → ResultsDrawer (paginated GET /api/results/{dim})
  └─ "+ Dimension" → DimensionFormDrawer (create mode, blank)
  └─ "⚙ Config" → ConfigPanel (GET/PATCH /api/config)
```

### Dimension card

Each card shows:
- Aggregate progress bar across all batches
- Code distribution bar (1 = Conservative, 0 = Neutral, -1 = Liberal, 99 = N/A, ERROR)
- N batch cells — colour coded:
  - Dark grey = idle
  - Amber = partial (some sentences done)
  - Blue pulsing = running
  - Green = completed
- Stop buttons appear in card footer for any running batch
- ↺ / ✎ / ⎘ icon buttons in card header (↺ Refine only on base dims)

**Refine cards** are visually distinct: purple-tinted background, violet border, and a "↺ refinement of {parent}" sub-label. They appear immediately below their parent in the grid.

---

## Data

### Input (read-only, from rlang/)
```
/home/control/rlang/sentences_part_{1..6}.json
```
Each file: `[{"ID": int, "QuasiSentence": str}, ...]`

### Output (written by classifier.py)
```
sol_projekt/data/output_{dimension}_{batch}.json
```
Each file: `[{"ID": int, "QuasiSentence": str, "Code": int|"ERROR"}, ...]`

Results are written incrementally (after every sentence) and merged across batches in `/api/results/{dim}` (deduplicating by ID, preferring non-ERROR).

### Dimension config (written by the dashboard)
```
sol_projekt/data/dimensions.json
```
Created automatically on the first create/edit/refine action in the UI. Contains the full config map:
```json
{
  "childcare": { "label": "...", "model": "...", "prompt_template": "..." },
  "childcare_r": { "label": "...", "model": "...", "prompt_template": "...", "refine_of": "childcare", "batches": [1, 2] }
}
```
If absent, built-in defaults from `config.py` are used. Bind-mounted in Docker.

### Refine input files (written by the dashboard)
```
sol_projekt/data/input_{dimension}_{batch}.json
```
Created by `POST /api/dimensions/{id}/refine`. Contains sentences from the parent's results with `Code == 99` stripped. Format identical to rlang input files: `[{"ID": int, "QuasiSentence": str}, ...]`. `classifier.py` auto-detects these files — if present they take priority over the rlang sentence files.

### Coding scheme
| Code | Meaning |
|------|---------|
| `1` | Conservative |
| `0` | Neutral |
| `-1` | Liberal |
| `99` | Not relevant |
| `"ERROR"` | API failure after all retries |

---

## Dimensions & Models

| Key | Label | Model |
|-----|-------|-------|
| childcare | Childcare & Parental Leave | gemini-3-flash-preview |
| edu | Girls' Education | gemini-2.5-flash |
| equal | Gender Equality | gemini-3-flash-preview |
| famcare | Family Care | gemini-2.5-flash |
| famplan | Family Planning | gemini-2.5-flash |
| femim | Female Immigrant Rights (General) | gemini-3-flash-preview |
| femimspec | Female Immigrant Rights (Specific) | gemini-2.5-flash |
| labour | Women's Labour Market | gemini-2.5-flash |
| lgbtq | LGBTQ+ Rights | gemini-2.5-flash |
| lgbtqim | LGBTQ+ Immigrant Rights | gemini-3-flash-preview |
| mix | Mixed/Interethnic Marriages | gemini-2.5-flash |
| nontradfam | Non-Traditional Families | gemini-3-flash-preview |
| part | Women's Political Participation | gemini-2.5-flash |
| pronat | Pro-Natalism | gemini-2.5-flash |
| quota | Gender Quotas in Politics | gemini-3-flash-preview |
| repfam | Family vs. Individual Representation | gemini-3-flash-preview |
| tradrole | Traditional Gender Roles | gemini-3-flash-preview |
| womorg | Women's Organizations | gemini-2.5-flash |

---

## Running

```bash
# Start everything
cd /home/control/sol_projekt
./start.sh

# Or individually:
source /home/control/rlang/venv/bin/activate
cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload

cd frontend && npm run dev
```

Dashboard: http://localhost:3000
API docs: http://localhost:8000/docs

---

## Legacy (`rlang/`)

The original 18 standalone scripts (`Modelchildcare.py`, etc.) are **read-only reference**. Do not modify them. The new `classifier.py` replicates their logic in a single unified script driven by `config.py`.
