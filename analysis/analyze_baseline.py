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
    parser.add_argument(
        "--plot-dir",
        type=Path,
        default=None,
        help="Optional output directory for plots. Requires matplotlib.",
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
    compact_parent_sequence = [
        value for index, value in enumerate(parent_sequence) if index == 0 or value != parent_sequence[index - 1]
    ]
    oscillations = 0
    for left, middle, right in zip(parent_sequence, parent_sequence[1:], parent_sequence[2:]):
        if left == right and left != middle:
            oscillations += 1

    initial_observed_parent = rows[0].get("parent_node_guess")
    final_observed_parent = rows[-1].get("parent_node_guess")
    if switch_times:
        result_classification = "switch_observed"
    elif initial_observed_parent and final_observed_parent:
        result_classification = "no_switch_observed"
    else:
        result_classification = "inconclusive"

    return {
        "file": str(path),
        "sample_count": len(rows),
        "initial_observed_parent": initial_observed_parent,
        "final_observed_parent": final_observed_parent,
        "parent_sequence": compact_parent_sequence,
        "result_classification": result_classification,
        "switch_count": len(switch_times),
        "first_switch_time_s": switch_times[0] if switch_times else None,
        "total_outage_s": total_outage_s,
        "packet_delivery_ratio": round(total_rx / total_tx, 6) if total_tx else None,
        "oscillation_events": oscillations,
        "parent_ids_seen": sorted({value for value in parent_sequence if value}),
        "plot_note": "Install matplotlib to add parent/time and position/time plots.",
    }


def _parent_numeric_id(parent_ids_seen: list[str], parent_value: str | None) -> int | None:
    if not parent_value:
        return None
    try:
        return parent_ids_seen.index(parent_value)
    except ValueError:
        return None


def generate_plots(path: Path, summary: dict[str, Any], plot_dir: Path) -> str:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return "matplotlib is not installed; skipping plot generation."

    rows = load_rows(path)
    plot_dir.mkdir(parents=True, exist_ok=True)

    times = [to_float(row["sim_time_s"]) or 0.0 for row in rows]
    positions = [to_float(row["mobile_x"]) or 0.0 for row in rows]
    connectivity = [1 if to_bool(row.get("connectivity_ok")) else 0 for row in rows]
    parent_values = [row.get("parent_node_guess") for row in rows]
    parent_labels = summary["parent_ids_seen"]
    parent_numeric = [_parent_numeric_id(parent_labels, value) for value in parent_values]

    packet_columns = [key for key in rows[0].keys() if key.endswith("_loss_pct")]
    packet_delivery = []
    for row in rows:
        losses = [to_float(row.get(column)) for column in packet_columns]
        valid_losses = [loss for loss in losses if loss is not None]
        if not valid_losses:
            packet_delivery.append(None)
            continue
        packet_delivery.append(1.0 - (sum(valid_losses) / len(valid_losses) / 100.0))

    stem = path.stem

    fig, axis = plt.subplots(figsize=(10, 4))
    axis.step(times, parent_numeric, where="post")
    axis.set_title("Parent over time")
    axis.set_xlabel("Simulation time (s)")
    axis.set_ylabel("Parent")
    axis.set_yticks(range(len(parent_labels)))
    axis.set_yticklabels(parent_labels)
    axis.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(plot_dir / f"{stem}_parent_over_time.png")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(10, 4))
    axis.plot(times, positions)
    axis.set_title("Mobile position over time")
    axis.set_xlabel("Simulation time (s)")
    axis.set_ylabel("Mobile x-position")
    axis.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(plot_dir / f"{stem}_position_over_time.png")
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(10, 4))
    axis.step(times, connectivity, where="post", label="connectivity_ok")
    if any(value is not None for value in packet_delivery):
        numeric_delivery = [value if value is not None else float("nan") for value in packet_delivery]
        axis.plot(times, numeric_delivery, label="packet_delivery_ratio")
    axis.set_title("Connectivity and packet delivery over time")
    axis.set_xlabel("Simulation time (s)")
    axis.set_ylabel("1 = good, 0 = outage")
    axis.set_ylim(-0.05, 1.05)
    axis.grid(True, alpha=0.3)
    axis.legend()
    fig.tight_layout()
    fig.savefig(plot_dir / f"{stem}_connectivity_over_time.png")
    plt.close(fig)

    return f"plots written to {plot_dir}"


def main() -> int:
    args = parse_args()
    summaries = [summarize_run(path) for path in args.inputs]
    plot_messages = []
    if args.plot_dir:
        for path, summary in zip(args.inputs, summaries):
            plot_messages.append(generate_plots(path, summary, args.plot_dir))
    payload = {"runs": summaries}
    if plot_messages:
        payload["plot_status"] = plot_messages

    if args.output_json:
        with args.output_json.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
