#!/usr/bin/env python3
"""Run the stock OpenThread mobility baseline in OTNS or in mock mode."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
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
PARENT_RANK_LOG_RE = re.compile(r"^\s*(?P<sim_time_us>\d+)\s+.*\bParentRank:\s+(?P<fields>.+)$")
PARENT_RANK_FIELD_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>\S+)")
PREFPARENT_EVENT_RE = re.compile(r"(?:^|\s)PREFPARENT\s+(?P<fields>.+)$")
PARENT_RANK_KEY_ALIASES = {
    "d": "decision",
    "c": "criterion",
    "r": "challenger_rloc16",
    "i": "incumbent_rloc16",
    "v": "challenger_value",
    "iv": "incumbent_value",
    "lm": "challenger_margin",
    "im": "incumbent_margin",
}
PARENT_RANK_CRITERION_ALIASES = {
    "tw_lq": "two_way_link_quality",
    "router": "is_router",
    "priority": "parent_priority",
    "lq3_count": "link_quality_3_count",
    "version": "thread_version",
    "sed_buf": "sed_buffer_size",
    "sed_dgram": "sed_datagram_count",
    "lq2_count": "link_quality_2_count",
    "lq1_count": "link_quality_1_count",
    "tw_margin": "two_way_link_margin",
}
PARENT_RANK_CSV_FIELDS = [
    "source_log",
    "node",
    "sim_time_us",
    "sim_time_s",
    "decision",
    "criterion",
    "challenger_rloc16",
    "incumbent_rloc16",
    "challenger_value",
    "incumbent_value",
    "challenger_margin",
    "incumbent_margin",
]
PREFERRED_PARENT_EVENT_CSV_FIELDS = [
    "observed_time_s",
    "event",
    "generation",
    "target",
    "parent",
    "rloc16",
    "rssi",
    "time_us",
    "timing_source",
    "resolution_us",
    "state",
    "mode",
    "reason",
    "error",
]


@dataclass
class NodeRef:
    name: str
    node_id: int
    extaddr: str | None = None
    rloc16: str | None = None
    x: float | None = None
    y: float | None = None
    tx_power_dbm: float | None = None
    verified_tx_power_dbm: float | None = None
    executable_path: str | None = None
    executable_sha256: str | None = None
    firmware_profile: str | None = None


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
        "--otns-runtime-dir",
        type=Path,
        default=None,
        help=(
            "Optional isolated directory used as the OTNS process working directory. "
            "The repeated runner uses this to isolate tmp files, PCAPs, replays, and node logs."
        ),
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
        "--node-binary-profile",
        choices=("stock", "preferred-parent"),
        default=None,
        help="Declared profile for --node-binary-path; required by directed scenarios.",
    )
    parser.add_argument(
        "--ftd-node-binary-path",
        type=Path,
        default=None,
        help="Optional FTD node binary path. When provided, OTNS is told to use it for router/reed/fed nodes.",
    )
    parser.add_argument(
        "--ftd-node-binary-profile",
        choices=("stock", "fastpr"),
        default=None,
        help="Declared profile for --ftd-node-binary-path; required by directed scenarios.",
    )
    parser.add_argument(
        "--build-config-source",
        default=None,
        help="Path or command that documents how the node binary was built.",
    )
    parser.add_argument(
        "--firmware-source-repo",
        type=Path,
        default=Path(os.environ["FIRMWARE_SOURCE_REPO"]) if os.environ.get("FIRMWARE_SOURCE_REPO") else None,
        help="Optional firmware/patch repository recorded in artifact provenance.",
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def command_option_value(command: str, option: str) -> str | None:
    arguments = shlex.split(command)
    for index, argument in enumerate(arguments):
        if argument == option and index + 1 < len(arguments):
            return arguments[index + 1]
        if argument.startswith(f"{option}="):
            return argument.split("=", 1)[1]
    return None


def git_source_state(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    resolved = path.resolve()
    state: dict[str, Any] = {"path": str(resolved), "commit": None, "tracked_changes": None}
    try:
        state["commit"] = subprocess.run(
            ["git", "-C", str(resolved), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "-C", str(resolved), "status", "--porcelain", "--untracked-files=no"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        state["tracked_changes"] = bool(status.strip())
    except (OSError, subprocess.CalledProcessError) as exc:
        state["error"] = str(exc)
    return state


def write_artifact_checksums(artifact_dir: Path, output_name: str = "checksums.sha256") -> dict[str, str]:
    checksums = {
        path.relative_to(artifact_dir).as_posix(): sha256_file(path)
        for path in sorted(artifact_dir.rglob("*"))
        if path.is_file() and path.name != output_name
    }
    output_path = artifact_dir / output_name
    with output_path.open("w", encoding="utf-8") as handle:
        for relative_path, digest in checksums.items():
            handle.write(f"{digest}  {relative_path}\n")
    return checksums


def expand_executable_path(value: str | Path, scenario_path: Path) -> Path:
    expanded = Path(os.path.expandvars(os.path.expanduser(str(value))))
    if not expanded.is_absolute():
        expanded = scenario_path.resolve().parent / expanded
    return expanded.resolve()


def validate_scenario_configuration(
    scenario: dict[str, Any],
    scenario_path: Path,
    *,
    node_binary_path: Path | None,
    node_binary_profile: str | None,
    ftd_node_binary_path: Path | None,
    ftd_node_binary_profile: str | None,
    mock: bool,
) -> None:
    if scenario.get("scenario_type") != "directed_parent_switch":
        return

    directed = scenario.get("directed_switch")
    if not isinstance(directed, dict):
        raise ValueError("directed_parent_switch requires a directed_switch mapping")
    mode = directed.get("mode")
    if mode not in {"multicast", "unicast"}:
        raise ValueError("directed_switch.mode must be multicast or unicast")
    if directed.get("target_selection") != "random_non_current_parent":
        raise ValueError("directed_switch.target_selection must be random_non_current_parent")
    if not isinstance(directed.get("random_seed"), int):
        raise ValueError("directed_switch.random_seed must be an integer")
    expected_router_profile = directed.get("expected_router_firmware")
    if expected_router_profile not in {"stock", "fastpr"}:
        raise ValueError("directed_switch.expected_router_firmware must be stock or fastpr")
    if mode == "multicast" and expected_router_profile != "stock":
        raise ValueError("multicast directed switching requires stock router firmware")
    if expected_router_profile == "fastpr" and mode != "unicast":
        raise ValueError("fastpr router firmware is only valid with unicast mode")

    mobile = scenario.get("nodes", {}).get("mobile", {})
    mobile_override = mobile.get("executable")
    mobile_path = mobile_override or node_binary_path
    mobile_expected_profile = mobile.get("firmware_profile")
    mobile_profile = mobile_expected_profile if mobile_override else (node_binary_profile or mobile_expected_profile)
    if mobile_expected_profile != "preferred-parent" or mobile_profile != "preferred-parent":
        raise ValueError("directed switching requires the preferred-parent MTD profile")
    if not mock and mobile_path is None:
        raise ValueError("directed switching requires --node-binary-path or nodes.mobile.executable")
    if not mock and mobile_override is None and node_binary_profile is None:
        raise ValueError("--node-binary-profile is required with --node-binary-path")

    for name in router_names(scenario):
        config = scenario["nodes"][name]
        executable_override = config.get("executable")
        executable = executable_override or ftd_node_binary_path
        configured_profile = config.get("firmware_profile")
        profile = configured_profile if executable_override else (ftd_node_binary_profile or configured_profile)
        if configured_profile != expected_router_profile or profile != expected_router_profile:
            raise ValueError(
                f"{name} firmware profile {profile!r} does not match expected {expected_router_profile!r}"
            )
        if not mock and executable is None:
            raise ValueError(f"directed switching requires an executable for {name}")
        if not mock and executable_override is None and ftd_node_binary_profile is None:
            raise ValueError("--ftd-node-binary-profile is required with --ftd-node-binary-path")

    if mock:
        return
    configured_paths = [("mobile", mobile_path)] + [
        (name, scenario["nodes"][name].get("executable") or ftd_node_binary_path)
        for name in router_names(scenario)
    ]
    for name, value in configured_paths:
        assert value is not None
        path = expand_executable_path(value, scenario_path)
        if not path.is_file():
            raise ValueError(f"Executable for {name} does not exist: {path}")
        if not os.access(path, os.X_OK):
            raise ValueError(f"Executable for {name} is not executable: {path}")


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


def router_names(scenario: dict[str, Any]) -> list[str]:
    return [
        name
        for name, config in scenario.get("nodes", {}).items()
        if config.get("type") == "router" or name.startswith("router_")
    ]


def node_tx_power_dbm(config: dict[str, Any]) -> float | None:
    value = config.get("tx_power_dbm")
    if value in (None, "", "None"):
        return None
    return float(value)


def format_cli_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else str(value)


def parse_tx_power_output(lines: list[str]) -> float | None:
    for line in lines:
        match = re.search(r"-?\d+(?:\.\d+)?", line)
        if match:
            return float(match.group(0))
    return None


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
    tx_power_dbm: float | None = None,
) -> float | None:
    """Mirror OTNS MutualInterference 3GPP indoor RSS calculation at a ping event."""

    if None in (src_x, src_y, dst_x, dst_y, tx_power_dbm):
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


def otns_runtime_cwd(otns_workdir: Path | None, otns_runtime_dir: Path | None = None) -> Path:
    if otns_runtime_dir is not None:
        return otns_runtime_dir
    return otns_workdir if otns_workdir is not None else ROOT


def otns_output_dir(otns_workdir: Path | None, otns_runtime_dir: Path | None = None) -> Path:
    return otns_runtime_cwd(otns_workdir, otns_runtime_dir) / DEFAULT_OTNS_OUTPUT_DIRNAME


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
    otns_runtime_dir: Path | None,
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

    replay_workdir = otns_runtime_cwd(otns_workdir, otns_runtime_dir)
    detected_source, warning = infer_replay_source(replay_source, replay_workdir, replay_before)
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
        "otns_seed": command_option_value(otns_command, "-seed"),
        "otns_workdir": str(otns_workdir) if otns_workdir is not None else None,
        "otns_runtime_dir": str(replay_workdir),
        "replay_source": str(detected_source),
        "copied_replay_path": str(copied_path),
        "csv_path": str(csv_path),
        "summary_json_path": str(json_path),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mock": False,
        "selected_radio_model": summary.get("selected_radio_model"),
        "initial_observed_parent": summary.get("initial_observed_parent"),
        "pre_movement_parent_final": summary.get("pre_movement_parent_final"),
        "pre_movement_switch_count": summary.get("pre_movement_switch_count"),
        "pre_movement_parent_events": summary.get("pre_movement_parent_events"),
        "final_observed_parent": summary.get("final_observed_parent"),
        "switch_count": summary.get("switch_count"),
        "first_switch_time_s": summary.get("first_switch_time_s"),
        "second_switch_time_s": summary.get("second_switch_time_s"),
        "detach_count": summary.get("detach_count"),
        "first_detach_time_s": summary.get("first_detach_time_s"),
        "first_reattach_time_s": summary.get("first_reattach_time_s"),
        "reattach_latency_s": summary.get("reattach_latency_s"),
        "ended_detached": summary.get("ended_detached"),
        "recovery_classification": summary.get("recovery_classification"),
        "result_classification": summary.get("result_classification"),
        "configured_node_tx_power_dbm": summary.get("configured_node_tx_power_dbm"),
        "verified_node_tx_power_dbm": summary.get("verified_node_tx_power_dbm"),
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
    otns_runtime_dir: Path | None,
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

    output_dir = otns_output_dir(otns_workdir, otns_runtime_dir)
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


def parse_parent_rank_events(node_log_files: list[str]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for node_log_file in node_log_files:
        path = Path(node_log_file)
        node_label = path.stem.removeprefix("node_log_")
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = PARENT_RANK_LOG_RE.match(line)
            if match is None:
                continue

            event: dict[str, Any] = {
                "source_log": path.name,
                "node": node_label,
                "sim_time_us": int(match.group("sim_time_us")),
                "sim_time_s": round(int(match.group("sim_time_us")) / 1_000_000, 6),
            }
            for field in PARENT_RANK_FIELD_RE.finditer(match.group("fields")):
                key = PARENT_RANK_KEY_ALIASES.get(field.group("key"), field.group("key"))
                value = field.group("value")
                if key == "criterion":
                    value = PARENT_RANK_CRITERION_ALIASES.get(value, value)
                event[key] = value
            events.append(event)
    return events


def parent_rank_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    decisions: dict[str, int] = {}
    criteria: dict[str, int] = {}
    for event in events:
        decision = str(event.get("decision") or "unknown")
        criterion = str(event.get("criterion") or "unknown")
        decisions[decision] = decisions.get(decision, 0) + 1
        criteria[criterion] = criteria.get(criterion, 0) + 1
    return {
        "parent_rank_event_count": len(events),
        "parent_rank_decision_counts": decisions,
        "parent_rank_criterion_counts": criteria,
    }


def write_parent_rank_csv(events: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PARENT_RANK_CSV_FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(events)


def write_preferred_parent_event_csv(events: list[dict[str, Any]], path: Path) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=PREFERRED_PARENT_EVENT_CSV_FIELDS,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(events)


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
    node_binary_profile: str | None,
    ftd_node_binary_path: Path | None,
    ftd_node_binary_profile: str | None,
    build_config_source: str | None,
    firmware_source_repo: Path | None,
    equivalent_to: str | None,
    openthread_commit: str,
    otns_commit: str,
    otns_command: str,
    otns_workdir: Path | None,
    runner_invocation: list[str],
    scenario_copy_file: str,
    csv_file: str,
    summary_file: str,
    preferred_parent_event_file: str | None,
    parent_rank_file: str | None,
    replay_file: str | None,
    replay_metadata_file: str | None,
    node_log_files: list[str],
    token: str,
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_schema_version": 1,
        "results_collection": collection_name,
        "run_id": run_id,
        "scenario_name": scenario["name"],
        "scenario_file": scenario_file_label(scenario_path),
        "scenario_copy_file": scenario_copy_file,
        "scenario_sha256": sha256_file(scenario_path),
        "firmware_variant": firmware_variant,
        "device_profile": summary.get("device_profile"),
        "thread_device_type": thread_device_type,
        "parent_search_config": parent_search_config,
        "node_binary_path": str(node_binary_path) if node_binary_path is not None else None,
        "node_binary_profile": node_binary_profile,
        "ftd_node_binary_path": str(ftd_node_binary_path) if ftd_node_binary_path is not None else None,
        "ftd_node_binary_profile": ftd_node_binary_profile,
        "build_config_source": build_config_source,
        "source_repositories": {
            "otns_maps": git_source_state(ROOT),
            "otns": git_source_state(otns_workdir),
            "firmware_patches": git_source_state(firmware_source_repo),
        },
        "equivalent_to": equivalent_to,
        "openthread_commit": openthread_commit,
        "otns_commit": otns_commit,
        "otns_command": otns_command,
        "otns_seed": command_option_value(otns_command, "-seed"),
        "otns_workdir": str(otns_workdir) if otns_workdir is not None else None,
        "runner_invocation": runner_invocation,
        "runner_command": shlex.join(runner_invocation),
        "csv_file": csv_file,
        "summary_file": summary_file,
        "preferred_parent_event_file": preferred_parent_event_file,
        "parent_rank_file": parent_rank_file,
        "replay_file": replay_file,
        "replay_metadata_file": replay_metadata_file,
        "node_log_files": node_log_files,
        "checksums_file": "checksums.sha256",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "parent_rank_event_count": summary.get("parent_rank_event_count"),
        "parent_rank_decision_counts": summary.get("parent_rank_decision_counts"),
        "parent_rank_criterion_counts": summary.get("parent_rank_criterion_counts"),
        "scenario_type": summary.get("scenario_type", scenario.get("scenario_type")),
        "router_count": summary.get("router_count"),
        "parent_before_removal": summary.get("parent_before_removal"),
        "removed_parent_node": summary.get("removed_parent_node"),
        "removed_parent_node_id": summary.get("removed_parent_node_id"),
        "removed_parent_rloc16": summary.get("removed_parent_rloc16"),
        "removed_parent_extaddr": summary.get("removed_parent_extaddr"),
        "parent_removal_time_s": summary.get("parent_removal_time_s"),
        "parent_after_removal_final": summary.get("parent_after_removal_final"),
        "post_removal_switch_count": summary.get("post_removal_switch_count"),
        "post_removal_first_switch_time_s": summary.get("post_removal_first_switch_time_s"),
        "post_removal_reattach_latency_s": summary.get("post_removal_reattach_latency_s"),
        "selected_radio_model": summary.get("selected_radio_model"),
        "otns_watch_level": summary.get("otns_watch_level"),
        "initial_observed_parent": summary.get("initial_observed_parent"),
        "pre_movement_parent_final": summary.get("pre_movement_parent_final"),
        "pre_movement_switch_count": summary.get("pre_movement_switch_count"),
        "pre_movement_parent_events": summary.get("pre_movement_parent_events"),
        "final_observed_parent": summary.get("final_observed_parent"),
        "switch_count": summary.get("switch_count"),
        "first_switch_time_s": summary.get("first_switch_time_s"),
        "second_switch_time_s": summary.get("second_switch_time_s"),
        "switch_position_x": summary.get("switch_position_x"),
        "second_switch_position_x": summary.get("second_switch_position_x"),
        "detach_count": summary.get("detach_count"),
        "first_detach_time_s": summary.get("first_detach_time_s"),
        "first_detach_position_x": summary.get("first_detach_position_x"),
        "first_reattach_time_s": summary.get("first_reattach_time_s"),
        "first_reattach_position_x": summary.get("first_reattach_position_x"),
        "reattach_latency_s": summary.get("reattach_latency_s"),
        "ended_detached": summary.get("ended_detached"),
        "recovery_classification": summary.get("recovery_classification"),
        "packet_delivery_ratio": summary.get("packet_delivery_ratio"),
        "total_outage_s": summary.get("total_outage_s"),
        "oscillation_events": summary.get("oscillation_events"),
        "parent_sequence": summary.get("parent_sequence"),
        "time_spent_by_parent_s": summary.get("time_spent_by_parent_s"),
        "configured_node_tx_power_dbm": summary.get("configured_node_tx_power_dbm"),
        "verified_node_tx_power_dbm": summary.get("verified_node_tx_power_dbm"),
        "mle_parent_changes": summary.get("mle_parent_changes"),
        "mle_attach_attempts": summary.get("mle_attach_attempts"),
        "mle_better_parent_attach_attempts": summary.get("mle_better_parent_attach_attempts"),
        "result_classification": summary.get("result_classification"),
        "node_executables": summary.get("node_executables", {}),
        "directed_mode": summary.get("directed_mode"),
        "random_seed": summary.get("random_seed"),
        "initial_parent": summary.get("initial_parent"),
        "target_parent": summary.get("target_parent"),
        "target_parent_extaddr": summary.get("target_parent_extaddr"),
        "target_parent_rloc16": summary.get("target_parent_rloc16"),
        "command_acknowledged": summary.get("command_acknowledged"),
        "final_parent": summary.get("final_parent"),
        "labels": summary.get("labels", []),
        "preferred_parent_events": summary.get("preferred_parent_events", []),
        "protocol_event_timestamps": summary.get("protocol_event_timestamps", {}),
        "protocol_timing_ms": summary.get("protocol_timing_ms", {}),
        "protocol_timing_complete": summary.get("protocol_timing_complete"),
        "protocol_timing_source": summary.get("protocol_timing_source"),
        "protocol_timing_resolution_us": summary.get("protocol_timing_resolution_us"),
        "parent_deletion_to_target_observed_ms": summary.get("parent_deletion_to_target_observed_ms"),
        "parent_deletion_to_target_observed_source": summary.get("parent_deletion_to_target_observed_source"),
        "router_topology_changes": summary.get("router_topology_changes", {}),
        "directed_result_classification": summary.get("directed_result_classification"),
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
            f'- Packaged scenario: `{manifest["scenario_copy_file"]}`',
            f'- Firmware variant: `{manifest["firmware_variant"]}`',
            f'- Device profile: `{manifest["device_profile"]}`',
            f'- Thread device type: `{manifest["thread_device_type"]}`',
            f'- Parent search config: `{manifest["parent_search_config"]}`',
            f'- Node binary path: `{manifest["node_binary_path"]}`',
            f'- Node binary profile: `{manifest["node_binary_profile"]}`',
            f'- FTD node binary path: `{manifest["ftd_node_binary_path"]}`',
            f'- FTD node binary profile: `{manifest["ftd_node_binary_profile"]}`',
            f'- Build config source: `{manifest["build_config_source"]}`',
            f'- Equivalent to: `{manifest["equivalent_to"]}`',
            f'- OpenThread commit: `{manifest["openthread_commit"]}`',
            f'- OTNS commit: `{manifest["otns_commit"]}`',
            f'- OTNS command: `{manifest["otns_command"]}`',
            f'- OTNS random seed: `{manifest["otns_seed"]}`',
            f'- OTNS workdir: `{manifest["otns_workdir"]}`',
            f'- Runner command: `{manifest["runner_command"]}`',
            f'- OTNS watch level: `{manifest["otns_watch_level"]}`',
            f'- Selected radio model: `{manifest["selected_radio_model"]}`',
            f'- Initial observed parent: `{manifest["initial_observed_parent"]}`',
            f'- Pre-movement final parent: `{manifest["pre_movement_parent_final"]}`',
            f'- Pre-movement switch count: `{manifest["pre_movement_switch_count"]}`',
            f'- Pre-movement parent events: `{manifest["pre_movement_parent_events"]}`',
            f'- Final observed parent: `{manifest["final_observed_parent"]}`',
            f'- Switch count: `{manifest["switch_count"]}`',
            f'- First switch time (s): `{manifest["first_switch_time_s"]}`',
            f'- Second switch time (s): `{manifest["second_switch_time_s"]}`',
            f'- Switch position x: `{manifest["switch_position_x"]}`',
            f'- Second switch position x: `{manifest["second_switch_position_x"]}`',
            f'- Detach count: `{manifest["detach_count"]}`',
            f'- First detach time (s): `{manifest["first_detach_time_s"]}`',
            f'- First detach position x: `{manifest["first_detach_position_x"]}`',
            f'- First reattach time (s): `{manifest["first_reattach_time_s"]}`',
            f'- First reattach position x: `{manifest["first_reattach_position_x"]}`',
            f'- Reattach latency (s): `{manifest["reattach_latency_s"]}`',
            f'- Ended detached: `{manifest["ended_detached"]}`',
            f'- Recovery classification: `{manifest["recovery_classification"]}`',
            f'- Packet delivery ratio: `{manifest["packet_delivery_ratio"]}`',
            f'- Total outage (s): `{manifest["total_outage_s"]}`',
            f'- Oscillation events: `{manifest["oscillation_events"]}`',
            f'- Parent sequence: `{manifest["parent_sequence"]}`',
            f'- Time spent by parent (s): `{manifest["time_spent_by_parent_s"]}`',
            f'- Configured node TX power (dBm): `{manifest["configured_node_tx_power_dbm"]}`',
            f'- Verified node TX power (dBm): `{manifest["verified_node_tx_power_dbm"]}`',
            f'- MLE parent changes: `{manifest["mle_parent_changes"]}`',
            f'- MLE attach attempts: `{manifest["mle_attach_attempts"]}`',
            f'- MLE better parent attach attempts: `{manifest["mle_better_parent_attach_attempts"]}`',
            f'- Result classification: `{manifest["result_classification"]}`',
            f'- Node executable provenance: `{manifest["node_executables"]}`',
            f'- Directed mode: `{manifest["directed_mode"]}`',
            f'- Directed random seed: `{manifest["random_seed"]}`',
            f'- Directed initial parent: `{manifest["initial_parent"]}`',
            f'- Directed target parent: `{manifest["target_parent"]}`',
            f'- Directed command acknowledged: `{manifest["command_acknowledged"]}`',
            f'- Directed final parent: `{manifest["final_parent"]}`',
            f'- Directed labels: `{manifest["labels"]}`',
            f'- Directed result: `{manifest["directed_result_classification"]}`',
            f'- Parent ranking events: `{manifest["parent_rank_event_count"]}`',
            f'- Parent ranking decisions: `{manifest["parent_rank_decision_counts"]}`',
            f'- Parent ranking criteria: `{manifest["parent_rank_criterion_counts"]}`',
            f'- Scenario type: `{manifest["scenario_type"]}`',
            f'- Router count: `{manifest["router_count"]}`',
            f'- Parent before removal: `{manifest["parent_before_removal"]}`',
            f'- Removed parent: `{manifest["removed_parent_node"]}`',
            f'- Parent removal time (s): `{manifest["parent_removal_time_s"]}`',
            f'- Final parent after removal: `{manifest["parent_after_removal_final"]}`',
            f'- Post-removal switch count: `{manifest["post_removal_switch_count"]}`',
            f'- Post-removal first switch time (s): `{manifest["post_removal_first_switch_time_s"]}`',
            f'- Post-removal reattach latency (s): `{manifest["post_removal_reattach_latency_s"]}`',
            "",
            "## Parent Ranking",
            "",
            f'- Ranking CSV: `{manifest["parent_rank_file"] or "not captured"}`',
            f'- Preferred-parent event CSV: `{manifest["preferred_parent_event_file"] or "not captured"}`',
            f'- Integrity checks: `{manifest["checksums_file"]}`',
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
    node_binary_profile: str | None,
    ftd_node_binary_path: Path | None,
    ftd_node_binary_profile: str | None,
    build_config_source: str | None,
    firmware_source_repo: Path | None,
    equivalent_to: str | None,
    openthread_commit: str,
    otns_commit: str,
    otns_command: str,
    otns_workdir: Path | None,
    runner_invocation: list[str],
    token: str,
    csv_path: Path,
    json_path: Path,
    preferred_parent_event_path: Path | None,
    parent_rank_path: Path | None,
    replay_info: dict[str, Any],
    node_log_files: list[str],
    summary: dict[str, Any],
) -> dict[str, str]:
    if tracked_dir.exists():
        raise FileExistsError(f"Tracked results directory already exists: {tracked_dir}")
    tracked_dir.mkdir(parents=True, exist_ok=False)

    tracked_csv = tracked_dir / csv_path.name
    tracked_summary = tracked_dir / json_path.name
    tracked_scenario = tracked_dir / "scenario.yaml"
    shutil.copy2(csv_path, tracked_csv)
    shutil.copy2(json_path, tracked_summary)
    shutil.copy2(scenario_path, tracked_scenario)

    preferred_parent_event_relpath = None
    if preferred_parent_event_path is not None:
        tracked_preferred_parent_events = tracked_dir / preferred_parent_event_path.name
        shutil.copy2(preferred_parent_event_path, tracked_preferred_parent_events)
        preferred_parent_event_relpath = tracked_preferred_parent_events.name

    parent_rank_relpath = None
    if parent_rank_path is not None:
        tracked_parent_rank = tracked_dir / parent_rank_path.name
        shutil.copy2(parent_rank_path, tracked_parent_rank)
        parent_rank_relpath = tracked_parent_rank.name

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
        replay_metadata = json.loads(tracked_replay_metadata.read_text(encoding="utf-8"))
        replay_metadata["source_paths"] = {
            "copied_replay_path": replay_metadata.get("copied_replay_path"),
            "csv_path": replay_metadata.get("csv_path"),
            "summary_json_path": replay_metadata.get("summary_json_path"),
        }
        replay_metadata["copied_replay_path"] = replay_relpath
        replay_metadata["csv_path"] = tracked_csv.name
        replay_metadata["summary_json_path"] = tracked_summary.name
        write_json(replay_metadata, tracked_replay_metadata)

    tracked_node_log_files: list[str] = []
    for node_log_file in node_log_files:
        node_log_source = Path(node_log_file)
        tracked_node_log = tracked_dir / node_log_source.name
        shutil.copy2(node_log_source, tracked_node_log)
        tracked_node_log_files.append(tracked_node_log.name)

    tracked_summary_data = json.loads(tracked_summary.read_text(encoding="utf-8"))
    tracked_summary_data["preferred_parent_event_file"] = preferred_parent_event_relpath
    tracked_summary_data["parent_rank_file"] = parent_rank_relpath
    tracked_summary_data["replay_file"] = replay_relpath
    tracked_summary_data["replay_metadata_file"] = metadata_relpath
    tracked_summary_data["node_log_files"] = tracked_node_log_files
    tracked_summary_data["scenario_file"] = tracked_scenario.name
    write_json(tracked_summary_data, tracked_summary)

    manifest = tracked_results_manifest(
        collection_name=tracked_collection,
        run_id=run_id,
        scenario=scenario,
        scenario_path=scenario_path,
        firmware_variant=firmware_variant,
        thread_device_type=thread_device_type,
        parent_search_config=parent_search_config,
        node_binary_path=node_binary_path,
        node_binary_profile=node_binary_profile,
        ftd_node_binary_path=ftd_node_binary_path,
        ftd_node_binary_profile=ftd_node_binary_profile,
        build_config_source=build_config_source,
        firmware_source_repo=firmware_source_repo,
        equivalent_to=equivalent_to,
        openthread_commit=openthread_commit,
        otns_commit=otns_commit,
        otns_command=otns_command,
        otns_workdir=otns_workdir,
        runner_invocation=runner_invocation,
        scenario_copy_file=tracked_scenario.name,
        csv_file=tracked_csv.name,
        summary_file=tracked_summary.name,
        preferred_parent_event_file=preferred_parent_event_relpath,
        parent_rank_file=parent_rank_relpath,
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
    write_artifact_checksums(tracked_dir)
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


def parse_prefparent_events(lines: list[str], observed_time_s: float | None = None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in lines:
        match = PREFPARENT_EVENT_RE.search(line)
        if match is None:
            continue
        fields = {
            field.group("key"): field.group("value")
            for field in PARENT_RANK_FIELD_RE.finditer(match.group("fields"))
        }
        if "event" not in fields:
            continue
        events.append({"observed_time_s": observed_time_s, **fields})
    return events


def directed_preflight_labels(
    *,
    has_parent: bool,
    parent_is_mapped: bool,
    parent_is_leader: bool = False,
    eligible_target_count: int = 0,
) -> list[str]:
    """Classify directed-switch setup without depending on an OTNS session."""
    if not has_parent:
        return ["SKIP_NO_CHILD_PARENT"]
    if not parent_is_mapped:
        return ["SKIP_PARENT_NOT_MAPPED_TO_DEVICE"]

    labels = ["SKIP_PARENT_IS_LEADER"] if parent_is_leader else []
    if eligible_target_count < 1:
        labels.append("SKIP_NO_ELIGIBLE_TARGET_PARENT")
    return labels


def classify_directed_result(
    *,
    command_acknowledged: bool,
    command_error: str | None,
    labels: list[str],
    final_parent: str | None,
    target_parent: str | None,
) -> tuple[str, str | None]:
    """Return the stable result classification and optional result label."""
    if command_acknowledged:
        if final_parent == target_parent:
            return "selected_target_reached", "SELECTED_TARGET_REACHED"
        if final_parent:
            return "attached_to_non_target_parent", "ATTACHED_TO_NON_TARGET_PARENT"
        return "no_reattachment", "NO_REATTACHMENT"
    if command_error or "COMMAND_REJECTED" in labels:
        return "command_rejected", None
    return "skipped", None


def command_payload_lines(lines: list[str]) -> list[str]:
    """Return synchronous CLI payload lines, excluding asynchronous controller events."""
    return [line for line in lines if PREFPARENT_EVENT_RE.search(line) is None]


def first_integer_payload(lines: list[str], description: str) -> int:
    for line in command_payload_lines(lines):
        value = line.strip()
        if re.fullmatch(r"-?\d+", value):
            return int(value)
    raise OtnsSessionError(f"No integer {description} found in OTNS output: {lines!r}")


PROTOCOL_EVENT_NAMES = {
    "send_parent_request": "parent_request_started",
    "receive_parent_response": "target_response",
    "send_child_id_request": "child_id_request_started",
    "receive_child_id_response": "child_id_response_received",
}


def uint32_microsecond_delta(start_us: int, end_us: int) -> int:
    return (end_us - start_us) & 0xFFFFFFFF


def derive_preferred_parent_timing(
    events: list[dict[str, Any]],
    *,
    deletion_time_s: float | None,
    samples: list[dict[str, Any]],
    target_parent: str | None,
    poll_resolution_s: int,
) -> dict[str, Any]:
    event_records: dict[str, dict[str, Any]] = {}
    for semantic_name, event_name in PROTOCOL_EVENT_NAMES.items():
        event = next(
            (
                candidate
                for candidate in events
                if candidate.get("event") == event_name and candidate.get("time_us") is not None
            ),
            None,
        )
        if event is None:
            continue
        time_us = int(str(event["time_us"]), 10)
        event_records[semantic_name] = {
            "event": event_name,
            "time_us": time_us,
            "clock_time_s": round(time_us / 1_000_000.0, 6),
            "timing_source": event.get("timing_source", "otns_openthread_event"),
            "resolution_us": int(str(event.get("resolution_us", 1))),
            "clock_bits": 32,
        }

    def interval_ms(start: str, end: str) -> float | None:
        if start not in event_records or end not in event_records:
            return None
        delta_us = uint32_microsecond_delta(
            event_records[start]["time_us"], event_records[end]["time_us"]
        )
        if delta_us > 0x7FFFFFFF:
            return None
        return round(delta_us / 1000.0, 3)

    timing_ms = {
        "parent_request_to_response": interval_ms("send_parent_request", "receive_parent_response"),
        "parent_response_to_child_id_request": interval_ms(
            "receive_parent_response", "send_child_id_request"
        ),
        "child_id_request_to_response": interval_ms(
            "send_child_id_request", "receive_child_id_response"
        ),
        "parent_request_to_child_id_response": interval_ms(
            "send_parent_request", "receive_child_id_response"
        ),
    }
    complete = all(value is not None for value in timing_ms.values())
    target_sample = next(
        (sample for sample in samples if sample.get("parent_node_guess") == target_parent),
        None,
    )
    target_observed_s = float(target_sample["sim_time_s"]) if target_sample is not None else None
    deletion_to_target_ms = (
        round((target_observed_s - deletion_time_s) * 1000.0, 3)
        if target_observed_s is not None and deletion_time_s is not None
        else None
    )
    return {
        "protocol_event_timestamps": event_records,
        "protocol_timing_ms": timing_ms,
        "protocol_timing_complete": complete,
        "protocol_timing_source": "otns_openthread_event" if complete else None,
        "protocol_timing_resolution_us": 1 if complete else None,
        "protocol_clock": "otns_node_platform_micro_32",
        "parent_deletion": {
            "time_s": deletion_time_s,
            "timing_source": "otns_simulator_time" if deletion_time_s is not None else None,
            "resolution_us": 1 if deletion_time_s is not None else None,
        },
        "target_parent_observation": {
            "time_s": target_observed_s,
            "timing_source": "otns_parent_poll" if target_observed_s is not None else None,
            "resolution_us": poll_resolution_s * 1_000_000 if target_observed_s is not None else None,
        },
        "parent_deletion_to_target_observed_ms": deletion_to_target_ms,
        "parent_deletion_to_target_observed_source": (
            "otns_parent_poll" if deletion_to_target_ms is not None else None
        ),
    }


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
        otns_runtime_dir: Path | None = None,
        otns_watch_level: str = "off",
        node_binary_path: Path | None = None,
        ftd_node_binary_path: Path | None = None,
        node_binary_profile: str | None = None,
        ftd_node_binary_profile: str | None = None,
        thread_device_type: str | None = None,
        parent_search_config: str = "unknown",
        capture_sim_ping_rss: bool = False,
        scenario_path: Path = DEFAULT_SCENARIO,
    ) -> None:
        self.scenario = scenario
        self.scenario_path = scenario_path
        self.otns_command = with_otns_watch_level(otns_command, otns_watch_level)
        self.otns_workdir = otns_workdir
        self.otns_runtime_dir = otns_runtime_dir
        self.otns_watch_level = otns_watch_level
        self.node_binary_path = node_binary_path
        self.ftd_node_binary_path = ftd_node_binary_path
        self.node_binary_profile = node_binary_profile
        self.ftd_node_binary_profile = ftd_node_binary_profile
        self.thread_device_type = thread_device_type
        self.parent_search_config = parent_search_config
        self.capture_sim_ping_rss = capture_sim_ping_rss
        self.otns_runtime_cwd = otns_runtime_cwd(otns_workdir, otns_runtime_dir)
        self.notes: list[str] = []
        self.node_refs: dict[str, NodeRef] = {}
        self.parent_before_delayed_nodes: str | None = None
        self.initial_attachment_expected_parent: str | None = None
        self.initial_attachment_observed_parent: str | None = None
        self.initial_attachment_wait_s: int | None = None
        self.initial_attachment_timed_out = False
        self.pre_movement_parent_sequence: list[str] = []
        self.pre_movement_parent_events: list[dict[str, Any]] = []
        self.pre_movement_parent_final: str | None = None
        self.pre_movement_parent_observation_count = 0
        self.observability = scenario.get("observability", {})
        self.removed_node_names: set[str] = set()

    def run(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if shutil.which(self.otns_command.split()[0]) is None:
            raise FileNotFoundError(
                f"OTNS command not found: {self.otns_command}. Install OTNS or use --mock."
            )

        timing = self.scenario["timing"]
        if self.scenario.get("scenario_type") == "static_parent_removal":
            return self._run_static_parent_removal(timing)
        if self.scenario.get("scenario_type") == "directed_parent_switch":
            return self._run_directed_parent_switch(timing)

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
            initial_attachment_expected_parent=self.initial_attachment_expected_parent,
            initial_attachment_observed_parent=self.initial_attachment_observed_parent,
            initial_attachment_wait_s=self.initial_attachment_wait_s,
            initial_attachment_timed_out=self.initial_attachment_timed_out,
            pre_movement_parent_sequence=self.pre_movement_parent_sequence,
            pre_movement_parent_events=self.pre_movement_parent_events,
            pre_movement_parent_final=self.pre_movement_parent_final,
            pre_movement_parent_observation_count=self.pre_movement_parent_observation_count,
            thread_device_type=self.thread_device_type,
            parent_search_config=self.parent_search_config,
            sim_ping_rss_capture_enabled=self.capture_sim_ping_rss,
            node_refs=self.node_refs,
        )
        return rows, summary

    def _configure_session(self, session: OtnsSession) -> str:
        session.command_output("speed 0")
        session.command_output(f'title "{self.scenario["title"]}"')
        if self.ftd_node_binary_path is not None:
            session.command_output(f'exe ftd "{self.ftd_node_binary_path}"')
            self.notes.append(f"OTNS FTD executable set to {self.ftd_node_binary_path}.")
        if self.node_binary_path is not None:
            session.command_output(f'exe mtd "{self.node_binary_path}"')
            self.notes.append(f"OTNS MTD executable set to {self.node_binary_path}.")
        return self._select_radio_model(session)

    def _router_topology_snapshot(self, session: OtnsSession) -> dict[str, dict[str, Any]]:
        self._refresh_node_identity(session)
        snapshot: dict[str, dict[str, Any]] = {}
        for name in router_names(self.scenario):
            if name in self.removed_node_names:
                continue
            ref = self.node_refs[name]
            state = command_payload_lines(session.command_output(f'node {ref.node_id} "state"'))
            snapshot[name] = {
                "node_id": ref.node_id,
                "role": state[0] if state else None,
                "rloc16": ref.rloc16,
                "extaddr": ref.extaddr,
            }
        return snapshot

    def _run_directed_parent_switch(self, timing: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        directed = self.scenario["directed_switch"]
        mode = str(directed["mode"])
        seed = int(directed["random_seed"])
        step_seconds = max(1, int(timing.get("step_seconds", 1)))
        observe_seconds = int(timing.get("after_parent_removed_seconds", 0))
        router_settle_seconds = int(timing.get("router_settling_seconds", 0))
        child_attach_seconds = int(timing.get("child_attach_seconds", 0))
        samples: list[dict[str, Any]] = []
        switch_events: list[dict[str, Any]] = []
        preferred_parent_events: list[dict[str, Any]] = []
        labels: list[str] = []
        total_outage = 0.0
        outage_start: float | None = None
        initial_parent_name: str | None = None
        initial_parent_extaddr: str | None = None
        initial_parent_rloc16: str | None = None
        initial_parent_node_id: int | None = None
        target_name: str | None = None
        target_extaddr: str | None = None
        target_rloc16: str | None = None
        target_node_id: int | None = None
        command_acknowledged = False
        operation_generation: str | None = None
        command_output_lines: list[str] = []
        command_error: str | None = None
        deletion_time_s: float | None = None
        topology_before: dict[str, dict[str, Any]] = {}
        topology_after: dict[str, dict[str, Any]] = {}

        with OtnsSession(self.otns_command, cwd=self.otns_runtime_cwd) as session:
            radio_model = self._configure_session(session)
            router_node_names = list(
                self.scenario.get("activation", {}).get("initial_nodes") or router_names(self.scenario)
            )
            named_ids = self._create_nodes(session, router_node_names)
            if router_settle_seconds:
                session.command_output(f"go {router_settle_seconds}")
            topology_before = self._router_topology_snapshot(session)

            named_ids.update(self._create_nodes(session, ["mobile"]))
            if child_attach_seconds:
                session.command_output(f"go {child_attach_seconds}")
            self._refresh_node_identity(session)

            mobile_ref = self.node_refs["mobile"]
            parent_info: dict[str, str] = {}
            try:
                parent_info = parse_key_value_lines(
                    session.command_output(f'node {mobile_ref.node_id} "parent"')
                )
            except OtnsSessionError as exc:
                if "InvalidState" not in str(exc):
                    raise
            initial_parent_extaddr = parent_info.get("Ext Addr")
            initial_parent_rloc16 = parent_info.get("Rloc") or parent_info.get("RLOC16")
            initial_parent_name = self._parent_name_from_identity(parent_info)

            if not parent_info:
                labels.extend(
                    directed_preflight_labels(
                        has_parent=False,
                        parent_is_mapped=False,
                    )
                )
            elif initial_parent_name is None:
                labels.extend(
                    directed_preflight_labels(
                        has_parent=True,
                        parent_is_mapped=False,
                    )
                )
            else:
                initial_ref = self.node_refs[initial_parent_name]
                initial_parent_node_id = initial_ref.node_id
                eligible = sorted(
                    name
                    for name in router_node_names
                    if name != initial_parent_name and self.node_refs[name].extaddr
                )
                labels.extend(
                    directed_preflight_labels(
                        has_parent=True,
                        parent_is_mapped=True,
                        parent_is_leader=(
                            topology_before.get(initial_parent_name, {}).get("role") == "leader"
                        ),
                        eligible_target_count=len(eligible),
                    )
                )
                if eligible:
                    target_name = random.Random(seed).choice(eligible)
                    target_ref = self.node_refs[target_name]
                    target_extaddr = target_ref.extaddr
                    target_rloc16 = target_ref.rloc16
                    target_node_id = target_ref.node_id
                    try:
                        command_output_lines = session.command_output(
                            f'node {mobile_ref.node_id} "prefparent switch {target_extaddr} {mode}"'
                        )
                        now_s = first_integer_payload(session.command_output("time"), "simulation time") / 1_000_000.0
                        command_events = parse_prefparent_events(command_output_lines, now_s)
                        requested_event = next(
                            (event for event in command_events if event.get("event") == "requested"),
                            None,
                        )
                        command_acknowledged = requested_event is not None
                        if requested_event is not None:
                            operation_generation = requested_event.get("generation")
                            preferred_parent_events.extend(
                                event
                                for event in command_events
                                if event.get("generation") == operation_generation
                            )
                    except OtnsSessionError as exc:
                        command_error = str(exc)
                    if not command_acknowledged:
                        labels.append("COMMAND_REJECTED")
                    elif directed.get("remove_initial_parent", True):
                        session.command_output(f"del {initial_ref.node_id}")
                        self.removed_node_names.add(initial_parent_name)
                        deletion_time_s = first_integer_payload(
                            session.command_output("time"), "simulation time"
                        ) / 1_000_000.0

            previous_parent = initial_parent_name
            mobile_x = float(self.scenario["nodes"]["mobile"]["x"])
            mobile_y = float(self.scenario["nodes"]["mobile"]["y"])
            sample_count = max(1, observe_seconds // step_seconds)
            for index in range(sample_count):
                parent_probe = self._send_mobile_to_parent_probe(session, named_ids["mobile"])
                go_lines = session.command_output(f"go {step_seconds}")
                sim_time_s = first_integer_payload(
                    session.command_output("time"), "simulation time"
                ) / 1_000_000.0
                preferred_parent_events.extend(
                    event
                    for event in parse_prefparent_events(go_lines, sim_time_s)
                    if operation_generation is not None
                    and event.get("generation") == operation_generation
                )
                sample = self._collect_sample(
                    session, index, mobile_x, mobile_y, go_lines, parent_probe
                )
                sample.update(
                    {
                        "selected_radio_model": radio_model,
                        "scenario_phase": "post_parent_removal",
                        "removed_parent_node": initial_parent_name if deletion_time_s is not None else None,
                        "removed_parent_node_id": initial_parent_node_id if deletion_time_s is not None else None,
                        "directed_target_node": target_name,
                        "directed_target_extaddr": target_extaddr,
                    }
                )
                parent_identity = sample.get("parent_node_guess")
                switch = bool(previous_parent and parent_identity and parent_identity != previous_parent)
                sample["parent_switch"] = switch
                if switch:
                    switch_events.append(
                        {
                            "sample_index": index,
                            "sim_time_s": sample["sim_time_s"],
                            "phase": "post_parent_removal",
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
            topology_after = self._router_topology_snapshot(session)

        topology_changes = {
            name: {"before": before, "after": topology_after.get(name)}
            for name, before in topology_before.items()
            if name != initial_parent_name
            and (
                topology_after.get(name, {}).get("role") != before.get("role")
                or topology_after.get(name, {}).get("rloc16") != before.get("rloc16")
            )
        }
        if topology_changes:
            labels.append("ROUTER_TOPOLOGY_CHANGED")

        final_parent = samples[-1].get("parent_node_guess") if samples else None
        directed_result, result_label = classify_directed_result(
            command_acknowledged=command_acknowledged,
            command_error=command_error,
            labels=labels,
            final_parent=final_parent,
            target_parent=target_name,
        )
        if result_label is not None:
            labels.append(result_label)

        rows = flatten_samples(samples)
        summary = build_summary(
            scenario=self.scenario,
            samples=samples,
            switch_events=switch_events,
            notes=self.notes,
            selected_radio_model=rows[0]["selected_radio_model"] if rows else None,
            total_outage_s=round(total_outage, 3),
            mock=False,
            thread_device_type=self.thread_device_type,
            parent_search_config=self.parent_search_config,
            sim_ping_rss_capture_enabled=self.capture_sim_ping_rss,
            node_refs=self.node_refs,
        )
        timing_summary = derive_preferred_parent_timing(
            preferred_parent_events,
            deletion_time_s=deletion_time_s,
            samples=samples,
            target_parent=target_name,
            poll_resolution_s=step_seconds,
        )
        summary.update(
            {
                "scenario_type": "directed_parent_switch",
                "router_count": len(router_node_names),
                "router_settling_seconds": router_settle_seconds,
                "child_attach_seconds": child_attach_seconds,
                "after_parent_removed_seconds": observe_seconds,
                "directed_mode": mode,
                "target_selection": directed["target_selection"],
                "random_seed": seed,
                "initial_parent": initial_parent_name,
                "initial_parent_node_id": initial_parent_node_id,
                "initial_parent_extaddr": initial_parent_extaddr,
                "initial_parent_rloc16": initial_parent_rloc16,
                "target_parent": target_name,
                "target_parent_node_id": target_node_id,
                "target_parent_extaddr": target_extaddr,
                "target_parent_rloc16": target_rloc16,
                "command_acknowledged": command_acknowledged,
                "operation_generation": operation_generation,
                "command_output": command_output_lines,
                "command_error": command_error,
                "parent_removal_time_s": deletion_time_s,
                "final_parent": final_parent,
                "preferred_parent_events": preferred_parent_events,
                "labels": labels,
                "router_topology_before": topology_before,
                "router_topology_after": topology_after,
                "router_topology_changes": topology_changes,
                "directed_result_classification": directed_result,
                "result_classification": directed_result,
                **timing_summary,
            }
        )
        return rows, summary

    def _run_static_parent_removal(self, timing: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        removal = self.scenario.get("removal", {})
        step_seconds = int(timing.get("step_seconds", 1))
        observe_seconds = int(timing.get("after_parent_removed_seconds", 0))
        router_settle_seconds = int(timing.get("router_settling_seconds", 0))
        child_attach_seconds = int(timing.get("child_attach_seconds", 0))
        samples: list[dict[str, Any]] = []
        switch_events: list[dict[str, Any]] = []
        total_outage = 0.0
        outage_start = None
        parent_before_removal: str | None = None
        removed_parent_name: str | None = None
        removed_parent_node_id: int | None = None
        removed_parent_rloc16: str | None = None
        removed_parent_extaddr: str | None = None
        removal_time_s: float | None = None

        with OtnsSession(self.otns_command, cwd=self.otns_runtime_cwd) as session:
            radio_model = self._configure_session(session)
            router_node_names = list(
                self.scenario.get("activation", {}).get("initial_nodes")
                or [name for name in self.scenario["nodes"] if name != "mobile"]
            )
            named_ids = self._create_nodes(session, router_node_names)
            if router_settle_seconds:
                session.command_output(f"go {router_settle_seconds}")
            self._refresh_node_identity(session)

            named_ids.update(self._create_nodes(session, ["mobile"]))
            if child_attach_seconds:
                session.command_output(f"go {child_attach_seconds}")
            self._refresh_node_identity(session)

            mobile_ref = self.node_refs["mobile"]
            try:
                parent_info = parse_key_value_lines(session.command_output(f'node {mobile_ref.node_id} "parent"'))
                parent_before_removal = self._parent_name_from_identity(parent_info)
            except OtnsSessionError as exc:
                if "InvalidState" not in str(exc):
                    raise
                parent_before_removal = None
                self.notes.append("Static removal scenario could not read a mobile parent before removal.")

            if removal.get("target") == "observed_mobile_parent" and parent_before_removal:
                removed_parent_name = parent_before_removal
                removed_ref = self.node_refs[removed_parent_name]
                removed_parent_node_id = removed_ref.node_id
                removed_parent_rloc16 = removed_ref.rloc16
                removed_parent_extaddr = removed_ref.extaddr
                session.command_output(f"del {removed_ref.node_id}")
                self.removed_node_names.add(removed_parent_name)
                removal_time_s = first_integer_payload(
                    session.command_output("time"), "simulation time"
                ) / 1_000_000.0
                self.notes.append(
                    f"Static removal scenario deleted observed mobile parent `{removed_parent_name}` "
                    f"(Node<{removed_ref.node_id}>) after {child_attach_seconds}s child attach wait."
                )
            else:
                reason = "no observed mobile parent" if not parent_before_removal else f"unsupported target {removal.get('target')!r}"
                self.notes.append(f"Static removal scenario did not delete a parent: {reason}.")

            previous_parent = parent_before_removal
            mobile_x = float(self.scenario["nodes"]["mobile"]["x"])
            mobile_y = float(self.scenario["nodes"]["mobile"]["y"])
            sample_count = max(1, observe_seconds // max(1, step_seconds))
            for index in range(sample_count):
                parent_probe = self._send_mobile_to_parent_probe(session, named_ids["mobile"])
                go_output_lines = session.command_output(f"go {step_seconds}")
                sample = self._collect_sample(session, index, mobile_x, mobile_y, go_output_lines, parent_probe)
                sample["selected_radio_model"] = radio_model
                sample["scenario_phase"] = "post_parent_removal"
                sample["removed_parent_node"] = removed_parent_name
                sample["removed_parent_node_id"] = removed_parent_node_id

                parent_identity = sample.get("parent_node_guess")
                switch = bool(previous_parent and parent_identity and parent_identity != previous_parent)
                sample["parent_switch"] = switch
                if switch:
                    switch_events.append(
                        {
                            "sample_index": index,
                            "sim_time_s": sample["sim_time_s"],
                            "phase": "post_parent_removal",
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
            thread_device_type=self.thread_device_type,
            parent_search_config=self.parent_search_config,
            sim_ping_rss_capture_enabled=self.capture_sim_ping_rss,
            node_refs=self.node_refs,
        )
        summary.update(
            {
                "scenario_type": "static_parent_removal",
                "router_count": len(router_names(self.scenario)),
                "router_settling_seconds": router_settle_seconds,
                "child_attach_seconds": child_attach_seconds,
                "after_parent_removed_seconds": observe_seconds,
                "parent_before_removal": parent_before_removal,
                "removed_parent_node": removed_parent_name,
                "removed_parent_node_id": removed_parent_node_id,
                "removed_parent_rloc16": removed_parent_rloc16,
                "removed_parent_extaddr": removed_parent_extaddr,
                "parent_removal_time_s": removal_time_s,
                "parent_after_removal_final": samples[-1].get("parent_node_guess") if samples else None,
                "post_removal_switch_events": switch_events,
                "post_removal_switch_count": len(switch_events),
            }
        )
        if switch_events:
            summary["post_removal_first_switch_time_s"] = switch_events[0]["sim_time_s"]
            summary["post_removal_reattach_latency_s"] = (
                round(float(switch_events[0]["sim_time_s"]) - float(removal_time_s), 6)
                if removal_time_s is not None
                else None
            )
        else:
            summary["post_removal_first_switch_time_s"] = None
            summary["post_removal_reattach_latency_s"] = None
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

        request_rssi = derive_mutual_interference_rssi_dbm(
            src.x,
            src.y,
            dst.x,
            dst.y,
            tx_power_dbm=src.tx_power_dbm,
        )
        rx_count = int((ping_result or {}).get("rx") or 0)
        reply_rssi = (
            derive_mutual_interference_rssi_dbm(
                dst.x,
                dst.y,
                src.x,
                src.y,
                tx_power_dbm=dst.tx_power_dbm,
            )
            if rx_count > 0
            else None
        )
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
            tx_power = node_tx_power_dbm(config)
            is_mtd = config["type"] in {"med", "sed", "ssed"}
            executable_override = config.get("executable")
            executable_value = executable_override or (
                self.node_binary_path if is_mtd else self.ftd_node_binary_path
            )
            default_profile = self.node_binary_profile if is_mtd else self.ftd_node_binary_profile
            firmware_profile = (
                config.get("firmware_profile")
                if executable_override
                else (default_profile or config.get("firmware_profile"))
            )
            executable_path = (
                expand_executable_path(executable_value, self.scenario_path)
                if executable_value is not None
                else None
            )
            # OTNS-specific command: create a stock node type in the simulator.
            add_command = f'add {config["type"]}'
            if executable_path is not None:
                add_command += f' exe "{executable_path}"'
            output = session.command_output(add_command)
            node_id = first_integer_payload(output, "node id")
            named_ids[name] = node_id
            session.command_output(f'move {node_id} {config["x"]} {config["y"]}')
            verified_tx_power = None
            if tx_power is not None:
                session.command_output(f'node {node_id} "txpower {format_cli_number(tx_power)}"')
                try:
                    verified_tx_power = parse_tx_power_output(session.command_output(f'node {node_id} "txpower"'))
                except OtnsSessionError as exc:
                    self.notes.append(f"Unable to verify TX power for {name}: {exc}")
            self.node_refs[name] = NodeRef(
                name=name,
                node_id=node_id,
                x=config["x"],
                y=config["y"],
                tx_power_dbm=tx_power,
                verified_tx_power_dbm=verified_tx_power,
                executable_path=str(executable_path) if executable_path is not None else None,
                executable_sha256=sha256_file(executable_path) if executable_path is not None else None,
                firmware_profile=firmware_profile,
            )
        return named_ids

    def _activate_nodes(self, session: OtnsSession, timing: dict[str, Any]) -> dict[str, int]:
        activation = self.scenario.get("activation", {})
        configured_names = list(self.scenario["nodes"].keys())
        initial_node_names = activation.get("initial_nodes") or configured_names
        named_ids = self._create_nodes(session, list(initial_node_names))
        self._await_initial_parent(session, activation)

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
                try:
                    parent_info = parse_key_value_lines(session.command_output(f'node {mobile_ref.node_id} "parent"'))
                    self.parent_before_delayed_nodes = self._parent_name_from_identity(parent_info)
                except OtnsSessionError as exc:
                    if "InvalidState" not in str(exc):
                        raise
                    self.parent_before_delayed_nodes = "unknown"
                    note = (
                        "OTNS parent command returned InvalidState before delayed node activation; "
                        "initial parent before delayed activation is recorded as unknown."
                    )
                    if note not in self.notes:
                        self.notes.append(note)

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
            self._monitor_pre_movement_parent(session, post_activation_settle_seconds)
        return named_ids

    def _await_initial_parent(self, session: OtnsSession, activation: dict[str, Any]) -> None:
        wait_config = activation.get("await_initial_parent")
        if not wait_config:
            return

        expected_parent = wait_config.get("expected_parent") or self.scenario.get("expected_initial_parent")
        timeout_seconds = int(wait_config.get("timeout_seconds", 0))
        poll_interval_seconds = max(1, int(wait_config.get("poll_interval_seconds", 5)))
        self.initial_attachment_expected_parent = expected_parent

        mobile_ref = self.node_refs.get("mobile")
        if mobile_ref is None:
            return

        elapsed = 0
        last_parent: str | None = None
        while True:
            self._refresh_node_identity(session)
            try:
                parent_info = parse_key_value_lines(session.command_output(f'node {mobile_ref.node_id} "parent"'))
                last_parent = self._parent_name_from_identity(parent_info)
            except OtnsSessionError as exc:
                if "InvalidState" not in str(exc):
                    raise
                last_parent = None

            if last_parent:
                self.initial_attachment_observed_parent = last_parent
                self.parent_before_delayed_nodes = last_parent
            if expected_parent and last_parent == expected_parent:
                self.initial_attachment_wait_s = elapsed
                self.notes.append(
                    f"Initial parent `{expected_parent}` observed after {elapsed} simulated seconds; "
                    "delayed nodes are activated after this attachment gate."
                )
                return

            if elapsed >= timeout_seconds:
                break

            step = min(poll_interval_seconds, timeout_seconds - elapsed)
            if step <= 0:
                break
            session.command_output(f"go {step}")
            elapsed += step

        self.initial_attachment_wait_s = elapsed
        self.initial_attachment_timed_out = True
        if self.initial_attachment_observed_parent is None:
            self.parent_before_delayed_nodes = "unknown"
        self.notes.append(
            "Initial parent attachment gate timed out"
            + (f" after {elapsed} simulated seconds" if elapsed else "")
            + (
                f"; expected `{expected_parent}`, observed `{self.initial_attachment_observed_parent or 'unknown'}`."
                if expected_parent
                else "."
            )
        )

    def _current_mobile_parent_name(self, session: OtnsSession) -> str | None:
        self._refresh_node_identity(session)
        mobile_ref = self.node_refs.get("mobile")
        if mobile_ref is None:
            return None
        try:
            parent_info = parse_key_value_lines(session.command_output(f'node {mobile_ref.node_id} "parent"'))
        except OtnsSessionError as exc:
            if "InvalidState" not in str(exc):
                raise
            return None
        return self._parent_name_from_identity(parent_info)

    def _record_pre_movement_parent_observation(
        self,
        *,
        parent_name: str | None,
        sim_time_s: float,
        elapsed_s: int,
        previous_parent: str | None,
    ) -> str | None:
        self.pre_movement_parent_observation_count += 1
        if parent_name:
            self.pre_movement_parent_final = parent_name
            if not self.pre_movement_parent_sequence or self.pre_movement_parent_sequence[-1] != parent_name:
                self.pre_movement_parent_sequence.append(parent_name)
            if previous_parent and parent_name != previous_parent:
                self.pre_movement_parent_events.append(
                    {
                        "phase": "post_activation_settle",
                        "sim_time_s": round(sim_time_s, 6),
                        "elapsed_s": elapsed_s,
                        "from_parent": previous_parent,
                        "to_parent": parent_name,
                    }
                )
            return parent_name
        return previous_parent

    def _monitor_pre_movement_parent(self, session: OtnsSession, settle_seconds: int) -> None:
        activation = self.scenario.get("activation", {})
        poll_interval = max(
            1,
            int(
                activation.get(
                    "pre_movement_parent_poll_interval_seconds",
                    self.scenario.get("timing", {}).get("step_seconds", 1),
                )
            ),
        )
        previous_parent = (
            self.parent_before_delayed_nodes
            if self.parent_before_delayed_nodes not in (None, "", "unknown")
            else None
        )
        if previous_parent:
            self.pre_movement_parent_sequence = [previous_parent]
            self.pre_movement_parent_final = previous_parent

        elapsed = 0
        while elapsed < settle_seconds:
            step = min(poll_interval, settle_seconds - elapsed)
            session.command_output(f"go {step}")
            elapsed += step
            sim_time_us = first_integer_payload(session.command_output("time"), "simulation time")
            parent_name = self._current_mobile_parent_name(session)
            previous_parent = self._record_pre_movement_parent_observation(
                parent_name=parent_name,
                sim_time_s=sim_time_us / 1_000_000.0,
                elapsed_s=elapsed,
                previous_parent=previous_parent,
            )

        if self.pre_movement_parent_events:
            self.notes.append(
                "Parent changed during post-activation settle before movement sampling: "
                + ", ".join(
                    f"{event['from_parent']}->{event['to_parent']} at {event['sim_time_s']}s"
                    for event in self.pre_movement_parent_events
                )
            )

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
        sim_time_us = first_integer_payload(session.command_output("time"), "simulation time")
        state_lines = command_payload_lines(session.command_output(f'node {mobile.node_id} "state"'))
        rloc_lines = command_payload_lines(session.command_output(f'node {mobile.node_id} "rloc16"'))
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
            "mobile_tx_power_dbm": mobile.tx_power_dbm,
            "mobile_verified_tx_power_dbm": mobile.verified_tx_power_dbm,
            "mobile_to_parent_target_tx_power_dbm": (
                self.node_refs[(parent_probe or {}).get("target")].tx_power_dbm
                if (parent_probe or {}).get("target") in self.node_refs
                else None
            ),
            "mobile_to_parent_target_verified_tx_power_dbm": (
                self.node_refs[(parent_probe or {}).get("target")].verified_tx_power_dbm
                if (parent_probe or {}).get("target") in self.node_refs
                else None
            ),
            "mobile_to_parent_result": {},
            "ip_counters": ip_counters,
            "mle_counters": mle_counters,
            "probe_results": {},
        }

        for router_name in router_names(self.scenario):
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
            if name in self.removed_node_names:
                continue
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
        src_tx_power_dbm: float | None,
        dst_tx_power_dbm: float | None,
    ) -> dict[str, Any]:
        if not self.capture_sim_ping_rss or src is None or dst is None:
            return {}
        request_rssi = derive_mutual_interference_rssi_dbm(
            src[0],
            src[1],
            dst[0],
            dst[1],
            tx_power_dbm=src_tx_power_dbm,
        )
        reply_rssi = (
            derive_mutual_interference_rssi_dbm(
                dst[0],
                dst[1],
                src[0],
                src[1],
                tx_power_dbm=dst_tx_power_dbm,
            )
            if rx > 0
            else None
        )
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
        if self.scenario.get("scenario_type") == "static_parent_removal":
            return self._run_static_parent_removal_mock()
        if self.scenario.get("scenario_type") == "directed_parent_switch":
            return self._run_directed_parent_switch_mock()

        timing = self.scenario["timing"]
        positions = movement_positions(self.scenario)
        routers = {name: self.scenario["nodes"][name] for name in router_names(self.scenario)}
        router_identity = {
            name: {
                "extaddr": f"{index + 1:02x}" * 8,
                "rloc16": f"0x{(index + 1) * 0x1000:04x}",
            }
            for index, name in enumerate(routers)
        }
        mobile_tx_power = node_tx_power_dbm(self.scenario["nodes"]["mobile"])

        samples: list[dict[str, Any]] = []
        switch_events: list[dict[str, Any]] = []
        previous_parent = None
        total_outage = 0.0
        outage_active = False
        outage_start = None

        for index, (x, y) in enumerate(positions):
            sim_time_s = timing["settle_seconds"] + index * timing["step_seconds"]
            distances = {
                name: math.dist((x, y), (config["x"], config["y"]))
                for name, config in routers.items()
            }
            parent = min(distances, key=distances.get)
            if index in (10, 11):
                mobile_state = "detached"
            else:
                mobile_state = "child"
            parent_probe_rx = 1 if mobile_state == "child" else 0
            parent_identity = router_identity[parent]
            parent_tx_power = node_tx_power_dbm(routers[parent])

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
                "mobile_rloc16": "0x5400",
                "device_profile": self.scenario.get("device_profile", "mobile_end_device"),
                "thread_device_type": self.thread_device_type,
                "parent_search_config": self.parent_search_config,
                "packet_probe_reliable": self.observability.get("packet_probe_reliable", True),
                "primary_parent_observation": self.observability.get("primary_parent_observation", "packet_probe"),
                "parent_extaddr": parent_identity["extaddr"],
                "parent_rloc16": parent_identity["rloc16"],
                "parent_link_quality_in": 3 if connectivity_ok else 0,
                "parent_link_quality_out": 3 if connectivity_ok else 0,
                "parent_age": 5,
                "parent_version": 4,
                "parent_node_guess": parent,
                "mobile_to_parent_target": parent,
                "mobile_to_parent_target_rloc16": parent_identity["rloc16"],
                "mobile_to_parent_target_extaddr": parent_identity["extaddr"],
                "mobile_tx_power_dbm": mobile_tx_power,
                "mobile_verified_tx_power_dbm": mobile_tx_power,
                "mobile_to_parent_target_tx_power_dbm": parent_tx_power,
                "mobile_to_parent_target_verified_tx_power_dbm": parent_tx_power,
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
                "probe_results": {},
                "probe_sim_rss": {},
                "mobile_to_parent_sim_rss": self._mock_ping_sim_rss(
                    (x, y),
                    (routers[parent]["x"], routers[parent]["y"]),
                    sim_time_s,
                    parent_probe_rx,
                    mobile_tx_power,
                    parent_tx_power,
                ),
                "selected_radio_model": "mock",
                "connectivity_ok": connectivity_ok,
                "parent_switch": bool(switch_events and switch_events[-1]["sample_index"] == index),
            }
            for router_name, distance in distances.items():
                sample[f"{router_name}_scan_dbm"] = str(round(-25 - distance / 8, 1))
                sample[f"{router_name}_scan_lqi"] = "3" if distance < 250 else "2"
            samples.append(sample)

        if outage_active and outage_start is not None and samples:
            total_outage += samples[-1]["sim_time_s"] - outage_start

        rows = flatten_samples(samples)
        configured_tx_power, verified_tx_power = scenario_tx_power_summary(self.scenario)
        mock_node_refs = {
            name: NodeRef(
                name=name,
                node_id=index + 1,
                tx_power_dbm=configured_tx_power.get(name),
                verified_tx_power_dbm=verified_tx_power.get(name),
            )
            for index, name in enumerate(self.scenario.get("nodes", {}))
        }
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
            node_refs=mock_node_refs,
        )
        return rows, summary

    def _run_directed_parent_switch_mock(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        timing = self.scenario["timing"]
        directed = self.scenario["directed_switch"]
        routers = {name: self.scenario["nodes"][name] for name in router_names(self.scenario)}
        router_names_list = list(routers)
        router_identity = {
            name: {
                "extaddr": f"{index + 1:02x}" * 8,
                "rloc16": f"0x{(index + 1) * 0x1000:04x}",
            }
            for index, name in enumerate(router_names_list)
        }
        initial_parent = router_names_list[0]
        eligible = sorted(name for name in router_names_list if name != initial_parent)
        target = random.Random(int(directed["random_seed"])).choice(eligible)
        observe_seconds = int(timing.get("after_parent_removed_seconds", 0))
        step_seconds = max(1, int(timing.get("step_seconds", 1)))
        base_time = int(timing.get("router_settling_seconds", 0)) + int(
            timing.get("child_attach_seconds", 0)
        )
        mobile = self.scenario["nodes"]["mobile"]
        mobile_tx_power = node_tx_power_dbm(mobile)
        samples: list[dict[str, Any]] = []
        switch_events: list[dict[str, Any]] = []

        for index in range(max(1, observe_seconds // step_seconds)):
            sim_time_s = base_time + (index + 1) * step_seconds
            parent = None if index < 1 else target
            mobile_state = "detached" if parent is None else "child"
            parent_identity = router_identity.get(parent or "", {})
            parent_probe_rx = 1 if parent else 0
            if index == 1:
                switch_events.append(
                    {
                        "sample_index": index,
                        "sim_time_s": sim_time_s,
                        "phase": "post_parent_removal",
                        "from_parent": initial_parent,
                        "to_parent": target,
                    }
                )
            sample = {
                "sample_index": index,
                "sim_time_s": sim_time_s,
                "mobile_x": mobile["x"],
                "mobile_y": mobile["y"],
                "mobile_state": mobile_state,
                "mobile_rloc16": "0x5400" if parent else "0xfffe",
                "device_profile": self.scenario.get("device_profile", "minimal_end_device"),
                "thread_device_type": self.thread_device_type,
                "parent_search_config": self.parent_search_config,
                "packet_probe_reliable": self.observability.get("packet_probe_reliable", True),
                "primary_parent_observation": self.observability.get("primary_parent_observation", "packet_probe"),
                "parent_extaddr": parent_identity.get("extaddr"),
                "parent_rloc16": parent_identity.get("rloc16"),
                "parent_link_quality_in": 3 if parent else None,
                "parent_link_quality_out": 3 if parent else None,
                "parent_age": 1 if parent else None,
                "parent_version": 4 if parent else None,
                "parent_node_guess": parent,
                "mobile_to_parent_target": parent,
                "mobile_to_parent_target_rloc16": parent_identity.get("rloc16"),
                "mobile_to_parent_target_extaddr": parent_identity.get("extaddr"),
                "mobile_tx_power_dbm": mobile_tx_power,
                "mobile_verified_tx_power_dbm": mobile_tx_power,
                "mobile_to_parent_target_tx_power_dbm": node_tx_power_dbm(routers[parent]) if parent else None,
                "mobile_to_parent_target_verified_tx_power_dbm": node_tx_power_dbm(routers[parent]) if parent else None,
                "mobile_to_parent_result": {
                    "tx": 1 if parent else None,
                    "rx": parent_probe_rx if parent else None,
                    "loss_pct": 0.0 if parent else None,
                    "rtt_min_ms": 8.0 if parent else None,
                    "rtt_avg_ms": 10.0 if parent else None,
                    "rtt_max_ms": 12.0 if parent else None,
                },
                "ip_counters": {},
                "mle_counters": {},
                "probe_results": {},
                "probe_sim_rss": {},
                "mobile_to_parent_sim_rss": {},
                "selected_radio_model": "mock",
                "connectivity_ok": bool(parent),
                "parent_switch": index == 1,
                "scenario_phase": "post_parent_removal",
                "removed_parent_node": initial_parent,
                "removed_parent_node_id": 1,
                "directed_target_node": target,
                "directed_target_extaddr": router_identity[target]["extaddr"],
            }
            for router_name in router_names_list:
                sample[f"{router_name}_scan_dbm"] = "-40.0"
                sample[f"{router_name}_scan_lqi"] = "3"
            samples.append(sample)

        rows = flatten_samples(samples)
        mock_node_refs = {
            name: NodeRef(
                name=name,
                node_id=index + 1,
                extaddr=(router_identity.get(name) or {}).get("extaddr"),
                rloc16=(router_identity.get(name) or {}).get("rloc16"),
                tx_power_dbm=node_tx_power_dbm(config),
                verified_tx_power_dbm=node_tx_power_dbm(config),
                firmware_profile=config.get("firmware_profile"),
            )
            for index, (name, config) in enumerate(self.scenario["nodes"].items())
        }
        summary = build_summary(
            scenario=self.scenario,
            samples=samples,
            switch_events=switch_events,
            notes=["Mock mode was used. These results are for script validation only."],
            selected_radio_model="mock",
            total_outage_s=float(step_seconds),
            mock=True,
            thread_device_type=self.thread_device_type,
            parent_search_config=self.parent_search_config,
            sim_ping_rss_capture_enabled=self.capture_sim_ping_rss,
            node_refs=mock_node_refs,
        )
        topology = {
            name: {"node_id": index + 1, "role": "router", **router_identity[name]}
            for index, name in enumerate(router_names_list)
        }
        base_time_us = base_time * 1_000_000
        timing_fields = {"timing_source": "otns_openthread_event", "resolution_us": "1"}
        preferred_events = [
            {"observed_time_s": base_time, "event": "requested", "generation": "1", "target": router_identity[target]["extaddr"], "mode": directed["mode"]},
            {"observed_time_s": base_time, "event": "parent_request_started", "generation": "1", "time_us": str(base_time_us + 1_000), **timing_fields},
            {"observed_time_s": base_time, "event": "target_response", "generation": "1", "time_us": str(base_time_us + 51_000), **timing_fields},
            {"observed_time_s": base_time, "event": "child_id_request_started", "generation": "1", "time_us": str(base_time_us + 56_000), **timing_fields},
            {"observed_time_s": base_time, "event": "child_id_response_received", "generation": "1", "time_us": str(base_time_us + 66_000), **timing_fields},
            {"observed_time_s": base_time + step_seconds, "event": "succeeded", "generation": "1", "parent": router_identity[target]["extaddr"], "time_us": str(base_time_us + 66_000), **timing_fields},
        ]
        timing_summary = derive_preferred_parent_timing(
            preferred_events,
            deletion_time_s=float(base_time),
            samples=samples,
            target_parent=target,
            poll_resolution_s=step_seconds,
        )
        summary.update(
            {
                "scenario_type": "directed_parent_switch",
                "router_count": len(router_names_list),
                "router_settling_seconds": int(timing.get("router_settling_seconds", 0)),
                "child_attach_seconds": int(timing.get("child_attach_seconds", 0)),
                "after_parent_removed_seconds": observe_seconds,
                "directed_mode": directed["mode"],
                "target_selection": directed["target_selection"],
                "random_seed": int(directed["random_seed"]),
                "initial_parent": initial_parent,
                "initial_parent_node_id": 1,
                "initial_parent_extaddr": router_identity[initial_parent]["extaddr"],
                "initial_parent_rloc16": router_identity[initial_parent]["rloc16"],
                "target_parent": target,
                "target_parent_node_id": router_names_list.index(target) + 1,
                "target_parent_extaddr": router_identity[target]["extaddr"],
                "target_parent_rloc16": router_identity[target]["rloc16"],
                "command_acknowledged": True,
                "command_output": [f"PREFPARENT event=requested generation=1 target={router_identity[target]['extaddr']} mode={directed['mode']}"],
                "command_error": None,
                "parent_removal_time_s": float(base_time),
                "final_parent": target,
                "preferred_parent_events": preferred_events,
                "labels": ["SKIP_PARENT_IS_LEADER", "SELECTED_TARGET_REACHED"],
                "router_topology_before": topology,
                "router_topology_after": {name: value for name, value in topology.items() if name != initial_parent},
                "router_topology_changes": {},
                "directed_result_classification": "selected_target_reached",
                "result_classification": "selected_target_reached",
                **timing_summary,
            }
        )
        return rows, summary

    def _run_static_parent_removal_mock(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        timing = self.scenario["timing"]
        routers = {name: self.scenario["nodes"][name] for name in router_names(self.scenario)}
        router_names_list = list(routers)
        router_identity = {
            name: {
                "extaddr": f"{index + 1:02x}" * 8,
                "rloc16": f"0x{(index + 1) * 0x1000:04x}",
            }
            for index, name in enumerate(routers)
        }
        mobile = self.scenario["nodes"]["mobile"]
        mobile_tx_power = node_tx_power_dbm(mobile)
        removed_parent = router_names_list[0]
        fallback_parent = router_names_list[1] if len(router_names_list) > 1 else removed_parent
        observe_seconds = int(timing.get("after_parent_removed_seconds", 0))
        step_seconds = int(timing.get("step_seconds", 1))
        sample_count = max(1, observe_seconds // max(1, step_seconds))
        base_time = int(timing.get("router_settling_seconds", 0)) + int(timing.get("child_attach_seconds", 0))
        samples: list[dict[str, Any]] = []
        switch_events: list[dict[str, Any]] = []
        previous_parent = removed_parent
        total_outage = 0.0
        outage_start = None

        for index in range(sample_count):
            sim_time_s = base_time + (index + 1) * step_seconds
            mobile_state = "detached" if index < 2 else "child"
            parent = None if mobile_state == "detached" else fallback_parent
            parent_identity = router_identity.get(parent or "", {})
            parent_probe_rx = 1 if parent else 0
            if parent and previous_parent and parent != previous_parent:
                switch_events.append(
                    {
                        "sample_index": index,
                        "sim_time_s": sim_time_s,
                        "phase": "post_parent_removal",
                        "from_parent": previous_parent,
                        "to_parent": parent,
                    }
                )
            previous_parent = parent or previous_parent

            connectivity_ok = parent_probe_rx > 0
            if not connectivity_ok and outage_start is None:
                outage_start = sim_time_s
            elif connectivity_ok and outage_start is not None:
                total_outage += sim_time_s - outage_start
                outage_start = None

            parent_tx_power = node_tx_power_dbm(routers[parent]) if parent else None
            sample = {
                "sample_index": index,
                "sim_time_s": sim_time_s,
                "mobile_x": mobile["x"],
                "mobile_y": mobile["y"],
                "mobile_state": mobile_state,
                "mobile_rloc16": "0x5400",
                "device_profile": self.scenario.get("device_profile", "mobile_end_device"),
                "thread_device_type": self.thread_device_type,
                "parent_search_config": self.parent_search_config,
                "packet_probe_reliable": self.observability.get("packet_probe_reliable", True),
                "primary_parent_observation": self.observability.get("primary_parent_observation", "packet_probe"),
                "parent_extaddr": parent_identity.get("extaddr"),
                "parent_rloc16": parent_identity.get("rloc16"),
                "parent_link_quality_in": 3 if parent else None,
                "parent_link_quality_out": 3 if parent else None,
                "parent_age": 5 if parent else None,
                "parent_version": 4 if parent else None,
                "parent_node_guess": parent,
                "mobile_to_parent_target": parent,
                "mobile_to_parent_target_rloc16": parent_identity.get("rloc16"),
                "mobile_to_parent_target_extaddr": parent_identity.get("extaddr"),
                "mobile_tx_power_dbm": mobile_tx_power,
                "mobile_verified_tx_power_dbm": mobile_tx_power,
                "mobile_to_parent_target_tx_power_dbm": parent_tx_power,
                "mobile_to_parent_target_verified_tx_power_dbm": parent_tx_power,
                "mobile_to_parent_result": {
                    "tx": 1 if parent else None,
                    "rx": parent_probe_rx if parent else None,
                    "loss_pct": 0.0 if parent else None,
                    "rtt_min_ms": 8.0 if parent else None,
                    "rtt_avg_ms": 10.0 if parent else None,
                    "rtt_max_ms": 12.0 if parent else None,
                },
                "ip_counters": {"TxSuccess": str(index), "TxFailed": "0", "RxSuccess": str(index), "RxFailed": "0"},
                "mle_counters": {"AttachAttempts": "2", "RoleDetached": "1" if mobile_state == "detached" else "0"},
                "probe_results": {},
                "probe_sim_rss": {},
                "mobile_to_parent_sim_rss": self._mock_ping_sim_rss(
                    (mobile["x"], mobile["y"]),
                    (routers[parent]["x"], routers[parent]["y"]) if parent else None,
                    sim_time_s,
                    parent_probe_rx,
                    mobile_tx_power,
                    parent_tx_power,
                ),
                "selected_radio_model": "mock",
                "connectivity_ok": connectivity_ok,
                "parent_switch": bool(switch_events and switch_events[-1]["sample_index"] == index),
                "scenario_phase": "post_parent_removal",
                "removed_parent_node": removed_parent,
                "removed_parent_node_id": 1,
            }
            for router_name, router in routers.items():
                distance = math.dist((mobile["x"], mobile["y"]), (router["x"], router["y"]))
                sample[f"{router_name}_scan_dbm"] = str(round(-25 - distance / 8, 1))
                sample[f"{router_name}_scan_lqi"] = "3"
            samples.append(sample)

        if outage_start is not None and samples:
            total_outage += samples[-1]["sim_time_s"] - outage_start

        rows = flatten_samples(samples)
        configured_tx_power, verified_tx_power = scenario_tx_power_summary(self.scenario)
        mock_node_refs = {
            name: NodeRef(
                name=name,
                node_id=index + 1,
                tx_power_dbm=configured_tx_power.get(name),
                verified_tx_power_dbm=verified_tx_power.get(name),
            )
            for index, name in enumerate(self.scenario.get("nodes", {}))
        }
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
            node_refs=mock_node_refs,
        )
        removal_time_s = base_time
        summary.update(
            {
                "scenario_type": "static_parent_removal",
                "router_count": len(router_names_list),
                "router_settling_seconds": int(timing.get("router_settling_seconds", 0)),
                "child_attach_seconds": int(timing.get("child_attach_seconds", 0)),
                "after_parent_removed_seconds": observe_seconds,
                "parent_before_removal": removed_parent,
                "removed_parent_node": removed_parent,
                "removed_parent_node_id": 1,
                "removed_parent_rloc16": router_identity[removed_parent]["rloc16"],
                "removed_parent_extaddr": router_identity[removed_parent]["extaddr"],
                "parent_removal_time_s": removal_time_s,
                "parent_after_removal_final": samples[-1].get("parent_node_guess") if samples else None,
                "post_removal_switch_events": switch_events,
                "post_removal_switch_count": len(switch_events),
                "post_removal_first_switch_time_s": switch_events[0]["sim_time_s"] if switch_events else None,
                "post_removal_reattach_latency_s": (
                    round(float(switch_events[0]["sim_time_s"]) - float(removal_time_s), 6)
                    if switch_events
                    else None
                ),
            }
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
            "mobile_tx_power_dbm": sample.get("mobile_tx_power_dbm"),
            "mobile_verified_tx_power_dbm": sample.get("mobile_verified_tx_power_dbm"),
            "mobile_to_parent_target_tx_power_dbm": sample.get("mobile_to_parent_target_tx_power_dbm"),
            "mobile_to_parent_target_verified_tx_power_dbm": sample.get(
                "mobile_to_parent_target_verified_tx_power_dbm"
            ),
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
            "scenario_phase": sample.get("scenario_phase"),
            "removed_parent_node": sample.get("removed_parent_node"),
            "removed_parent_node_id": sample.get("removed_parent_node_id"),
            "directed_target_node": sample.get("directed_target_node"),
            "directed_target_extaddr": sample.get("directed_target_extaddr"),
            "ip_counters_json": json.dumps(sample["ip_counters"], sort_keys=True),
            "mle_counters_json": json.dumps(sample["mle_counters"], sort_keys=True),
        }
        for key, value in sorted(sample.items()):
            if key.endswith("_scan_dbm") or key.endswith("_scan_lqi"):
                row[key] = value
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


def time_spent_by_parent(samples: list[dict[str, Any]], step_seconds: float | int | None) -> dict[str, float]:
    spent: dict[str, float] = {}
    if step_seconds in (None, "", "None"):
        return spent
    step = float(step_seconds)
    for sample in samples:
        parent = sample.get("parent_node_guess")
        if parent:
            spent[parent] = round(spent.get(parent, 0.0) + step, 6)
    return spent


def is_detached_sample(sample: dict[str, Any]) -> bool:
    return str(sample.get("mobile_state") or "").lower() in {"detached", "disabled"}


def detach_recovery_summary(samples: list[dict[str, Any]]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    detached = False
    current_event: dict[str, Any] | None = None
    last_parent: str | None = None

    for sample in samples:
        parent = sample.get("parent_node_guess")
        state_detached = is_detached_sample(sample)
        if parent:
            last_parent = parent

        if state_detached and not detached:
            detached = True
            current_event = {
                "detach_time_s": sample.get("sim_time_s"),
                "detach_position_x": sample.get("mobile_x"),
                "previous_parent": last_parent,
                "reattach_time_s": None,
                "reattach_position_x": None,
                "reattach_parent": None,
                "reattach_latency_s": None,
            }
            events.append(current_event)
            continue

        if detached and not state_detached and parent:
            detached = False
            if current_event is not None:
                current_event["reattach_time_s"] = sample.get("sim_time_s")
                current_event["reattach_position_x"] = sample.get("mobile_x")
                current_event["reattach_parent"] = parent
                detach_time = current_event.get("detach_time_s")
                if detach_time is not None and sample.get("sim_time_s") is not None:
                    current_event["reattach_latency_s"] = round(
                        float(sample["sim_time_s"]) - float(detach_time),
                        6,
                    )
            current_event = None

    first_event = events[0] if events else {}
    reattached_events = [event for event in events if event.get("reattach_time_s") is not None]
    ended_detached = bool(samples and is_detached_sample(samples[-1]))
    recovery_classification = "no_detach"
    if ended_detached and events:
        recovery_classification = "detached_no_reattach"
    elif reattached_events:
        first_reattached = reattached_events[0]
        if (
            first_reattached.get("previous_parent")
            and first_reattached.get("reattach_parent")
            and first_reattached["previous_parent"] != first_reattached["reattach_parent"]
        ):
            recovery_classification = "detached_reattached_new_parent"
        else:
            recovery_classification = "detached_reattached_same_parent"

    return {
        "detach_count": len(events),
        "detach_events": events,
        "first_detach_time_s": first_event.get("detach_time_s"),
        "first_detach_position_x": first_event.get("detach_position_x"),
        "first_detach_previous_parent": first_event.get("previous_parent"),
        "first_reattach_time_s": first_event.get("reattach_time_s"),
        "first_reattach_position_x": first_event.get("reattach_position_x"),
        "first_reattach_parent": first_event.get("reattach_parent"),
        "reattach_latency_s": first_event.get("reattach_latency_s"),
        "final_mobile_state": samples[-1].get("mobile_state") if samples else None,
        "ended_detached": ended_detached,
        "recovery_classification": recovery_classification,
    }


def node_tx_power_summary(samples: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, float]]:
    configured: dict[str, float] = {}
    verified: dict[str, float] = {}
    if not samples:
        return configured, verified
    mobile_value = samples[0].get("mobile_tx_power_dbm")
    mobile_verified = samples[0].get("mobile_verified_tx_power_dbm")
    if mobile_value is not None:
        configured["mobile"] = float(mobile_value)
    if mobile_verified is not None:
        verified["mobile"] = float(mobile_verified)
    for sample in samples:
        parent = sample.get("mobile_to_parent_target")
        parent_value = sample.get("mobile_to_parent_target_tx_power_dbm")
        parent_verified = sample.get("mobile_to_parent_target_verified_tx_power_dbm")
        if parent and parent_value is not None:
            configured[str(parent)] = float(parent_value)
        if parent and parent_verified is not None:
            verified[str(parent)] = float(parent_verified)
    return configured, verified


def node_ref_tx_power_summary(node_refs: dict[str, NodeRef]) -> tuple[dict[str, float], dict[str, float]]:
    configured = {
        name: float(ref.tx_power_dbm)
        for name, ref in node_refs.items()
        if ref.tx_power_dbm is not None
    }
    verified = {
        name: float(ref.verified_tx_power_dbm)
        for name, ref in node_refs.items()
        if ref.verified_tx_power_dbm is not None
    }
    return configured, verified


def scenario_tx_power_summary(scenario: dict[str, Any]) -> tuple[dict[str, float], dict[str, float]]:
    configured = {
        name: float(tx_power)
        for name, config in scenario.get("nodes", {}).items()
        if (tx_power := node_tx_power_dbm(config)) is not None
    }
    return configured, dict(configured)


def scenario_model_rss_summary(scenario: dict[str, Any]) -> dict[str, Any]:
    nodes = scenario.get("nodes", {})
    movement = scenario.get("movement", {})
    endpoint = movement.get("end", {})
    mobile = nodes.get("mobile", {})
    mobile_endpoint = {
        "x": endpoint.get("x", mobile.get("x")),
        "y": endpoint.get("y", mobile.get("y")),
    }


def node_executable_summary(node_refs: dict[str, NodeRef] | None) -> dict[str, dict[str, Any]]:
    if not node_refs:
        return {}
    return {
        name: {
            "node_id": ref.node_id,
            "firmware_profile": ref.firmware_profile,
            "executable_path": ref.executable_path,
            "executable_sha256": ref.executable_sha256,
        }
        for name, ref in sorted(node_refs.items())
    }
    endpoint_rss: dict[str, float | None] = {}
    router_link_rss: dict[str, float | None] = {}
    routers = router_names(scenario)
    for name in routers:
        router = nodes[name]
        endpoint_rss[name] = derive_mutual_interference_rssi_dbm(
            router.get("x"),
            router.get("y"),
            mobile_endpoint.get("x"),
            mobile_endpoint.get("y"),
            tx_power_dbm=node_tx_power_dbm(router),
        )
    for left, right in zip(routers, routers[1:]):
        left_node = nodes[left]
        right_node = nodes[right]
        router_link_rss[f"{left}_to_{right}"] = derive_mutual_interference_rssi_dbm(
            left_node.get("x"),
            left_node.get("y"),
            right_node.get("x"),
            right_node.get("y"),
            tx_power_dbm=node_tx_power_dbm(left_node),
        )
    return {
        "mobile_endpoint": mobile_endpoint,
        "endpoint_router_to_mobile_rss_dbm": endpoint_rss,
        "router_to_router_rss_dbm": router_link_rss,
        "method": "otns_model_derived_at_ping",
    }


def build_summary(
    scenario: dict[str, Any],
    samples: list[dict[str, Any]],
    switch_events: list[dict[str, Any]],
    notes: list[str],
    selected_radio_model: str | None,
    total_outage_s: float,
    mock: bool,
    parent_before_delayed_nodes: str | None = None,
    initial_attachment_expected_parent: str | None = None,
    initial_attachment_observed_parent: str | None = None,
    initial_attachment_wait_s: int | None = None,
    initial_attachment_timed_out: bool = False,
    pre_movement_parent_sequence: list[str] | None = None,
    pre_movement_parent_events: list[dict[str, Any]] | None = None,
    pre_movement_parent_final: str | None = None,
    pre_movement_parent_observation_count: int = 0,
    thread_device_type: str | None = None,
    parent_search_config: str = "unknown",
    sim_ping_rss_capture_enabled: bool = False,
    node_refs: dict[str, NodeRef] | None = None,
) -> dict[str, Any]:
    total_tx = 0
    total_rx = 0
    parent_probe_total_tx = 0
    parent_probe_total_rx = 0
    parent_probe_rtt_values: list[float] = []
    parent_sequence = [sample.get("parent_node_guess") for sample in samples if sample.get("parent_node_guess")]
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
    oscillations = 0
    for left, middle, right in zip(
        compact_parent_sequence,
        compact_parent_sequence[1:],
        compact_parent_sequence[2:],
    ):
        if left == right and left != middle:
            oscillations += 1
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
    step_seconds = scenario.get("timing", {}).get("step_seconds")
    if node_refs:
        configured_tx_power, verified_tx_power = node_ref_tx_power_summary(node_refs)
    else:
        configured_tx_power, verified_tx_power = node_tx_power_summary(samples)
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
    recovery_summary = detach_recovery_summary(samples)
    expected_initial_parent = scenario.get("expected_initial_parent")
    if expected_initial_parent and initial_observed_parent != expected_initial_parent:
        result_classification = (
            "pre_movement_switch_observed"
            if pre_movement_parent_events
            else "initial_parent_unexpected"
        )
    elif switch_events:
        result_classification = "switch_observed"
    elif pre_movement_parent_events:
        result_classification = "pre_movement_switch_observed"
    elif recovery_summary["recovery_classification"] == "detached_no_reattach":
        result_classification = "detached_no_reattach"
    elif recovery_summary["recovery_classification"] in {
        "detached_reattached_same_parent",
        "detached_reattached_new_parent",
    }:
        result_classification = recovery_summary["recovery_classification"]
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
        "initial_attachment_expected_parent": initial_attachment_expected_parent,
        "initial_attachment_observed_parent": initial_attachment_observed_parent,
        "initial_attachment_wait_s": initial_attachment_wait_s,
        "initial_attachment_timed_out": initial_attachment_timed_out,
        "pre_movement_parent_observation_count": pre_movement_parent_observation_count,
        "pre_movement_parent_sequence": pre_movement_parent_sequence or [],
        "pre_movement_parent_final": pre_movement_parent_final,
        "pre_movement_switch_count": len(pre_movement_parent_events or []),
        "pre_movement_parent_events": pre_movement_parent_events or [],
        "initial_observed_parent": initial_observed_parent,
        "final_observed_parent": final_observed_parent,
        "parent_sequence": compact_parent_sequence,
        "result_classification": result_classification,
        "switch_count": len(switch_events),
        "first_switch_time_s": switch_events[0]["sim_time_s"] if switch_events else None,
        "switch_position_x": samples[switch_events[0]["sample_index"]].get("mobile_x") if switch_events else None,
        "second_switch_time_s": switch_events[1]["sim_time_s"] if len(switch_events) > 1 else None,
        "second_switch_position_x": (
            samples[switch_events[1]["sample_index"]].get("mobile_x") if len(switch_events) > 1 else None
        ),
        "switch_events": switch_events,
        **recovery_summary,
        "time_spent_by_parent_s": time_spent_by_parent(samples, step_seconds),
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
        "configured_node_tx_power_dbm": configured_tx_power,
        "verified_node_tx_power_dbm": verified_tx_power,
        "node_executables": node_executable_summary(node_refs),
        "tx_power_command": "txpower",
        "scenario_model_rss": scenario_model_rss_summary(scenario),
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
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(data: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    args = parse_args()
    scenario = load_scenario(args.scenario)
    try:
        validate_scenario_configuration(
            scenario,
            args.scenario,
            node_binary_path=args.node_binary_path,
            node_binary_profile=args.node_binary_profile,
            ftd_node_binary_path=args.ftd_node_binary_path,
            ftd_node_binary_profile=args.ftd_node_binary_profile,
            mock=args.mock,
        )
    except ValueError as exc:
        print(f"Invalid scenario configuration: {exc}", file=sys.stderr)
        return 2
    ensure_results_dir(args.results_dir)

    token = args.timestamp_token or timestamp_token()
    csv_path = args.results_dir / f"baseline_run_{token}.csv"
    json_path = args.results_dir / f"baseline_summary_{token}.json"
    parent_rank_path = args.results_dir / f"parent_rank_{token}.csv"
    preferred_parent_event_path = args.results_dir / f"preferred_parent_events_{token}.csv"
    captured_parent_rank_path: Path | None = None
    runtime_dir = otns_runtime_cwd(args.otns_workdir, args.otns_runtime_dir)
    if not args.mock:
        runtime_dir.mkdir(parents=True, exist_ok=True)
    replay_before = snapshot_replay_files(runtime_dir) if args.capture_replay and not args.mock else {}

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
            otns_workdir=args.otns_workdir,
            otns_runtime_dir=args.otns_runtime_dir,
            otns_watch_level=args.otns_watch_level,
            node_binary_path=args.node_binary_path,
            ftd_node_binary_path=args.ftd_node_binary_path,
            node_binary_profile=args.node_binary_profile,
            ftd_node_binary_profile=args.ftd_node_binary_profile,
            thread_device_type=args.thread_device_type,
            parent_search_config=args.parent_search_config,
            capture_sim_ping_rss=args.capture_sim_ping_rss,
            scenario_path=args.scenario,
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
        otns_runtime_dir=args.otns_runtime_dir,
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
            otns_runtime_dir=args.otns_runtime_dir,
            watch_level=args.otns_watch_level,
        )
        if node_log_info.get("warning"):
            summary.setdefault("notes", []).append(str(node_log_info["warning"]))
    parent_rank_events = parse_parent_rank_events(node_log_info.get("copied_files", []))
    summary.update(parent_rank_summary(parent_rank_events))
    if parent_rank_events:
        write_parent_rank_csv(parent_rank_events, parent_rank_path)
        captured_parent_rank_path = parent_rank_path
    elif not args.mock and args.otns_watch_level.lower() == "off":
        summary.setdefault("notes", []).append(
            "Parent ranking export requires OTNS node logs; rerun with --otns-watch-level info or lower."
        )
    summary["firmware_variant"] = args.firmware_variant
    summary["thread_device_type"] = args.thread_device_type
    summary["parent_search_config"] = args.parent_search_config
    summary["node_binary_path"] = str(args.node_binary_path) if args.node_binary_path is not None else None
    summary["node_binary_profile"] = args.node_binary_profile
    summary["ftd_node_binary_path"] = (
        str(args.ftd_node_binary_path) if args.ftd_node_binary_path is not None else None
    )
    summary["ftd_node_binary_profile"] = args.ftd_node_binary_profile
    summary["build_config_source"] = args.build_config_source
    summary["firmware_source_repo"] = (
        str(args.firmware_source_repo.resolve()) if args.firmware_source_repo is not None else None
    )
    summary["equivalent_to"] = args.equivalent_to
    summary["openthread_commit"] = args.openthread_commit
    summary["otns_commit"] = args.otns_commit
    summary["otns_watch_level"] = args.otns_watch_level
    summary["otns_runtime_dir"] = str(runtime_dir) if not args.mock else None
    summary["node_log_files"] = node_log_info.get("copied_files", [])
    summary["replay_capture_requested"] = args.capture_replay
    summary["sim_ping_rss_capture_requested"] = args.capture_sim_ping_rss
    summary["replay_file"] = replay_info.get("copied_path")
    summary["replay_metadata_file"] = replay_info.get("metadata_path")

    preferred_parent_events = summary.get("preferred_parent_events", [])
    if preferred_parent_events:
        write_preferred_parent_event_csv(preferred_parent_events, preferred_parent_event_path)
        summary["preferred_parent_event_file"] = str(preferred_parent_event_path)
    else:
        summary["preferred_parent_event_file"] = None

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
                node_binary_profile=args.node_binary_profile,
                ftd_node_binary_path=args.ftd_node_binary_path,
                ftd_node_binary_profile=args.ftd_node_binary_profile,
                build_config_source=args.build_config_source,
                firmware_source_repo=args.firmware_source_repo,
                equivalent_to=args.equivalent_to,
                openthread_commit=args.openthread_commit,
                otns_commit=args.otns_commit,
                otns_command=args.otns_command,
                otns_workdir=args.otns_workdir,
                runner_invocation=[sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
                token=token,
                csv_path=csv_path,
                json_path=json_path,
                preferred_parent_event_path=(preferred_parent_event_path if preferred_parent_events else None),
                parent_rank_path=captured_parent_rank_path,
                replay_info=replay_info,
                node_log_files=node_log_info.get("copied_files", []),
                summary=summary,
            )
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        print(tracked_info["tracked_dir"])
        print(tracked_info["manifest_path"])

    if captured_parent_rank_path is not None:
        print(captured_parent_rank_path)
    if preferred_parent_events:
        print(preferred_parent_event_path)
    print(csv_path)
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
