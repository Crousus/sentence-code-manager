#!/usr/bin/env python3
"""
Batch prediction classifier using Google Cloud Batch Prediction API.

Usage:
  python batch_classifier.py --dimension childcare --batch 1 --gcs-bucket my-bucket
  python batch_classifier.py --dimension childcare --batch 1 --gcs-bucket my-bucket --max-sentences 500

Re-attach behaviour:
  If a previous run was stopped (SIGTERM) while a Google Cloud batch job was
  still running, this script saves a tracking file
  (data/.batch_state_{dim}_{batch}.json). On the next invocation it detects
  the file, queries the remote job status, and re-attaches to the poll loop
  instead of creating a duplicate job.

Structured log protocol (stdout) — compatible with classifier.py:
  TOTAL:{n}            total sentences in input file
  RESUME:{n}           already processed (skipping)
  LOG:{msg}            informational message
  SUCCESS:{id}:{code}  classified successfully
  FAILED:{id}          permanent failure for sentence
  PROGRESS:{done}      cumulative count after result parsing
  COMPLETE             all sentences processed
  ERROR:{msg}          fatal startup error
"""

import argparse
import json
import os
import signal
import sys
import time
import uuid

from google import genai
from google.cloud import storage
from google.genai.types import CreateBatchJobConfig
from pydantic import BaseModel

# Add backend dir to path so config.py is importable regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DIMENSIONS, DATA_DIR, LOCATION, PROJECT_ID, input_path, output_path, refine_input_path


def _get_input_file(dimension: str, batch: int) -> str:
    """Return refine input if present, else fall back to standard rlang sentences."""
    custom = refine_input_path(dimension, batch)
    if os.path.exists(custom):
        return custom
    return input_path(batch)


class Classification(BaseModel):
    ID: int
    QuasiSentence: str
    Code: int


# ---------------------------------------------------------------------------
# Batch state tracking — persists across process restarts
# ---------------------------------------------------------------------------

def _state_path(dimension: str, batch: int) -> str:
    return os.path.join(DATA_DIR, f".batch_state_{dimension}_{batch}.json")


