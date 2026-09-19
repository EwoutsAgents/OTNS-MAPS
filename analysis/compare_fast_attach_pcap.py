#!/usr/bin/env python3
"""Build an n-sample OTNS event/PCAP versus hardware-PCAP timing report."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import statistics
from pathlib import Path
from typing import Any


INTERVALS = (
    ("parent_request_to_response", "Parent Request -> Parent Response"),
    ("parent_response_to_child_id_request", "Parent Response -> Child ID Request"),
    ("child_id_request_to_response", "Child ID Request -> Child ID Response"),
    ("parent_request_to_child_id_response", "Full attach"),
)
HARDWARE_COLUMNS = {
    "parent_request_to_response": (
        "parent_request_to_parent_response_mean_ms",
        "parent_request_to_parent_response_sd_ms",
    ),
    "parent_response_to_child_id_request": (
        "parent_response_to_child_id_request_mean_ms",
        "parent_response_to_child_id_request_sd_ms",
    ),
    "child_id_request_to_response": (
        "child_id_request_to_child_id_response_mean_ms",
        "child_id_request_to_child_id_response_sd_ms",
    ),
    "parent_request_to_child_id_response": ("full_attach_mean_ms", "full_attach_sd_ms"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--campaign",
        action="append",
        required=True,
        metavar="ROUTERS=PATH",
        help="Campaign directory; repeat PATH for replacements with another option.",
    )
    parser.add_argument("--hardware-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--variant", default="fast-attach-ucast-1")
    parser.add_argument("--limit", type=int, default=100)
    return parser.parse_args()


def parse_campaigns(values: list[str]) -> dict[int, list[Path]]:
    campaigns: dict[int, list[Path]] = {}
    for value in values:
        router_text, separator, path_text = value.partition("=")
        if not separator:
            raise ValueError(f"Campaign must use ROUTERS=PATH: {value}")
        routers = int(router_text)
        campaigns.setdefault(routers, []).append(Path(path_text))
    return campaigns


def load_hardware(path: Path, variant: str) -> dict[int, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = csv.DictReader(handle)
        return {
            int(row["routers"]): row
            for row in rows
            if row["variant"] == variant
        }


def load_selected(campaigns: list[Path], limit: int) -> tuple[list[tuple[Path, dict[str, Any]]], list[dict[str, Any]]]:
    candidates: list[tuple[Path, dict[str, Any]]] = []
    exclusions: list[dict[str, Any]] = []
    for campaign in campaigns:
        for path in sorted(campaign.rglob("baseline_summary_*.json")):
            summary = json.loads(path.read_text(encoding="utf-8"))
            accepted = (
                summary.get("result_classification") in {"selected_target_reached", "switch_observed"}
                and summary.get("protocol_timing_source") == "otns_pcap"
                and summary.get("protocol_timing_complete") is True
                and (
                    not summary.get("fast_attach", {}).get("expected")
                    or summary.get("fast_attach", {}).get("valid") is True
                )
                and all(summary.get("protocol_timing_ms", {}).get(key) is not None for key, _ in INTERVALS)
            )
            if accepted:
                candidates.append((path, summary))
            else:
                exclusions.append(
                    {
                        "summary": str(path),
                        "classification": summary.get("result_classification"),
                        "timing_source": summary.get("protocol_timing_source"),
                        "timing_failure_reason": summary.get("protocol_timing_failure_reason"),
                    }
                )
    if len(candidates) < limit:
        raise ValueError(f"Only {len(candidates)} accepted runs are available; {limit} required")
    return candidates[:limit], exclusions + [
        {"summary": str(path), "reason": "beyond_requested_sample_size"}
        for path, _summary in candidates[limit:]
    ]


def stats(values: list[float]) -> dict[str, float | int]:
    return {
        "n": len(values),
        "mean_ms": round(statistics.mean(values), 6),
        "sample_sd_ms": round(statistics.stdev(values), 6) if len(values) > 1 else 0.0,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def format_stat(value: dict[str, float | int]) -> str:
    return f'{float(value["mean_ms"]):.3f} +/- {float(value["sample_sd_ms"]):.3f}'


def timing_delta(pcap: dict[str, float | int], hardware: dict[str, float | int]) -> dict[str, float]:
    hardware_mean = float(hardware["mean_ms"])
    delta_ms = float(pcap["mean_ms"]) - hardware_mean
    return {
        "delta_ms": round(delta_ms, 6),
        "delta_percent": round(delta_ms / hardware_mean * 100.0, 6),
    }


def main() -> int:
    args = parse_args()
    campaigns = parse_campaigns(args.campaign)
    hardware = load_hardware(args.hardware_csv, args.variant)
    args.output_dir.mkdir(parents=True, exist_ok=False)

    result_rows: list[dict[str, Any]] = []
    accepted_rows: list[dict[str, Any]] = []
    selection: dict[str, Any] = {"sample_limit": args.limit, "router_counts": {}}
    report_rows: list[tuple[int, str, dict[str, Any] | None, dict[str, Any], dict[str, Any], dict[str, float]]] = []
    for routers in sorted(campaigns):
        selected, excluded = load_selected(campaigns[routers], args.limit)
        if routers not in hardware:
            raise ValueError(f"No hardware row for {routers} routers")
        hardware_row = hardware[routers]
        selection["router_counts"][str(routers)] = {
            "campaigns": [str(path) for path in campaigns[routers]],
            "selected_count": len(selected),
            "selected_summaries": [str(path) for path, _summary in selected],
            "excluded": excluded,
        }
        pcap_dir = args.output_dir / "pcaps" / f"{routers}_routers"
        pcap_dir.mkdir(parents=True, exist_ok=True)
        selected_manifest_rows = []
        for sample_index, (summary_path, summary) in enumerate(selected, start=1):
            source_pcap = Path(str(summary["pcap_file"]))
            if not source_pcap.is_file():
                raise ValueError(f"Selected run PCAP is missing: {source_pcap}")
            artifact_pcap = pcap_dir / f"run_{sample_index:03d}.pcap"
            shutil.copy2(source_pcap, artifact_pcap)
            relative_pcap = artifact_pcap.relative_to(args.output_dir).as_posix()
            digest = sha256_file(artifact_pcap)
            selected_manifest_rows.append(
                {
                    "sample_index": sample_index,
                    "summary": str(summary_path),
                    "pcap_file": relative_pcap,
                    "pcap_sha256": digest,
                }
            )
            accepted_row: dict[str, Any] = {
                "routers": routers,
                "sample_index": sample_index,
                "source_summary": str(summary_path),
                "pcap_file": relative_pcap,
                "pcap_sha256": digest,
            }
            for key, _label in INTERVALS:
                accepted_row[f"pcap_{key}_ms"] = summary["protocol_timing_ms"][key]
                accepted_row[f"event_{key}_ms"] = (
                    summary.get("openthread_event_timing", {}).get("timing_ms", {}).get(key)
                )
            for packet_name, packet_data in summary.get("protocol_packet_timestamps", {}).items():
                accepted_row[f"{packet_name}_frame"] = packet_data.get("frame_number")
                accepted_row[f"{packet_name}_timestamp_s"] = packet_data.get("timestamp_s")
            accepted_rows.append(accepted_row)
        selection["router_counts"][str(routers)]["selected_runs"] = selected_manifest_rows
        for key, label in INTERVALS:
            pcap = stats([float(summary["protocol_timing_ms"][key]) for _path, summary in selected])
            internal_values = [
                float(value)
                for _path, summary in selected
                if (value := summary.get("openthread_event_timing", {}).get("timing_ms", {}).get(key))
                is not None
            ]
            internal = stats(internal_values) if internal_values else None
            mean_column, sd_column = HARDWARE_COLUMNS[key]
            hw = {
                "n": int(hardware_row["n"]),
                "mean_ms": float(hardware_row[mean_column]),
                "sample_sd_ms": float(hardware_row[sd_column]),
            }
            delta = timing_delta(pcap, hw)
            report_rows.append((routers, label, internal, pcap, hw, delta))
            sources = [("otns_pcap", pcap), ("hardware_pcap", hw)]
            if internal is not None:
                sources.insert(0, ("otns_openthread_event", internal))
            for source, value in sources:
                result_rows.append(
                    {
                        "routers": routers,
                        "interval": key,
                        "source": source,
                        **value,
                        **(delta if source == "otns_pcap" else {"delta_ms": "", "delta_percent": ""}),
                    }
                )

    csv_path = args.output_dir / "comparison.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "routers", "interval", "source", "n", "mean_ms", "sample_sd_ms",
                "delta_ms", "delta_percent",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(result_rows)
    accepted_path = args.output_dir / "accepted_runs.csv"
    accepted_fields = list(accepted_rows[0])
    with accepted_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=accepted_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(accepted_rows)
    (args.output_dir / "selection_manifest.json").write_text(
        json.dumps(selection, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        f"# {args.variant}: simulated PCAP and hardware PCAP",
        "",
        f"Each OTNS column uses exactly {args.limit} accepted runs. Values are mean +/- sample SD in ms.",
        "",
        "| Routers | Interval | Internal OTNS event | OTNS PCAP | Hardware PCAP | OTNS - hardware |",
        "| ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for routers, label, internal, pcap, hw, delta in report_rows:
        lines.append(
            f"| {routers} | {label} | {format_stat(internal) if internal is not None else 'n/a'} | "
            f"{format_stat(pcap)} | {format_stat(hw)} | {delta['delta_ms']:+.3f} ms "
            f"({delta['delta_percent']:+.1f}%) |"
        )
    lines.extend(
        [
            "",
            "The OTNS-PCAP column is canonical for hardware comparison. The event column is retained only to inspect internal stack behavior. `accepted_runs.csv` records every interval and frame selection; `selection_manifest.json` records every selected and excluded summary. All 300 selected PCAPs are preserved under `pcaps/`.",
            "",
            "The PCAP timestamp is the OTNS simulated IEEE 802.15.4 frame time. It aligns packet boundaries with the hardware sniffer analysis but does not model ESP32-C6 execution or physical RF cycle-accurately.",
        ]
    )
    (args.output_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    checksum_path = args.output_dir / "checksums.sha256"
    with checksum_path.open("w", encoding="utf-8") as handle:
        for path in sorted(args.output_dir.rglob("*")):
            if path.is_file() and path != checksum_path:
                handle.write(f"{sha256_file(path)}  {path.relative_to(args.output_dir).as_posix()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
