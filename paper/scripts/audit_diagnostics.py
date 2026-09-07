#!/usr/bin/env python3
"""Reproduce the review's added diagnostics; read-only, no SNAP statistical imports.

Implements the independent audit's request grouping and nominal agreement screen.
Results are exploratory; no scoring, threshold or historical result is changed.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime
import hashlib
from itertools import combinations
import json
from pathlib import Path
import sqlite3
import statistics
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.local_paths import fresh_directory


def agreement(pairs):
    n = len(pairs)
    a, b = Counter(x for x, y in pairs), Counter(y for x, y in pairs)
    observed = sum(x == y for x, y in pairs) / n
    expected = sum(a[k] * b[k] for k in a.keys() | b.keys()) / n**2
    return {
        "n": n,
        "exact": observed,
        "kappa": (observed - expected) / (1 - expected) if expected < 1 else None,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "artifacts/runs/review-diagnostics"
    )
    args = parser.parse_args()
    source = ROOT / "data/snap_poc_v3_1.db"
    if not source.is_file():
        parser.error("Retained campaign database required; see docs/DATA.md")
    cfg = yaml.safe_load((ROOT / "config/models.yaml").read_text())
    model_ids = {m["id"]: m["openrouter_model_id"] for m in cfg["models"]}
    paths = [
        source,
        ROOT / "config/models.yaml",
        ROOT / "src/runner.py",
        ROOT / "src/api_client.py",
        Path(__file__),
    ]
    hashes = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in paths
    }
    with sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
        rows = [dict(r) for r in conn.execute("SELECT * FROM responses ORDER BY id")]
    try:
        out = fresh_directory(args.output_dir, ROOT, ("artifacts/runs",))
    except ValueError as error:
        parser.error(str(error))
    groups, by_item = defaultdict(list), defaultdict(list)
    for row in rows:
        messages = []
        if row["system_prompt_text"]:
            messages.append(
                {"role": "system", "content": row["system_prompt_text"].strip()}
            )
        messages.append({"role": "user", "content": row["user_prompt_text"]})
        request = {
            "model": model_ids[row["model"]],
            "messages": messages,
            "max_tokens": cfg["collection"]["max_tokens"],
        }
        if row["temperature_applied"]:
            request["temperature"] = row["temperature"]
        if row["top_p_applied"]:
            request["top_p"] = cfg["collection"]["top_p"]
        signature = hashlib.sha256(
            json.dumps(request, sort_keys=True).encode()
        ).hexdigest()
        groups[(row["model"], signature)].append(row)
        by_item[row["item_id"]].append(row)
    pairs = []
    for (model, signature), group in groups.items():
        for a, b in combinations(sorted(group, key=lambda r: r["run"]), 2):
            pairs.append(
                {
                    "model": model,
                    "item_id": a["item_id"],
                    "system_prompt": a["system_prompt"],
                    "run_a": a["run"],
                    "run_b": b["run"],
                    "score_a": a["score_final"],
                    "score_b": b["score_final"],
                    "request_signature": signature,
                    "raw_text_equal": a["raw_response"] == b["raw_response"],
                    "prompt_tokens_equal": a["prompt_tokens"] == b["prompt_tokens"],
                    "delta_seconds": abs(
                        (
                            datetime.fromisoformat(a["timestamp"])
                            - datetime.fromisoformat(b["timestamp"])
                        ).total_seconds()
                    ),
                }
            )
    item_rows = []
    for item, group in sorted(by_item.items()):
        complete = [
            (r["score_judge1"], r["score_judge2"])
            for r in group
            if r["score_judge1"] is not None and r["score_judge2"] is not None
        ]
        item_rows.append(
            {
                "item": item,
                **agreement(complete),
                "final_counts": json.dumps(
                    dict(Counter(r["score_final"] for r in group)), sort_keys=True
                ),
            }
        )
    for filename, records in [
        ("gpt52_opportunistic_pairs.csv", pairs),
        ("item_agreement.csv", item_rows),
    ]:
        with (out / filename).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)
    scores = [(r["score_a"], r["score_b"]) for r in pairs]
    deltas = [r["delta_seconds"] for r in pairs]
    report = {
        "status": "exploratory_review_diagnostics",
        "input_sha256": hashes,
        "request_reconstruction": "Stored messages and sent/omitted flags; endpoint, max_tokens and top_p inferred from retained config/code, not captured per-call payloads.",
        "provider_equivalence_verified": False,
        "repeated_pairs": len(pairs),
        "models": dict(Counter(r["model"] for r in pairs)),
        "run_pairs": dict(Counter(f"{r['run_a']}/{r['run_b']}" for r in pairs)),
        "score_agreement": agreement(scores),
        "score_pearson": statistics.correlation(
            [int(a) for a, b in scores], [int(b) for a, b in scores]
        ),
        "raw_text_equal": sum(r["raw_text_equal"] for r in pairs),
        "different_prompt_token_counts": sum(
            not r["prompt_tokens_equal"] for r in pairs
        ),
        "storage_time_deltas_seconds": {
            "min": min(deltas),
            "median": statistics.median(deltas),
            "max": max(deltas),
        },
        "item_kappas_below_060": [
            r["item"] for r in item_rows if r["kappa"] is not None and r["kappa"] < 0.6
        ],
        "E1_judge1": dict(Counter(r["score_judge1"] for r in by_item["E1"])),
        "E1_judge2": dict(Counter(r["score_judge2"] for r in by_item["E1"])),
        "source_files_unchanged": all(
            hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h
            for p, h in hashes.items()
        ),
    }
    assert report["source_files_unchanged"]
    (out / "audit_diagnostics.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: report[k]
                for k in [
                    "repeated_pairs",
                    "score_agreement",
                    "different_prompt_token_counts",
                    "item_kappas_below_060",
                    "source_files_unchanged",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
