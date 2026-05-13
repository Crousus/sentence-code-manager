"""
FastAPI backend for the manifesto classification dashboard.

Jobs are keyed by (dimension, batch). Each dimension card in the UI
shows 6 batch sub-cells.
"""

import asyncio
import json
import math
import os
import sys
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel as PydanticModel

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import BATCHES, DATA_DIR, DIMENSIONS_CONFIG_PATH, _DEFAULT_DIMENSIONS, LOCATION, PROJECT_ID, RLANG_DIR, input_path, output_path, refine_input_path

# ---------------------------------------------------------------------------
# Mutable dimension registry — loaded from dimensions.json at startup
# ---------------------------------------------------------------------------

def _init_dimensions() -> dict:
    if os.path.exists(DIMENSIONS_CONFIG_PATH):
        try:
            with open(DIMENSIONS_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {k: dict(v) for k, v in _DEFAULT_DIMENSIONS.items()}


_dimensions: dict = _init_dimensions()


def _save_dimensions() -> None:
    with open(DIMENSIONS_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(_dimensions, f, indent=2, ensure_ascii=False)


def _get_input_path(dimension: str, batch: int) -> str:
    """Prefer refine input file (data/input_{dim}_{batch}.json) over rlang sentences."""
    custom = refine_input_path(dimension, batch)
    if os.path.exists(custom):
        return custom
    return input_path(batch)


def _dim_batches(dim_id: str) -> list[int]:
    """Return the batch list for a dimension (custom for refine dims, global BATCHES otherwise)."""
    return _dimensions[dim_id].get("batches", BATCHES)

app = FastAPI(title="Manifesto Classifier API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# In-memory job store
# ---------------------------------------------------------------------------

class Job:
    def __init__(self, job_id: str, dimension: str, batch: int, mode: str = "singular", max_sentences: int = 0, fix_errors: bool = False):
        self.job_id = job_id
        self.dimension = dimension
        self.batch = batch
        self.mode = mode
        self.max_sentences = max_sentences
        self.fix_errors = fix_errors
        self.status = "running"          # running | completed | error | stopped
        self.started_at = datetime.utcnow().isoformat()
        self.finished_at: str | None = None
        self.logs: list[str] = []
        self.total: int = 0
        self.processed: int = 0
        self.process: asyncio.subprocess.Process | None = None
        self._log_subscribers: list[asyncio.Queue] = []

    def add_log(self, line: str):
        self.logs.append(line)
        if len(self.logs) > 2000:
            self.logs = self.logs[-2000:]
        for q in self._log_subscribers:
            q.put_nowait(line)
        if line.startswith("TOTAL:"):
            self.total = int(line.split(":", 1)[1])
        elif line.startswith("RESUME:"):
            self.processed = int(line.split(":", 1)[1])
        elif line.startswith("PROGRESS:"):
            self.processed = int(line.split(":", 1)[1])
        elif line == "COMPLETE":
            self.status = "completed"
            self.finished_at = datetime.utcnow().isoformat()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._log_subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        try:
            self._log_subscribers.remove(q)
        except ValueError:
            pass

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "dimension": self.dimension,
            "batch": self.batch,
            "mode": self.mode,
            "max_sentences": self.max_sentences,
            "fix_errors": self.fix_errors,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total": self.total,
            "processed": self.processed,
            "log_count": len(self.logs),
        }


# Global job registry: job_id -> Job
jobs: dict[str, Job] = {}
# Track active job per (dim, batch): key = "dim:batch" -> job_id
active_job_per_dim_batch: dict[str, str] = {}


# ---------------------------------------------------------------------------
# Job runner
# ---------------------------------------------------------------------------

async def run_job(job: Job):
    python = os.path.join(RLANG_DIR, "venv", "bin", "python")
    if not os.path.exists(python):
        python = sys.executable

    backend_dir = os.path.dirname(os.path.abspath(__file__))

    if job.fix_errors:
        script = os.path.join(backend_dir, "fix_errors.py")
        cmd = [
            python, script,
            "--dimension", job.dimension,
            "--mode", job.mode,
            "--project-id", _runtime_config["project_id"],
            "--location", _runtime_config["location"],
        ]
        if job.mode == "batch":
            cmd.extend(["--gcs-bucket", _runtime_config["gcs_bucket"]])
        if job.max_sentences > 0:
            cmd.extend(["--max-sentences", str(job.max_sentences)])
    elif job.mode == "batch":
        script = os.path.join(backend_dir, "batch_classifier.py")
        cmd = [
            python, script,
            "--dimension", job.dimension,
            "--batch", str(job.batch),
            "--project-id", _runtime_config["project_id"],
            "--location", _runtime_config["location"],
            "--gcs-bucket", _runtime_config["gcs_bucket"],
            "--max-sentences", str(job.max_sentences),
        ]
    else:
        script = os.path.join(backend_dir, "classifier.py")
        cmd = [
            python, script,
            "--dimension", job.dimension,
            "--batch", str(job.batch),
            "--project-id", _runtime_config["project_id"],
            "--location", _runtime_config["location"],
        ]

    classifier = script

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=os.path.dirname(classifier),
        )
        job.process = proc

        assert proc.stdout is not None
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
            job.add_log(line)

        await proc.wait()

        if job.status == "running":
            job.status = "error" if proc.returncode != 0 else "completed"
            job.finished_at = datetime.utcnow().isoformat()

    except asyncio.CancelledError:
        if job.process:
            job.process.terminate()
        job.status = "stopped"
        job.finished_at = datetime.utcnow().isoformat()
        job.add_log("STOPPED")
    except Exception as e:
        job.status = "error"
        job.finished_at = datetime.utcnow().isoformat()
        job.add_log(f"ERROR:{e}")
    finally:
        for q in job._log_subscribers:
            q.put_nowait(None)


# ---------------------------------------------------------------------------
# Helper: read per-batch file stats from disk
# ---------------------------------------------------------------------------

def get_batch_stats(dimension: str, batch: int) -> dict:
    in_path = _get_input_path(dimension, batch)
    out_path = output_path(dimension, batch)

    total = 0
    try:
        with open(in_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        total = len(data)
    except Exception:
        pass

    processed = 0
    code_dist: dict[str, int] = defaultdict(int)
    try:
        with open(out_path, "r", encoding="utf-8") as f:
            out_data = json.load(f)
        if isinstance(out_data, list):
            processed = len(out_data)
            for item in out_data:
                code = str(item.get("Code", "?"))
                code_dist[code] += 1
    except Exception:
        pass

    return {
        "batch": batch,
        "total": total,
        "processed": processed,
        "code_distribution": dict(code_dist),
    }


def get_dim_aggregate(dimension: str, batch_stats: list[dict]) -> dict:
    """Aggregate stats across all batches for a dimension."""
    total = sum(b["total"] for b in batch_stats)
    processed = sum(b["processed"] for b in batch_stats)
    code_dist: dict[str, int] = defaultdict(int)
    for b in batch_stats:
        for code, count in b["code_distribution"].items():
            code_dist[code] += count
    return {
        "total": total,
        "processed": processed,
        "code_distribution": dict(code_dist),
    }


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

# Mutable runtime config (starts from config.py values, changeable via API)
_runtime_config: dict = {
    "project_id": PROJECT_ID,
    "location": LOCATION,
    "gcs_bucket": os.environ.get("GCS_BUCKET", ""),
}


@app.get("/api/config")
async def get_config():
    return _runtime_config


class ConfigUpdate(PydanticModel):
    project_id: str | None = None
    location: str | None = None
    gcs_bucket: str | None = None


@app.patch("/api/config")
async def update_config(update: ConfigUpdate):
    if update.project_id is not None:
        _runtime_config["project_id"] = update.project_id
    if update.location is not None:
        _runtime_config["location"] = update.location
    if update.gcs_bucket is not None:
        _runtime_config["gcs_bucket"] = update.gcs_bucket
    return _runtime_config


# ---------------------------------------------------------------------------
# Dimension CRUD
# ---------------------------------------------------------------------------

class DimensionCreate(PydanticModel):
    id: str
    label: str
    model: str
    prompt_template: str


class DimensionUpdate(PydanticModel):
    label: str | None = None
    model: str | None = None
    prompt_template: str | None = None


@app.get("/api/dimensions/{dim_id}/config")
async def get_dimension_config(dim_id: str):
    if dim_id not in _dimensions:
        raise HTTPException(status_code=404, detail="Dimension not found")
    return {"id": dim_id, **_dimensions[dim_id]}


@app.post("/api/dimensions")
async def create_dimension(req: DimensionCreate):
    if req.id in _dimensions:
        raise HTTPException(status_code=409, detail=f"Dimension '{req.id}' already exists")
    _dimensions[req.id] = {
        "label": req.label,
        "model": req.model,
        "prompt_template": req.prompt_template,
    }
    _save_dimensions()
    return {"id": req.id, **_dimensions[req.id]}


@app.delete("/api/dimensions/{dim_id}")
async def delete_dimension(dim_id: str):
    if dim_id not in _dimensions:
        raise HTTPException(status_code=404, detail="Dimension not found")
    cfg = _dimensions[dim_id]
    # Block deletion if any refinement dimensions reference this one
    children = [k for k, v in _dimensions.items() if v.get("refine_of") == dim_id]
    if children:
        raise HTTPException(status_code=400, detail=f"Cannot delete: refinement dimensions exist ({', '.join(children)}). Delete them first.")

    # Check for running jobs
    for b in _dim_batches(dim_id):
        key = f"{dim_id}:{b}"
        jid = active_job_per_dim_batch.get(key)
        if jid and jobs.get(jid) and jobs[jid].status == "running":
            raise HTTPException(status_code=409, detail=f"Cannot delete: job running for batch {b}")
    fix_key = f"{dim_id}:fix-errors"
    fix_jid = active_job_per_dim_batch.get(fix_key)
    if fix_jid and jobs.get(fix_jid) and jobs[fix_jid].status == "running":
        raise HTTPException(status_code=409, detail="Cannot delete: fix-errors job is running")

    # Clean up associated files
    for b in _dim_batches(dim_id):
        for path in [output_path(dim_id, b), refine_input_path(dim_id, b)]:
            if os.path.exists(path):
                os.remove(path)

    del _dimensions[dim_id]
    _save_dimensions()
    return {"deleted": dim_id}


@app.put("/api/dimensions/{dim_id}")
async def update_dimension(dim_id: str, req: DimensionUpdate):
    if dim_id not in _dimensions:
        raise HTTPException(status_code=404, detail="Dimension not found")
    if req.label is not None:
        _dimensions[dim_id]["label"] = req.label
    if req.model is not None:
        _dimensions[dim_id]["model"] = req.model
    if req.prompt_template is not None:
        _dimensions[dim_id]["prompt_template"] = req.prompt_template
    _save_dimensions()
    return {"id": dim_id, **_dimensions[dim_id]}


class RefineCreate(PydanticModel):
    id: str
    label: str
    model: str
    prompt_template: str


@app.post("/api/dimensions/{parent_id}/refine")
async def create_refine_dimension(parent_id: str, req: RefineCreate):
    if parent_id not in _dimensions:
        raise HTTPException(status_code=404, detail="Parent dimension not found")
    if _dimensions[parent_id].get("refine_of"):
        raise HTTPException(status_code=400, detail="Cannot create a refinement of a refinement")
    if req.id in _dimensions:
        raise HTTPException(status_code=409, detail=f"Dimension '{req.id}' already exists")

    # Collect non-99 sentences from all parent batches (dedup by ID)
    sentences: list[dict] = []
    seen_ids: set = set()
    for b in _dim_batches(parent_id):
        try:
            with open(output_path(parent_id, b), "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                if not isinstance(item, dict) or "ID" not in item:
                    continue
                if item.get("Code") == 99:
                    continue
                iid = item["ID"]
                if iid in seen_ids:
                    continue
                seen_ids.add(iid)
                sentences.append({"ID": iid, "QuasiSentence": item.get("QuasiSentence", "")})
        except Exception:
            pass

    if not sentences:
        raise HTTPException(
            status_code=400,
            detail="No non-99 sentences found. Run the parent classification first.",
        )

    # Equal distribution: ceil(total / 7000) batches, each ≤ 7000
    total = len(sentences)
    n_batches = max(1, math.ceil(total / 7000))
    batch_size = math.ceil(total / n_batches)
    new_batches = list(range(1, n_batches + 1))

    os.makedirs(DATA_DIR, exist_ok=True)
    for i, batch_num in enumerate(new_batches):
        chunk = sentences[i * batch_size: (i + 1) * batch_size]
        with open(refine_input_path(req.id, batch_num), "w", encoding="utf-8") as f:
            json.dump(chunk, f, indent=2, ensure_ascii=False)

    _dimensions[req.id] = {
        "label": req.label,
        "model": req.model,
        "prompt_template": req.prompt_template,
        "refine_of": parent_id,
        "batches": new_batches,
    }
    _save_dimensions()

    return {
        "id": req.id,
        "total_sentences": total,
        "batches": new_batches,
        **_dimensions[req.id],
    }


@app.get("/api/dimensions")
async def list_dimensions():
    result = []
    for dim_id, cfg in _dimensions.items():
        dim_batch_list = _dim_batches(dim_id)
        batches_info = []
        for b in dim_batch_list:
            key = f"{dim_id}:{b}"
            active_job_id = active_job_per_dim_batch.get(key)
            job = jobs.get(active_job_id) if active_job_id else None
            stats = get_batch_stats(dim_id, b)

            # Running job overrides disk stats for processed count
            if job and job.status == "running":
                batch_status = "running"
                stats["processed"] = job.processed
                stats["total"] = job.total or stats["total"]
            elif stats["total"] > 0 and stats["processed"] >= stats["total"]:
                batch_status = "completed"
            elif stats["processed"] > 0:
                batch_status = "partial"
            else:
                batch_status = "idle"

            batches_info.append({
                **stats,
                "status": batch_status,
                "job_id": active_job_id if job and job.status == "running" else None,
            })

        agg = get_dim_aggregate(dim_id, batches_info)

        # Determine dimension-level status
        running_count = sum(1 for b in batches_info if b["status"] == "running")
        completed_count = sum(1 for b in batches_info if b["status"] == "completed")
        if running_count > 0:
            dim_status = "running"
        elif completed_count == len(dim_batch_list):
            dim_status = "completed"
        elif agg["processed"] > 0:
            dim_status = "partial"
        else:
            dim_status = "idle"

        # Check for active fix-errors job
        fix_key = f"{dim_id}:fix-errors"
        fix_job_id = active_job_per_dim_batch.get(fix_key)
        fix_job = jobs.get(fix_job_id) if fix_job_id else None

        result.append({
            "id": dim_id,
            "label": cfg["label"],
            "model": cfg["model"],
            "status": dim_status,
            "total": agg["total"],
            "processed": agg["processed"],
            "code_distribution": agg["code_distribution"],
            "batches": batches_info,
            "refine_of": cfg.get("refine_of"),
            "fix_errors_job_id": fix_job_id if fix_job and fix_job.status == "running" else None,
        })
    return result


class StartJobRequest(PydanticModel):
    dimension: str
    batch: int = 0
    mode: str = "singular"
    max_sentences: int = 0
    fix_errors: bool = False


@app.post("/api/jobs")
async def start_job(req: StartJobRequest):
    if req.mode not in ("singular", "batch"):
        raise HTTPException(status_code=400, detail=f"Invalid mode: {req.mode}. Must be 'singular' or 'batch'")
    if req.mode == "batch" and not _runtime_config.get("gcs_bucket"):
        raise HTTPException(status_code=400, detail="GCS bucket must be configured before using batch mode. Set it in ⚙ Config.")
    if req.dimension not in _dimensions:
        raise HTTPException(status_code=400, detail=f"Unknown dimension: {req.dimension}")

    if req.fix_errors:
        key = f"{req.dimension}:fix-errors"
    else:
        dim_batch_list = _dim_batches(req.dimension)
        if req.batch not in dim_batch_list:
            raise HTTPException(status_code=400, detail=f"Invalid batch: {req.batch}. Must be one of {dim_batch_list}")
        key = f"{req.dimension}:{req.batch}"

    existing_job_id = active_job_per_dim_batch.get(key)
    if existing_job_id:
        existing = jobs.get(existing_job_id)
        if existing and existing.status == "running":
            detail = f"Fix-errors job already running for '{req.dimension}'" if req.fix_errors else f"Job already running for '{req.dimension}' batch {req.batch}"
            raise HTTPException(status_code=409, detail=detail)

    job_id = str(uuid.uuid4())
    job = Job(job_id, req.dimension, req.batch, mode=req.mode, max_sentences=req.max_sentences, fix_errors=req.fix_errors)
    jobs[job_id] = job
    active_job_per_dim_batch[key] = job_id

    asyncio.create_task(run_job(job))
    return {"job_id": job_id, "status": "running", "mode": req.mode}


@app.get("/api/jobs")
async def list_jobs():
    return [j.to_dict() for j in jobs.values()]


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    d = job.to_dict()
    d["logs"] = job.logs[-200:]
    return d


@app.get("/api/jobs/{job_id}/logs")
async def get_job_logs(job_id: str, offset: int = 0):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"logs": job.logs[offset:], "total": len(job.logs), "status": job.status}


@app.get("/api/jobs/{job_id}/stream")
async def stream_logs(job_id: str):
    """Server-Sent Events stream of live log lines."""
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_gen():
        for line in job.logs:
            yield f"data: {json.dumps({'line': line})}\n\n"

        if job.status != "running":
            yield f"data: {json.dumps({'done': True})}\n\n"
            return

        q = job.subscribe()
        try:
            while True:
                try:
                    line = await asyncio.wait_for(q.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if line is None:
                    yield f"data: {json.dumps({'done': True})}\n\n"
                    break
                yield f"data: {json.dumps({'line': line})}\n\n"
        finally:
            job.unsubscribe(q)

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.post("/api/jobs/{job_id}/stop")
async def stop_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "running":
        raise HTTPException(status_code=400, detail="Job is not running")
    if job.process:
        job.process.terminate()
    job.status = "stopped"
    job.finished_at = datetime.utcnow().isoformat()
    return {"status": "stopped"}


@app.get("/api/stats")
async def get_stats():
    total_sentences = 0
    total_processed = 0
    running_jobs = sum(1 for j in jobs.values() if j.status == "running")
    completed_dims = 0

    for dim_id in _dimensions:
        dim_batch_list = _dim_batches(dim_id)
        dim_total = 0
        dim_processed = 0
        dim_completed_batches = 0
        for b in dim_batch_list:
            stats = get_batch_stats(dim_id, b)
            dim_total += stats["total"]
            dim_processed += stats["processed"]
            if stats["total"] > 0 and stats["processed"] >= stats["total"]:
                dim_completed_batches += 1
        total_sentences += dim_total
        total_processed += dim_processed
        if dim_completed_batches == len(dim_batch_list):
            completed_dims += 1

    return {
        "total_dimensions": len(_dimensions),
        "completed_dimensions": completed_dims,
        "total_sentences": total_sentences,
        "total_processed": total_processed,
        "running_jobs": running_jobs,
        "total_jobs_ever": len(jobs),
    }


@app.get("/api/results/{dim_id}")
async def get_results(
    dim_id: str,
    limit: int = 50,
    offset: int = 0,
    code: str | None = None,
):
    """Return paginated results for a dimension (merged across all batches).

    Optional `code` filter narrows the result set *before* pagination so each
    code value gets its own contiguous, fully-paginated list. Accepts the
    string forms used in output files: "1", "0", "-1", "99", "ERROR".
    """
    if dim_id not in _dimensions:
        raise HTTPException(status_code=404, detail="Dimension not found")

    # Merge all batches, dedup by ID
    merged: dict[int, dict] = {}
    for b in _dim_batches(dim_id):
        out_path = output_path(dim_id, b)
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                if isinstance(item, dict) and "ID" in item:
                    iid = item["ID"]
                    if iid not in merged or merged[iid].get("Code") == "ERROR":
                        merged[iid] = item
        except Exception:
            pass

    all_records = sorted(merged.values(), key=lambda x: x.get("ID", 0))

    if code is not None and code != "" and code != "all":
        all_records = [r for r in all_records if str(r.get("Code")) == code]

    return {
        "dimension": dim_id,
        "total": len(all_records),
        "offset": offset,
        "limit": limit,
        "code": code,
        "results": all_records[offset: offset + limit],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
