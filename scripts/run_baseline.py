#!/usr/bin/env python3
"""Run the stock OpenThread mobility baseline in OTNS or in mock mode."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shlex
import shutil
import time
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = ROOT / "scenarios" / "med_simple_parent_switch.yaml"
DEFAULT_RESULTS_DIR = ROOT / "results"
DEFAULT_REPLAY_DIR = DEFAULT_RESULTS_DIR / "replays"
DEFAULT_OTNS_OUTPUT_DIRNAME = "tmp"
PING_NODE_RE = re.compile(r"Node<(\d+)>")
SCAN_NODE_PREFIX_RE = re.compile(r"^Node<\d+>\s+")
TIMESTAMP_TOKEN_RE = re.compile(r"^(?P<date>\d{8})T(?P<time>\d{6})Z$")
OTNS_LOG_LINE_RE = re.compile(r"^(trace|debug|info|note|warn|error)\t\d{4}-\d{2}-\d{2}\s", re.IGNORECASE)


@dataclass
class NodeRef:
    name: str
    node_id: int
    extaddr: str | None = None
    rloc16: str | None = None
    x: float | None = None
    y: float | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument(
        "--otns-command",
        default=os.environ.get("OTNS_COMMAND", "otns"),
        help="OTNS executable or full command string",
    )
    parser.add_argument(
        "--otns-workdir",
        type=Path,
        default=Path(os.environ["OTNS_WORKDIR"]) if os.environ.get("OTNS_WORKDIR") else None,
        help="Optional working directory used to launch OTNS. Needed when OTNS relies on relative node paths.",
    )
    parser.add_argument(
        "--otns-watch-level",
        default="off",
        help="Optional OTNS default watch level for all newly created nodes: trace, debug, info, note, warn, error, off.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Generate deterministic mock output without OTNS",
    )
    parser.add_argument("--capture-replay", action="store_true", help="Copy a replay file after a real OTNS run.")
    parser.add_argument(
        "--capture-sim-ping-rss",
        action="store_true",
        help=(
            "Attach simulator-level, OTNS MutualInterference model-derived RSS/LQI values "
            "to each ping probe row."
        ),
    )
    parser.add_argument(
        "--replay-source",
        type=Path,
        default=None,
        help="Optional replay file to copy. Defaults to an OTNS workdir replay when possible.",
    )
    parser.add_argument(
        "--replay-dir",
        type=Path,
        default=DEFAULT_REPLAY_DIR,
        help="Scratch output directory for copied replay files.",
    )
    parser.add_argument(
        "--firmware-variant",
        default="stock-openthread",
        help="Firmware or build label recorded in replay/artifact metadata.",
    )
    parser.add_argument(
        "--thread-device-type",
        default=None,
        help="Thread device type for the mobile node metadata, for example med.",
    )
    parser.add_argument(
        "--parent-search-config",
        choices=("enabled", "disabled", "observed", "unknown"),
        default="unknown",
        help="Periodic Parent Search state recorded in metadata.",
    )
    parser.add_argument(
        "--node-binary-path",
        type=Path,
        default=None,
        help="Optional MTD node binary path. When provided, OTNS is told to use it for med/sed/ssed nodes.",
    )
    parser.add_argument(
        "--ftd-node-binary-path",
        type=Path,
        default=None,
        help="Optional FTD node binary path. When provided, OTNS is told to use it for router/reed/fed nodes.",
    )
    parser.add_argument(
        "--build-config-source",
        default=None,
        help="Path or command that documents how the node binary was built.",
    )
    parser.add_argument(
        "--equivalent-to",
        default=None,
        help="Optional default-build classification, for example stock-med-pps-on.",
    )
    parser.add_argument(
        "--openthread-commit",
        default="unknown",
        help="Optional OpenThread commit or build label recorded in metadata.",
    )
    parser.add_argument(
        "--otns-commit",
        default="unknown",
        help="Optional OTNS commit or build label recorded in metadata.",
    )
    parser.add_argument(
        "--copy-results-to-artifact",
        action="store_true",
        help="Copy CSV, summary, replay, and manifest into a tracked results directory.",
    )
    parser.add_argument(
        "--commit-artifact-dir",
        type=Path,
        default=None,
        help="Explicit tracked results run directory. Defaults to results/<scenario>_<variant>/<run-id>/<run-id>.",
    )
    parser.add_argument(
        "--artifact-name",
        default=None,
        help="Legacy name for the tracked results variant suffix.",
    )
    parser.add_argument(
        "--timestamp-token",
        default=None,
        help="Optional UTC token reused for filenames and tracked results directories.",
    )
    return parser.parse_args()


def load_scenario(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def timestamp_token() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_results_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def scenario_file_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def slugify_variant(value: str) -> str:
    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "run"


def format_run_id(token: str, run_index: int = 1) -> str:
    match = TIMESTAMP_TOKEN_RE.match(token)
    if match is None:
        raise ValueError(f"Unsupported timestamp token format: {token}")
    return f'{match.group("date")}-{match.group("time")}-run{run_index:02d}'


def tracked_results_collection_name(scenario_name: str, variant: str | None) -> str:
    if not variant:
        return scenario_name
    return f"{scenario_name}_{slugify_variant(variant)}"


def unique_file_path(directory: Path, filename: str) -> Path:
    base = Path(filename)
    candidate = directory / base.name
    counter = 1
    while candidate.exists():
        candidate = directory / f"{base.stem}_{counter}{base.suffix}"
        counter += 1
    return candidate


def with_otns_watch_level(command: str, watch_level: str) -> str:
    if watch_level.lower() == "off":
        return command
    parts = shlex.split(command)
    if "-watch" in parts:
        return command
    return f"{command} -watch {watch_level}"


def numeric_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def numeric_median(values: list[float]) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    if len(sorted_values) % 2:
        return round(sorted_values[midpoint], 6)
    return round((sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2, 6)


def sim_lqi_from_rssi(rssi_dbm: float | None) -> int | None:
    if rssi_dbm is None:
        return None
    if rssi_dbm >= -70:
        return 3
    if rssi_dbm >= -85:
        return 2
    if rssi_dbm >= -100:
        return 1
    return 0


def derive_mutual_interference_rssi_dbm(
    src_x: float | None,
    src_y: float | None,
    dst_x: float | None,
    dst_y: float | None,
    meter_per_unit: float = 0.1,
    tx_power_dbm: float = 20.0,
) -> float | None:
    """Mirror OTNS MutualInterference 3GPP indoor RSS calculation at a ping event."""

    if None in (src_x, src_y, dst_x, dst_y):
        return None
    distance_units = math.dist((float(src_x), float(src_y)), (float(dst_x), float(dst_y)))
    distance_meters = distance_units * meter_per_unit
    if distance_meters <= 0.0:
        rssi = tx_power_dbm
    else:
        los_fixed_loss = 32.4 + 20.0 * math.log10(2.4)
        nlos_fixed_loss = 17.3 + 24.9 * math.log10(2.4)
        los_pathloss = 17.3 * math.log10(distance_meters) + los_fixed_loss
        nlos_pathloss = 38.3 * math.log10(distance_meters) + nlos_fixed_loss
        rssi = tx_power_dbm - max(los_pathloss, nlos_pathloss)
    if rssi < -126.0:
        return -127.0
    if rssi > 126.0:
        return 126.0
    return round(rssi, 3)


def unavailable_sim_rss(status: str = "unavailable") -> dict[str, Any]:
    return {
        "method": None,
        "match_status": status,
        "match_confidence": 0.0,
        "request_rx_sim_rss_dbm": None,
        "request_rx_sim_lqi": None,
        "reply_rx_sim_rss_dbm": None,
        "reply_rx_sim_lqi": None,
        "event_time_s": None,
    }


def otns_runtime_cwd(otns_workdir: Path | None) -> Path:
    return otns_workdir if otns_workdir is not None else ROOT


def otns_output_dir(otns_workdir: Path | None) -> Path:
    return otns_runtime_cwd(otns_workdir) / DEFAULT_OTNS_OUTPUT_DIRNAME


def snapshot_replay_files(workdir: Path | None) -> dict[Path, float]:
    if workdir is None or not workdir.exists():
        return {}
    snapshot: dict[Path, float] = {}
    for path in workdir.glob("otns_*.replay"):
        try:
            snapshot[path.resolve()] = path.stat().st_mtime
        except FileNotFoundError:
            continue
    return snapshot


def infer_replay_source(
    explicit_source: Path | None,
    otns_workdir: Path | None,
    replay_before: dict[Path, float],
) -> tuple[Path | None, str | None]:
    if explicit_source is not None:
        return explicit_source, None
    if otns_workdir is None:
        return None, "Replay capture requested but no replay source or OTNS workdir was provided."

    replay_after = snapshot_replay_files(otns_workdir)
    candidates: list[tuple[float, Path]] = []
    for path, mtime in replay_after.items():
        previous_mtime = replay_before.get(path)
        if previous_mtime is None or mtime > previous_mtime:
            candidates.append((mtime, path))
    if candidates:
        candidates.sort()
        return candidates[-1][1], None

    default_source = otns_workdir / "otns_0.replay"
    if default_source.exists():
        return default_source, None

    return None, f"Replay capture requested but no replay file was found in {otns_workdir}."


def maybe_capture_replay(
    *,
    capture_replay: bool,
    mock: bool,
    scenario: dict[str, Any],
    scenario_path: Path,
    token: str,
    otns_command: str,
    otns_workdir: Path | None,
    replay_source: Path | None,
    replay_dir: Path,
    firmware_variant: str,
    thread_device_type: str | None,
    parent_search_config: str,
    node_binary_path: Path | None,
    ftd_node_binary_path: Path | None,
    build_config_source: str | None,
    equivalent_to: str | None,
    openthread_commit: str,
    otns_commit: str,
    csv_path: Path,
    json_path: Path,
    summary: dict[str, Any],
    replay_before: dict[Path, float],
) -> dict[str, Any]:
    info: dict[str, Any] = {
        "requested": capture_replay,
        "captured": False,
        "source": None,
        "copied_path": None,
        "metadata_path": None,
        "warning": None,
    }
    if not capture_replay:
        return info
    if mock:
        info["warning"] = "Replay capture was requested in mock mode; no replay file was captured."
        return info

    detected_source, warning = infer_replay_source(replay_source, otns_workdir, replay_before)
    if detected_source is None:
        info["warning"] = warning
        return info
    if not detected_source.exists():
        info["warning"] = f"Replay capture requested but source replay file does not exist: {detected_source}"
        info["source"] = str(detected_source)
        return info

    ensure_results_dir(replay_dir)
    replay_name = f'{scenario["name"]}_{token}.replay'
    copied_path = unique_file_path(replay_dir, replay_name)
    shutil.copy2(detected_source, copied_path)

    metadata_path = copied_path.with_suffix(".replay.json")
    metadata = {
        "scenario_name": scenario["name"],
        "scenario_title": scenario["title"],
        "scenario_file": scenario_file_label(scenario_path),
        "firmware_variant": firmware_variant,
        "device_profile": summary.get("device_profile"),
        "thread_device_type": thread_device_type,
        "parent_search_config": parent_search_config,
        "node_binary_path": str(node_binary_path) if node_binary_path is not None else None,
        "ftd_node_binary_path": str(ftd_node_binary_path) if ftd_node_binary_path is not None else None,
        "build_config_source": build_config_source,
        "equivalent_to": equivalent_to,
        "openthread_commit": openthread_commit,
        "otns_commit": otns_commit,
        "otns_command": otns_command,
        "otns_workdir": str(otns_workdir) if otns_workdir is not None else None,
        "replay_source": str(detected_source),
        "copied_replay_path": str(copied_path),
        "csv_path": str(csv_path),
        "summary_json_path": str(json_path),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mock": False,
        "selected_radio_model": summary.get("selected_radio_model"),
        "initial_observed_parent": summary.get("initial_observed_parent"),
        "final_observed_parent": summary.get("final_observed_parent"),
        "switch_count": summary.get("switch_count"),
        "first_switch_time_s": summary.get("first_switch_time_s"),
        "result_classification": summary.get("result_classification"),
    }
    write_json(metadata, metadata_path)

    info.update(
        {
            "captured": True,
            "source": str(detected_source),
            "copied_path": str(copied_path),
            "metadata_path": str(metadata_path),
        }
    )
    return info


def capture_node_logs(
    *,
    results_dir: Path,
    node_refs: dict[str, NodeRef],
    otns_workdir: Path | None,
    watch_level: str,
) -> dict[str, Any]:
    info: dict[str, Any] = {
        "requested": watch_level.lower() != "off",
        "watch_level": watch_level,
        "copied_files": [],
        "warning": None,
    }
    if watch_level.lower() == "off":
        return info

    output_dir = otns_output_dir(otns_workdir)
    if not output_dir.exists():
        info["warning"] = f"OTNS node log directory was not found: {output_dir}"
        return info

    copied: list[str] = []
    missing: list[str] = []
    for name, node_ref in sorted(node_refs.items()):
        candidates = sorted(
            output_dir.glob(f"*_{node_ref.node_id}.log"),
            key=lambda path: path.stat().st_mtime,
        )
        if not candidates:
            missing.append(f"{name}:{node_ref.node_id}")
            continue
        source = candidates[-1]
        destination = results_dir / f"node_log_{name}_{node_ref.node_id}.log"
        shutil.copy2(source, destination)
        copied.append(str(destination))

    if missing:
        info["warning"] = "Some OTNS node logs were not found: " + ", ".join(missing)
    info["copied_files"] = copied
    return info


def resolve_tracked_results_dir(
    commit_artifact_dir: Path | None,
    artifact_name: str | None,
    scenario_name: str,
    token: str,
) -> Path:
    if commit_artifact_dir is not None:
        return commit_artifact_dir
    collection = tracked_results_collection_name(scenario_name, artifact_name)
    run_id = format_run_id(token)
    return DEFAULT_RESULTS_DIR / collection / run_id / run_id


def tracked_results_manifest(
    *,
    collection_name: str,
    run_id: str,
    scenario: dict[str, Any],
    scenario_path: Path,
    firmware_variant: str,
    thread_device_type: str | None,
    parent_search_config: str,
    node_binary_path: Path | None,
    ftd_node_binary_path: Path | None,
    build_config_source: str | None,
    equivalent_to: str | None,
    openthread_commit: str,
    otns_commit: str,
    otns_command: str,
    otns_workdir: Path | None,
    csv_file: str,
    summary_file: str,
    replay_file: str | None,
    replay_metadata_file: str | None,
    node_log_files: list[str],
    token: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "results_collection": collection_name,
        "run_id": run_id,
        "scenario_name": scenario["name"],
        "scenario_file": scenario_file_label(scenario_path),
        "firmware_variant": firmware_variant,
        "device_profile": summary.get("device_profile"),
        "thread_device_type": thread_device_type,
        "parent_search_config": parent_search_config,
        "node_binary_path": str(node_binary_path) if node_binary_path is not None else None,
        "ftd_node_binary_path": str(ftd_node_binary_path) if ftd_node_binary_path is not None else None,
        "build_config_source": build_config_source,
        "equivalent_to": equivalent_to,
        "openthread_commit": openthread_commit,
        "otns_commit": otns_commit,
        "otns_command": otns_command,
        "otns_workdir": str(otns_workdir) if otns_workdir is not None else None,
        "csv_file": csv_file,
        "summary_file": summary_file,
        "replay_file": replay_file,
        "replay_metadata_file": replay_metadata_file,
        "node_log_files": node_log_files,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected_radio_model": summary.get("selected_radio_model"),
        "otns_watch_level": summary.get("otns_watch_level"),
        "initial_observed_parent": summary.get("initial_observed_parent"),
        "final_observed_parent": summary.get("final_observed_parent"),
        "switch_count": summary.get("switch_count"),
        "first_switch_time_s": summary.get("first_switch_time_s"),
        "switch_position_x": summary.get("switch_position_x"),
        "packet_delivery_ratio": summary.get("packet_delivery_ratio"),
        "total_outage_s": summary.get("total_outage_s"),
        "oscillation_events": summary.get("oscillation_events"),
        "parent_sequence": summary.get("parent_sequence"),
        "mle_parent_changes": summary.get("mle_parent_changes"),
        "mle_attach_attempts": summary.get("mle_attach_attempts"),
        "mle_better_parent_attach_attempts": summary.get("mle_better_parent_attach_attempts"),
        "result_classification": summary.get("result_classification"),
    }


def write_tracked_results_readme(
    path: Path,
    *,
    manifest: dict[str, Any],
    scenario: dict[str, Any],
    replay_file: str | None,
) -> None:
    replay_instruction = (
        f"otns-replay {replay_file}" if replay_file is not None else "Replay was not captured for this artifact."
    )
    content = "\n".join(
        [
            f'# Result: {manifest["results_collection"]} / {manifest["run_id"]}',
            "",
            scenario.get("description", "").strip() or "Tracked OTNS benchmark result.",
            "",
            "## Metadata",
            "",
            f'- Scenario: `{manifest["scenario_name"]}`',
            f'- Scenario file: `{manifest["scenario_file"]}`',
            f'- Firmware variant: `{manifest["firmware_variant"]}`',
            f'- Device profile: `{manifest["device_profile"]}`',
            f'- Thread device type: `{manifest["thread_device_type"]}`',
            f'- Parent search config: `{manifest["parent_search_config"]}`',
            f'- Node binary path: `{manifest["node_binary_path"]}`',
            f'- FTD node binary path: `{manifest["ftd_node_binary_path"]}`',
            f'- Build config source: `{manifest["build_config_source"]}`',
            f'- Equivalent to: `{manifest["equivalent_to"]}`',
            f'- OpenThread commit: `{manifest["openthread_commit"]}`',
            f'- OTNS commit: `{manifest["otns_commit"]}`',
            f'- OTNS command: `{manifest["otns_command"]}`',
            f'- OTNS workdir: `{manifest["otns_workdir"]}`',
            f'- OTNS watch level: `{manifest["otns_watch_level"]}`',
            f'- Selected radio model: `{manifest["selected_radio_model"]}`',
            f'- Initial observed parent: `{manifest["initial_observed_parent"]}`',
            f'- Final observed parent: `{manifest["final_observed_parent"]}`',
            f'- Switch count: `{manifest["switch_count"]}`',
            f'- First switch time (s): `{manifest["first_switch_time_s"]}`',
            f'- Switch position x: `{manifest["switch_position_x"]}`',
            f'- Packet delivery ratio: `{manifest["packet_delivery_ratio"]}`',
            f'- Total outage (s): `{manifest["total_outage_s"]}`',
            f'- Oscillation events: `{manifest["oscillation_events"]}`',
            f'- Parent sequence: `{manifest["parent_sequence"]}`',
            f'- MLE parent changes: `{manifest["mle_parent_changes"]}`',
            f'- MLE attach attempts: `{manifest["mle_attach_attempts"]}`',
            f'- MLE better parent attach attempts: `{manifest["mle_better_parent_attach_attempts"]}`',
            f'- Result classification: `{manifest["result_classification"]}`',
            "",
            "## Node Logs",
            "",
            *([f"- `{log_file}`" for log_file in manifest.get("node_log_files", [])] or ["- No node log files were captured."]),
            "",
            "## Replay",
            "",
            "Replay command:",
            "",
            "```bash",
            replay_instruction,
            "```",
        ]
    )
    path.write_text(content + "\n", encoding="utf-8")


def export_tracked_results(
    *,
    tracked_dir: Path,
    tracked_collection: str,
    run_id: str,
    scenario: dict[str, Any],
    scenario_path: Path,
    firmware_variant: str,
    thread_device_type: str | None,
    parent_search_config: str,
    node_binary_path: Path | None,
    ftd_node_binary_path: Path | None,
    build_config_source: str | None,
    equivalent_to: str | None,
    openthread_commit: str,
    otns_commit: str,
    otns_command: str,
    otns_workdir: Path | None,
    token: str,
    csv_path: Path,
    json_path: Path,
    replay_info: dict[str, Any],
    node_log_files: list[str],
    summary: dict[str, Any],
) -> dict[str, str]:
    if tracked_dir.exists():
        raise FileExistsError(f"Tracked results directory already exists: {tracked_dir}")
    tracked_dir.mkdir(parents=True, exist_ok=False)

    tracked_csv = tracked_dir / csv_path.name
    tracked_summary = tracked_dir / json_path.name
    shutil.copy2(csv_path, tracked_csv)
    shutil.copy2(json_path, tracked_summary)

    replay_relpath = None
    metadata_relpath = None
    if replay_info.get("copied_path"):
        replay_source = Path(replay_info["copied_path"])
        tracked_replay = tracked_dir / replay_source.name
        shutil.copy2(replay_source, tracked_replay)
        replay_relpath = tracked_replay.name
        metadata_source = Path(replay_info["metadata_path"])
        tracked_replay_metadata = tracked_dir / metadata_source.name
        shutil.copy2(metadata_source, tracked_replay_metadata)
        metadata_relpath = tracked_replay_metadata.name

    tracked_node_log_files: list[str] = []
    for node_log_file in node_log_files:
        node_log_source = Path(node_log_file)
        tracked_node_log = tracked_dir / node_log_source.name
        shutil.copy2(node_log_source, tracked_node_log)
        tracked_node_log_files.append(tracked_node_log.name)

    manifest = tracked_results_manifest(
        collection_name=tracked_collection,
        run_id=run_id,
        scenario=scenario,
        scenario_path=scenario_path,
        firmware_variant=firmware_variant,
        thread_device_type=thread_device_type,
        parent_search_config=parent_search_config,
        node_binary_path=node_binary_path,
        ftd_node_binary_path=ftd_node_binary_path,
        build_config_source=build_config_source,
        equivalent_to=equivalent_to,
        openthread_commit=openthread_commit,
        otns_commit=otns_commit,
        otns_command=otns_command,
        otns_workdir=otns_workdir,
        csv_file=tracked_csv.name,
        summary_file=tracked_summary.name,
        replay_file=replay_relpath,
        replay_metadata_file=metadata_relpath,
        node_log_files=tracked_node_log_files,
        token=token,
        summary=summary,
    )
    manifest_path = tracked_dir / "manifest.json"
    write_json(manifest, manifest_path)
    write_tracked_results_readme(
        tracked_dir / "README.md",
        manifest=manifest,
        scenario=scenario,
        replay_file=replay_relpath,
    )
    return {
        "tracked_dir": str(tracked_dir),
        "manifest_path": str(manifest_path),
    }


def linear_positions(start: dict[str, float], end: dict[str, float], steps: int) -> list[tuple[float, float]]:
    if steps < 1:
        return [(float(start["x"]), float(start["y"]))]
    sample_count = steps + 1
    positions = []
    for index in range(sample_count):
        fraction = index / steps
        x = start["x"] + (end["x"] - start["x"]) * fraction
        y = start["y"] + (end["y"] - start["y"]) * fraction
        positions.append((round(float(x), 3), round(float(y), 3)))
    return positions


def movement_positions(scenario: dict[str, Any]) -> list[tuple[float, float]]:
    timing = scenario["timing"]
    movement = scenario["movement"]
    positions = linear_positions(
        movement["start"],
        movement["end"],
        int(timing["movement_steps"]),
    )
    hold_end_steps = int(movement.get("hold_end_steps", 0))
    if hold_end_steps > 0 and positions:
        positions.extend([positions[-1]] * hold_end_steps)
    return positions


def sanitize_command_output(lines: list[str]) -> list[str]:
    return [line.rstrip("\r\n") for line in lines if line not in {"Done", "Started"} and line]


def parse_key_value_lines(lines: list[str]) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


def counter_int(counters: dict[str, Any], key: str) -> int | None:
    value = counters.get(key)
    if value in (None, "", "None"):
        return None
    return int(value)


def parse_ping_summary(lines: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "tx": None,
        "rx": None,
        "loss_pct": None,
        "rtt_min_ms": None,
        "rtt_avg_ms": None,
        "rtt_max_ms": None,
    }
    for line in lines:
        if "packets transmitted" in line and "packets received" in line:
            left, right = line.split("Packet loss =", 1)
            tx_part = left.split("packets transmitted", 1)[0].strip()
            rx_part = left.split("packets received", 1)[0].split(",")[-1].strip()
            result["tx"] = int(tx_part.split()[-1])
            result["rx"] = int(rx_part.split()[-1])
            result["loss_pct"] = float(right.split("%", 1)[0].strip())
        if "Round-trip min/avg/max" in line:
            values = line.rsplit("=", 1)[-1].strip().split("/")
            if len(values) == 3:
                result["rtt_min_ms"] = float(values[0])
                result["rtt_avg_ms"] = float(values[1])
                result["rtt_max_ms"] = float(values[2].split()[0])
    return result


def parse_ping_summaries_by_source(lines: list[str]) -> dict[int, dict[str, Any]]:
    grouped: dict[int, list[str]] = {}
    for line in lines:
        match = PING_NODE_RE.match(line)
        if not match:
            continue
        source_id = int(match.group(1))
        grouped.setdefault(source_id, []).append(line)
    return {source_id: parse_ping_summary(group_lines) for source_id, group_lines in grouped.items()}


def parse_nodes(lines: list[str]) -> dict[int, dict[str, str]]:
    nodes: dict[int, dict[str, str]] = {}
    for line in lines:
        if not line.startswith("id="):
            continue
        entry: dict[str, str] = {}
        for part in line.replace("\t", " ").split():
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            entry[key] = value
        if "id" in entry:
            nodes[int(entry["id"])] = entry
    return nodes


def parse_scan_table(lines: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in lines:
        line = SCAN_NODE_PREFIX_RE.sub("", line).strip()
        if not line.startswith("|") or "MAC Address" in line or line.startswith("+-"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 8:
            rows.append(
                {
                    "joinable": cells[0],
                    "network_name": cells[1],
                    "extpanid": cells[2],
                    "panid": cells[3],
                    "mac_address": cells[4].lower(),
                    "channel": cells[5],
                    "dbm": cells[6],
                    "lqi": cells[7],
                }
            )
            continue
        if len(cells) >= 5:
            rows.append(
                {
                    "joinable": "",
                    "network_name": "",
                    "extpanid": "",
                    "panid": cells[0],
                    "mac_address": cells[1].lower(),
                    "channel": cells[2],
                    "dbm": cells[3],
                    "lqi": cells[4],
                }
            )
            continue
    return rows


class OtnsSessionError(RuntimeError):
    """Raised when OTNS exits or reports a CLI error."""


class OtnsSession:
    def __init__(self, command: str, cwd: Path | None = None) -> None:
        self.command = command
        self.cwd = str(cwd) if cwd else None
        self.process: subprocess.Popen[bytes] | None = None

    def __enter__(self) -> "OtnsSession":
        argv = shlex.split(self.command) if isinstance(self.command, str) else list(self.command)
        self.process = subprocess.Popen(
            argv,
            cwd=self.cwd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        time.sleep(0.1)
        if self.process.poll() is not None:
            output = self.process.stdout.read().decode("utf-8", errors="replace") if self.process.stdout else ""
            raise OtnsSessionError(
                f"OTNS exited during startup with code {self.process.returncode}: {output.strip()}"
            )
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.process is None:
            return
        try:
            self.command_output("exit")
        except Exception:
            pass
        self.process.kill()
        self.process.wait()

    def command_output(self, command: str, *, force_global_scope: bool = True) -> list[str]:
        assert self.process is not None
        assert self.process.stdin is not None
        assert self.process.stdout is not None

        wire_command = command
        if force_global_scope and command and not command.startswith("!"):
            wire_command = f"!{command}"

        try:
            self.process.stdin.write(wire_command.encode("ascii") + b"\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise OtnsSessionError(f"Failed to send OTNS command {command!r}: {exc}") from exc

        output: list[str] = []
        while True:
            line = self.process.stdout.readline()
            if line == b"":
                raise OtnsSessionError(f"OTNS exited while waiting for {command!r} output.")
            text = line.rstrip(b"\r\n").decode("utf-8", errors="replace")
            if OTNS_LOG_LINE_RE.match(text):
                continue
            if text.startswith("Error: ") or text.startswith("Error "):
                raise OtnsSessionError(f"{text} while running {command!r}")
            output.append(text)
            if text in {"Done", "Started"}:
                return sanitize_command_output(output)


class RealBenchmarkRunner:
    def __init__(
        self,
        scenario: dict[str, Any],
        otns_command: str,
        otns_workdir: Path | None = None,
        otns_watch_level: str = "off",
        node_binary_path: Path | None = None,
        ftd_node_binary_path: Path | None = None,
        thread_device_type: str | None = None,
        parent_search_config: str = "unknown",
        capture_sim_ping_rss: bool = False,
    ) -> None:
        self.scenario = scenario
        self.otns_command = with_otns_watch_level(otns_command, otns_watch_level)
        self.otns_workdir = otns_workdir
        self.otns_watch_level = otns_watch_level
        self.node_binary_path = node_binary_path
        self.ftd_node_binary_path = ftd_node_binary_path
        self.thread_device_type = thread_device_type
        self.parent_search_config = parent_search_config
        self.capture_sim_ping_rss = capture_sim_ping_rss
        self.otns_runtime_cwd = otns_runtime_cwd(otns_workdir)
        self.notes: list[str] = []
        self.node_refs: dict[str, NodeRef] = {}
        self.parent_before_delayed_nodes: str | None = None
        self.observability = scenario.get("observability", {})

    def run(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if shutil.which(self.otns_command.split()[0]) is None:
            raise FileNotFoundError(
                f"OTNS command not found: {self.otns_command}. Install OTNS or use --mock."
            )

        timing = self.scenario["timing"]
        positions = movement_positions(self.scenario)

        with OtnsSession(self.otns_command, cwd=self.otns_runtime_cwd) as session:
            session.command_output("speed 0")
            session.command_output(f'title "{self.scenario["title"]}"')
            if self.ftd_node_binary_path is not None:
                session.command_output(f'exe ftd "{self.ftd_node_binary_path}"')
                self.notes.append(f"OTNS FTD executable set to {self.ftd_node_binary_path}.")
            if self.node_binary_path is not None:
                session.command_output(f'exe mtd "{self.node_binary_path}"')
                self.notes.append(f"OTNS MTD executable set to {self.node_binary_path}.")
            radio_model = self._select_radio_model(session)
            named_ids = self._activate_nodes(session, timing)
            self._refresh_node_identity(session)

            samples: list[dict[str, Any]] = []
            switch_events: list[dict[str, Any]] = []
            previous_parent = None
            outage_start = None
            total_outage = 0.0

            for index, (x, y) in enumerate(positions):
                mobile_id = named_ids["mobile"]
                session.command_output(f"move {mobile_id} {int(round(x))} {int(round(y))}")
                self.node_refs["mobile"].x = x
                self.node_refs["mobile"].y = y
                # The active benchmark sends exactly one probe per sample: mobile ED -> current parent.
                parent_probe: dict[str, Any] = self._send_mobile_to_parent_probe(session, mobile_id)
                go_output_lines = session.command_output(f'go {timing["step_seconds"]}')
                sample = self._collect_sample(session, index, x, y, go_output_lines, parent_probe)
                sample["selected_radio_model"] = radio_model

                parent_identity = (
                    sample.get("parent_node_guess") or sample.get("parent_extaddr") or sample.get("parent_rloc16")
                )
                switch = bool(previous_parent and parent_identity and parent_identity != previous_parent)
                sample["parent_switch"] = switch
                if switch:
                    switch_events.append(
                        {
                            "sample_index": index,
                            "sim_time_s": sample["sim_time_s"],
                            "from_parent": previous_parent,
                            "to_parent": parent_identity,
                        }
                    )
                previous_parent = parent_identity or previous_parent

                connectivity_ok = self._connectivity_ok(sample)
                if not connectivity_ok and outage_start is None:
                    outage_start = sample["sim_time_s"]
                elif connectivity_ok and outage_start is not None:
                    total_outage += sample["sim_time_s"] - outage_start
                    outage_start = None
                sample["connectivity_ok"] = connectivity_ok
                samples.append(sample)

            if outage_start is not None and samples:
                total_outage += samples[-1]["sim_time_s"] - outage_start

        rows = flatten_samples(samples)
        summary = build_summary(
            scenario=self.scenario,
            samples=samples,
            switch_events=switch_events,
            notes=self.notes,
            selected_radio_model=rows[0]["selected_radio_model"] if rows else None,
            total_outage_s=round(total_outage, 3),
            mock=False,
            parent_before_delayed_nodes=self.parent_before_delayed_nodes,
            thread_device_type=self.thread_device_type,
            parent_search_config=self.parent_search_config,
            sim_ping_rss_capture_enabled=self.capture_sim_ping_rss,
        )
        return rows, summary

    def _derive_ping_sim_rss(
        self,
        src_name: str | None,
        dst_name: str | None,
        sim_time_s: float,
        ping_result: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not self.capture_sim_ping_rss:
            return {}
        if not src_name or not dst_name:
            return {}
        src = self.node_refs.get(src_name)
        dst = self.node_refs.get(dst_name)
        if src is None or dst is None:
            return {}

        request_rssi = derive_mutual_interference_rssi_dbm(src.x, src.y, dst.x, dst.y)
        rx_count = int((ping_result or {}).get("rx") or 0)
        reply_rssi = derive_mutual_interference_rssi_dbm(dst.x, dst.y, src.x, src.y) if rx_count > 0 else None
        return {
            "method": "otns_model_derived_at_ping",
            "match_status": "model_derived",
            "match_confidence": 1.0,
            "request_rx_sim_rss_dbm": request_rssi,
            "request_rx_sim_lqi": sim_lqi_from_rssi(request_rssi),
            "reply_rx_sim_rss_dbm": reply_rssi,
            "reply_rx_sim_lqi": sim_lqi_from_rssi(reply_rssi),
            "event_time_s": sim_time_s,
        }

    def _select_radio_model(self, session: OtnsSession) -> str:
        preferred = [self.scenario["radio_model"]["preferred"], *self.scenario["radio_model"]["fallbacks"]]
        for model in preferred:
            output = session.command_output(f"radiomodel {model}")
            chosen = output[0] if output else None
            if chosen and chosen.lower().startswith(model.lower()[0]):
                if model != preferred[0]:
                    self.notes.append(f"Preferred radio model unavailable, fell back to {model}.")
                return chosen
        self.notes.append("Unable to confirm configured OTNS radio model from CLI output.")
        return "unknown"

    def _create_nodes(self, session: OtnsSession, node_names: list[str]) -> dict[str, int]:
        named_ids: dict[str, int] = {}
        for name in node_names:
            config = self.scenario["nodes"][name]
            # OTNS-specific command: create a stock node type in the simulator.
            output = session.command_output(f'add {config["type"]}')
            node_id = int(output[0])
            named_ids[name] = node_id
            session.command_output(f'move {node_id} {config["x"]} {config["y"]}')
            self.node_refs[name] = NodeRef(name=name, node_id=node_id, x=config["x"], y=config["y"])
        return named_ids

    def _activate_nodes(self, session: OtnsSession, timing: dict[str, Any]) -> dict[str, int]:
        activation = self.scenario.get("activation", {})
        configured_names = list(self.scenario["nodes"].keys())
        initial_node_names = activation.get("initial_nodes") or configured_names
        named_ids = self._create_nodes(session, list(initial_node_names))

        delayed_groups = activation.get("delayed_node_groups", [])
        if not delayed_groups:
            session.command_output(f'go {timing["settle_seconds"]}')
            return named_ids

        for group in delayed_groups:
            delay_seconds = int(group.get("delay_seconds", 0))
            if delay_seconds:
                session.command_output(f"go {delay_seconds}")
            self._refresh_node_identity(session)
            mobile_ref = self.node_refs.get("mobile")
            if mobile_ref is not None and self.parent_before_delayed_nodes is None:
                parent_info = parse_key_value_lines(session.command_output(f'node {mobile_ref.node_id} "parent"'))
                self.parent_before_delayed_nodes = self._parent_name_from_identity(parent_info)

            group_names = list(group["nodes"])
            for name in group_names:
                named_ids.update(self._create_nodes(session, [name]))
            self.notes.append(
                "Delayed node activation applied: "
                + ", ".join(group_names)
                + f" after {delay_seconds} simulated seconds."
            )

        post_activation_settle_seconds = int(activation.get("post_activation_settle_seconds", 0))
        if post_activation_settle_seconds:
            session.command_output(f"go {post_activation_settle_seconds}")
        return named_ids

    def _refresh_node_identity(self, session: OtnsSession) -> None:
        parsed = parse_nodes(session.command_output("nodes"))
        for node_ref in self.node_refs.values():
            entry = parsed.get(node_ref.node_id, {})
            node_ref.extaddr = entry.get("extaddr")
            node_ref.rloc16 = entry.get("rloc16")
            if "x" in entry:
                node_ref.x = float(entry["x"])
            if "y" in entry:
                node_ref.y = float(entry["y"])

    def _collect_sample(
        self,
        session: OtnsSession,
        index: int,
        x: float,
        y: float,
        go_output_lines: list[str],
        parent_probe: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        mobile = self.node_refs["mobile"]
        sim_time_us = int(session.command_output("time")[0])
        state_lines = session.command_output(f'node {mobile.node_id} "state"')
        rloc_lines = session.command_output(f'node {mobile.node_id} "rloc16"')
        try:
            parent_lines = session.command_output(f'node {mobile.node_id} "parent"')
        except OtnsSessionError as exc:
            if "InvalidState" not in str(exc):
                raise
            parent_lines = []
            note = "OTNS parent command returned InvalidState for at least one sample; parent fields are empty for that sample."
            if note not in self.notes:
                self.notes.append(note)
        ip_counter_lines = session.command_output(f'node {mobile.node_id} "counters ip"')
        mle_counter_lines = session.command_output(f'node {mobile.node_id} "counters mle"')
        scan_rows: list[dict[str, str]] = []
        scan_note = (
            "Live OTNS scan compatibility is inconsistent in this setup; "
            "scan-derived RSSI/LQI fields are left empty."
        )
        if scan_note not in self.notes:
            self.notes.append(scan_note)

        parent_info = parse_key_value_lines(parent_lines)
        ip_counters = parse_key_value_lines(ip_counter_lines)
        mle_counters = parse_key_value_lines(mle_counter_lines)
        ping_results_by_source = parse_ping_summaries_by_source(go_output_lines)

        sample: dict[str, Any] = {
            "sample_index": index,
            "sim_time_s": round(sim_time_us / 1_000_000.0, 6),
            "mobile_x": x,
            "mobile_y": y,
            "mobile_state": state_lines[0] if state_lines else None,
            "mobile_rloc16": rloc_lines[0] if rloc_lines else None,
            "device_profile": self.scenario.get("device_profile", "mobile_end_device"),
            "thread_device_type": self.thread_device_type,
            "parent_search_config": self.parent_search_config,
            "packet_probe_reliable": self.observability.get("packet_probe_reliable", True),
            "primary_parent_observation": self.observability.get("primary_parent_observation", "packet_probe"),
            "parent_extaddr": parent_info.get("Ext Addr"),
            "parent_rloc16": parent_info.get("Rloc") or parent_info.get("RLOC16"),
            "parent_link_quality_in": parent_info.get("Link Quality In"),
            "parent_link_quality_out": parent_info.get("Link Quality Out"),
            "parent_age": parent_info.get("Age"),
            "parent_version": parent_info.get("Version"),
            "parent_node_guess": self._parent_name_from_identity(parent_info),
            "mobile_to_parent_target": (parent_probe or {}).get("target"),
            "mobile_to_parent_target_rloc16": (parent_probe or {}).get("target_rloc16"),
            "mobile_to_parent_target_extaddr": (parent_probe or {}).get("target_extaddr"),
            "mobile_to_parent_result": {},
            "ip_counters": ip_counters,
            "mle_counters": mle_counters,
            "probe_results": {},
        }

        for router_name in ("router_a", "router_b"):
            router = self.node_refs[router_name]
            scan_match = next((row for row in scan_rows if row["mac_address"] == (router.extaddr or "").lower()), None)
            sample[f"{router_name}_scan_dbm"] = scan_match["dbm"] if scan_match else None
            sample[f"{router_name}_scan_lqi"] = scan_match["lqi"] if scan_match else None

        for probe in self.scenario.get("traffic_probes", []):
            src_id = self.node_refs[probe["src"]].node_id
            sample["probe_results"][probe["name"]] = ping_results_by_source.get(
                src_id,
                {
                    "tx": None,
                    "rx": None,
                    "loss_pct": None,
                    "rtt_min_ms": None,
                    "rtt_avg_ms": None,
                    "rtt_max_ms": None,
                },
            )
            sample.setdefault("probe_sim_rss", {})[probe["name"]] = self._derive_ping_sim_rss(
                probe["src"],
                probe["dst"],
                sample["sim_time_s"],
                sample["probe_results"][probe["name"]],
            )

        sample["mobile_to_parent_result"] = ping_results_by_source.get(
            mobile.node_id,
            {
                "tx": None,
                "rx": None,
                "loss_pct": None,
                "rtt_min_ms": None,
                "rtt_avg_ms": None,
                "rtt_max_ms": None,
            },
        )
        sample["mobile_to_parent_sim_rss"] = self._derive_ping_sim_rss(
            "mobile",
            sample.get("mobile_to_parent_target"),
            sample["sim_time_s"],
            sample["mobile_to_parent_result"],
        )

        return sample

    def _send_mobile_to_parent_probe(self, session: OtnsSession, mobile_id: int) -> dict[str, Any]:
        try:
            parent_lines = session.command_output(f'node {mobile_id} "parent"')
        except OtnsSessionError as exc:
            if "InvalidState" not in str(exc):
                raise
            return {"target": None, "target_rloc16": None, "target_extaddr": None}

        parent_info = parse_key_value_lines(parent_lines)
        parent_name = self._parent_name_from_identity(parent_info)
        if not parent_name:
            return {
                "target": None,
                "target_rloc16": parent_info.get("Rloc") or parent_info.get("RLOC16"),
                "target_extaddr": parent_info.get("Ext Addr"),
            }

        target_ref = self.node_refs[parent_name]
        session.command_output(f"ping {mobile_id} {target_ref.node_id} count 1")
        return {
            "target": parent_name,
            "target_rloc16": target_ref.rloc16,
            "target_extaddr": target_ref.extaddr,
        }

    def _connectivity_ok(self, sample: dict[str, Any]) -> bool:
        packet_probe_reliable = self.observability.get("packet_probe_reliable", True)
        if packet_probe_reliable:
            parent_probe = sample.get("mobile_to_parent_result", {})
            return bool(parent_probe.get("rx") and parent_probe["rx"] > 0)

        mobile_state = str(sample.get("mobile_state") or "").lower()
        parent_observed = bool(
            sample.get("parent_node_guess") or sample.get("parent_extaddr") or sample.get("parent_rloc16")
        )
        if mobile_state in {"child", "router", "leader"} and parent_observed:
            return True
        if mobile_state in {"detached", "disabled"}:
            return False
        return parent_observed

    def _parent_name_from_identity(self, parent_info: dict[str, str]) -> str | None:
        extaddr = parent_info.get("Ext Addr", "").lower()
        rloc16 = (parent_info.get("Rloc") or parent_info.get("RLOC16") or "").lower()
        for name, node_ref in self.node_refs.items():
            if node_ref.extaddr and node_ref.extaddr.lower() == extaddr:
                return name
            if node_ref.rloc16 and node_ref.rloc16.lower() == rloc16:
                return name
        return None


class MockBenchmarkRunner:
    def __init__(
        self,
        scenario: dict[str, Any],
        thread_device_type: str | None = None,
        parent_search_config: str = "unknown",
        capture_sim_ping_rss: bool = False,
    ) -> None:
        self.scenario = scenario
        self.thread_device_type = thread_device_type
        self.parent_search_config = parent_search_config
        self.capture_sim_ping_rss = capture_sim_ping_rss
        self.observability = scenario.get("observability", {})

    def _mock_ping_sim_rss(
        self,
        src: tuple[float, float] | None,
        dst: tuple[float, float] | None,
        sim_time_s: float,
        rx: int,
    ) -> dict[str, Any]:
        if not self.capture_sim_ping_rss or src is None or dst is None:
            return {}
        request_rssi = derive_mutual_interference_rssi_dbm(src[0], src[1], dst[0], dst[1])
        reply_rssi = derive_mutual_interference_rssi_dbm(dst[0], dst[1], src[0], src[1]) if rx > 0 else None
        return {
            "method": "otns_model_derived_at_ping",
            "match_status": "model_derived",
            "match_confidence": 1.0,
            "request_rx_sim_rss_dbm": request_rssi,
            "request_rx_sim_lqi": sim_lqi_from_rssi(request_rssi),
            "reply_rx_sim_rss_dbm": reply_rssi,
            "reply_rx_sim_lqi": sim_lqi_from_rssi(reply_rssi),
            "event_time_s": sim_time_s,
        }

    def run(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        timing = self.scenario["timing"]
        positions = movement_positions(self.scenario)
        router_a = self.scenario["nodes"]["router_a"]
        router_b = self.scenario["nodes"]["router_b"]

        samples: list[dict[str, Any]] = []
        switch_events: list[dict[str, Any]] = []
        previous_parent = None
        total_outage = 0.0
        outage_active = False
        outage_start = None

        for index, (x, y) in enumerate(positions):
            sim_time_s = timing["settle_seconds"] + index * timing["step_seconds"]
            dist_a = math.dist((x, y), (router_a["x"], router_a["y"]))
            dist_b = math.dist((x, y), (router_b["x"], router_b["y"]))
            parent = "router_a" if dist_a <= dist_b + 20 else "router_b"
            if index in (10, 11):
                mobile_state = "detached"
            else:
                mobile_state = "child"
            parent_probe_rx = 1 if mobile_state == "child" else 0

            if previous_parent and parent != previous_parent:
                switch_events.append(
                    {
                        "sample_index": index,
                        "sim_time_s": sim_time_s,
                        "from_parent": previous_parent,
                        "to_parent": parent,
                    }
                )
            previous_parent = parent

            if self.observability.get("packet_probe_reliable", True):
                connectivity_ok = bool(parent_probe_rx)
            else:
                connectivity_ok = mobile_state == "child"
            if not connectivity_ok and not outage_active:
                outage_start = sim_time_s
                outage_active = True
            elif connectivity_ok and outage_active and outage_start is not None:
                total_outage += sim_time_s - outage_start
                outage_active = False

            sample = {
                "sample_index": index,
                "sim_time_s": sim_time_s,
                "mobile_x": x,
                "mobile_y": y,
                "mobile_state": mobile_state,
                "mobile_rloc16": "0x5400" if parent == "router_a" else "0x9800",
                "device_profile": self.scenario.get("device_profile", "mobile_end_device"),
                "thread_device_type": self.thread_device_type,
                "parent_search_config": self.parent_search_config,
                "packet_probe_reliable": self.observability.get("packet_probe_reliable", True),
                "primary_parent_observation": self.observability.get("primary_parent_observation", "packet_probe"),
                "parent_extaddr": "aa00aa00aa00aa00" if parent == "router_a" else "bb00bb00bb00bb00",
                "parent_rloc16": "0x1000" if parent == "router_a" else "0x2000",
                "parent_link_quality_in": 3 if connectivity_ok else 0,
                "parent_link_quality_out": 3 if connectivity_ok else 0,
                "parent_age": 5,
                "parent_version": 4,
                "parent_node_guess": parent,
                "mobile_to_parent_target": parent,
                "mobile_to_parent_target_rloc16": "0x1000" if parent == "router_a" else "0x2000",
                "mobile_to_parent_target_extaddr": (
                    "aa00aa00aa00aa00" if parent == "router_a" else "bb00bb00bb00bb00"
                ),
                "mobile_to_parent_result": {
                    "tx": 1,
                    "rx": parent_probe_rx,
                    "loss_pct": 0.0 if parent_probe_rx else 100.0,
                    "rtt_min_ms": 8.0 if parent_probe_rx else None,
                    "rtt_avg_ms": 10.0 if parent_probe_rx else None,
                    "rtt_max_ms": 12.0 if parent_probe_rx else None,
                },
                "ip_counters": {
                    "TxSuccess": str(index + parent_probe_rx),
                    "TxFailed": str(max(0, 1 - parent_probe_rx)),
                    "RxSuccess": str(index + parent_probe_rx),
                    "RxFailed": "0",
                },
                "mle_counters": {
                    "AttachAttempts": str(index // 6 + 1),
                    "RoleDetached": "1" if mobile_state == "detached" else "0",
                },
                "router_a_scan_dbm": str(round(-25 - dist_a / 8, 1)),
                "router_a_scan_lqi": "3" if dist_a < 250 else "2",
                "router_b_scan_dbm": str(round(-25 - dist_b / 8, 1)),
                "router_b_scan_lqi": "3" if dist_b < 250 else "2",
                "probe_results": {},
                "probe_sim_rss": {},
                "mobile_to_parent_sim_rss": self._mock_ping_sim_rss(
                    (x, y),
                    (
                        router_a["x"] if parent == "router_a" else router_b["x"],
                        router_a["y"] if parent == "router_a" else router_b["y"],
                    ),
                    sim_time_s,
                    parent_probe_rx,
                ),
                "selected_radio_model": "mock",
                "connectivity_ok": connectivity_ok,
                "parent_switch": bool(switch_events and switch_events[-1]["sample_index"] == index),
            }
            samples.append(sample)

        if outage_active and outage_start is not None and samples:
            total_outage += samples[-1]["sim_time_s"] - outage_start

        rows = flatten_samples(samples)
        summary = build_summary(
            scenario=self.scenario,
            samples=samples,
            switch_events=switch_events,
            notes=["Mock mode was used. These results are for script validation only."],
            selected_radio_model="mock",
            total_outage_s=round(total_outage, 3),
            mock=True,
            thread_device_type=self.thread_device_type,
            parent_search_config=self.parent_search_config,
            sim_ping_rss_capture_enabled=self.capture_sim_ping_rss,
        )
        return rows, summary


def flatten_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sample in samples:
        mobile_parent_sim_rss = sample.get("mobile_to_parent_sim_rss", {})
        row = {
            "sample_index": sample["sample_index"],
            "sim_time_s": sample["sim_time_s"],
            "mobile_x": sample["mobile_x"],
            "mobile_y": sample["mobile_y"],
            "mobile_state": sample["mobile_state"],
            "mobile_rloc16": sample["mobile_rloc16"],
            "parent_extaddr": sample["parent_extaddr"],
            "parent_rloc16": sample["parent_rloc16"],
            "parent_node_guess": sample["parent_node_guess"],
            "parent_link_quality_in": sample["parent_link_quality_in"],
            "parent_link_quality_out": sample["parent_link_quality_out"],
            "parent_age": sample["parent_age"],
            "parent_version": sample["parent_version"],
            "mobile_to_parent_target": sample.get("mobile_to_parent_target"),
            "mobile_to_parent_target_rloc16": sample.get("mobile_to_parent_target_rloc16"),
            "mobile_to_parent_target_extaddr": sample.get("mobile_to_parent_target_extaddr"),
            "mobile_to_parent_tx": sample.get("mobile_to_parent_result", {}).get("tx"),
            "mobile_to_parent_rx": sample.get("mobile_to_parent_result", {}).get("rx"),
            "mobile_to_parent_loss_pct": sample.get("mobile_to_parent_result", {}).get("loss_pct"),
            "mobile_to_parent_rtt_min_ms": sample.get("mobile_to_parent_result", {}).get("rtt_min_ms"),
            "mobile_to_parent_rtt_avg_ms": sample.get("mobile_to_parent_result", {}).get("rtt_avg_ms"),
            "mobile_to_parent_rtt_max_ms": sample.get("mobile_to_parent_result", {}).get("rtt_max_ms"),
            "mobile_to_parent_sim_rss_method": mobile_parent_sim_rss.get("method"),
            "mobile_to_parent_sim_rss_match_status": mobile_parent_sim_rss.get("match_status"),
            "mobile_to_parent_sim_rss_match_confidence": mobile_parent_sim_rss.get("match_confidence"),
            "mobile_to_parent_request_rx_sim_rss_dbm": mobile_parent_sim_rss.get("request_rx_sim_rss_dbm"),
            "mobile_to_parent_request_rx_sim_lqi": mobile_parent_sim_rss.get("request_rx_sim_lqi"),
            "mobile_to_parent_reply_rx_sim_rss_dbm": mobile_parent_sim_rss.get("reply_rx_sim_rss_dbm"),
            "mobile_to_parent_reply_rx_sim_lqi": mobile_parent_sim_rss.get("reply_rx_sim_lqi"),
            "mobile_to_parent_sim_rss_event_time_s": mobile_parent_sim_rss.get("event_time_s"),
            "parent_switch": sample["parent_switch"],
            "connectivity_ok": sample["connectivity_ok"],
            "selected_radio_model": sample["selected_radio_model"],
            "device_profile": sample.get("device_profile"),
            "thread_device_type": sample.get("thread_device_type"),
            "parent_search_config": sample.get("parent_search_config"),
            "packet_probe_reliable": sample.get("packet_probe_reliable"),
            "primary_parent_observation": sample.get("primary_parent_observation"),
            "router_a_scan_dbm": sample["router_a_scan_dbm"],
            "router_a_scan_lqi": sample["router_a_scan_lqi"],
            "router_b_scan_dbm": sample["router_b_scan_dbm"],
            "router_b_scan_lqi": sample["router_b_scan_lqi"],
            "ip_counters_json": json.dumps(sample["ip_counters"], sort_keys=True),
            "mle_counters_json": json.dumps(sample["mle_counters"], sort_keys=True),
        }
        for probe_name, probe in sample["probe_results"].items():
            prefix = probe_name
            sim_rss = sample.get("probe_sim_rss", {}).get(probe_name, {})
            row[f"{prefix}_tx"] = probe["tx"]
            row[f"{prefix}_rx"] = probe["rx"]
            row[f"{prefix}_loss_pct"] = probe["loss_pct"]
            row[f"{prefix}_rtt_min_ms"] = probe["rtt_min_ms"]
            row[f"{prefix}_rtt_avg_ms"] = probe["rtt_avg_ms"]
            row[f"{prefix}_rtt_max_ms"] = probe["rtt_max_ms"]
            row[f"{prefix}_sim_rss_method"] = sim_rss.get("method")
            row[f"{prefix}_sim_rss_match_status"] = sim_rss.get("match_status")
            row[f"{prefix}_sim_rss_match_confidence"] = sim_rss.get("match_confidence")
            row[f"{prefix}_request_rx_sim_rss_dbm"] = sim_rss.get("request_rx_sim_rss_dbm")
            row[f"{prefix}_request_rx_sim_lqi"] = sim_rss.get("request_rx_sim_lqi")
            row[f"{prefix}_reply_rx_sim_rss_dbm"] = sim_rss.get("reply_rx_sim_rss_dbm")
            row[f"{prefix}_reply_rx_sim_lqi"] = sim_rss.get("reply_rx_sim_lqi")
            row[f"{prefix}_sim_rss_event_time_s"] = sim_rss.get("event_time_s")
        rows.append(row)
    return rows


def collect_sim_rss_records(samples: list[dict[str, Any]]) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    records: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for sample in samples:
        for probe_name, sim_rss in sample.get("probe_sim_rss", {}).items():
            if sim_rss:
                records.append((probe_name, sim_rss, sample))
        if sample.get("mobile_to_parent_sim_rss"):
            records.append(("mobile_to_parent", sample["mobile_to_parent_sim_rss"], sample))
    return records


def sim_rss_summary_for_probe(records: list[tuple[str, dict[str, Any], dict[str, Any]]], probe_name: str) -> dict[str, Any]:
    probe_records = [(sim_rss, sample) for name, sim_rss, sample in records if name == probe_name]
    request_values = [
        float(sim_rss["request_rx_sim_rss_dbm"])
        for sim_rss, _ in probe_records
        if sim_rss.get("request_rx_sim_rss_dbm") is not None
    ]
    reply_values = [
        float(sim_rss["reply_rx_sim_rss_dbm"])
        for sim_rss, _ in probe_records
        if sim_rss.get("reply_rx_sim_rss_dbm") is not None
    ]
    matched = sum(1 for sim_rss, _ in probe_records if sim_rss.get("match_status") == "model_derived")
    return {
        "request_rx_dbm_mean": numeric_mean(request_values),
        "request_rx_dbm_median": numeric_median(request_values),
        "reply_rx_dbm_mean": numeric_mean(reply_values),
        "reply_rx_dbm_median": numeric_median(reply_values),
        "match_rate": round(matched / len(probe_records), 6) if probe_records else None,
    }


def end_dwell_sim_rss_values(
    samples: list[dict[str, Any]],
    movement_steps: int,
    probe_name: str,
    field: str = "request_rx_sim_rss_dbm",
) -> list[float]:
    values: list[float] = []
    for sample in samples:
        if int(sample.get("sample_index") or 0) < movement_steps:
            continue
        if probe_name == "mobile_to_parent":
            sim_rss = sample.get("mobile_to_parent_sim_rss", {})
        else:
            sim_rss = sample.get("probe_sim_rss", {}).get(probe_name, {})
        value = sim_rss.get(field)
        if value is not None:
            values.append(float(value))
    return values


def build_summary(
    scenario: dict[str, Any],
    samples: list[dict[str, Any]],
    switch_events: list[dict[str, Any]],
    notes: list[str],
    selected_radio_model: str | None,
    total_outage_s: float,
    mock: bool,
    parent_before_delayed_nodes: str | None = None,
    thread_device_type: str | None = None,
    parent_search_config: str = "unknown",
    sim_ping_rss_capture_enabled: bool = False,
) -> dict[str, Any]:
    total_tx = 0
    total_rx = 0
    parent_probe_total_tx = 0
    parent_probe_total_rx = 0
    parent_probe_rtt_values: list[float] = []
    parent_sequence = [sample.get("parent_node_guess") for sample in samples if sample.get("parent_node_guess")]
    oscillations = 0
    for left, middle, right in zip(parent_sequence, parent_sequence[1:], parent_sequence[2:]):
        if left == right and left != middle:
            oscillations += 1

    for sample in samples:
        for probe in sample["probe_results"].values():
            total_tx += int(probe["tx"] or 0)
            total_rx += int(probe["rx"] or 0)
        parent_probe = sample.get("mobile_to_parent_result", {})
        parent_probe_total_tx += int(parent_probe.get("tx") or 0)
        parent_probe_total_rx += int(parent_probe.get("rx") or 0)
        if parent_probe.get("rtt_avg_ms") is not None:
            parent_probe_rtt_values.append(float(parent_probe["rtt_avg_ms"]))

    parent_probe_pdr = (parent_probe_total_rx / parent_probe_total_tx) if parent_probe_total_tx else None
    pdr = (total_rx / total_tx) if total_tx else parent_probe_pdr
    compact_parent_sequence = [value for index, value in enumerate(parent_sequence) if index == 0 or value != parent_sequence[index - 1]]
    initial_observed_parent = samples[0].get("parent_node_guess") if samples else None
    final_observed_parent = samples[-1].get("parent_node_guess") if samples else None
    final_mle_counters = samples[-1].get("mle_counters", {}) if samples else {}
    sim_rss_records = collect_sim_rss_records(samples)
    sim_rss_total_probe_events = len(sim_rss_records) if sim_ping_rss_capture_enabled else 0
    sim_rss_matched_probe_events = sum(
        1 for _, sim_rss, _ in sim_rss_records if sim_rss.get("match_status") == "model_derived"
    )
    sim_rss_ambiguous_probe_events = sum(
        1 for _, sim_rss, _ in sim_rss_records if sim_rss.get("match_status") == "ambiguous"
    )
    sim_rss_unmatched_probe_events = max(
        0,
        sim_rss_total_probe_events - sim_rss_matched_probe_events - sim_rss_ambiguous_probe_events,
    )
    sim_rss_probe_names = sorted({name for name, _, _ in sim_rss_records})
    sim_rss_probe_stats = {
        name: sim_rss_summary_for_probe(sim_rss_records, name)
        for name in sim_rss_probe_names
        if sim_ping_rss_capture_enabled
    }
    movement_steps = int(scenario.get("timing", {}).get("movement_steps", 0) or 0)
    mobile_parent_end_rssi = end_dwell_sim_rss_values(
        samples,
        movement_steps,
        "mobile_to_parent",
        "reply_rx_sim_rss_dbm",
    )
    mobile_parent_end_lqi = end_dwell_sim_rss_values(
        samples,
        movement_steps,
        "mobile_to_parent",
        "reply_rx_sim_lqi",
    )
    expected_initial_parent = scenario.get("expected_initial_parent")
    if expected_initial_parent and initial_observed_parent != expected_initial_parent:
        result_classification = "initial_parent_unexpected"
    elif switch_events:
        result_classification = "switch_observed"
    elif initial_observed_parent and final_observed_parent:
        result_classification = "no_switch_observed"
    else:
        result_classification = "inconclusive"

    return {
        "scenario_name": scenario["name"],
        "scenario_title": scenario["title"],
        "device_profile": scenario.get("device_profile", "mobile_end_device"),
        "thread_device_type": thread_device_type,
        "parent_search_config": parent_search_config,
        "mock": mock,
        "selected_radio_model": selected_radio_model,
        "packet_probe_reliable": scenario.get("observability", {}).get("packet_probe_reliable", True),
        "primary_parent_observation": scenario.get("observability", {}).get(
            "primary_parent_observation",
            "packet_probe",
        ),
        "sample_count": len(samples),
        "expected_initial_parent": expected_initial_parent,
        "pre_movement_parent_before_delayed_nodes": parent_before_delayed_nodes,
        "initial_observed_parent": initial_observed_parent,
        "final_observed_parent": final_observed_parent,
        "parent_sequence": compact_parent_sequence,
        "result_classification": result_classification,
        "switch_count": len(switch_events),
        "first_switch_time_s": switch_events[0]["sim_time_s"] if switch_events else None,
        "switch_position_x": samples[switch_events[0]["sample_index"]].get("mobile_x") if switch_events else None,
        "switch_events": switch_events,
        "total_outage_s": total_outage_s,
        "packet_delivery_ratio": round(pdr, 6) if pdr is not None else None,
        "parent_probe_enabled": True,
        "parent_probe_interval_s": scenario.get("timing", {}).get("step_seconds"),
        "parent_probe_total_tx": parent_probe_total_tx,
        "parent_probe_total_rx": parent_probe_total_rx,
        "parent_probe_delivery_ratio": round(parent_probe_pdr, 6) if parent_probe_pdr is not None else None,
        "parent_probe_mean_rtt_avg_ms": (
            round(sum(parent_probe_rtt_values) / len(parent_probe_rtt_values), 6)
            if parent_probe_rtt_values
            else None
        ),
        "sim_ping_rss_capture_enabled": sim_ping_rss_capture_enabled,
        "sim_ping_rss_capture_method": (
            "otns_model_derived_at_ping" if sim_ping_rss_capture_enabled else None
        ),
        "sim_ping_rss_policy": "request_and_reply_when_available",
        "sim_ping_rss_total_probe_events": sim_rss_total_probe_events,
        "sim_ping_rss_matched_probe_events": sim_rss_matched_probe_events,
        "sim_ping_rss_match_rate": (
            round(sim_rss_matched_probe_events / sim_rss_total_probe_events, 6)
            if sim_rss_total_probe_events
            else None
        ),
        "sim_ping_rss_unmatched_probe_events": sim_rss_unmatched_probe_events,
        "sim_ping_rss_ambiguous_probe_events": sim_rss_ambiguous_probe_events,
        "sim_ping_rss_probe_stats": sim_rss_probe_stats,
        "mobile_to_parent_end_dwell_sim_rss_dbm_mean": numeric_mean(mobile_parent_end_rssi),
        "mobile_to_parent_end_dwell_sim_rss_dbm_median": numeric_median(mobile_parent_end_rssi),
        "mobile_to_parent_end_dwell_sim_lqi_median": numeric_median(mobile_parent_end_lqi),
        "oscillation_events": oscillations,
        "mle_parent_changes": counter_int(final_mle_counters, "Parent Changes"),
        "mle_attach_attempts": counter_int(final_mle_counters, "Attach Attempts"),
        "mle_better_parent_attach_attempts": counter_int(final_mle_counters, "Better Parent Attach Attempts"),
        "notes": [*scenario.get("observability", {}).get("notes", []), *notes],
    }


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        raise ValueError("No rows to write")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(data: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    args = parse_args()
    scenario = load_scenario(args.scenario)
    ensure_results_dir(args.results_dir)

    token = args.timestamp_token or timestamp_token()
    csv_path = args.results_dir / f"baseline_run_{token}.csv"
    json_path = args.results_dir / f"baseline_summary_{token}.json"
    replay_before = snapshot_replay_files(args.otns_workdir) if args.capture_replay and not args.mock else {}

    runner: RealBenchmarkRunner | MockBenchmarkRunner
    runner = (
        MockBenchmarkRunner(
            scenario,
            thread_device_type=args.thread_device_type,
            parent_search_config=args.parent_search_config,
            capture_sim_ping_rss=args.capture_sim_ping_rss,
        )
        if args.mock
        else RealBenchmarkRunner(
            scenario,
            args.otns_command,
            args.otns_workdir,
            args.otns_watch_level,
            node_binary_path=args.node_binary_path,
            ftd_node_binary_path=args.ftd_node_binary_path,
            thread_device_type=args.thread_device_type,
            parent_search_config=args.parent_search_config,
            capture_sim_ping_rss=args.capture_sim_ping_rss,
        )
    )

    try:
        rows, summary = runner.run()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OtnsSessionError, subprocess.SubprocessError, TimeoutError) as exc:
        print(f"Benchmark execution failed: {exc}", file=sys.stderr)
        return 1

    replay_info = maybe_capture_replay(
        capture_replay=args.capture_replay,
        mock=args.mock,
        scenario=scenario,
        scenario_path=args.scenario,
        token=token,
        otns_command=args.otns_command,
        otns_workdir=args.otns_workdir,
        replay_source=args.replay_source,
        replay_dir=args.replay_dir,
        firmware_variant=args.firmware_variant,
        thread_device_type=args.thread_device_type,
        parent_search_config=args.parent_search_config,
        node_binary_path=args.node_binary_path,
        ftd_node_binary_path=args.ftd_node_binary_path,
        build_config_source=args.build_config_source,
        equivalent_to=args.equivalent_to,
        openthread_commit=args.openthread_commit,
        otns_commit=args.otns_commit,
        csv_path=csv_path,
        json_path=json_path,
        summary=summary,
        replay_before=replay_before,
    )
    if replay_info.get("warning"):
        summary.setdefault("notes", []).append(str(replay_info["warning"]))
    node_log_info: dict[str, Any] = {
        "requested": args.otns_watch_level.lower() != "off",
        "watch_level": args.otns_watch_level,
        "copied_files": [],
        "warning": None,
    }
    if args.mock:
        if node_log_info["requested"]:
            summary.setdefault("notes", []).append(
                "OTNS watch logging was requested in mock mode; no per-device OTNS node logs were captured."
            )
    else:
        node_log_info = capture_node_logs(
            results_dir=args.results_dir,
            node_refs=runner.node_refs,
            otns_workdir=args.otns_workdir,
            watch_level=args.otns_watch_level,
        )
        if node_log_info.get("warning"):
            summary.setdefault("notes", []).append(str(node_log_info["warning"]))
    summary["firmware_variant"] = args.firmware_variant
    summary["thread_device_type"] = args.thread_device_type
    summary["parent_search_config"] = args.parent_search_config
    summary["node_binary_path"] = str(args.node_binary_path) if args.node_binary_path is not None else None
    summary["ftd_node_binary_path"] = (
        str(args.ftd_node_binary_path) if args.ftd_node_binary_path is not None else None
    )
    summary["build_config_source"] = args.build_config_source
    summary["equivalent_to"] = args.equivalent_to
    summary["openthread_commit"] = args.openthread_commit
    summary["otns_commit"] = args.otns_commit
    summary["otns_watch_level"] = args.otns_watch_level
    summary["node_log_files"] = node_log_info.get("copied_files", [])
    summary["replay_capture_requested"] = args.capture_replay
    summary["sim_ping_rss_capture_requested"] = args.capture_sim_ping_rss
    summary["replay_file"] = replay_info.get("copied_path")
    summary["replay_metadata_file"] = replay_info.get("metadata_path")

    write_csv(rows, csv_path)
    write_json(summary, json_path)

    if args.copy_results_to_artifact:
        tracked_dir = resolve_tracked_results_dir(
            args.commit_artifact_dir,
            args.artifact_name,
            scenario["name"],
            token,
        )
        tracked_collection = tracked_results_collection_name(scenario["name"], args.artifact_name)
        run_id = format_run_id(token)
        try:
            tracked_info = export_tracked_results(
                tracked_dir=tracked_dir,
                tracked_collection=tracked_collection,
                run_id=run_id,
                scenario=scenario,
                scenario_path=args.scenario,
                firmware_variant=args.firmware_variant,
                thread_device_type=args.thread_device_type,
                parent_search_config=args.parent_search_config,
                node_binary_path=args.node_binary_path,
                ftd_node_binary_path=args.ftd_node_binary_path,
                build_config_source=args.build_config_source,
                equivalent_to=args.equivalent_to,
                openthread_commit=args.openthread_commit,
                otns_commit=args.otns_commit,
                otns_command=args.otns_command,
                otns_workdir=args.otns_workdir,
                token=token,
                csv_path=csv_path,
                json_path=json_path,
                replay_info=replay_info,
                node_log_files=node_log_info.get("copied_files", []),
                summary=summary,
            )
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(tracked_info["tracked_dir"])
        print(tracked_info["manifest_path"])

    print(csv_path)
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
