#!/usr/bin/env python3
"""Validate OTNS CLI compatibility for the baseline benchmark runner."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
from pathlib import Path
from typing import Any

import run_baseline as rb


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--otns-command",
        default=os.environ.get("OTNS_COMMAND", "/home/ewout/go/bin/otns -web=false -autogo=false -speed 1"),
        help="OTNS executable or full command string to validate.",
    )
    parser.add_argument(
        "--otns-workdir",
        type=Path,
        default=Path(os.environ["OTNS_WORKDIR"]) if os.environ.get("OTNS_WORKDIR") else None,
        help="Optional OTNS launch working directory.",
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=9990,
        help="Listen port to append when the command does not already include -listen.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional JSON output path.",
    )
    return parser.parse_args()


def with_listen_port(command: str, listen_port: int) -> str:
    argv = shlex.split(command)
    if "-listen" in argv:
        return command
    return f"{command} -listen localhost:{listen_port}"


def basename_command(command: str) -> str:
    return Path(shlex.split(command)[0]).name


def run_command_suite(command: str, workdir: Path | None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "command": command,
        "workdir": str(workdir) if workdir else None,
        "commands": {},
        "notes": [],
    }

    with rb.OtnsSession(command, cwd=workdir) as session:
        payload["commands"]["speed 0"] = session.command_output("speed 0")
        payload["commands"]["radiomodel MutualInterference"] = session.command_output("radiomodel MutualInterference")
        payload["commands"]["add router #1"] = session.command_output("add router")
        payload["commands"]["add router #2"] = session.command_output("add router")
        payload["commands"]["add med"] = session.command_output("add med")
        payload["commands"]["move 1 100 300"] = session.command_output("move 1 100 300")
        payload["commands"]["move 2 500 300"] = session.command_output("move 2 500 300")
        payload["commands"]["move 3 140 300"] = session.command_output("move 3 140 300")

        try:
            session.command_output("move 3 140.5 300.5")
        except rb.OtnsSessionError as exc:
            payload["commands"]["move 3 140.5 300.5"] = {"error": str(exc)}

        payload["commands"]["go 120"] = session.command_output("go 120")
        payload["commands"]["time"] = session.command_output("time")
        payload["commands"]["nodes"] = session.command_output("nodes")
        payload["commands"]['node 3 "state"'] = session.command_output('node 3 "state"')
        payload["commands"]['node 3 "rloc16"'] = session.command_output('node 3 "rloc16"')
        payload["commands"]['node 3 "parent"'] = session.command_output('node 3 "parent"')
        payload["commands"]['node 3 "counters ip"'] = session.command_output('node 3 "counters ip"')
        payload["commands"]['node 3 "counters mle"'] = session.command_output('node 3 "counters mle"')
        payload["commands"]["ping 1 3 count 1"] = session.command_output("ping 1 3 count 1")
        payload["commands"]["go 5 after ping"] = session.command_output("go 5")

        try:
            payload["commands"]["scan 3 immediate"] = session.command_output("scan 3")
            payload["commands"]["go 5 after scan"] = session.command_output("go 5")
            scan_rows = rb.parse_scan_table(payload["commands"]["go 5 after scan"])
            payload["commands"]["scan 3 parsed_rows"] = scan_rows
            if scan_rows:
                payload["notes"].append(
                    "scan is asynchronous: rows appear during the following go command, not as immediate scan output."
                )
            else:
                payload["notes"].append("scan produced no parsed rows in the follow-up go output.")
        except rb.OtnsSessionError as exc:
            payload["commands"]["scan 3"] = {"error": str(exc)}
            payload["notes"].append("scan compatibility is inconsistent in this setup.")

    return payload


def validate_launch_variants(base_command: str, workdir: Path | None) -> list[dict[str, Any]]:
    path_name = basename_command(base_command)
    variants = [
        {
            "name": "explicit_command_with_workdir",
            "command": base_command,
            "workdir": workdir,
        }
    ]

    if shutil.which(path_name):
        variants.append(
            {
                "name": "path_command_with_workdir",
                "command": f"{path_name} -web=false -autogo=false -speed 1 -listen localhost:10000",
                "workdir": workdir,
            }
        )

    variants.append(
        {
            "name": "explicit_command_without_workdir",
            "command": base_command,
            "workdir": None,
        }
    )

    results: list[dict[str, Any]] = []
    for variant in variants:
        entry = {
            "name": variant["name"],
            "command": variant["command"],
            "workdir": str(variant["workdir"]) if variant["workdir"] else None,
        }
        try:
            with rb.OtnsSession(variant["command"], cwd=variant["workdir"]) as session:
                session.command_output("speed 0")
                session.command_output("add router")
            entry["status"] = "ok"
        except Exception as exc:
            entry["status"] = "error"
            entry["error"] = str(exc)
        results.append(entry)
    return results


def main() -> int:
    args = parse_args()
    if args.listen_port < 9000 or args.listen_port % 10 != 0:
        raise SystemExit("--listen-port must be >= 9000 and divisible by 10")

    validated_command = with_listen_port(args.otns_command, args.listen_port)
    payload = {
        "validated_command": validated_command,
        "launch_variants": validate_launch_variants(validated_command, args.otns_workdir),
        "command_suite": run_command_suite(validated_command, args.otns_workdir),
    }

    if args.output_json:
        with args.output_json.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
