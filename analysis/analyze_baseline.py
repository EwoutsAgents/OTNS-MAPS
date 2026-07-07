#!/usr/bin/env python3
"""Summarize one or more baseline benchmark CSV files."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="CSV files from scripts/run_baseline.py")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional summary JSON output path",
    )
    return parser.parse_args()


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def to_float(value: str | None) -> float | None:
    if value in (None, "", "None"):
        return None
    return float(value)


def to_bool(value: str | None) -> bool:
    return str(value).lower() in {"1", "true", "yes"}


def summarize_run(path: Path) -> dict[str, Any]:
    rows = load_rows(path)
    if not rows:
        raise ValueError(f"No rows in {path}")

    switch_times = [to_float(row["sim_time_s"]) for row in rows if to_bool(row.get("parent_switch"))]
    connectivity = [to_bool(row.get("connectivity_ok")) for row in rows]
    times = [to_float(row["sim_time_s"]) or 0.0 for row in rows]

    total_tx = 0.0
    total_rx = 0.0
    for row in rows:
        for key, value in row.items():
            if key.endswith("_tx"):
                total_tx += float(value or 0)
            elif key.endswith("_rx"):
                total_rx += float(value or 0)

    outages = []
    outage_start = None
    for row, ok in zip(rows, connectivity):
        now = to_float(row["sim_time_s"]) or 0.0
        if not ok and outage_start is None:
            outage_start = now
        elif ok and outage_start is not None:
            outages.append((outage_start, now))
            outage_start = None
    if outage_start is not None:
        outages.append((outage_start, times[-1]))

    total_outage_s = round(sum(end - start for start, end in outages), 6)

    parent_sequence = [row.get("parent_node_guess") for row in rows if row.get("parent_node_guess")]
    oscillations = 0
    for left, middle, right in zip(parent_sequence, parent_sequence[1:], parent_sequence[2:]):
        if left == right and left != middle:
            oscillations += 1

    return {
        "file": str(path),
        "sample_count": len(rows),
        "switch_count": len(switch_times),
        "first_switch_time_s": switch_times[0] if switch_times else None,
        "total_outage_s": total_outage_s,
        "packet_delivery_ratio": round(total_rx / total_tx, 6) if total_tx else None,
        "oscillation_events": oscillations,
        "parent_ids_seen": sorted({value for value in parent_sequence if value}),
        "plot_note": "Install matplotlib to add parent/time and position/time plots.",
    }


def main() -> int:
    args = parse_args()
    summaries = [summarize_run(path) for path in args.inputs]
    payload = {"runs": summaries}

    if args.output_json:
        with args.output_json.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
