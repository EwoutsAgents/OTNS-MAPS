#!/usr/bin/env python3
"""Run the stock OpenThread mobility baseline in OTNS or in mock mode."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pexpect
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = ROOT / "scenarios" / "baseline_mobile_parent_switch.yaml"
DEFAULT_RESULTS_DIR = ROOT / "results"
PROMPT_RE = r"(?:node \d+> |> )"


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
        "--mock",
        action="store_true",
        help="Generate deterministic mock output without OTNS",
    )
    return parser.parse_args()


def load_scenario(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def timestamp_token() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_results_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def linear_positions(start: dict[str, float], end: dict[str, float], steps: int) -> list[tuple[float, float]]:
    if steps < 2:
        return [(float(start["x"]), float(start["y"]))]
    positions = []
    for index in range(steps):
        fraction = index / (steps - 1)
        x = start["x"] + (end["x"] - start["x"]) * fraction
        y = start["y"] + (end["y"] - start["y"]) * fraction
        positions.append((round(float(x), 3), round(float(y), 3)))
    return positions


def sanitize_command_output(text: str) -> list[str]:
    lines = []
    for line in text.replace("\r", "").split("\n"):
        stripped = line.strip()
        if not stripped or stripped == "Done":
            continue
        lines.append(stripped)
    return lines


def parse_key_value_lines(lines: list[str]) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


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
        if not line.startswith("|") or "MAC Address" in line or line.startswith("+-"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 8:
            continue
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
    return rows


class OtnsSession:
    def __init__(self, command: str) -> None:
        self.command = command
        self.child: pexpect.spawn[str] | None = None

    def __enter__(self) -> "OtnsSession":
        parts = self.command if isinstance(self.command, str) else " ".join(self.command)
        self.child = pexpect.spawn(parts, encoding="utf-8", timeout=120, echo=False)
        self.child.expect(PROMPT_RE)
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.child is None:
            return
        try:
            self.command_output("exit")
        except Exception:
            pass
        self.child.close(force=True)

    def command_output(self, command: str) -> list[str]:
        assert self.child is not None
        self.child.sendline(command)
        self.child.expect(PROMPT_RE)
        return sanitize_command_output(self.child.before)


class RealBenchmarkRunner:
    def __init__(self, scenario: dict[str, Any], otns_command: str) -> None:
        self.scenario = scenario
        self.otns_command = otns_command
        self.notes: list[str] = []
        self.node_refs: dict[str, NodeRef] = {}

    def run(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if shutil.which(self.otns_command.split()[0]) is None:
            raise FileNotFoundError(
                f"OTNS command not found: {self.otns_command}. Install OTNS or use --mock."
            )

        timing = self.scenario["timing"]
        positions = linear_positions(
            self.scenario["movement"]["start"],
            self.scenario["movement"]["end"],
            int(timing["movement_steps"]),
        )

        with OtnsSession(self.otns_command) as session:
            session.command_output("speed 0")
            session.command_output(f'title "{self.scenario["title"]}"')
            radio_model = self._select_radio_model(session)
            named_ids = self._create_nodes(session)
            session.command_output(f'go {timing["settle_seconds"]}')
            self._refresh_node_identity(session)

            samples: list[dict[str, Any]] = []
            switch_events: list[dict[str, Any]] = []
            previous_parent = None
            outage_start = None
            total_outage = 0.0

            for index, (x, y) in enumerate(positions):
                mobile_id = named_ids["mobile"]
                session.command_output(f"move {mobile_id} {x} {y}")
                session.command_output(f'go {timing["step_seconds"]}')
                sample = self._collect_sample(session, index, x, y)
                sample["selected_radio_model"] = radio_model

                parent_identity = (
                    sample.get("parent_extaddr") or sample.get("parent_rloc16") or sample.get("parent_node_guess")
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

                connectivity_ok = any(
                    probe["rx"] and probe["rx"] > 0 for probe in sample["probe_results"].values()
                )
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
        )
        return rows, summary

    def _select_radio_model(self, session: OtnsSession) -> str:
        preferred = [self.scenario["radio_model"]["preferred"], *self.scenario["radio_model"]["fallbacks"]]
        for model in preferred:
            output = session.command_output(f"radiomodel {model}")
            chosen = output[-1] if output else None
            if chosen and chosen.lower().startswith(model.lower()[0]):
                if model != preferred[0]:
                    self.notes.append(f"Preferred radio model unavailable, fell back to {model}.")
                return chosen
        self.notes.append("Unable to confirm configured OTNS radio model from CLI output.")
        return "unknown"

    def _create_nodes(self, session: OtnsSession) -> dict[str, int]:
        named_ids: dict[str, int] = {}
        for name, config in self.scenario["nodes"].items():
            # OTNS-specific command: create a stock node type in the simulator.
            output = session.command_output(f'add {config["type"]}')
            node_id = int(output[0])
            named_ids[name] = node_id
            session.command_output(f'move {node_id} {config["x"]} {config["y"]}')
            self.node_refs[name] = NodeRef(name=name, node_id=node_id, x=config["x"], y=config["y"])
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

    def _collect_sample(self, session: OtnsSession, index: int, x: float, y: float) -> dict[str, Any]:
        mobile = self.node_refs["mobile"]
        sim_time_us = int(session.command_output("time")[0])
        state_lines = session.command_output(f'node {mobile.node_id} "state"')
        rloc_lines = session.command_output(f'node {mobile.node_id} "rloc16"')
        parent_lines = session.command_output(f'node {mobile.node_id} "parent"')
        ip_counter_lines = session.command_output(f'node {mobile.node_id} "counters ip"')
        mle_counter_lines = session.command_output(f'node {mobile.node_id} "counters mle"')
        scan_rows = parse_scan_table(session.command_output(f"scan {mobile.node_id}"))

        parent_info = parse_key_value_lines(parent_lines)
        ip_counters = parse_key_value_lines(ip_counter_lines)
        mle_counters = parse_key_value_lines(mle_counter_lines)

        sample: dict[str, Any] = {
            "sample_index": index,
            "sim_time_s": round(sim_time_us / 1_000_000.0, 6),
            "mobile_x": x,
            "mobile_y": y,
            "mobile_state": state_lines[0] if state_lines else None,
            "mobile_rloc16": rloc_lines[0] if rloc_lines else None,
            "parent_extaddr": parent_info.get("Ext Addr"),
            "parent_rloc16": parent_info.get("Rloc") or parent_info.get("RLOC16"),
            "parent_link_quality_in": parent_info.get("Link Quality In"),
            "parent_link_quality_out": parent_info.get("Link Quality Out"),
            "parent_age": parent_info.get("Age"),
            "parent_version": parent_info.get("Version"),
            "parent_node_guess": self._parent_name_from_identity(parent_info),
            "ip_counters": ip_counters,
            "mle_counters": mle_counters,
            "probe_results": {},
        }

        for router_name in ("router_a", "router_b"):
            router = self.node_refs[router_name]
            scan_match = next((row for row in scan_rows if row["mac_address"] == (router.extaddr or "").lower()), None)
            sample[f"{router_name}_scan_dbm"] = scan_match["dbm"] if scan_match else None
            sample[f"{router_name}_scan_lqi"] = scan_match["lqi"] if scan_match else None

        for probe in self.scenario["traffic_probes"]:
            src_id = self.node_refs[probe["src"]].node_id
            dst_id = self.node_refs[probe["dst"]].node_id
            # OTNS-specific command: perform a single ICMP probe to quantify reachability during motion.
            lines = session.command_output(f'ping {src_id} {dst_id} count {probe["count"]}')
            sample["probe_results"][probe["name"]] = parse_ping_summary(lines)

        return sample

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
    def __init__(self, scenario: dict[str, Any]) -> None:
        self.scenario = scenario

    def run(self) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        timing = self.scenario["timing"]
        positions = linear_positions(
            self.scenario["movement"]["start"],
            self.scenario["movement"]["end"],
            int(timing["movement_steps"]),
        )
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
                ping_a_rx = 0
                ping_b_rx = 0
            else:
                mobile_state = "child"
                ping_a_rx = 1 if dist_a < 330 else 0
                ping_b_rx = 1 if dist_b < 330 else 0

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

            connectivity_ok = bool(ping_a_rx or ping_b_rx)
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
                "parent_extaddr": "aa00aa00aa00aa00" if parent == "router_a" else "bb00bb00bb00bb00",
                "parent_rloc16": "0x1000" if parent == "router_a" else "0x2000",
                "parent_link_quality_in": 3 if connectivity_ok else 0,
                "parent_link_quality_out": 3 if connectivity_ok else 0,
                "parent_age": 5,
                "parent_version": 4,
                "parent_node_guess": parent,
                "ip_counters": {
                    "TxSuccess": str(index + ping_a_rx + ping_b_rx),
                    "TxFailed": str(max(0, 2 - ping_a_rx - ping_b_rx)),
                    "RxSuccess": str(index + ping_a_rx + ping_b_rx),
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
                "probe_results": {
                    "router_a_to_mobile": {
                        "tx": 1,
                        "rx": ping_a_rx,
                        "loss_pct": 0.0 if ping_a_rx else 100.0,
                        "rtt_min_ms": 10.0 + round(dist_a / 40, 3) if ping_a_rx else None,
                        "rtt_avg_ms": 12.0 + round(dist_a / 40, 3) if ping_a_rx else None,
                        "rtt_max_ms": 14.0 + round(dist_a / 40, 3) if ping_a_rx else None,
                    },
                    "router_b_to_mobile": {
                        "tx": 1,
                        "rx": ping_b_rx,
                        "loss_pct": 0.0 if ping_b_rx else 100.0,
                        "rtt_min_ms": 10.0 + round(dist_b / 40, 3) if ping_b_rx else None,
                        "rtt_avg_ms": 12.0 + round(dist_b / 40, 3) if ping_b_rx else None,
                        "rtt_max_ms": 14.0 + round(dist_b / 40, 3) if ping_b_rx else None,
                    },
                },
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
        )
        return rows, summary


def flatten_samples(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sample in samples:
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
            "parent_switch": sample["parent_switch"],
            "connectivity_ok": sample["connectivity_ok"],
            "selected_radio_model": sample["selected_radio_model"],
            "router_a_scan_dbm": sample["router_a_scan_dbm"],
            "router_a_scan_lqi": sample["router_a_scan_lqi"],
            "router_b_scan_dbm": sample["router_b_scan_dbm"],
            "router_b_scan_lqi": sample["router_b_scan_lqi"],
            "ip_counters_json": json.dumps(sample["ip_counters"], sort_keys=True),
            "mle_counters_json": json.dumps(sample["mle_counters"], sort_keys=True),
        }
        for probe_name, probe in sample["probe_results"].items():
            prefix = probe_name
            row[f"{prefix}_tx"] = probe["tx"]
            row[f"{prefix}_rx"] = probe["rx"]
            row[f"{prefix}_loss_pct"] = probe["loss_pct"]
            row[f"{prefix}_rtt_min_ms"] = probe["rtt_min_ms"]
            row[f"{prefix}_rtt_avg_ms"] = probe["rtt_avg_ms"]
            row[f"{prefix}_rtt_max_ms"] = probe["rtt_max_ms"]
        rows.append(row)
    return rows


def build_summary(
    scenario: dict[str, Any],
    samples: list[dict[str, Any]],
    switch_events: list[dict[str, Any]],
    notes: list[str],
    selected_radio_model: str | None,
    total_outage_s: float,
    mock: bool,
) -> dict[str, Any]:
    total_tx = 0
    total_rx = 0
    parent_sequence = [sample.get("parent_node_guess") for sample in samples if sample.get("parent_node_guess")]
    oscillations = 0
    for left, middle, right in zip(parent_sequence, parent_sequence[1:], parent_sequence[2:]):
        if left == right and left != middle:
            oscillations += 1

    for sample in samples:
        for probe in sample["probe_results"].values():
            total_tx += int(probe["tx"] or 0)
            total_rx += int(probe["rx"] or 0)

    pdr = (total_rx / total_tx) if total_tx else None

    return {
        "scenario_name": scenario["name"],
        "scenario_title": scenario["title"],
        "mock": mock,
        "selected_radio_model": selected_radio_model,
        "sample_count": len(samples),
        "switch_count": len(switch_events),
        "first_switch_time_s": switch_events[0]["sim_time_s"] if switch_events else None,
        "switch_events": switch_events,
        "total_outage_s": total_outage_s,
        "packet_delivery_ratio": round(pdr, 6) if pdr is not None else None,
        "oscillation_events": oscillations,
        "notes": notes,
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

    token = timestamp_token()
    csv_path = args.results_dir / f"baseline_run_{token}.csv"
    json_path = args.results_dir / f"baseline_summary_{token}.json"

    runner: RealBenchmarkRunner | MockBenchmarkRunner
    runner = MockBenchmarkRunner(scenario) if args.mock else RealBenchmarkRunner(scenario, args.otns_command)

    try:
        rows, summary = runner.run()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (pexpect.TIMEOUT, pexpect.EOF, subprocess.SubprocessError) as exc:
        print(f"Benchmark execution failed: {exc}", file=sys.stderr)
        return 1

    write_csv(rows, csv_path)
    write_json(summary, json_path)

    print(csv_path)
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
