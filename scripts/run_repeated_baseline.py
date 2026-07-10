#!/usr/bin/env python3
"""Run the baseline benchmark repeatedly and collect per-run artifacts."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = ROOT / "scenarios" / "baseline_mobile_parent_switch.yaml"
DEFAULT_RESULTS_DIR = ROOT / "results" / "repeated"
RUNNER = ROOT / "scripts" / "run_baseline.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--repeat-count", type=int, default=3, help="Number of runs to execute.")
    parser.add_argument(
        "--experiment-name",
        default=None,
        help="Optional experiment directory name. Defaults to scenario name plus UTC timestamp.",
    )
    parser.add_argument(
        "--otns-command",
        default=os.environ.get("OTNS_COMMAND", "otns"),
        help="OTNS executable or full command string passed through to run_baseline.py",
    )
    parser.add_argument(
        "--otns-workdir",
        type=Path,
        default=Path(os.environ["OTNS_WORKDIR"]) if os.environ.get("OTNS_WORKDIR") else None,
        help="Optional OTNS working directory passed through to run_baseline.py",
    )
    parser.add_argument(
        "--otns-watch-level",
        default="off",
        help="Optional OTNS default watch level passed through to run_baseline.py.",
    )
    parser.add_argument(
        "--listen-port-base",
        type=int,
        default=9990,
        help="Base listen port for repeated real OTNS runs. Must be >= 9000 and divisible by 10.",
    )
    parser.add_argument("--capture-replay", action="store_true", help="Pass through replay capture to each run.")
    parser.add_argument(
        "--replay-dir",
        type=Path,
        default=None,
        help="Optional scratch replay directory base. Each run gets a replay subdirectory beneath its run directory unless overridden.",
    )
    parser.add_argument(
        "--firmware-variant",
        default="stock-openthread",
        help="Firmware or build label recorded in per-run replay/artifact metadata.",
    )
    parser.add_argument(
        "--thread-device-type",
        default=None,
        help="Thread device type metadata passed through to run_baseline.py.",
    )
    parser.add_argument(
        "--parent-search-config",
        choices=("enabled", "disabled", "observed", "unknown"),
        default="unknown",
        help="Periodic Parent Search metadata passed through to run_baseline.py.",
    )
    parser.add_argument(
        "--node-binary-path",
        type=Path,
        default=None,
        help="Optional MTD node binary path passed through to run_baseline.py.",
    )
    parser.add_argument(
        "--build-config-source",
        default=None,
        help="Build provenance metadata passed through to run_baseline.py.",
    )
    parser.add_argument(
        "--equivalent-to",
        default=None,
        help="Optional default-build classification passed through to run_baseline.py.",
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
        help="Copy each run plus aggregate outputs into tracked results directories.",
    )
    parser.add_argument(
        "--commit-artifact-dir",
        type=Path,
        default=None,
        help="Explicit repeated-run tracked results directory.",
    )
    parser.add_argument(
        "--artifact-name",
        default=None,
        help="Legacy name for the tracked results variant suffix.",
    )
    parser.add_argument("--mock", action="store_true", help="Run in mock mode.")
    return parser.parse_args()


def timestamp_token() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slugify_variant(value: str) -> str:
    import re

    lowered = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "run"


def format_run_id(token: str, run_index: int) -> str:
    return f"{token[:8]}-{token[9:15]}-run{run_index:02d}"


def format_experiment_id(token: str) -> str:
    return f"{token[:8]}-{token[9:15]}-experiment"


def tracked_results_collection_name(scenario_stem: str, variant: str | None) -> str:
    if not variant:
        return scenario_stem
    return f"{scenario_stem}_{slugify_variant(variant)}"


def ensure_results_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def scenario_name(path: Path) -> str:
    return path.stem


def command_with_listen_port(command: str, port: int) -> str:
    if "-listen" in command.split():
        return command
    return f"{command} -listen localhost:{port}"


def write_json(data: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_results_readme(path: Path, experiment_name: str, scenario: Path, aggregate_summary_exists: bool) -> None:
    lines = [
        f"# Result set: {path.parent.name}",
        "",
        "Curated repeated-run OTNS benchmark artifact.",
        "",
        "## Metadata",
        "",
        f"- Experiment name: `{experiment_name}`",
        f"- Scenario file: `{scenario}`",
        f"- Aggregate summary: `{'aggregate_summary.json' if aggregate_summary_exists else 'not generated'}`",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def resolve_tracked_results_dir(
    commit_artifact_dir: Path | None,
    artifact_name: str | None,
    scenario_stem: str,
    experiment_token: str,
) -> Path:
    if commit_artifact_dir is not None:
        return commit_artifact_dir
    collection = tracked_results_collection_name(scenario_stem, artifact_name)
    return ROOT / "results" / collection / format_experiment_id(experiment_token)


def main() -> int:
    args = parse_args()
    if args.repeat_count < 1:
        print("--repeat-count must be >= 1", file=sys.stderr)
        return 2
    if not args.mock and (args.listen_port_base < 9000 or args.listen_port_base % 10 != 0):
        print("--listen-port-base must be >= 9000 and divisible by 10 for real OTNS runs", file=sys.stderr)
        return 2

    experiment_token = timestamp_token()
    experiment_name = args.experiment_name or f"{scenario_name(args.scenario)}_{experiment_token}"
    experiment_dir = args.results_dir / experiment_name
    ensure_results_dir(experiment_dir)
    tracked_experiment_dir = None
    if args.copy_results_to_artifact:
        tracked_experiment_dir = resolve_tracked_results_dir(
            args.commit_artifact_dir,
            args.artifact_name,
            scenario_name(args.scenario),
            experiment_token,
        )
        if tracked_experiment_dir.exists():
            print(f"Tracked results directory already exists: {tracked_experiment_dir}", file=sys.stderr)
            return 2

    runs: list[dict[str, Any]] = []
    for index in range(args.repeat_count):
        run_dir = experiment_dir / f"run_{index + 1:03d}"
        ensure_results_dir(run_dir)
        run_token = timestamp_token()
        run_id = format_run_id(run_token, index + 1)

        cmd = [
            "python3",
            str(RUNNER),
            "--scenario",
            str(args.scenario),
            "--results-dir",
            str(run_dir),
            "--timestamp-token",
            run_token,
        ]
        if args.mock:
            cmd.append("--mock")
        else:
            port = args.listen_port_base + index * 10
            cmd.extend(["--otns-command", command_with_listen_port(args.otns_command, port)])
            if args.otns_workdir is not None:
                cmd.extend(["--otns-workdir", str(args.otns_workdir)])
        if args.capture_replay:
            cmd.append("--capture-replay")
            run_replay_dir = args.replay_dir if args.replay_dir is not None else run_dir / "replay"
            cmd.extend(["--replay-dir", str(run_replay_dir)])
        cmd.extend(
            [
                "--firmware-variant",
                args.firmware_variant,
                "--parent-search-config",
                args.parent_search_config,
                "--openthread-commit",
                args.openthread_commit,
                "--otns-commit",
                args.otns_commit,
                "--otns-watch-level",
                args.otns_watch_level,
            ]
        )
        if args.thread_device_type is not None:
            cmd.extend(["--thread-device-type", args.thread_device_type])
        if args.node_binary_path is not None:
            cmd.extend(["--node-binary-path", str(args.node_binary_path)])
        if args.build_config_source is not None:
            cmd.extend(["--build-config-source", args.build_config_source])
        if args.equivalent_to is not None:
            cmd.extend(["--equivalent-to", args.equivalent_to])
        if args.copy_results_to_artifact:
            run_tracked_dir = tracked_experiment_dir / run_id / run_id
            cmd.extend(
                [
                    "--copy-results-to-artifact",
                    "--commit-artifact-dir",
                    str(run_tracked_dir),
                ]
            )

        completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        run_entry: dict[str, Any] = {
            "run_index": index + 1,
            "command": cmd,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip().splitlines(),
            "stderr": completed.stderr.strip(),
            "run_dir": str(run_dir),
        }
        runs.append(run_entry)
        if completed.returncode != 0:
            manifest_path = experiment_dir / "repeated_run_manifest.json"
            with manifest_path.open("w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "experiment_name": experiment_name,
                        "scenario": str(args.scenario),
                        "repeat_count": args.repeat_count,
                        "mock": args.mock,
                        "runs": runs,
                    },
                    handle,
                    indent=2,
                    sort_keys=True,
                )
                handle.write("\n")
            print(f"Repeated run failed at run {index + 1}", file=sys.stderr)
            print(manifest_path)
            return 1

    manifest = {
        "experiment_name": experiment_name,
        "scenario": str(args.scenario),
        "repeat_count": args.repeat_count,
        "mock": args.mock,
        "runs": runs,
    }
    manifest_path = experiment_dir / "repeated_run_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")

    if tracked_experiment_dir is not None:
        tracked_experiment_dir.mkdir(parents=True, exist_ok=True)
        artifact_manifest_path = tracked_experiment_dir / "repeated_run_manifest.json"
        shutil.copy2(manifest_path, artifact_manifest_path)

        aggregate_summary_path = tracked_experiment_dir / "aggregate_summary.json"
        analysis_cmd = [
            "python3",
            str(ROOT / "analysis" / "analyze_baseline.py"),
            str(experiment_dir),
            "--output-json",
            str(aggregate_summary_path),
        ]
        completed = subprocess.run(analysis_cmd, cwd=ROOT, capture_output=True, text=True)
        if completed.returncode != 0:
            print(completed.stderr or completed.stdout, file=sys.stderr)
            return 1

        artifact_readme = tracked_experiment_dir / "README.md"
        write_results_readme(
            artifact_readme,
            experiment_name=experiment_name,
            scenario=args.scenario,
            aggregate_summary_exists=aggregate_summary_path.exists(),
        )
        print(tracked_experiment_dir)
        print(artifact_manifest_path)
        print(aggregate_summary_path)

    print(experiment_dir)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
