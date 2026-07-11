#!/usr/bin/env python3
"""Summarize one or more baseline benchmark CSV files."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="CSV files or directories containing CSV files from scripts/run_baseline.py",
    )
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


def expand_inputs(inputs: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for path in inputs:
        if path.is_dir():
            expanded.extend(sorted(path.rglob("baseline_run*.csv")))
        else:
            expanded.append(path)
    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for path in expanded:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_paths.append(path)
    return unique_paths


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def to_float(value: str | None) -> float | None:
    if value in (None, "", "None"):
        return None
    return float(value)


def to_bool(value: str | None) -> bool:
    return str(value).lower() in {"1", "true", "yes"}


def counter_value(row: dict[str, str], key: str) -> int | None:
    try:
        counters = json.loads(row.get("mle_counters_json") or "{}")
    except json.JSONDecodeError:
        return None
    value = counters.get(key)
    if value in (None, "", "None"):
        return None
    return int(value)


def sim_rss_probe_prefixes(rows: list[dict[str, str]]) -> list[str]:
    if not rows:
        return []
    prefixes = []
    for key in rows[0]:
        if key.endswith("_sim_rss_method"):
            prefixes.append(key[: -len("_sim_rss_method")])
    return sorted(prefixes)


def sim_rss_probe_stats(rows: list[dict[str, str]], prefix: str) -> dict[str, Any]:
    request_values = [to_float(row.get(f"{prefix}_request_rx_sim_rss_dbm")) for row in rows]
    reply_values = [to_float(row.get(f"{prefix}_reply_rx_sim_rss_dbm")) for row in rows]
    statuses = [row.get(f"{prefix}_sim_rss_match_status") for row in rows if row.get(f"{prefix}_sim_rss_match_status")]
    matched = sum(1 for status in statuses if status == "model_derived")
    ambiguous = sum(1 for status in statuses if status == "ambiguous")
    return {
        "request_rx_dbm_mean": _mean_or_none(request_values),
        "request_rx_dbm_median": _median_or_none(request_values),
        "reply_rx_dbm_mean": _mean_or_none(reply_values),
        "reply_rx_dbm_median": _median_or_none(reply_values),
        "match_rate": round(matched / len(statuses), 6) if statuses else None,
        "ambiguous_events": ambiguous,
    }


def end_dwell_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    positions = [to_float(row.get("mobile_x")) for row in rows]
    numeric_positions = [value for value in positions if value is not None]
    if not numeric_positions:
        return []
    max_x = max(numeric_positions)
    return [row for row in rows if to_float(row.get("mobile_x")) == max_x]


def summarize_run(path: Path) -> dict[str, Any]:
    rows = load_rows(path)
    if not rows:
        raise ValueError(f"No rows in {path}")

    device_profile = rows[0].get("device_profile") or "mobile_end_device"
    thread_device_type = rows[0].get("thread_device_type") or None
    parent_search_config = rows[0].get("parent_search_config") or "unknown"
    packet_probe_reliable = to_bool(rows[0].get("packet_probe_reliable"))
    primary_parent_observation = rows[0].get("primary_parent_observation") or "packet_probe"
    switch_times = [to_float(row["sim_time_s"]) for row in rows if to_bool(row.get("parent_switch"))]
    connectivity = [to_bool(row.get("connectivity_ok")) for row in rows]
    times = [to_float(row["sim_time_s"]) or 0.0 for row in rows]

    total_tx = 0.0
    total_rx = 0.0
    parent_probe_tx = 0.0
    parent_probe_rx = 0.0
    parent_probe_rtt_avg_values: list[float] = []
    for row in rows:
        for key, value in row.items():
            if key.endswith("_tx"):
                if key == "mobile_to_parent_tx":
                    parent_probe_tx += float(value or 0)
                else:
                    total_tx += float(value or 0)
            elif key.endswith("_rx"):
                if key == "mobile_to_parent_rx":
                    parent_probe_rx += float(value or 0)
                else:
                    total_rx += float(value or 0)
        parent_probe_rtt_avg = to_float(row.get("mobile_to_parent_rtt_avg_ms"))
        if parent_probe_rtt_avg is not None:
            parent_probe_rtt_avg_values.append(parent_probe_rtt_avg)

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
    mle_parent_changes = counter_value(rows[-1], "Parent Changes")
    mle_attach_attempts = counter_value(rows[-1], "Attach Attempts")
    mle_better_parent_attach_attempts = counter_value(rows[-1], "Better Parent Attach Attempts")
    sim_prefixes = sim_rss_probe_prefixes(rows)
    sim_total_events = 0
    sim_matched_events = 0
    sim_unmatched_events = 0
    sim_ambiguous_events = 0
    for row in rows:
        for prefix in sim_prefixes:
            method = row.get(f"{prefix}_sim_rss_method")
            status = row.get(f"{prefix}_sim_rss_match_status")
            if not method and not status:
                continue
            sim_total_events += 1
            if status == "model_derived":
                sim_matched_events += 1
            elif status == "ambiguous":
                sim_ambiguous_events += 1
            else:
                sim_unmatched_events += 1
    sim_capture_enabled = sim_total_events > 0 and sim_matched_events > 0
    sim_probe_stats = {
        prefix: sim_rss_probe_stats(rows, prefix)
        for prefix in sim_prefixes
        if sim_capture_enabled
    }
    dwell_rows = end_dwell_rows(rows)
    mobile_parent_end_rssi = [
        to_float(row.get("mobile_to_parent_reply_rx_sim_rss_dbm"))
        for row in dwell_rows
    ]
    mobile_parent_end_lqi = [
        to_float(row.get("mobile_to_parent_reply_rx_sim_lqi"))
        for row in dwell_rows
    ]
    packet_delivery_ratio = (
        round(total_rx / total_tx, 6)
        if total_tx
        else round(parent_probe_rx / parent_probe_tx, 6)
        if parent_probe_tx
        else None
    )
    if switch_times:
        result_classification = "switch_observed"
    elif initial_observed_parent and final_observed_parent:
        result_classification = "no_switch_observed"
    else:
        result_classification = "inconclusive"

    return {
        "file": str(path),
        "device_profile": device_profile,
        "thread_device_type": thread_device_type,
        "parent_search_config": parent_search_config,
        "packet_probe_reliable": packet_probe_reliable,
        "primary_parent_observation": primary_parent_observation,
        "sample_count": len(rows),
        "initial_observed_parent": initial_observed_parent,
        "final_observed_parent": final_observed_parent,
        "parent_sequence": compact_parent_sequence,
        "result_classification": result_classification,
        "switch_count": len(switch_times),
        "first_switch_time_s": switch_times[0] if switch_times else None,
        "switch_position_x": next(
            (to_float(row.get("mobile_x")) for row in rows if to_bool(row.get("parent_switch"))),
            None,
        ),
        "total_outage_s": total_outage_s,
        "packet_delivery_ratio": packet_delivery_ratio,
        "parent_probe_enabled": "mobile_to_parent_tx" in rows[0],
        "parent_probe_total_tx": int(parent_probe_tx),
        "parent_probe_total_rx": int(parent_probe_rx),
        "parent_probe_delivery_ratio": round(parent_probe_rx / parent_probe_tx, 6) if parent_probe_tx else None,
        "parent_probe_mean_rtt_avg_ms": _mean_or_none(parent_probe_rtt_avg_values),
        "sim_ping_rss_capture_enabled": sim_capture_enabled,
        "sim_ping_rss_capture_method": "otns_model_derived_at_ping" if sim_capture_enabled else None,
        "sim_ping_rss_policy": "request_and_reply_when_available",
        "sim_ping_rss_total_probe_events": sim_total_events,
        "sim_ping_rss_matched_probe_events": sim_matched_events,
        "sim_ping_rss_match_rate": round(sim_matched_events / sim_total_events, 6) if sim_total_events else None,
        "sim_ping_rss_unmatched_probe_events": sim_unmatched_events,
        "sim_ping_rss_ambiguous_probe_events": sim_ambiguous_events,
        "sim_ping_rss_probe_stats": sim_probe_stats,
        "mobile_to_parent_end_dwell_sim_rss_dbm_mean": _mean_or_none(mobile_parent_end_rssi),
        "mobile_to_parent_end_dwell_sim_rss_dbm_median": _median_or_none(mobile_parent_end_rssi),
        "mobile_to_parent_end_dwell_sim_lqi_median": _median_or_none(mobile_parent_end_lqi),
        "oscillation_events": oscillations,
        "mle_parent_changes": mle_parent_changes,
        "mle_attach_attempts": mle_attach_attempts,
        "mle_better_parent_attach_attempts": mle_better_parent_attach_attempts,
        "parent_ids_seen": sorted({value for value in parent_sequence if value}),
        "plot_note": "Install matplotlib to add parent/time and position/time plots.",
        "observability_note": (
            "Packet probes are marked unreliable for this run; connectivity is derived from parent/state observation."
            if not packet_probe_reliable
            else None
        ),
    }


def _mean_or_none(values: list[float | None]) -> float | None:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return round(statistics.mean(numeric), 6)


def _min_or_none(values: list[float | None]) -> float | None:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return round(min(numeric), 6)


def _max_or_none(values: list[float | None]) -> float | None:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return round(max(numeric), 6)


def _median_or_none(values: list[float | None]) -> float | None:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    return round(statistics.median(numeric), 6)


def _stddev_or_none(values: list[float | None]) -> float | None:
    numeric = [value for value in values if value is not None]
    if not numeric:
        return None
    if len(numeric) == 1:
        return 0.0
    return round(statistics.stdev(numeric), 6)


def _iqr_or_none(values: list[float | None]) -> float | None:
    numeric = sorted(value for value in values if value is not None)
    if not numeric:
        return None
    if len(numeric) == 1:
        return 0.0
    q1, _, q3 = statistics.quantiles(numeric, n=4, method="inclusive")
    return round(q3 - q1, 6)


def _sample_size(values: list[float | None]) -> int:
    return sum(1 for value in values if value is not None)


def aggregate_runs(summaries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(summaries) < 2:
        return None

    switch_times = [summary.get("first_switch_time_s") for summary in summaries]
    switch_positions = [summary.get("switch_position_x") for summary in summaries]
    outage_values = [summary.get("total_outage_s") for summary in summaries]
    pdr_values = [summary.get("packet_delivery_ratio") for summary in summaries]
    parent_probe_pdr_values = [summary.get("parent_probe_delivery_ratio") for summary in summaries]
    parent_probe_rtt_values = [summary.get("parent_probe_mean_rtt_avg_ms") for summary in summaries]
    mobile_parent_end_rssi_values = [
        summary.get("mobile_to_parent_end_dwell_sim_rss_dbm_mean") for summary in summaries
    ]
    sim_match_rate_values = [summary.get("sim_ping_rss_match_rate") for summary in summaries]
    switch_counts = [summary.get("switch_count") or 0 for summary in summaries]
    oscillation_values = [summary.get("oscillation_events") or 0 for summary in summaries]
    classification_counts: dict[str, int] = {}
    for summary in summaries:
        classification = summary.get("result_classification") or "unknown"
        classification_counts[classification] = classification_counts.get(classification, 0) + 1

    switch_observed_runs = sum(1 for summary in summaries if summary.get("switch_count"))
    oscillation_runs = sum(1 for value in oscillation_values if value > 0)
    return {
        "run_count": len(summaries),
        "switch_observed_runs": switch_observed_runs,
        "switch_observed_rate": round(switch_observed_runs / len(summaries), 6),
        "classification_counts": classification_counts,
        "mean_switch_count": round(statistics.mean(switch_counts), 6),
        "median_switch_count": round(statistics.median(switch_counts), 6),
        "stddev_switch_count": round(statistics.stdev(switch_counts), 6) if len(switch_counts) > 1 else 0.0,
        "min_switch_count": min(switch_counts),
        "max_switch_count": max(switch_counts),
        "mean_first_switch_time_s": _mean_or_none(switch_times),
        "median_first_switch_time_s": _median_or_none(switch_times),
        "stddev_first_switch_time_s": _stddev_or_none(switch_times),
        "iqr_first_switch_time_s": _iqr_or_none(switch_times),
        "min_first_switch_time_s": _min_or_none(switch_times),
        "max_first_switch_time_s": _max_or_none(switch_times),
        "switch_time_sample_size": _sample_size(switch_times),
        "mean_switch_position_x": _mean_or_none(switch_positions),
        "median_switch_position_x": _median_or_none(switch_positions),
        "stddev_switch_position_x": _stddev_or_none(switch_positions),
        "min_switch_position_x": _min_or_none(switch_positions),
        "max_switch_position_x": _max_or_none(switch_positions),
        "switch_position_sample_size": _sample_size(switch_positions),
        "mean_total_outage_s": _mean_or_none(outage_values),
        "median_total_outage_s": _median_or_none(outage_values),
        "stddev_total_outage_s": _stddev_or_none(outage_values),
        "iqr_total_outage_s": _iqr_or_none(outage_values),
        "min_total_outage_s": _min_or_none(outage_values),
        "max_total_outage_s": _max_or_none(outage_values),
        "outage_sample_size": _sample_size(outage_values),
        "mean_packet_delivery_ratio": _mean_or_none(pdr_values),
        "median_packet_delivery_ratio": _median_or_none(pdr_values),
        "stddev_packet_delivery_ratio": _stddev_or_none(pdr_values),
        "iqr_packet_delivery_ratio": _iqr_or_none(pdr_values),
        "min_packet_delivery_ratio": _min_or_none(pdr_values),
        "max_packet_delivery_ratio": _max_or_none(pdr_values),
        "pdr_sample_size": _sample_size(pdr_values),
        "mean_parent_probe_delivery_ratio": _mean_or_none(parent_probe_pdr_values),
        "median_parent_probe_delivery_ratio": _median_or_none(parent_probe_pdr_values),
        "stddev_parent_probe_delivery_ratio": _stddev_or_none(parent_probe_pdr_values),
        "parent_probe_pdr_sample_size": _sample_size(parent_probe_pdr_values),
        "mean_parent_probe_rtt_avg_ms": _mean_or_none(parent_probe_rtt_values),
        "median_parent_probe_rtt_avg_ms": _median_or_none(parent_probe_rtt_values),
        "stddev_parent_probe_rtt_avg_ms": _stddev_or_none(parent_probe_rtt_values),
        "parent_probe_rtt_sample_size": _sample_size(parent_probe_rtt_values),
        "mean_mobile_to_parent_end_dwell_sim_rss_dbm": _mean_or_none(mobile_parent_end_rssi_values),
        "median_mobile_to_parent_end_dwell_sim_rss_dbm": _median_or_none(mobile_parent_end_rssi_values),
        "stddev_mobile_to_parent_end_dwell_sim_rss_dbm": _stddev_or_none(mobile_parent_end_rssi_values),
        "mobile_to_parent_end_dwell_sim_rss_sample_size": _sample_size(mobile_parent_end_rssi_values),
        "mean_sim_ping_rss_match_rate": _mean_or_none(sim_match_rate_values),
        "median_sim_ping_rss_match_rate": _median_or_none(sim_match_rate_values),
        "mean_oscillation_events": round(statistics.mean(oscillation_values), 6),
        "oscillation_runs": oscillation_runs,
        "oscillation_rate": round(oscillation_runs / len(summaries), 6),
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
    expanded_inputs = expand_inputs(args.inputs)
    summaries = [summarize_run(path) for path in expanded_inputs]
    plot_messages = []
    if args.plot_dir:
        for path, summary in zip(expanded_inputs, summaries):
            plot_messages.append(generate_plots(path, summary, args.plot_dir))
    payload = {"runs": summaries}
    aggregate = aggregate_runs(summaries)
    if aggregate is not None:
        payload["aggregate"] = aggregate
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
