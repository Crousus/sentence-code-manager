#!/usr/bin/env python3
"""
Migrate existing rlang/ output files to sol_projekt/data/.

Rules:
- Extract (dimension, batch_number) from filename: output_{dim}_{N}[_anything].json
- Merge all files for the same (dim, batch) → deduplicate by ID
- Write to data/output_{dim}_{N}.json
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DIMENSIONS

RLANG_DIR = "/home/control/rlang"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# Map display dim name variants → config key
DIM_KEYS = set(DIMENSIONS.keys())


def extract_dim_batch(filename: str):
    """
    Given 'output_labour_2_1.json' return ('labour', 2).
    Given 'output_repfam_1_1.json' return ('repfam', 1).
    """
    m = re.match(r"output_(.+?)_(\d+).*\.json$", filename)
    if not m:
        return None, None
    dim = m.group(1)
    batch = int(m.group(2))
    if dim not in DIM_KEYS:
        return None, None
    return dim, batch


def migrate():
    os.makedirs(DATA_DIR, exist_ok=True)

    # Collect all output files from rlang/
    groups: dict[tuple, list[str]] = {}
    for fname in sorted(os.listdir(RLANG_DIR)):
        if not fname.startswith("output_") or not fname.endswith(".json"):
            continue
        dim, batch = extract_dim_batch(fname)
        if dim is None:
            print(f"  SKIP  {fname}  (unrecognised)")
            continue
        key = (dim, batch)
        groups.setdefault(key, []).append(os.path.join(RLANG_DIR, fname))

    migrated = 0
    for (dim, batch), files in sorted(groups.items()):
        dest = os.path.join(DATA_DIR, f"output_{dim}_{batch}.json")

        # Load + merge, dedup by ID
        merged: dict[int, dict] = {}
        for fpath in files:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    if isinstance(item, dict) and "ID" in item:
                        iid = item["ID"]
                        # Prefer non-ERROR over ERROR
                        if iid not in merged or merged[iid].get("Code") == "ERROR":
                            merged[iid] = item
            except Exception as e:
                print(f"  ERROR reading {fpath}: {e}")

        records = list(merged.values())

        # If dest already exists, also merge with it
        if os.path.exists(dest):
            try:
                with open(dest, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                for item in existing:
                    if isinstance(item, dict) and "ID" in item:
                        iid = item["ID"]
                        if iid not in merged or merged[iid].get("Code") == "ERROR":
                            merged[iid] = item
                records = list(merged.values())
            except Exception:
                pass

        with open(dest, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

        src_names = [os.path.basename(p) for p in files]
        print(f"  {dim:15s} batch {batch}  →  {len(records):5d} records  [{', '.join(src_names)}]")
        migrated += 1

    print(f"\nMigrated {migrated} (dim, batch) groups to {DATA_DIR}")


if __name__ == "__main__":
    migrate()
