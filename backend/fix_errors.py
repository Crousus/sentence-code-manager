#!/usr/bin/env python3
"""
Fix ERROR entries across all batch output files for a dimension.

Scans every output_{dimension}_{batch}.json, collects entries where
Code == "ERROR", reprocesses them (singular or batch prediction mode),
and writes the fixed results back into their original output files.

Re-attach behaviour (batch mode only):
  If a previous run was stopped while a Google Cloud batch job was still
  running, a tracking file (data/.batch_state_{dim}_fix_errors.json) is
  saved. On the next invocation it detects the file, queries the remote
  job, and re-attaches instead of creating a duplicate.

Usage:
  python fix_errors.py --dimension childcare --mode singular
  python fix_errors.py --dimension childcare --mode batch --gcs-bucket my-bucket

Structured log protocol (stdout) — compatible with classifier.py:
  TOTAL:{n}            total error sentences found
  RESUME:0             (always 0 — resume is implicit via re-scan)
  LOG:{msg}            informational message
  PROCESSING:{id}      starting sentence (singular only)
  SUCCESS:{id}:{code}  fixed successfully
  RETRY:{id}:{attempt} retrying after error (singular only)
  FAILED:{id}          permanent failure after all retries
  PROGRESS:{done}      cumulative count of processed errors
  COMPLETE             all errors processed
  ERROR:{msg}          fatal startup error
"""

import argparse
import json
import os
import signal
import sys
import time
import uuid

import vertexai
from pydantic import BaseModel
from vertexai.generative_models import GenerationConfig, GenerativeModel

from google import genai
from google.cloud import storage
from google.genai.types import CreateBatchJobConfig

# Add backend dir to path so config.py is importable regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DIMENSIONS, BATCHES, DATA_DIR, LOCATION, PROJECT_ID, output_path


class Classification(BaseModel):
    ID: int
    QuasiSentence: str
    Code: int


# ---------------------------------------------------------------------------
# Batch state tracking — persists across process restarts
# ---------------------------------------------------------------------------

def _state_path(dimension: str) -> str:
    return os.path.join(DATA_DIR, f".batch_state_{dimension}_fix_errors.json")


