#!/usr/bin/env python3
"""Cross-variant OTNS versus ESP32-C6 packet/ACK residual analysis.

The two campaigns are independent samples.  This tool never pairs runs across
platforms: it normalizes runs within each platform and compares distribution
statistics with an independent-sample bootstrap.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


VALID_VARIANTS = (
    "stock",
    "stock-low-power",
    "ucast",
    "fast-attach-corrected",
    "fast-attach-ucast-1",
)
HW_VARIANT = {"fast-attach-corrected": "fast-attach"}
OTNS_DIR = {
    variant: f"results/{variant}-n100-pcap-comparison-20260919"
    for variant in VALID_VARIANTS
}
INTERVALS = {
    "parent_request_to_response_ms": ("parent_request_time", "parent_response_time"),
    "parent_response_to_child_id_request_ms": ("parent_response_time", "child_id_request_time"),
    "child_id_request_to_response_ms": ("child_id_request_time", "child_id_response_time"),
    "full_attach_ms": ("parent_request_time", "child_id_response_time"),
    "parent_request_to_ack_ms": ("parent_request_time", "parent_request_ack_time"),
    "parent_request_ack_to_parent_response_ms": ("parent_request_ack_time", "parent_response_time"),
    "parent_response_to_ack_ms": ("parent_response_time", "parent_response_ack_time"),
    "parent_response_ack_to_child_id_request_ms": ("parent_response_ack_time", "child_id_request_time"),
    "child_id_request_to_ack_ms": ("child_id_request_time", "child_id_request_ack_time"),
    "child_id_request_ack_to_child_id_response_ms": ("child_id_request_ack_time", "child_id_response_time"),
}
FRAME_NAMES = ("parent_request", "parent_response", "child_id_request", "child_id_response")


def fnum(value: Any) -> float | None:
    if value in (None, "", "N/A"):
        return None
    return float(value)


def delta_ms(start: Any, end: Any) -> float | None:
    a, b = fnum(start), fnum(end)
    return None if a is None or b is None else round((b - a) * 1000.0, 6)


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def describe(values: Iterable[float | None]) -> dict[str, float | int | None]:
    data = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not data:
        return {key: None for key in ("n", "mean", "sd", "median", "iqr", "p05", "p25", "p75", "p95", "min", "max", "trimmed_mean")}
    trim = max(0, math.floor(len(data) * 0.1))
    ordered = sorted(data)
    trimmed = ordered[trim:len(ordered) - trim] if trim and len(ordered) > 2 * trim else ordered
    p25, p75 = percentile(data, .25), percentile(data, .75)
    return {
        "n": len(data), "mean": statistics.mean(data),
        "sd": statistics.stdev(data) if len(data) > 1 else 0.0,
        "median": statistics.median(data), "iqr": p75 - p25,
        "p05": percentile(data, .05), "p25": p25, "p75": p75,
        "p95": percentile(data, .95), "min": min(data), "max": max(data),
        "trimmed_mean": statistics.mean(trimmed),
    }


def bootstrap_difference(a: list[float], b: list[float], statistic: str, seed: int, iterations: int) -> tuple[float, float, float]:
    """Return A-B point estimate and independent bootstrap 95% CI."""
    fn = statistics.mean if statistic == "mean" else statistics.median
    rng = random.Random(seed)
    estimates = []
    for _ in range(iterations):
        aa = [rng.choice(a) for _ in a]
        bb = [rng.choice(b) for _ in b]
        estimates.append(fn(aa) - fn(bb))
    return fn(a) - fn(b), percentile(estimates, .025), percentile(estimates, .975)


def run_json(command: list[str]) -> Any:
    process = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return json.loads(process.stdout)


def tshark_frames(tshark: str, pcap: Path, wanted: dict[str, int]) -> dict[str, Any]:
    minimum, maximum = min(wanted.values()), max(wanted.values())
    command = [
        tshark, "-r", str(pcap), "-Y", f"frame.number >= {max(1, minimum - 4)} && frame.number <= {maximum + 8}",
        "-T", "fields", "-E", "header=y", "-E", "separator=,", "-E", "quote=d", "-E", "occurrence=f",
    ]
    fields = ("frame.number", "frame.time_epoch", "frame.len", "wpan.frame_type", "wpan.seq_no", "wpan.ack_request", "wpan.src64", "wpan.dst64", "wpan.src16", "wpan.dst16")
    for field in fields:
        command.extend(("-e", field))
    process = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    rows = list(csv.DictReader(process.stdout.splitlines()))
    by_number = {int(row["frame.number"]): row for row in rows if row.get("frame.number")}
    result: dict[str, Any] = {}
    selected_numbers = set(wanted.values())
    sequence_lo, sequence_hi = minimum, maximum
    selected_seq: list[str] = []
    retransmission = False
    duplicate = False
    for name, number in wanted.items():
        frame = by_number.get(number, {})
        seq = frame.get("wpan.seq_no", "")
        result[f"{name}_seq"] = seq
        result[f"{name}_length"] = frame.get("frame.len", "")
        result[f"{name}_ack_requested"] = frame.get("wpan.ack_request", "").lower() in ("1", "true")
        if seq:
            if seq in selected_seq:
                duplicate = True
            selected_seq.append(seq)
        ack = None
        if result[f"{name}_ack_requested"] and seq:
            for candidate_number in range(number + 1, min(number + 5, maximum + 9)):
                candidate = by_number.get(candidate_number)
                if not candidate:
                    continue
                if candidate.get("wpan.frame_type") in ("2", "0x0002") and candidate.get("wpan.seq_no") == seq:
                    ack = candidate
                    break
                if candidate_number in selected_numbers:
                    break
        result[f"{name}_ack_frame"] = int(ack["frame.number"]) if ack else ""
        result[f"{name}_ack_time"] = float(ack["frame.time_epoch"]) if ack else ""
        result[f"{name}_ack_match"] = "mac_sequence_and_adjacency" if ack else "unavailable"
    # A repeated selected sequence or a same-sequence data frame within the selected window is retained and flagged.
    for row in rows:
        number = int(row["frame.number"])
        if sequence_lo <= number <= sequence_hi and row.get("wpan.frame_type") in ("1", "0x0001"):
            seq = row.get("wpan.seq_no", "")
            if seq and number not in selected_numbers and seq in selected_seq:
                retransmission = True
    result["duplicate_sequence_observed"] = duplicate
    result["retransmission_observed"] = retransmission
    return result


def normalized_row(platform: str, variant: str, routers: int, source_run: str, sample_index: int,
                   pcap: Path, frames: dict[str, int], times: dict[str, float], delay_ms: float | None,
                   tshark_data: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "platform": platform, "variant": variant, "routers": routers,
        "source_run": source_run, "sample_index": sample_index, "pcap": str(pcap),
        "protocol_response_delay_ms": delay_ms if delay_ms is not None else "",
        "sequence_complete": all(name in frames and name in times for name in FRAME_NAMES),
    }
    for name in FRAME_NAMES:
        row[f"{name}_frame"] = frames.get(name, "")
        row[f"{name}_time"] = times.get(name, "")
        row[f"{name}_length"] = tshark_data.get(f"{name}_length", "")
        row[f"{name}_seq"] = tshark_data.get(f"{name}_seq", "")
        if name != "child_id_response":
            row[f"{name}_ack_frame"] = tshark_data.get(f"{name}_ack_frame", "")
            row[f"{name}_ack_time"] = tshark_data.get(f"{name}_ack_time", "")
            row[f"{name}_ack_match"] = tshark_data.get(f"{name}_ack_match", "unavailable")
    for metric, (start, end) in INTERVALS.items():
        row[metric] = delta_ms(row.get(start), row.get(end))
    pr_rsp = row["parent_request_to_response_ms"]
    row["adjusted_parent_request_to_response_ms"] = (
        round(float(pr_rsp) - delay_ms, 6) if pr_rsp is not None and delay_ms is not None else ""
    )
    row["retransmission_observed"] = tshark_data["retransmission_observed"]
    row["duplicate_sequence_observed"] = tshark_data["duplicate_sequence_observed"]
    return row


def load_otns(root: Path, tshark: str, workers: int) -> list[dict[str, Any]]:
    jobs = []
    for variant in VALID_VARIANTS:
        directory = root / OTNS_DIR[variant]
        accepted = directory / "accepted_runs.csv"
        if not accepted.exists():
            raise FileNotFoundError(f"required OTNS data missing: {accepted}")
        with accepted.open(newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                routers, index = int(raw["routers"]), int(raw["sample_index"])
                frames = {
                    "parent_request": int(raw["parent_request_frame"]),
                    "parent_response": int(raw["parent_response_frame"]),
                    "child_id_request": int(raw["child_id_request_frame"]),
                    "child_id_response": int(raw["child_id_response_frame"]),
                }
                times = {name: float(raw[f"{name}_timestamp_s"]) for name in FRAME_NAMES}
                pcap = directory / raw["pcap_file"]
                delay = 1.0 if variant == "fast-attach-ucast-1" else None
                jobs.append(("otns", variant, routers, raw["source_summary"], index, pcap, frames, times, delay))
    return execute_frame_jobs(jobs, tshark, workers)


def hardware_group_json(hardware_root: Path, variant: str, routers: int) -> list[dict[str, Any]]:
    repo = hardware_root.parents[2]
    analyzer = repo / "testing/scripts/analyze_test_logs.py"
    python = repo / ".venv/bin/python"
    group = hardware_root / HW_VARIANT.get(variant, variant) / f"{routers}-routers/runs"
    if not group.exists():
        raise FileNotFoundError(f"required hardware data missing: {group}")
    return run_json([
        str(python), str(analyzer), "--logs-dir", str(group), "--network-key", "dfd34f0f05cad978ec4e32b0413038ff",
        "--subtract-parent-response-random-delay", "--json", "--reuse-pcap-csv",
    ])


def load_hardware(hardware_root: Path, tshark: str, workers: int) -> list[dict[str, Any]]:
    jobs = []
    for variant in VALID_VARIANTS:
        for routers in (2, 3, 4):
            results = hardware_group_json(hardware_root, variant, routers)
            if len(results) != 100:
                raise RuntimeError(f"expected 100 hardware runs for {variant}/{routers}, got {len(results)}")
            for index, result in enumerate(results, 1):
                complete = [seq for seq in result["attach_sequences"] if seq.get("complete_pcap_attach")]
                if not complete:
                    raise RuntimeError(f"no complete hardware sequence: {result['manifest_path']}")
                # This documented capture crosses midnight. The analyzer retains
                # chronological capture order, so recovery is the first complete
                # item after time-of-day normalization rather than the last item.
                seq = complete[0] if "20260914-235554-run06" in result["manifest_path"] else complete[-1]
                mapping = {
                    "parent_request": "send_parent_request", "parent_response": "receive_parent_response",
                    "child_id_request": "send_child_id_request", "child_id_response": "receive_child_id_response",
                }
                frames = {name: int(seq["pcap_frame_numbers"][key]) for name, key in mapping.items()}
                epochs = seq.get("pcap_event_epochs", {})
                if epochs:
                    times = {name: float(epochs[key]) for name, key in mapping.items()}
                else:
                    # Recover exact epochs from tshark below; placeholders are replaced before normalization.
                    times = {}
                run_dir = Path(result["manifest_path"]).parent
                pcaps = sorted(run_dir.glob("*.pcap*"))
                if len(pcaps) != 1:
                    raise RuntimeError(f"expected one hardware capture in {run_dir}, found {len(pcaps)}")
                delay = fnum(seq.get("parent_response_random_delay_ms"))
                if variant == "fast-attach-ucast-1" and delay is None:
                    delay = 1.0
                jobs.append(("hardware", variant, routers, str(run_dir), index, pcaps[0], frames, times, delay))
    return execute_frame_jobs(jobs, tshark, workers)


def execute_frame_jobs(jobs: list[tuple[Any, ...]], tshark: str, workers: int) -> list[dict[str, Any]]:
    def execute(job: tuple[Any, ...]) -> dict[str, Any]:
        platform, variant, routers, source, index, pcap, frames, times, delay = job
        decoded = tshark_frames(tshark, pcap, frames)
        if not times:
            command = [tshark, "-r", str(pcap), "-Y", " || ".join(f"frame.number == {n}" for n in frames.values()),
                       "-T", "fields", "-E", "separator=,", "-e", "frame.number", "-e", "frame.time_epoch"]
            process = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            epoch_by_frame = {int(line.split(",")[0]): float(line.split(",")[1]) for line in process.stdout.splitlines() if line}
            times = {name: epoch_by_frame[number] for name, number in frames.items()}
        return normalized_row(platform, variant, routers, source, index, pcap, frames, times, delay, decoded)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(execute, jobs))
    return sorted(rows, key=lambda row: (row["platform"], row["variant"], row["routers"], row["sample_index"]))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty dataset: {path}")
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def analyze(rows: list[dict[str, Any]], iterations: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summary, comparisons = [], []
    metrics = list(INTERVALS) + ["adjusted_parent_request_to_response_ms"]
    for variant in VALID_VARIANTS:
        for routers in (2, 3, 4):
            groups = {platform: [r for r in rows if r["platform"] == platform and r["variant"] == variant and r["routers"] == routers] for platform in ("otns", "hardware")}
            for metric in metrics:
                distributions = {}
                for platform, group in groups.items():
                    values = [fnum(row.get(metric)) for row in group]
                    distributions[platform] = [value for value in values if value is not None]
                    stats = describe(values)
                    summary.append({"platform": platform, "variant": variant, "routers": routers, "metric": metric, **stats})
                hw, sim = distributions["hardware"], distributions["otns"]
                comparison = {"variant": variant, "routers": routers, "metric": metric,
                              "hardware_n": len(hw), "otns_n": len(sim)}
                if hw and sim:
                    mean_seed = int(hashlib.sha256(f"{variant}|{routers}|{metric}|mean".encode()).hexdigest()[:8], 16)
                    median_seed = int(hashlib.sha256(f"{variant}|{routers}|{metric}|median".encode()).hexdigest()[:8], 16)
                    mean, mean_lo, mean_hi = bootstrap_difference(hw, sim, "mean", mean_seed, iterations)
                    median, median_lo, median_hi = bootstrap_difference(hw, sim, "median", median_seed, iterations)
                    comparison.update({"hardware_mean_ms": statistics.mean(hw), "otns_mean_ms": statistics.mean(sim),
                                       "delta_mean_ms": mean, "delta_mean_ci95_low_ms": mean_lo, "delta_mean_ci95_high_ms": mean_hi,
                                       "hardware_median_ms": statistics.median(hw), "otns_median_ms": statistics.median(sim),
                                       "delta_median_ms": median, "delta_median_ci95_low_ms": median_lo, "delta_median_ci95_high_ms": median_hi})
                comparisons.append(comparison)
    return summary, comparisons


def outlier_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for platform in ("otns", "hardware"):
        for variant in VALID_VARIANTS:
            for routers in (2, 3, 4):
                group = [r for r in rows if r["platform"] == platform and r["variant"] == variant and r["routers"] == routers]
                for metric in ("parent_request_to_response_ms", "parent_response_to_child_id_request_ms", "child_id_request_to_response_ms", "full_attach_ms"):
                    values = [float(r[metric]) for r in group if r.get(metric) not in (None, "")]
                    q1, q3 = percentile(values, .25), percentile(values, .75)
                    lo, hi = q1 - 3 * (q3 - q1), q3 + 3 * (q3 - q1)
                    for row in group:
                        value = fnum(row.get(metric))
                        if value is not None and (value < lo or value > hi):
                            retransmission = row["retransmission_observed"]
                            duplicate = row["duplicate_sequence_observed"]
                            classification = (
                                "retransmission_or_repeated_attempt" if retransmission
                                else "duplicate_selected_mac_sequence" if duplicate
                                else "valid_complete_sequence_long_tail"
                            )
                            output.append({"platform": platform, "variant": variant, "routers": routers, "metric": metric,
                                           "value_ms": value, "outer_fence_low_ms": lo, "outer_fence_high_ms": hi,
                                           "source_run": row["source_run"], "retransmission_observed": retransmission,
                                           "duplicate_sequence_observed": duplicate, "classification": classification,
                                           "disposition": "retained"})
    return output


def comparison_index(comparisons: list[dict[str, Any]]) -> dict[tuple[str, int, str], dict[str, Any]]:
    return {(row["variant"], int(row["routers"]), row["metric"]): row for row in comparisons}


def fmt(value: Any) -> str:
    return "N/A" if value in (None, "") else f"{float(value):.3f}"


def render_tables(comparisons: list[dict[str, Any]]) -> str:
    indexed = comparison_index(comparisons)
    lines = [
        "# Generated cross-variant tables", "",
        "Values are means in milliseconds; delta is hardware minus OTNS. Campaigns are independent samples.", "",
        "| Variant | Routers | OTNS PR→PRsp | HW PR→PRsp | Δ | OTNS PRsp→CIDReq | HW PRsp→CIDReq | Δ | OTNS CIDReq→CIDRsp | HW CIDReq→CIDRsp | Δ | OTNS Full | HW Full | Δ |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    core = ("parent_request_to_response_ms", "parent_response_to_child_id_request_ms", "child_id_request_to_response_ms", "full_attach_ms")
    for variant in VALID_VARIANTS:
        for routers in (2, 3, 4):
            cells = []
            for metric in core:
                row = indexed[(variant, routers, metric)]
                cells.extend((fmt(row.get("otns_mean_ms")), fmt(row.get("hardware_mean_ms")), fmt(row.get("delta_mean_ms"))))
            lines.append(f"| {variant} | {routers} | " + " | ".join(cells) + " |")
    lines.extend(["", "## ACK decomposition", "",
                  "Values are platform means in milliseconds. `N/A` is expected for multicast Parent Requests, which do not request an ACK.", "",
                  "| Variant | Routers | OTNS PR→ACK | HW PR→ACK | OTNS ACK(PR)→PRsp | HW ACK(PR)→PRsp | OTNS PRsp→ACK | HW PRsp→ACK | OTNS ACK(PRsp)→CIDReq | HW ACK(PRsp)→CIDReq | OTNS CIDReq→ACK | HW CIDReq→ACK | OTNS ACK(CIDReq)→CIDRsp | HW ACK(CIDReq)→CIDRsp |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"])
    deep = ("parent_request_to_ack_ms", "parent_request_ack_to_parent_response_ms", "parent_response_to_ack_ms", "parent_response_ack_to_child_id_request_ms", "child_id_request_to_ack_ms", "child_id_request_ack_to_child_id_response_ms")
    for variant in VALID_VARIANTS:
        for routers in (2, 3, 4):
            cells = []
            for metric in deep:
                row = indexed[(variant, routers, metric)]
                cells.extend((fmt(row.get("otns_mean_ms")), fmt(row.get("hardware_mean_ms"))))
            lines.append(f"| {variant} | {routers} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--hardware-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tshark", default="tshark")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--bootstrap-iterations", type=int, default=5000)
    args = parser.parse_args()
    root, hardware, output = args.repo_root.resolve(), args.hardware_results.resolve(), args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = load_otns(root, args.tshark, args.workers) + load_hardware(hardware, args.tshark, args.workers)
    if len(rows) != 3000:
        raise RuntimeError(f"expected 3000 normalized observations, got {len(rows)}")
    summary, comparisons = analyze(rows, args.bootstrap_iterations)
    outliers = outlier_rows(rows)
    clean_rows = [row for row in rows if not row["retransmission_observed"] and not row["duplicate_sequence_observed"]]
    clean_summary, _ = analyze(clean_rows, args.bootstrap_iterations)
    write_csv(output / "normalized_runs.csv", rows)
    write_csv(output / "interval_summary.csv", summary)
    write_csv(output / "cross_variant_comparison.csv", comparisons)
    write_csv(output / "ack_turnaround_summary.csv", [r for r in summary if "ack" in r["metric"]])
    write_csv(output / "outliers.csv", outliers or [{"disposition": "none"}])
    write_csv(output / "clean_exchange_summary.csv", clean_summary)
    (output / "generated_tables.md").write_text(render_tables(comparisons), encoding="utf-8")
    manifest = {
        "schema_version": 1, "analysis": "independent-sample cross-variant platform residuals",
        "valid_variants": list(VALID_VARIANTS), "excluded_historical_dataset": "results/fast-attach-n100-pcap-comparison-20260919",
        "otns_commit": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
        "hardware_commit": subprocess.check_output(["git", "-C", str(hardware.parents[2]), "rev-parse", "HEAD"], text=True).strip(),
        "openthread_commit": "a12ff0d0f54fd41954b45047fcdd08f302731c5f",
        "sample_count": len(rows), "samples_per_platform_variant_topology": 100,
        "bootstrap_iterations": args.bootstrap_iterations, "tshark": args.tshark,
        "sources": {"otns": [OTNS_DIR[v] for v in VALID_VARIANTS], "hardware": str(hardware)},
        "ack_rule": "ACK request required; matching MAC sequence; within next four frames; stop at next selected MLE frame",
    }
    (output / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    generated = [output / name for name in ("normalized_runs.csv", "interval_summary.csv", "cross_variant_comparison.csv", "ack_turnaround_summary.csv", "outliers.csv", "clean_exchange_summary.csv", "generated_tables.md", "source_manifest.json")]
    (output / "checksums.sha256").write_text("".join(f"{checksum(path)}  {path.name}\n" for path in generated), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "summary_rows": len(summary), "comparison_rows": len(comparisons), "outliers": len(outliers), "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
