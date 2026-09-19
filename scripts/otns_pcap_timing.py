#!/usr/bin/env python3
"""Extract directed attach air-to-air timing from an OTNS IEEE 802.15.4 PCAP."""

from __future__ import annotations

import csv
import io
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


DEFAULT_THREAD_NETWORK_KEY = "00112233445566778899aabbccddeeff"
ATTACH_COMMANDS = {9, 10, 11, 12}
FAILURE_REASONS = {
    9: "missing_parent_request",
    10: "missing_parent_response",
    11: "missing_child_id_request",
    12: "missing_child_id_response",
}


@dataclass(frozen=True)
class AttachPacket:
    frame_number: int
    timestamp_s: float
    command: int
    src64: str | None
    dst64: str | None
    src16: str | None = None
    dst16: str | None = None


def normalize_extaddr(value: str | None) -> str | None:
    if not value:
        return None
    compact = re.sub(r"[^0-9a-fA-F]", "", value).lower()
    return compact if len(compact) == 16 else None


def tshark_decode_preferences(network_key: str) -> list[str]:
    compact = re.sub(r"[^0-9a-fA-F]", "", network_key).lower()
    if len(compact) != 32:
        raise ValueError("Thread network key must contain exactly 32 hexadecimal characters")
    return [
        "-o",
        "wpan.802154_fcs_ok:FALSE",
        "-o",
        "wpan.802154_sec_suite:AES-128 Encryption, 32-bit Integrity Protection",
        "-o",
        "thread.thr_seq_ctr:00000000",
        "-o",
        f'uat:ieee802154_keys:"{compact}","1","Thread hash"',
    ]