def _save_state(dimension: str, state: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_state_path(dimension), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _load_state(dimension: str) -> dict | None:
    path = _state_path(dimension)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _clear_state(dimension: str) -> None:
    path = _state_path(dimension)
    if os.path.exists(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# Signal handler — exit cleanly, keep remote job alive
# ---------------------------------------------------------------------------

def _handle_sigterm(signum, frame):
    """Exit cleanly — the remote batch job keeps running on Google Cloud."""
    print("LOG:Process stopped — remote batch job continues on Google Cloud", flush=True)
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_sigterm)


_ACTIVE_STATES = (
    "JOB_STATE_RUNNING", "JOB_STATE_PENDING", "JOB_STATE_QUEUED",
    "JobState.JOB_STATE_RUNNING", "JobState.JOB_STATE_PENDING", "JobState.JOB_STATE_QUEUED",
)


# ---------------------------------------------------------------------------
# Error collection
# ---------------------------------------------------------------------------

def collect_errors(dimension: str) -> tuple[list[dict], dict[int, list]]:
    """
    Scan all output files for this dimension.

    Returns:
        errors: list of {"ID", "QuasiSentence", "source_batch"} for every ERROR entry
        batch_data: {batch_num: [records]} — in-memory copy of each output file
    """
    cfg = DIMENSIONS.get(dimension, {})
    batch_list = cfg.get("batches", BATCHES)

    errors: list[dict] = []
    batch_data: dict[int, list] = {}

    for batch_num in batch_list:
        out_path = output_path(dimension, batch_num)
        if not os.path.exists(out_path):
            continue
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except (json.JSONDecodeError, IOError):
            continue

        batch_data[batch_num] = records
        for record in records:
            if isinstance(record, dict) and record.get("Code") == "ERROR":
                errors.append({
                    "ID": record["ID"],
                    "QuasiSentence": record.get("QuasiSentence", ""),
                    "source_batch": batch_num,
                })

    return errors, batch_data


def _save_batch(dimension: str, batch_num: int, records: list) -> None:
    """Write records back to the output file for a given batch."""
    out_path = output_path(dimension, batch_num)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def _update_record(
    batch_data: dict[int, list],
    dimension: str,
    sentence_id: int,
    new_record: dict,
    source_batch: int,
) -> None:
    """Replace the ERROR entry in the in-memory batch data and persist to disk."""
    records = batch_data.get(source_batch, [])
    for i, record in enumerate(records):
        if record.get("ID") == sentence_id:
            records[i] = new_record
            _save_batch(dimension, source_batch, records)
            return


# ---------------------------------------------------------------------------
# Shared: poll + download helpers
# ---------------------------------------------------------------------------

def _poll_until_done(client, job_name: str):
    """Poll a batch job until it leaves an active state."""
    last_state = None
    while True:
        try:
            batch_job = client.batches.get(name=job_name)
        except Exception as e:
            print(f"LOG:Poll error (retrying): {e}", flush=True)
            time.sleep(10)
            continue

        state = str(batch_job.state)
        if state != last_state:
            print(f"LOG:Batch job state: {state}", flush=True)
            last_state = state

        if state not in _ACTIVE_STATES:
            break

        time.sleep(30)

    return batch_job


def _download_results(bucket_obj, gcs_output_prefix: str) -> list[dict]:
    """Download and parse prediction results from GCS."""
    print("LOG:Downloading results from GCS", flush=True)
    blobs = list(bucket_obj.list_blobs(prefix=gcs_output_prefix))
    prediction_blobs = [b for b in blobs if b.name.endswith(".jsonl")]

    if not prediction_blobs:
        print("ERROR:No prediction output files found in GCS", flush=True)
        sys.exit(1)

    results = []
    for pb in prediction_blobs:
        content = pb.download_as_text()
        for line in content.strip().split("\n"):
            line = line.strip()
            if line:
                results.append(json.loads(line))

    print(f"LOG:Downloaded {len(results)} results", flush=True)
    return results


# ---------------------------------------------------------------------------
# Singular mode — one sentence at a time via vertexai
# ---------------------------------------------------------------------------

def fix_singular(
    errors: list[dict],
    batch_data: dict[int, list],
    dimension: str,
    cfg: dict,
    project_id: str,
    location: str,
) -> None:
    vertexai.init(project=project_id, location=location)
    model = GenerativeModel(cfg["model"])
    gen_config = GenerationConfig(
        response_mime_type="application/json",
        response_schema=Classification.model_json_schema(),
        temperature=0.0,
    )
    prompt_template = cfg["prompt_template"]

    done = 0
    for error in errors:
        sid = error["ID"]
        sentence = error["QuasiSentence"]
        source_batch = error["source_batch"]

        print(f"PROCESSING:{sid}", flush=True)
        prompt = prompt_template.replace("{ID}", str(sid)).replace("{sentence}", sentence)

        success = False
        for attempt in range(1, 7):
            try:
                response = model.generate_content(prompt, generation_config=gen_config)
                parsed = json.loads(response.text)
                _update_record(batch_data, dimension, sid, parsed, source_batch)
                success = True
                print(f"SUCCESS:{sid}:{parsed.get('Code')}", flush=True)
                break
            except Exception as e:
                print(f"RETRY:{sid}:{attempt}:{e}", flush=True)
                if attempt < 6:
                    time.sleep(2 * attempt)

        if not success:
            print(f"FAILED:{sid}", flush=True)

        done += 1
        print(f"PROGRESS:{done}", flush=True)

    print("COMPLETE", flush=True)


# ---------------------------------------------------------------------------
# Batch mode — Google Cloud Batch Prediction API
# ---------------------------------------------------------------------------

def _apply_batch_results(
    results: list[dict],
    errors: list[dict],
    batch_data: dict[int, list],
    dimension: str,
) -> None:
    """Parse batch prediction results and update output files in-place.

    Results are matched to errors by ID (not by index position) because the
    Batch Prediction API does not guarantee that output lines preserve the
    order of the input requests.
    """
    # Build lookup so we can find source_batch and QuasiSentence by sentence ID
    error_by_id: dict[int, dict] = {e["ID"]: e for e in errors}

    done = 0
    for i, result in enumerate(results):
        parsed_id: int | None = None
        try:
            response = result.get("response", {})
            candidates = response.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates in response")

            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            parsed = json.loads(text)

            if "ID" not in parsed or "Code" not in parsed:
                raise ValueError(f"Missing required fields: {parsed}")

            parsed_id = parsed["ID"]
            error = error_by_id.get(parsed_id)

            if error:
                if "QuasiSentence" not in parsed:
                    parsed["QuasiSentence"] = error["QuasiSentence"]
                _update_record(batch_data, dimension, error["ID"], parsed, error["source_batch"])
            else:
                print(f"LOG:Result ID {parsed_id} not in error list — skipping", flush=True)

            print(f"SUCCESS:{parsed_id}:{parsed['Code']}", flush=True)

        except Exception as e:
            label = str(parsed_id) if parsed_id is not None else f"result[{i}]"
            print(f"FAILED:{label}:{e}", flush=True)

        done += 1
        print(f"PROGRESS:{done}", flush=True)

    # Mark any errors that had no matching result as still failed
    result_ids = set()
    for result in results:
        try:
            text = result.get("response", {}).get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            result_ids.add(json.loads(text).get("ID"))
        except Exception:
            pass
    for error in errors:
        if error["ID"] not in result_ids:
            print(f"LOG:No result found for ID {error['ID']} — ERROR entry unchanged", flush=True)

    print("COMPLETE", flush=True)


def fix_batch(
    errors: list[dict],
    batch_data: dict[int, list],
    dimension: str,
    cfg: dict,
    project_id: str,
    location: str,
    gcs_bucket: str,
) -> None:
    prompt_template = cfg["prompt_template"]
    schema = Classification.model_json_schema()

    # --- Check for a saved batch job to re-attach to ---
    saved = _load_state(dimension)
    if saved:
        job_name = saved.get("batch_job_name")
        saved_bucket = saved.get("gcs_bucket", gcs_bucket)
        gcs_output_prefix = saved.get("gcs_output_prefix")
        saved_errors = saved.get("errors", errors)

        print(f"LOG:Found saved batch job — checking status of {job_name}", flush=True)
        try:
            client = genai.Client(vertexai=True, project=project_id, location=location)
            batch_job = client.batches.get(name=job_name)
            state = str(batch_job.state)
            print(f"LOG:Remote batch job state: {state}", flush=True)

            if state in _ACTIVE_STATES:
                print(f"LOG:Re-attaching to running batch job {job_name}", flush=True)
                batch_job = _poll_until_done(client, job_name)
                state = str(batch_job.state)

            if "SUCCEEDED" in state:
                storage_client = storage.Client(project=project_id)
                bucket_obj = storage_client.bucket(saved_bucket)
                try:
                    results = _download_results(bucket_obj, gcs_output_prefix)
                    _clear_state(dimension)
                    # Re-collect batch_data fresh (may have changed since save)
                    _, fresh_batch_data = collect_errors(dimension)
                    # Merge with any batch_data we already have
                    for k, v in fresh_batch_data.items():
                        if k not in batch_data:
                            batch_data[k] = v
                    _apply_batch_results(results, saved_errors, batch_data, dimension)
                    return
                except Exception as e:
                    print(f"ERROR:Failed to download results: {e}", flush=True)
                    _clear_state(dimension)
                    sys.exit(1)
            else:
                print(f"LOG:Previous batch job ended with state: {state} — starting fresh", flush=True)
                _clear_state(dimension)

        except Exception as e:
            print(f"LOG:Could not query saved batch job ({e}) — starting fresh", flush=True)
            _clear_state(dimension)

    # --- Build JSONL ---
    jsonl_lines = []
    for error in errors:
        prompt = prompt_template.replace("{ID}", str(error["ID"])).replace("{sentence}", error["QuasiSentence"])
        request = {
            "request": {
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": schema,
                    "temperature": 0,
                },
            }
        }
        jsonl_lines.append(json.dumps(request, ensure_ascii=False))

    jsonl_content = "\n".join(jsonl_lines)

    # --- Upload to GCS ---
    job_uuid = uuid.uuid4().hex[:8]
    ts = int(time.time())
    gcs_input_blob = f"batch_input/{dimension}_fix_errors_{ts}_{job_uuid}.jsonl"
    gcs_output_prefix = f"batch_output/{dimension}_fix_errors_{ts}_{job_uuid}"

    try:
        storage_client = storage.Client(project=project_id)
        bucket_obj = storage_client.bucket(gcs_bucket)
        blob = bucket_obj.blob(gcs_input_blob)
        blob.upload_from_string(jsonl_content, content_type="application/jsonl")
        gcs_input_uri = f"gs://{gcs_bucket}/{gcs_input_blob}"
        print(f"LOG:Uploaded {len(errors)} requests to {gcs_input_uri}", flush=True)
    except Exception as e:
        print(f"ERROR:GCS upload failed: {e}", flush=True)
        sys.exit(1)

    # --- Submit batch job ---
    gcs_output_uri = f"gs://{gcs_bucket}/{gcs_output_prefix}"
    try:
        client = genai.Client(vertexai=True, project=project_id, location=location)
        batch_job = client.batches.create(
            model=cfg["model"],
            src=gcs_input_uri,
            config=CreateBatchJobConfig(dest=gcs_output_uri),
        )
        print(f"LOG:Batch job submitted: {batch_job.name}", flush=True)
    except Exception as e:
        print(f"ERROR:Batch job creation failed: {e}", flush=True)
        sys.exit(1)

    # --- Save tracking state (survives SIGTERM) ---
    _save_state(dimension, {
        "batch_job_name": batch_job.name,
        "gcs_bucket": gcs_bucket,
        "gcs_output_prefix": gcs_output_prefix,
        "errors": errors,
    })

    # --- Poll for completion ---
    batch_job = _poll_until_done(client, batch_job.name)

    succeeded = "SUCCEEDED" in str(batch_job.state)
    if not succeeded:
        _clear_state(dimension)
        print(f"ERROR:Batch job ended with state: {batch_job.state}", flush=True)
        sys.exit(1)

    # --- Download results from GCS ---
    try:
        results = _download_results(bucket_obj, gcs_output_prefix)
    except Exception as e:
        print(f"ERROR:Failed to download results: {e}", flush=True)
        sys.exit(1)

    _clear_state(dimension)
    _apply_batch_results(results, errors, batch_data, dimension)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Fix ERROR entries across all batch output files")
    parser.add_argument("--dimension", required=True, help="Dimension to fix errors for")
    parser.add_argument("--mode", default="singular", choices=["singular", "batch"],
                        help="Processing mode: singular (one-by-one) or batch (Google Cloud)")
    parser.add_argument("--project-id", default=PROJECT_ID, help="GCP project ID")
    parser.add_argument("--location", default=LOCATION, help="Vertex AI location")
    parser.add_argument("--gcs-bucket", default="", help="GCS bucket name (required for batch mode)")
    parser.add_argument("--max-sentences", type=int, default=0, help="Max errors to process (0 = all)")
    args = parser.parse_args()

    cfg = DIMENSIONS.get(args.dimension)
    if not cfg:
        print(f"ERROR:Unknown dimension '{args.dimension}'. Available: {', '.join(DIMENSIONS)}", flush=True)
        sys.exit(1)

    if args.mode == "batch" and not args.gcs_bucket:
        print("ERROR:--gcs-bucket is required for batch prediction mode", flush=True)
        sys.exit(1)

    # Collect all errors across all batches
    errors, batch_data = collect_errors(args.dimension)

    if args.max_sentences > 0:
        errors = errors[:args.max_sentences]

    print(f"TOTAL:{len(errors)}", flush=True)
    print("RESUME:0", flush=True)

    batches_with_errors = sorted(set(e["source_batch"] for e in errors)) if errors else []
    print(f"LOG:Found {len(errors)} errors across batches {batches_with_errors}", flush=True)

    if not errors:
        print("LOG:No errors to fix", flush=True)
        print("COMPLETE", flush=True)
        return

    if args.mode == "batch":
        fix_batch(errors, batch_data, args.dimension, cfg, args.project_id, args.location, args.gcs_bucket)
    else:
        fix_singular(errors, batch_data, args.dimension, cfg, args.project_id, args.location)


if __name__ == "__main__":
    main()
