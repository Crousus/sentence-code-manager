#!/usr/bin/env python3
"""
Unified manifesto classifier — one script to rule them all.

Usage:
  python classifier.py --dimension childcare --batch 1
  python classifier.py --list

Structured log protocol (stdout):
  TOTAL:{n}            total sentences in input file
  RESUME:{n}           already processed (skipping)
  PROCESSING:{id}      starting sentence
  SUCCESS:{id}:{code}  classified successfully
  RETRY:{id}:{attempt} retrying after error
  FAILED:{id}          permanent failure after all retries
  PROGRESS:{done}      cumulative count after each save
  COMPLETE             all sentences processed
  ERROR:{msg}          fatal startup error
"""

import argparse
import json
import os
import sys
import time

import vertexai
from pydantic import BaseModel
from vertexai.generative_models import GenerationConfig, GenerativeModel

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


def classify(dimension: str, batch: int, project_id: str = PROJECT_ID, location: str = LOCATION) -> None:
    cfg = DIMENSIONS.get(dimension)
    if not cfg:
        print(f"ERROR:Unknown dimension '{dimension}'. Available: {', '.join(DIMENSIONS)}", flush=True)
        sys.exit(1)

    in_path = _get_input_file(dimension, batch)
    out_path = output_path(dimension, batch)
    prompt_template = cfg["prompt_template"]

    # --- Init Vertex AI ---
    try:
        vertexai.init(project=project_id, location=location)
    except Exception as e:
        print(f"ERROR:Vertex AI init failed: {e}", flush=True)
        sys.exit(1)

    model = GenerativeModel(cfg["model"])

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

    gen_config = GenerationConfig(
        response_mime_type="application/json",
        response_schema=Classification.model_json_schema(),
        temperature=0.0,
    )

    # --- Classification loop ---
    for item in sentences:
        current_id = item.get("ID")
        sentence = item.get("QuasiSentence", "")

        if current_id in processed_ids:
            continue

        print(f"PROCESSING:{current_id}", flush=True)

        prompt = prompt_template.replace("{ID}", str(current_id)).replace("{sentence}", sentence)

        success = False
        for attempt in range(1, 7):
            try:
                response = model.generate_content(prompt, generation_config=gen_config)
                parsed = json.loads(response.text)
                classified_list.append(parsed)
                success = True
                print(f"SUCCESS:{current_id}:{parsed.get('Code')}", flush=True)
                break
            except Exception as e:
                print(f"RETRY:{current_id}:{attempt}:{e}", flush=True)
                if attempt < 6:
                    time.sleep(2 * attempt)

        if not success:
            classified_list.append({"ID": current_id, "QuasiSentence": sentence, "Code": "ERROR"})
            print(f"FAILED:{current_id}", flush=True)

        # Incremental save
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(classified_list, f, indent=2, ensure_ascii=False)

        print(f"PROGRESS:{len(classified_list)}", flush=True)

    print("COMPLETE", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified manifesto classifier")
    parser.add_argument("--dimension", help="Dimension to classify (e.g. childcare)")
    parser.add_argument("--batch", type=int, help="Batch number (1-6)")
    parser.add_argument("--project-id", default=PROJECT_ID, help="GCP project ID")
    parser.add_argument("--location", default=LOCATION, help="Vertex AI location")
    parser.add_argument("--list", action="store_true", help="List available dimensions and exit")
    args = parser.parse_args()

    if args.list:
        print("Available dimensions:")
        for key, cfg in DIMENSIONS.items():
            print(f"  {key:15s} — {cfg['label']}")
        return

    if not args.dimension:
        parser.error("--dimension is required (or use --list)")
    if not args.batch:
        parser.error("--batch is required (1-6)")

    classify(args.dimension, args.batch, args.project_id, args.location)


if __name__ == "__main__":
    main()