def decode_attach_packets(
    pcap_path: Path,
    *,
    network_key: str = DEFAULT_THREAD_NETWORK_KEY,
    tshark: str = "tshark",
) -> list[AttachPacket]:
    executable = shutil.which(tshark) or tshark
    fields = (
        "frame.number",
        "frame.time_epoch",
        "wpan.src64",
        "wpan.dst64",
        "wpan.src16",
        "wpan.dst16",
        "mle.cmd",
    )
    command = [executable, "-r", str(pcap_path), *tshark_decode_preferences(network_key)]
    command.extend(
        [
            "-Y",
            "mle.cmd == 9 || mle.cmd == 10 || mle.cmd == 11 || mle.cmd == 12",
            "-T",
            "fields",
            "-E",
            "header=y",
            "-E",
            "separator=,",
            "-E",
            "quote=d",
            "-E",
            "occurrence=f",
        ]
    )
    for field in fields:
        command.extend(["-e", field])
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as exc:
        raise RuntimeError(f"Could not execute tshark: {exc}") from exc
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"tshark exited with {completed.returncode}")

    packets: list[AttachPacket] = []
    for row in csv.DictReader(io.StringIO(completed.stdout)):
        try:
            mle_command = int(row.get("mle.cmd") or "")
            if mle_command not in ATTACH_COMMANDS:
                continue
            packets.append(
                AttachPacket(
                    frame_number=int(row["frame.number"]),
                    timestamp_s=float(row["frame.time_epoch"]),
                    command=mle_command,
                    src64=normalize_extaddr(row.get("wpan.src64")),
                    dst64=normalize_extaddr(row.get("wpan.dst64")),
                    src16=(row.get("wpan.src16") or None),
                    dst16=(row.get("wpan.dst16") or None),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid tshark attach row: {row}") from exc
    return sorted(packets, key=lambda packet: (packet.timestamp_s, packet.frame_number))


def _is_broadcast(packet: AttachPacket) -> bool:
    return packet.dst64 is None and str(packet.dst16 or "").lower() in {"0xffff", "ffff"}


def _matches_direction(packet: AttachPacket, src: str, dst: str) -> bool:
    return packet.src64 == src and packet.dst64 == dst


def _find_complete_sequences(
    packets: Iterable[AttachPacket],
    *,
    child_extaddr: str,
    target_extaddr: str,
    mode: str,
    operation_start_s: float,
) -> tuple[list[dict[int, AttachPacket]], int | None]:
    child = normalize_extaddr(child_extaddr)
    target = normalize_extaddr(target_extaddr)
    if child is None or target is None:
        raise ValueError("Child and target extended addresses must each contain 16 hexadecimal characters")
    if mode not in {"unicast", "multicast"}:
        raise ValueError("Directed mode must be unicast or multicast")

    relevant = [packet for packet in packets if packet.timestamp_s >= operation_start_s]
    sequences: list[dict[int, AttachPacket]] = []
    furthest_command: int | None = None
    index = 0
    while index < len(relevant):
        packet = relevant[index]
        request_matches = packet.command == 9 and packet.src64 == child and (
            packet.dst64 == target if mode == "unicast" else _is_broadcast(packet)
        )
        if not request_matches:
            index += 1
            continue
        sequence = {9: packet}
        furthest_command = max(furthest_command or 0, 9)
        cursor = index + 1
        for expected in (10, 11, 12):
            while cursor < len(relevant):
                candidate = relevant[cursor]
                direction_matches = (
                    _matches_direction(candidate, target, child)
                    if expected in {10, 12}
                    else _matches_direction(candidate, child, target)
                )
                if candidate.command == expected and direction_matches:
                    sequence[expected] = candidate
                    furthest_command = max(furthest_command or 0, expected)
                    cursor += 1
                    break
                cursor += 1
            if expected not in sequence:
                break
        if len(sequence) == 4:
            sequences.append(sequence)
            index = cursor
        else:
            index += 1
    return sequences, furthest_command


def derive_air_timing(
    packets: Iterable[AttachPacket],
    *,
    child_extaddr: str,
    target_extaddr: str,
    mode: str,
    operation_start_s: float,
) -> dict[str, Any]:
    sequences, furthest_command = _find_complete_sequences(
        packets,
        child_extaddr=child_extaddr,
        target_extaddr=target_extaddr,
        mode=mode,
        operation_start_s=operation_start_s,
    )
    if not sequences:
        missing_command = 9 if furthest_command is None else min(furthest_command + 1, 12)
        return {
            "source": "otns_pcap",
            "complete": False,
            "failure_reason": FAILURE_REASONS[missing_command],
            "timing_ms": {},
            "packets": {},
            "timestamp_resolution_us": 1,
        }
    if len(sequences) != 1:
        return {
            "source": "otns_pcap",
            "complete": False,
            "failure_reason": "ambiguous_attach_sequence",
            "timing_ms": {},
            "packets": {},
            "candidate_sequence_count": len(sequences),
            "timestamp_resolution_us": 1,
        }

    sequence = sequences[0]
    request = sequence[9]
    response = sequence[10]
    child_request = sequence[11]
    child_response = sequence[12]

    def milliseconds(start: AttachPacket, end: AttachPacket) -> float:
        return round((end.timestamp_s - start.timestamp_s) * 1000.0, 3)

    timing = {
        "parent_request_to_response": milliseconds(request, response),
        "parent_response_to_child_id_request": milliseconds(response, child_request),
        "child_id_request_to_response": milliseconds(child_request, child_response),
        "parent_request_to_child_id_response": milliseconds(request, child_response),
    }
    return {
        "source": "otns_pcap",
        "complete": True,
        "failure_reason": None,
        "timing_ms": timing,
        "packets": {
            "parent_request": asdict(request),
            "parent_response": asdict(response),
            "child_id_request": asdict(child_request),
            "child_id_response": asdict(child_response),
        },
        "timestamp_resolution_us": 1,
    }


def extract_air_timing(
    pcap_path: Path,
    *,
    child_extaddr: str,
    target_extaddr: str,
    mode: str,
    operation_start_s: float,
    network_key: str = DEFAULT_THREAD_NETWORK_KEY,
    tshark: str = "tshark",
) -> dict[str, Any]:
    if not pcap_path.is_file():
        return {
            "source": "otns_pcap",
            "complete": False,
            "failure_reason": "pcap_missing",
            "timing_ms": {},
            "packets": {},
            "timestamp_resolution_us": 1,
        }
    try:
        packets = decode_attach_packets(pcap_path, network_key=network_key, tshark=tshark)
        return derive_air_timing(
            packets,
            child_extaddr=child_extaddr,
            target_extaddr=target_extaddr,
            mode=mode,
            operation_start_s=operation_start_s,
        )
    except (RuntimeError, ValueError) as exc:
        return {
            "source": "otns_pcap",
            "complete": False,
            "failure_reason": "pcap_parse_error",
            "error": str(exc),
            "timing_ms": {},
            "packets": {},
            "timestamp_resolution_us": 1,
        }
