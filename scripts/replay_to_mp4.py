#!/usr/bin/env python3
"""Render an OTNS replay file into an MP4 via the OTNS web UI."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import textwrap
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UI_URL = "http://127.0.0.1:8997/visualize?addr=localhost:8998"
OUTER_TIMESTAMP_RE = re.compile(r"^timestamp:(\d+)(\s+event:\{.*)$")
ADVANCE_TIME_RE = re.compile(r"advance_time:\{timestamp:(\d+)([^}]*)\}")
SPEED_FIELD_RE = re.compile(r"\s+speed:([^\s}]+)")
SET_SPEED_RE = re.compile(r"set_speed:\{(?:speed:([^\s}]+))?\}")
ADD_NODE_RE = re.compile(
    r'add_node:\{node_id:(\d+)(.*?)\sy:(-?\d+)(.*?)\snode_type:"([^"]+)"(.*?)\}'
)
SET_NODE_POS_RE = re.compile(r"set_node_pos:\{node_id:(\d+)(.*?)\sy:(-?\d+)(.*?)\}")
SET_NODE_ROLE_RE = re.compile(r"set_node_role:\{node_id:(\d+)\s+role:([A-Z_]+)\}")
SET_NODE_RLOC16_RE = re.compile(r"set_node_rloc16:\{node_id:(\d+)\s+rloc16:(\d+)\}")
SET_NODE_PARTITION_ID_RE = re.compile(r"set_node_partition_id:\{node_id:(\d+)\s+partition_id:(\d+)\}")
SET_NODE_MODE_RE = re.compile(r"set_node_mode:\{node_id:(\d+)\s+node_mode:\{([^}]*)\}\}")
ON_EXT_ADDR_CHANGE_RE = re.compile(r"on_ext_addr_change:\{node_id:(\d+)\s+ext_addr:(\d+)\}")
ON_NODE_FAIL_RE = re.compile(r"on_node_fail:\{node_id:(\d+)\}")
ON_NODE_RECOVER_RE = re.compile(r"on_node_recover:\{node_id:(\d+)\}")
SET_PARENT_RE = re.compile(r"set_parent:\{node_id:(\d+)\s+ext_addr:(\d+)\}")
SET_TITLE_RE = re.compile(r'set_title:\{title:"([^"]*)"(?:\s+x:(-?\d+))?\s+y:(-?\d+)\s+font_size:(\d+)\}')
SET_NETWORK_INFO_RE = re.compile(r"set_network_info:\{([^}]*)\}")
ADD_ROUTER_TABLE_RE = re.compile(r"add_router_table:\{node_id:(\d+)\s+ext_addr:(\d+)\}")
REMOVE_ROUTER_TABLE_RE = re.compile(r"remove_router_table:\{node_id:(\d+)\s+ext_addr:(\d+)\}")
ADD_CHILD_TABLE_RE = re.compile(r"add_child_table:\{node_id:(\d+)\s+ext_addr:(\d+)\}")
REMOVE_CHILD_TABLE_RE = re.compile(r"remove_child_table:\{node_id:(\d+)\s+ext_addr:(\d+)\}")
DELETE_NODE_RE = re.compile(r"delete_node:\{node_id:(\d+)\}")
NODE_ID_RE = re.compile(r"node_id:(\d+)")
END_DEVICE_TYPES = {"fed", "med", "sed", "ssed"}
NODE_TYPE_DISPLAY = {
    "router": "router",
    "fed": "fed",
    "med": "mobile",
    "sed": "sed",
    "ssed": "ssed",
    "br": "br",
    "matter": "matter",
}


class ReplayVideoError(RuntimeError):
    """Raised when replay-to-video rendering fails."""


@dataclass
class ReplaySession:
    replay_process: subprocess.Popen[Any]
    chrome_process: subprocess.Popen[Any]
    temp_dir: Path
    ui_url: str
    cdp_url: str
    prepared_replay_file: Path
    prepared_replay_duration_us: int
    replay_log_events: list["ReplayLogEvent"]

    def close(self) -> None:
        for process in (self.chrome_process, self.replay_process):
            if process.poll() is None:
                process.terminate()
        for process in (self.chrome_process, self.replay_process):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class DevToolsWebSocket:
    def __init__(self, websocket_url: str, timeout_s: float) -> None:
        self.websocket_url = websocket_url
        self.timeout_s = timeout_s
        self.socket: socket.socket | None = None
        self.next_id = 1

    def __enter__(self) -> "DevToolsWebSocket":
        parsed = urlparse(self.websocket_url)
        if parsed.scheme != "ws":
            raise ReplayVideoError(f"Unsupported DevTools websocket scheme: {parsed.scheme}")
        self.socket = socket.create_connection((parsed.hostname, parsed.port), timeout=self.timeout_s)
        self.socket.settimeout(self.timeout_s)

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        self.socket.sendall(request.encode("ascii"))

        response = b""
        while b"\r\n\r\n" not in response:
            chunk = self.socket.recv(4096)
            if not chunk:
                raise ReplayVideoError("DevTools websocket closed during handshake.")
            response += chunk

        status_line = response.split(b"\r\n", 1)[0].decode("ascii", errors="replace")
        if "101" not in status_line:
            raise ReplayVideoError(f"DevTools websocket handshake failed: {status_line}")
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def _send_text(self, text: str) -> None:
        assert self.socket is not None
        payload = text.encode("utf-8")
        header = bytearray([0x81])
        size = len(payload)
        if size < 126:
            header.append(0x80 | size)
        elif size < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", size))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", size))
        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.socket.sendall(header + masked)

    def _recv_frame(self) -> tuple[int, bytes]:
        assert self.socket is not None
        first_two = self.socket.recv(2)
        if not first_two:
            raise ReplayVideoError("DevTools websocket closed while reading a frame.")
        first, second = first_two
        opcode = first & 0x0F
        masked = bool(second >> 7)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self.socket.recv(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self.socket.recv(8))[0]

        mask = b""
        if masked:
            mask = self.socket.recv(4)

        payload = b""
        while len(payload) < length:
            payload += self.socket.recv(length - len(payload))

        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return opcode, payload

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        call_id = self.next_id
        self.next_id += 1
        message = {"id": call_id, "method": method}
        if params:
            message["params"] = params
        self._send_text(json.dumps(message))

        while True:
            opcode, payload = self._recv_frame()
            if opcode == 9:
                self._send_pong(payload)
                continue
            if opcode != 1:
                continue
            body = json.loads(payload)
            if body.get("id") != call_id:
                continue
            if "error" in body:
                raise ReplayVideoError(f"DevTools call failed for {method}: {body['error']}")
            return body["result"]

    def _send_pong(self, payload: bytes) -> None:
        assert self.socket is not None
        header = bytearray([0x8A])
        size = len(payload)
        if size >= 126:
            return
        header.append(size)
        self.socket.sendall(header + payload)


@dataclass
class ReplayLogEvent:
    offset_us: int
    text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay_file", type=Path, help="Replay file to render, for example results/.../*.replay")
    parser.add_argument(
        "--output-mp4",
        type=Path,
        default=None,
        help="Output MP4 path. Defaults to the replay file path with an .mp4 suffix in the same directory.",
    )
    parser.add_argument(
        "--otns-replay-command",
        default=os.environ.get("OTNS_REPLAY_COMMAND", "otns-replay"),
        help="OTNS replay executable or full command string",
    )
    parser.add_argument(
        "--chrome-command",
        default=os.environ.get("CHROME_COMMAND", "google-chrome"),
        help="Chrome or Chromium executable used for headless capture",
    )
    parser.add_argument(
        "--frame-count",
        type=int,
        default=24,
        help="Number of screenshots to capture from one persistent browser session",
    )
    parser.add_argument(
        "--frame-interval-ms",
        type=int,
        default=100,
        help="Delay between screenshots in milliseconds. Ignored when --cover-full-replay is used",
    )
    parser.add_argument(
        "--warmup-ms",
        type=int,
        default=300,
        help="Delay before the first screenshot, in milliseconds",
    )
    parser.add_argument(
        "--window-size",
        default="1280,720",
        help="Headless Chrome window size as WIDTH,HEIGHT",
    )
    parser.add_argument(
        "--ui-url",
        default=DEFAULT_UI_URL,
        help="OTNS visualize URL. Defaults to the standard otns-replay page",
    )
    parser.add_argument(
        "--cdp-port",
        type=int,
        default=9222,
        help="Chrome DevTools port used for screenshots",
    )
    parser.add_argument(
        "--page-ready-timeout-s",
        type=float,
        default=10.0,
        help="Maximum time to wait for OTNS and Chrome to expose their HTTP endpoints",
    )
    parser.add_argument(
        "--video-fps",
        "--mp4-fps",
        dest="video_fps",
        type=float,
        default=2.0,
        help="Frames per second written into the output MP4.",
    )
    parser.add_argument(
        "--cover-full-replay",
        action="store_true",
        help="Spread screenshots across the normalized replay duration instead of sampling only the first few seconds",
    )
    parser.add_argument(
        "--replay-speed",
        type=float,
        default=4.0,
        help="Target OTNS replay speed written into a temporary normalized replay before rendering",
    )
    parser.add_argument(
        "--end-device-y-offset",
        type=int,
        default=0,
        help="Optional vertical offset applied to end-device nodes in the temporary replay before rendering",
    )
    parser.add_argument(
        "--show-log-panel",
        action="store_true",
        help="Overlay a readable OTNS-style event log panel into the captured frames.",
    )
    parser.add_argument(
        "--log-panel-width",
        type=int,
        default=360,
        help="Width in pixels for the overlaid log panel when --show-log-panel is enabled.",
    )
    parser.add_argument(
        "--log-lines",
        type=int,
        default=8,
        help="Maximum number of recent log entries shown in the overlay panel.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Keep replay and Chrome logs in the temporary capture directory while rendering",
    )
    return parser.parse_args()


def ensure_tool(command: str) -> str:
    executable = command.split()[0]
    resolved = shutil.which(executable)
    if resolved is not None:
        return resolved

    home_go = Path.home() / "go" / "bin" / executable
    if home_go.exists():
        return str(home_go)

        raise ReplayVideoError(f"Required executable not found: {executable}")


def default_output_mp4(replay_file: Path) -> Path:
    return replay_file.with_suffix(".mp4")


def wait_for_http(url: str, timeout_s: float) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5) as response:
                if 200 <= response.status < 500:
                    return
        except urllib.error.URLError:
            time.sleep(0.1)
    raise ReplayVideoError(f"Timed out waiting for {url}")


def wait_for_cdp_target(port: int, timeout_s: float, ui_url: str) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=0.5) as response:
                targets = json.load(response)
            for target in targets:
                if target.get("type") == "page" and target.get("url") == ui_url:
                    return target["webSocketDebuggerUrl"]
        except Exception:
            time.sleep(0.1)
            continue
        time.sleep(0.1)
    raise ReplayVideoError("Timed out waiting for the OTNS replay page target in Chrome DevTools.")


def rewrite_speed_fields(line: str, replay_speed: float) -> str:
    if "set_speed:{" in line:
        return SET_SPEED_RE.sub(f"set_speed:{{speed:{replay_speed:g}}}", line)

    if "advance_time:{" in line and "speed:" in line:
        return SPEED_FIELD_RE.sub(f" speed:{replay_speed:g}", line, count=1)
    return line


def rewrite_visual_offsets(line: str, end_device_ids: set[int], end_device_y_offset: int) -> str:
    if end_device_y_offset == 0:
        return line

    add_node_match = ADD_NODE_RE.search(line)
    if add_node_match is not None:
        node_id = int(add_node_match.group(1))
        node_type = add_node_match.group(5)
        if node_type in END_DEVICE_TYPES:
            end_device_ids.add(node_id)
            y = int(add_node_match.group(3)) + end_device_y_offset
            return (
                line[: add_node_match.start()]
                + f'add_node:{{node_id:{node_id}{add_node_match.group(2)} y:{y}{add_node_match.group(4)} '
                + f'node_type:"{node_type}"{add_node_match.group(6)}}}'
                + line[add_node_match.end() :]
            )

    set_pos_match = SET_NODE_POS_RE.search(line)
    if set_pos_match is not None:
        node_id = int(set_pos_match.group(1))
        if node_id in end_device_ids:
            y = int(set_pos_match.group(3)) + end_device_y_offset
            return (
                line[: set_pos_match.start()]
                + f"set_node_pos:{{node_id:{node_id}{set_pos_match.group(2)} y:{y}{set_pos_match.group(4)}}}"
                + line[set_pos_match.end() :]
            )

    return line


def make_node_label(node_type: str, type_counts: dict[str, int]) -> str:
    type_counts[node_type] = type_counts.get(node_type, 0) + 1
    count = type_counts[node_type]
    if node_type == "router":
        return f"router_{chr(ord('a') + count - 1)}" if count <= 26 else f"router_{count}"
    if node_type in END_DEVICE_TYPES and not type_counts.get("__mobile_assigned__"):
        type_counts["__mobile_assigned__"] = 1
        return "mobile"
    display = NODE_TYPE_DISPLAY.get(node_type, node_type)
    return f"{display}_{count}"


def summarize_role(role: str) -> str:
    short = role.replace("OT_DEVICE_ROLE_", "").lower()
    return short


def summarize_mode(mode_text: str) -> str:
    flags: list[str] = []
    if "rx_on_when_idle:true" in mode_text:
        flags.append("rx-on-idle")
    if "secure_data_requests:true" in mode_text:
        flags.append("secure-req")
    if "full_thread_device:true" in mode_text:
        flags.append("ftd")
    if "full_network_data:true" in mode_text:
        flags.append("full-net")
    return ",".join(flags) if flags else "default"


def format_rloc16(value: int) -> str:
    return f"0x{value:04x}"


def format_partition(value: int) -> str:
    return f"0x{value:08x}"


def format_extaddr(value: int) -> str:
    return f"0x{value:016x}"


def pretty_node(node_id: int, node_labels: dict[int, str]) -> str:
    return node_labels.get(node_id, f"node_{node_id}")


def pretty_extaddr(ext_addr: int, ext_to_node: dict[int, int], node_labels: dict[int, str]) -> str:
    node_id = ext_to_node.get(ext_addr)
    if node_id is None:
        return format_extaddr(ext_addr)
    return f"{pretty_node(node_id, node_labels)} ({format_extaddr(ext_addr)})"


def format_offset(offset_us: int) -> str:
    return f"{offset_us / 1_000_000:.1f}s"


def extract_log_events(lines: list[str]) -> list[ReplayLogEvent]:
    events: list[ReplayLogEvent] = []
    start_us: int | None = None
    node_labels: dict[int, str] = {}
    type_counts: dict[str, int] = {}
    ext_to_node: dict[int, int] = {}
    prev_role: dict[int, str] = {}
    prev_mode: dict[int, str] = {}
    prev_rloc16: dict[int, int] = {}
    prev_partition: dict[int, int] = {}
    prev_parent: dict[int, int] = {}
    real_devices_logged = False

    for line in lines:
        outer_match = OUTER_TIMESTAMP_RE.match(line)
        if outer_match is None:
            continue
        timestamp_us = int(outer_match.group(1))
        if start_us is None:
            start_us = timestamp_us
        offset_us = max(0, timestamp_us - start_us)

        add_node_match = ADD_NODE_RE.search(line)
        if add_node_match is not None:
            node_id = int(add_node_match.group(1))
            node_type = add_node_match.group(5)
            label = make_node_label(node_type, type_counts)
            node_labels[node_id] = label
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {label} added"))
            continue

        delete_node_match = DELETE_NODE_RE.search(line)
        if delete_node_match is not None:
            node_id = int(delete_node_match.group(1))
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {pretty_node(node_id, node_labels)} deleted"))
            continue

        rloc16_match = SET_NODE_RLOC16_RE.search(line)
        if rloc16_match is not None:
            node_id = int(rloc16_match.group(1))
            new_value = int(rloc16_match.group(2))
            old_value = prev_rloc16.get(node_id)
            prev_rloc16[node_id] = new_value
            if old_value != new_value:
                if old_value is None:
                    text = f"{pretty_node(node_id, node_labels)} rloc16 -> {format_rloc16(new_value)}"
                else:
                    text = f"{pretty_node(node_id, node_labels)} rloc16 {format_rloc16(old_value)} -> {format_rloc16(new_value)}"
                events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {text}"))
            continue

        role_match = SET_NODE_ROLE_RE.search(line)
        if role_match is not None:
            node_id = int(role_match.group(1))
            old_role = prev_role.get(node_id)
            new_role = role_match.group(2)
            prev_role[node_id] = new_role
            label = pretty_node(node_id, node_labels)
            if old_role is None:
                text = f"{label} role -> {summarize_role(new_role)}"
            else:
                text = f"{label} role {summarize_role(old_role)} -> {summarize_role(new_role)}"
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {text}"))
            continue

        mode_match = SET_NODE_MODE_RE.search(line)
        if mode_match is not None:
            node_id = int(mode_match.group(1))
            new_mode = summarize_mode(mode_match.group(2))
            old_mode = prev_mode.get(node_id)
            prev_mode[node_id] = new_mode
            label = pretty_node(node_id, node_labels)
            if old_mode is None:
                text = f"{label} mode -> {new_mode}"
            else:
                text = f"{label} mode {old_mode} -> {new_mode}"
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {text}"))
            continue

        network_info_match = SET_NETWORK_INFO_RE.search(line)
        if network_info_match is not None:
            fields = network_info_match.group(1)
            node_id_match = NODE_ID_RE.search(fields)
            if node_id_match is None and not real_devices_logged:
                real_devices_logged = True
                real_text = "ON" if "real:true" in fields else "OFF"
                events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | real devices: {real_text}"))
            continue

        pos_match = SET_NODE_POS_RE.search(line)
        if pos_match is not None:
            node_id = int(pos_match.group(1))
            x_match = re.search(r"\sx:(-?\d+)", pos_match.group(0))
            y_match = re.search(r"\sy:(-?\d+)", pos_match.group(0))
            z_match = re.search(r"\sz:(-?\d+)", pos_match.group(0))
            if x_match and y_match:
                z_value = z_match.group(1) if z_match else "0"
                text = f"{pretty_node(node_id, node_labels)} moved to ({x_match.group(1)},{y_match.group(1)},{z_value})"
                events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {text}"))
            continue

        ext_match = ON_EXT_ADDR_CHANGE_RE.search(line)
        if ext_match is not None:
            node_id = int(ext_match.group(1))
            ext_addr = int(ext_match.group(2))
            ext_to_node[ext_addr] = node_id
            text = f"{pretty_node(node_id, node_labels)} extaddr -> {format_extaddr(ext_addr)}"
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {text}"))
            continue

        if ON_NODE_FAIL_RE.search(line):
            node_id = int(ON_NODE_FAIL_RE.search(line).group(1))
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {pretty_node(node_id, node_labels)} radio OFF"))
            continue

        if ON_NODE_RECOVER_RE.search(line):
            node_id = int(ON_NODE_RECOVER_RE.search(line).group(1))
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {pretty_node(node_id, node_labels)} radio ON"))
            continue

        parent_match = SET_PARENT_RE.search(line)
        if parent_match is not None:
            node_id = int(parent_match.group(1))
            ext_addr = int(parent_match.group(2))
            prev_parent[node_id] = ext_addr
            text = f"{pretty_node(node_id, node_labels)} parent -> {pretty_extaddr(ext_addr, ext_to_node, node_labels)}"
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {text}"))
            continue

        title_match = SET_TITLE_RE.search(line)
        if title_match is not None:
            title = title_match.group(1)
            x = title_match.group(2) or "0"
            y = title_match.group(3)
            font_size = title_match.group(4)
            events.append(
                ReplayLogEvent(
                    offset_us,
                    f'{format_offset(offset_us)} | title "{title}" at ({x},{y}), size {font_size}',
                )
            )
            continue

        partition_match = SET_NODE_PARTITION_ID_RE.search(line)
        if partition_match is not None:
            node_id = int(partition_match.group(1))
            new_partition = int(partition_match.group(2))
            old_partition = prev_partition.get(node_id)
            prev_partition[node_id] = new_partition
            label = pretty_node(node_id, node_labels)
            if old_partition is None:
                text = f"{label} partition -> {format_partition(new_partition)}"
            else:
                text = f"{label} partition {format_partition(old_partition)} -> {format_partition(new_partition)}"
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {text}"))
            continue

        if "set_speed:{" in line:
            set_speed_match = SET_SPEED_RE.search(line)
            if set_speed_match is not None:
                speed = set_speed_match.group(1)
                if speed:
                    events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | speed set to {speed}"))
            continue

        router_add_match = ADD_ROUTER_TABLE_RE.search(line)
        if router_add_match is not None:
            node_id = int(router_add_match.group(1))
            ext_addr = int(router_add_match.group(2))
            text = f"{pretty_node(node_id, node_labels)} router table + {pretty_extaddr(ext_addr, ext_to_node, node_labels)}"
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {text}"))
            continue

        router_remove_match = REMOVE_ROUTER_TABLE_RE.search(line)
        if router_remove_match is not None:
            node_id = int(router_remove_match.group(1))
            ext_addr = int(router_remove_match.group(2))
            text = f"{pretty_node(node_id, node_labels)} router table - {pretty_extaddr(ext_addr, ext_to_node, node_labels)}"
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {text}"))
            continue

        child_add_match = ADD_CHILD_TABLE_RE.search(line)
        if child_add_match is not None:
            node_id = int(child_add_match.group(1))
            child_ext = int(child_add_match.group(2))
            parent_ext = None
            for ext_addr, mapped_node_id in ext_to_node.items():
                if mapped_node_id == node_id:
                    parent_ext = ext_addr
                    break
            text = f"{pretty_node(node_id, node_labels)} child table + {pretty_extaddr(child_ext, ext_to_node, node_labels)}"
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {text}"))
            child_node_id = ext_to_node.get(child_ext)
            if child_node_id is not None and parent_ext is not None:
                prev_parent[child_node_id] = parent_ext
                parent_text = (
                    f"{pretty_node(child_node_id, node_labels)} parent -> "
                    f"{pretty_extaddr(parent_ext, ext_to_node, node_labels)}"
                )
                events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {parent_text}"))
            continue

        child_remove_match = REMOVE_CHILD_TABLE_RE.search(line)
        if child_remove_match is not None:
            node_id = int(child_remove_match.group(1))
            child_ext = int(child_remove_match.group(2))
            text = f"{pretty_node(node_id, node_labels)} child table - {pretty_extaddr(child_ext, ext_to_node, node_labels)}"
            events.append(ReplayLogEvent(offset_us, f"{format_offset(offset_us)} | {text}"))
            continue

    return events


def normalize_replay_timing(
    replay_file: Path,
    temp_dir: Path,
    replay_speed: float,
    end_device_y_offset: int,
) -> tuple[Path, int, list[ReplayLogEvent]]:
    if replay_speed <= 0:
        raise ReplayVideoError("--replay-speed must be > 0")

    output_path = temp_dir / f"{replay_file.stem}.normalized.replay"
    lines = replay_file.read_text(encoding="utf-8").splitlines()

    normalized_lines: list[str] = []
    initial_wall_us: int | None = None
    base_sim_us: int | None = None
    last_normalized_us: int | None = None
    min_normalized_us: int | None = None
    post_sim_counter = 0
    end_device_ids: set[int] = set()

    for line in lines:
        line = rewrite_visual_offsets(line, end_device_ids, end_device_y_offset)
        outer_match = OUTER_TIMESTAMP_RE.match(line)
        if outer_match is None:
            normalized_lines.append(rewrite_speed_fields(line, replay_speed))
            continue

        original_wall_us = int(outer_match.group(1))
        suffix = outer_match.group(2)
        if initial_wall_us is None:
            initial_wall_us = original_wall_us

        advance_match = ADVANCE_TIME_RE.search(suffix)
        if advance_match is not None:
            sim_us = int(advance_match.group(1))
            if base_sim_us is None:
                base_sim_us = sim_us
            normalized_us = initial_wall_us + int(round((sim_us - base_sim_us) / replay_speed))
            if last_normalized_us is not None and normalized_us <= last_normalized_us:
                normalized_us = last_normalized_us + 1
            if min_normalized_us is None:
                min_normalized_us = normalized_us
            last_normalized_us = normalized_us
            post_sim_counter = 0
            rewritten_suffix = rewrite_speed_fields(suffix, replay_speed)
            normalized_lines.append(f"timestamp:{normalized_us}{rewritten_suffix}")
            continue

        rewritten_suffix = rewrite_speed_fields(suffix, replay_speed)
        if last_normalized_us is None:
            normalized_lines.append(f"timestamp:{original_wall_us}{rewritten_suffix}")
            continue

        post_sim_counter += 1
        normalized_lines.append(f"timestamp:{last_normalized_us + post_sim_counter}{rewritten_suffix}")

    output_path.write_text("\n".join(normalized_lines) + "\n", encoding="utf-8")
    if min_normalized_us is None or last_normalized_us is None:
        raise ReplayVideoError("Replay did not contain any advance_time events.")
    return output_path, max(1, last_normalized_us - min_normalized_us), extract_log_events(normalized_lines)


def launch_replay_session(args: argparse.Namespace) -> ReplaySession:
    temp_dir = Path(tempfile.mkdtemp(prefix="otns-replay-mp4-"))
    prepared_replay_file, prepared_replay_duration_us, replay_log_events = normalize_replay_timing(
        args.replay_file,
        temp_dir,
        args.replay_speed,
        args.end_device_y_offset,
    )

    replay_command = shlex.split(args.otns_replay_command)
    replay_command[0] = ensure_tool(replay_command[0])
    replay_command.append(str(prepared_replay_file))

    chrome_command = shlex.split(args.chrome_command)
    chrome_command[0] = ensure_tool(chrome_command[0])
    chrome_command.extend(
        [
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-extensions",
            f"--remote-debugging-port={args.cdp_port}",
            f"--window-size={args.window_size}",
        ]
    )

    chrome_profile_dir = temp_dir / "chrome-profile"
    chrome_profile_dir.mkdir(parents=True, exist_ok=True)
    chrome_command.extend([f"--user-data-dir={chrome_profile_dir}", args.ui_url])

    stdout_target = subprocess.DEVNULL
    stderr_target = subprocess.DEVNULL
    if args.verbose:
        replay_log = (temp_dir / "replay.log").open("wb")
        chrome_log = (temp_dir / "chrome.log").open("wb")
        stdout_target = replay_log
        stderr_target = subprocess.STDOUT
        chrome_stdout = chrome_log
    else:
        chrome_stdout = subprocess.DEVNULL

    replay_process = subprocess.Popen(
        replay_command,
        stdout=stdout_target,
        stderr=stderr_target,
    )

    chrome_process = subprocess.Popen(
        chrome_command,
        stdout=chrome_stdout,
        stderr=subprocess.STDOUT,
    )

    try:
        wait_for_http(args.ui_url, args.page_ready_timeout_s)
        cdp_url = wait_for_cdp_target(args.cdp_port, args.page_ready_timeout_s, args.ui_url)
    except Exception:
        for process in (chrome_process, replay_process):
            if process.poll() is None:
                process.terminate()
        raise

    return ReplaySession(
        replay_process=replay_process,
        chrome_process=chrome_process,
        temp_dir=temp_dir,
        ui_url=args.ui_url,
        cdp_url=cdp_url,
        prepared_replay_file=prepared_replay_file,
        prepared_replay_duration_us=prepared_replay_duration_us,
        replay_log_events=replay_log_events,
    )


def frame_offsets_us(session: ReplaySession, args: argparse.Namespace) -> list[int]:
    if args.cover_full_replay:
        if args.frame_count == 1:
            return [0]
        step = session.prepared_replay_duration_us / max(1, args.frame_count - 1)
        return [int(round(step * index)) for index in range(args.frame_count)]
    return [index * args.frame_interval_ms * 1000 for index in range(args.frame_count)]


def overlay_log_panel(
    image: Image.Image,
    events: list[ReplayLogEvent],
    frame_offset_us: int,
    panel_width: int,
    max_lines: int,
) -> Image.Image:
    recent = [event.text for event in events if event.offset_us <= frame_offset_us]
    if not recent:
        recent = ["waiting for notable events..."]
    display_lines: list[str] = []
    for line in recent[-max_lines:]:
        display_lines.extend(textwrap.wrap(line, width=32) or [line])

    image = image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default()
    panel_width = min(panel_width, max(220, image.width - 40))
    x0 = image.width - panel_width - 12
    y0 = 12
    x1 = image.width - 12
    y1 = min(image.height - 12, y0 + 34 + 18 * (len(display_lines) + 1))
    draw.rounded_rectangle((x0, y0, x1, y1), radius=12, fill=(12, 16, 24, 210), outline=(110, 140, 200, 255), width=2)
    draw.text((x0 + 12, y0 + 10), "OTNS log", fill=(255, 255, 255, 255), font=font)
    cursor_y = y0 + 32
    for line in display_lines[-max_lines:]:
        draw.text((x0 + 12, cursor_y), line, fill=(200, 230, 255, 255), font=font)
        cursor_y += 16
    return Image.alpha_composite(image, overlay).convert("RGB")


def capture_frames(session: ReplaySession, args: argparse.Namespace) -> list[Image.Image]:
    frames: list[Image.Image] = []
    unique_hashes: set[str] = set()
    offsets_us = frame_offsets_us(session, args)

    time.sleep(args.warmup_ms / 1000.0)
    frame_interval_ms = args.frame_interval_ms
    if args.cover_full_replay:
        frame_interval_ms = max(
            1,
            int((session.prepared_replay_duration_us / 1000.0) / max(1, args.frame_count - 1)),
        )

    with DevToolsWebSocket(session.cdp_url, timeout_s=max(5.0, args.page_ready_timeout_s)) as cdp:
        for index in range(args.frame_count):
            result = cdp.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})
            png_bytes = base64.b64decode(result["data"])
            unique_hashes.add(hashlib.md5(png_bytes).hexdigest())
            image = Image.open(io_from_bytes(png_bytes)).convert("RGB")
            if args.show_log_panel:
                image = overlay_log_panel(
                    image,
                    session.replay_log_events,
                    offsets_us[index],
                    args.log_panel_width,
                    args.log_lines,
                )
            frames.append(image.copy())
            time.sleep(frame_interval_ms / 1000.0)

    if len(unique_hashes) < 2:
        raise ReplayVideoError(
            "Captured fewer than two distinct replay frames. "
            "Try increasing --frame-count, reducing --warmup-ms, or confirming the replay page is animating."
        )
    return frames


def io_from_bytes(data: bytes) -> Any:
    import io

    return io.BytesIO(data)


def write_mp4(frames: list[Image.Image], output_path: Path, fps: float) -> None:
    if fps <= 0:
        raise ReplayVideoError("--video-fps must be > 0")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = ensure_tool(str(Path.home() / ".local" / "bin" / "ffmpeg")) if (Path.home() / ".local" / "bin" / "ffmpeg").exists() else ensure_tool("ffmpeg")
    frame_dir = output_path.parent / f".{output_path.stem}_frames"
    frame_dir.mkdir(parents=True, exist_ok=True)
    try:
        for index, frame in enumerate(frames, start=1):
            frame.save(frame_dir / f"frame_{index:04d}.png", format="PNG")
        command = [
            ffmpeg,
            "-y",
            "-framerate",
            f"{fps:g}",
            "-i",
            str(frame_dir / "frame_%04d.png"),
            "-vf",
            "pad=ceil(iw/2)*2:ceil(ih/2)*2:color=black,format=yuv420p",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True)
        if completed.returncode != 0:
            raise ReplayVideoError(completed.stderr.strip() or completed.stdout.strip() or "ffmpeg encoding failed")
    finally:
        shutil.rmtree(frame_dir, ignore_errors=True)


def maybe_update_run_metadata(replay_file: Path, output_mp4: Path, args: argparse.Namespace) -> None:
    manifest_path = replay_file.parent / "manifest.json"
    if not manifest_path.exists():
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    manifest["video_file"] = output_mp4.name
    manifest["video_frame_count"] = args.frame_count
    manifest["video_fps"] = args.video_fps
    manifest["video_show_log_panel"] = bool(args.show_log_panel)
    manifest["video_replay_speed"] = args.replay_speed
    manifest["end_device_y_offset"] = args.end_device_y_offset
    manifest["video_log_lines"] = args.log_lines
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    readme_path = replay_file.parent / "README.md"
    if not readme_path.exists():
        return
    render_command = (
        f"python3 scripts/replay_to_mp4.py {replay_file.name} "
        f"--frame-count {args.frame_count} "
        f"--replay-speed {args.replay_speed:g} --cover-full-replay "
        f"--end-device-y-offset {args.end_device_y_offset} --video-fps {args.video_fps:g}"
        f"{' --show-log-panel --log-lines ' + str(args.log_lines) if args.show_log_panel else ''}"
    )
    content = readme_path.read_text(encoding="utf-8")
    content = re.sub(
        r"- Rendered from the replay with `python3 scripts/replay_to_[^`]+`",
        f"- Rendered from the replay with `{render_command}`",
        content,
    )
    if "Rendered from the replay with" not in content:
        content = content.rstrip() + f"\n\n- Rendered from the replay with `{render_command}`\n"
    readme_path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    if args.frame_count < 2:
        print("--frame-count must be >= 2", file=sys.stderr)
        return 2
    if args.frame_interval_ms < 1:
        print("--frame-interval-ms must be >= 1", file=sys.stderr)
        return 2

    replay_file = args.replay_file.resolve()
    if not replay_file.exists():
        print(f"Replay file not found: {replay_file}", file=sys.stderr)
        return 2

    if args.video_fps <= 0:
        print("--video-fps must be > 0", file=sys.stderr)
        return 2

    output_mp4 = (args.output_mp4 or default_output_mp4(replay_file)).resolve()
    if output_mp4.exists():
        print(f"Output MP4 already exists: {output_mp4}", file=sys.stderr)
        return 2

    session = launch_replay_session(args)
    try:
        frames = capture_frames(session, args)
        write_mp4(frames, output_mp4, args.video_fps)
        maybe_update_run_metadata(replay_file, output_mp4, args)
    except ReplayVideoError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        session.close()

    print(output_mp4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
