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
DEFAULT_ARTIFACTS_DIR = ROOT / "artifacts"
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
        help="Copy each run plus aggregate outputs into a tracked artifact directory.",
    )
    parser.add_argument(
        "--commit-artifact-dir",
        type=Path,
        default=None,
        help="Explicit repeated-run artifact directory. Defaults to artifacts/<artifact-name>.",
    )
    parser.add_argument(
        "--artifact-name",
        default=None,
        help="Artifact directory name for repeated-run exports. Defaults to the experiment name.",
    )
    parser.add_argument("--mock", action="store_true", help="Run in mock mode.")
    return parser.parse_args()


def timestamp_token() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def write_artifact_readme(path: Path, experiment_name: str, scenario: Path, aggregate_summary_exists: bool) -> None:
    lines = [
        f"# Artifact: {path.parent.name}",
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


def resolve_artifact_dir(
    commit_artifact_dir: Path | None,
    artifact_name: str | None,
    experiment_name: str,
) -> Path:
    if commit_artifact_dir is not None:
        return commit_artifact_dir
    return DEFAULT_ARTIFACTS_DIR / (artifact_name or experiment_name)


def main() -> int:
    args = parse_args()
    if args.repeat_count < 1:
        print("--repeat-count must be >= 1", file=sys.stderr)
        return 2
    if not args.mock and (args.listen_port_base < 9000 or args.listen_port_base % 10 != 0):
        print("--listen-port-base must be >= 9000 and divisible by 10 for real OTNS runs", file=sys.stderr)
        return 2

    experiment_name = args.experiment_name or f"{scenario_name(args.scenario)}_{timestamp_token()}"
    experiment_dir = args.results_dir / experiment_name
    ensure_results_dir(experiment_dir)
    artifact_dir = None
    if args.copy_results_to_artifact:
        artifact_dir = resolve_artifact_dir(args.commit_artifact_dir, args.artifact_name, experiment_name)
        if artifact_dir.exists():
            print(f"Artifact directory already exists: {artifact_dir}", file=sys.stderr)
            return 2

    runs: list[dict[str, Any]] = []
    for index in range(args.repeat_count):
        run_dir = experiment_dir / f"run_{index + 1:03d}"
        ensure_results_dir(run_dir)

        cmd = [
            "python3",
            str(RUNNER),
            "--scenario",
            str(args.scenario),
            "--results-dir",
            str(run_dir),
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
                "--openthread-commit",
                args.openthread_commit,
                "--otns-commit",
                args.otns_commit,
            ]
        )
        if args.copy_results_to_artifact:
            run_artifact_dir = artifact_dir / f"run_{index + 1:03d}"
            cmd.extend(
                [
                    "--copy-results-to-artifact",
                    "--commit-artifact-dir",
                    str(run_artifact_dir),
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

    if artifact_dir is not None:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_manifest_path = artifact_dir / "repeated_run_manifest.json"
        shutil.copy2(manifest_path, artifact_manifest_path)

        aggregate_summary_path = artifact_dir / "aggregate_summary.json"
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

        artifact_readme = artifact_dir / "README.md"
        write_artifact_readme(
            artifact_readme,
            experiment_name=experiment_name,
            scenario=args.scenario,
            aggregate_summary_exists=aggregate_summary_path.exists(),
        )
        print(artifact_dir)
        print(artifact_manifest_path)
        print(aggregate_summary_path)

    print(experiment_dir)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