def _save_state(dimension: str, batch: int, state: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(_state_path(dimension, batch), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _load_state(dimension: str, batch: int) -> dict | None:
    path = _state_path(dimension, batch)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _clear_state(dimension: str, batch: int) -> None:
    path = _state_path(dimension, batch)
    if os.path.exists(path):
        os.remove(path)


# ---------------------------------------------------------------------------
# Globals for signal handler
# ---------------------------------------------------------------------------
_current_dimension = None
_current_batch = None


def _handle_sigterm(signum, frame):
    """Exit cleanly — the remote batch job keeps running on Google Cloud.
    The tracking file persists so the next run can re-attach."""
    print("LOG:Process stopped — remote batch job continues on Google Cloud", flush=True)
    sys.exit(0)


signal.signal(signal.SIGTERM, _handle_sigterm)


_ACTIVE_STATES = (
    "JOB_STATE_RUNNING", "JOB_STATE_PENDING", "JOB_STATE_QUEUED",
    "JobState.JOB_STATE_RUNNING", "JobState.JOB_STATE_PENDING", "JobState.JOB_STATE_QUEUED",
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _poll_until_done(client, job_name: str):
    """Poll a batch job until it leaves an active state. Returns the final job object."""
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


def _parse_and_merge(results: list[dict], remaining: list[dict], classified_list: list, out_path: str) -> None:
    """Parse batch prediction results, merge into classified_list, and save.

    Results are matched to input sentences by ID (not by index position) because
    the Batch Prediction API does not guarantee output lines preserve input order.
    Sentences with no matching result are written as ERROR.
    """
    remaining_by_id: dict[int, dict] = {s["ID"]: s for s in remaining}
    result_ids: set[int] = set()

    for result in results:
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
            result_ids.add(parsed_id)

            if "QuasiSentence" not in parsed:
                source = remaining_by_id.get(parsed_id, {})
                parsed["QuasiSentence"] = source.get("QuasiSentence", "")

            classified_list.append(parsed)
            print(f"SUCCESS:{parsed_id}:{parsed['Code']}", flush=True)

        except Exception as e:
            label = str(parsed_id) if parsed_id is not None else "unknown"
            print(f"FAILED:{label}:{e}", flush=True)

        print(f"PROGRESS:{len(classified_list)}", flush=True)

    # Any submitted sentence that had no result gets written as ERROR
    for item in remaining:
        if item["ID"] not in result_ids:
            classified_list.append({
                "ID": item["ID"],
                "QuasiSentence": item.get("QuasiSentence", ""),
                "Code": "ERROR",
            })
            print(f"FAILED:{item['ID']}:no result returned by batch API", flush=True)
            print(f"PROGRESS:{len(classified_list)}", flush=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(classified_list, f, indent=2, ensure_ascii=False)

    print("COMPLETE", flush=True)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def classify_batch(
    dimension: str,
    batch: int,
    project_id: str = PROJECT_ID,
    location: str = LOCATION,
    gcs_bucket: str = "",
    max_sentences: int = 0,
) -> None:
    global _current_dimension, _current_batch
    _current_dimension = dimension
    _current_batch = batch

    cfg = DIMENSIONS.get(dimension)
    if not cfg:
        print(f"ERROR:Unknown dimension '{dimension}'. Available: {', '.join(DIMENSIONS)}", flush=True)
        sys.exit(1)

    if not gcs_bucket:
        print("ERROR:--gcs-bucket is required for batch prediction", flush=True)
        sys.exit(1)

    in_path = _get_input_file(dimension, batch)
    out_path = output_path(dimension, batch)
    prompt_template = cfg["prompt_template"]

    # --- Load input ---
    try:
        with open(in_path, "r", encoding="utf-8") as f:
            sentences = json.load(f)
    except FileNotFoundError:
        print(f"ERROR:Input file not found: {in_path}", flush=True)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR:Invalid JSON in input: {e}", flush=True)
        sys.exit(1)

    print(f"TOTAL:{len(sentences)}", flush=True)

    # --- Resume logic ---
    processed_ids: set = set()
    classified_list: list = []

    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, list):
                classified_list = existing
                for item in existing:
                    if isinstance(item, dict) and "ID" in item:
                        processed_ids.add(item["ID"])
        except (json.JSONDecodeError, IOError):
            classified_list = []

    print(f"RESUME:{len(processed_ids)}", flush=True)

    # --- Check for a saved batch job to re-attach to ---
    saved = _load_state(dimension, batch)
    if saved:
        job_name = saved.get("batch_job_name")
        saved_bucket = saved.get("gcs_bucket", gcs_bucket)
        gcs_output_prefix = saved.get("gcs_output_prefix")
        remaining = saved.get("remaining", [])

        print(f"LOG:Found saved batch job — checking status of {job_name}", flush=True)
        try:
            client = genai.Client(vertexai=True, project=project_id, location=location)
            batch_job = client.batches.get(name=job_name)
            state = str(batch_job.state)
            print(f"LOG:Remote batch job state: {state}", flush=True)

            if state in _ACTIVE_STATES:
                # Re-attach: poll until done
                print(f"LOG:Re-attaching to running batch job {job_name}", flush=True)
                batch_job = _poll_until_done(client, job_name)
                state = str(batch_job.state)

            if "SUCCEEDED" in state:
                # Download and merge results
                storage_client = storage.Client(project=project_id)
                bucket_obj = storage_client.bucket(saved_bucket)
                try:
                    results = _download_results(bucket_obj, gcs_output_prefix)
                    _clear_state(dimension, batch)
                    _parse_and_merge(results, remaining, classified_list, out_path)
                    return
                except Exception as e:
                    print(f"ERROR:Failed to download results: {e}", flush=True)
                    _clear_state(dimension, batch)
                    sys.exit(1)
            else:
                # Job failed or was cancelled — clean up and proceed with new job
                print(f"LOG:Previous batch job ended with state: {state} — starting fresh", flush=True)
                _clear_state(dimension, batch)

        except Exception as e:
            print(f"LOG:Could not query saved batch job ({e}) — starting fresh", flush=True)
            _clear_state(dimension, batch)

    # --- Filter to unprocessed sentences ---
    remaining = [s for s in sentences if s.get("ID") not in processed_ids]

    if max_sentences > 0:
        remaining = remaining[:max_sentences]

    if not remaining:
        print("LOG:No unprocessed sentences to classify", flush=True)
        print(f"PROGRESS:{len(classified_list)}", flush=True)
        print("COMPLETE", flush=True)
        return

    print(f"LOG:Preparing {len(remaining)} sentences for batch prediction", flush=True)

    # --- Build JSONL for batch API ---
    schema = Classification.model_json_schema()
    jsonl_lines = []
    for item in remaining:
        current_id = item.get("ID")
        sentence = item.get("QuasiSentence", "")
        prompt = prompt_template.replace("{ID}", str(current_id)).replace("{sentence}", sentence)

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
    gcs_input_blob = f"batch_input/{dimension}_{batch}_{ts}_{job_uuid}.jsonl"
    gcs_output_prefix = f"batch_output/{dimension}_{batch}_{ts}_{job_uuid}"

    try:
        storage_client = storage.Client(project=project_id)
        bucket_obj = storage_client.bucket(gcs_bucket)
        blob = bucket_obj.blob(gcs_input_blob)
        blob.upload_from_string(jsonl_content, content_type="application/jsonl")
        gcs_input_uri = f"gs://{gcs_bucket}/{gcs_input_blob}"
        print(f"LOG:Uploaded {len(remaining)} requests to {gcs_input_uri}", flush=True)
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
    _save_state(dimension, batch, {
        "batch_job_name": batch_job.name,
        "gcs_bucket": gcs_bucket,
        "gcs_output_prefix": gcs_output_prefix,
        "remaining": remaining,
    })

    # --- Poll for completion ---
    batch_job = _poll_until_done(client, batch_job.name)

    succeeded = "SUCCEEDED" in str(batch_job.state)
    if not succeeded:
        _clear_state(dimension, batch)
        print(f"ERROR:Batch job ended with state: {batch_job.state}", flush=True)
        sys.exit(1)

    # --- Download results from GCS ---
    try:
        results = _download_results(bucket_obj, gcs_output_prefix)
    except Exception as e:
        print(f"ERROR:Failed to download results: {e}", flush=True)
        sys.exit(1)

    _clear_state(dimension, batch)
    _parse_and_merge(results, remaining, classified_list, out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch prediction classifier")
    parser.add_argument("--dimension", required=True, help="Dimension to classify")
    parser.add_argument("--batch", type=int, required=True, help="Batch number")
    parser.add_argument("--project-id", default=PROJECT_ID, help="GCP project ID")
    parser.add_argument("--location", default=LOCATION, help="Vertex AI location")
    parser.add_argument("--gcs-bucket", required=True, help="GCS bucket name (without gs:// prefix)")
    parser.add_argument("--max-sentences", type=int, default=0, help="Max sentences to process (0 = all)")
    args = parser.parse_args()

    classify_batch(
        dimension=args.dimension,
        batch=args.batch,
        project_id=args.project_id,
        location=args.location,
        gcs_bucket=args.gcs_bucket,
        max_sentences=args.max_sentences,
    )


if __name__ == "__main__":
    main()
