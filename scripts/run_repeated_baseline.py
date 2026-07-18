#!/usr/bin/env python3
"""Run the baseline benchmark repeatedly and collect per-run artifacts."""

from __future__ import annotations

import argparse
import concurrent.futures
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = ROOT / "scenarios" / "med_simple_parent_switch.yaml"
DEFAULT_RESULTS_DIR = ROOT / "results" / "repeated"
RUNNER = ROOT / "scripts" / "run_baseline.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--repeat-count", type=int, default=3, help="Number of runs to execute.")
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Maximum number of isolated OTNS runs to execute concurrently.",
    )
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
    parser.add_argument(
        "--otns-seed-base",
        type=int,
        default=None,
        help="Optional deterministic OTNS seed for run 1; each following run increments it by one.",
    )
    parser.add_argument(
        "--target-seed-base",
        type=int,
        default=None,
        help="Optional directed target-selection seed for run 1; each following run increments it by one.",
    )
    parser.add_argument("--capture-replay", action="store_true", help="Pass through replay capture to each run.")
    parser.add_argument(
        "--capture-sim-ping-rss",
        action="store_true",
        help="Pass through simulator-level per-ping RSS capture to each run.",
    )
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
        "--node-binary-profile",
        choices=("stock", "preferred-parent"),
        default=None,
        help="Declared MTD profile passed through to run_baseline.py.",
    )
    parser.add_argument(
        "--ftd-node-binary-path",
        type=Path,
        default=None,
        help="Optional FTD node binary path passed through to run_baseline.py.",
    )
    parser.add_argument(
        "--ftd-node-binary-profile",
        choices=("stock", "fastpr"),
        default=None,
        help="Declared FTD profile passed through to run_baseline.py.",
    )
    parser.add_argument(
        "--build-config-source",
        default=None,
        help="Build provenance metadata passed through to run_baseline.py.",
    )
    parser.add_argument(
        "--firmware-source-repo",
        type=Path,
        default=Path(os.environ["FIRMWARE_SOURCE_REPO"]) if os.environ.get("FIRMWARE_SOURCE_REPO") else None,
        help="Optional firmware/patch repository passed through to run_baseline.py.",
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
    arguments = shlex.split(command)
    for index, argument in enumerate(arguments):
        if argument == "-listen":
            if index + 1 >= len(arguments):
                raise ValueError("-listen in --otns-command is missing its address")
            arguments[index + 1] = f"localhost:{port}"
            return shlex.join(arguments)
        if argument.startswith("-listen="):
            arguments[index] = f"-listen=localhost:{port}"
            return shlex.join(arguments)
    return shlex.join([*arguments, "-listen", f"localhost:{port}"])


def command_with_seed(command: str, seed: int) -> str:
    arguments = shlex.split(command)
    if "-seed" in arguments or any(argument.startswith("-seed=") for argument in arguments):
        raise ValueError("--otns-seed-base cannot be combined with -seed in --otns-command")
    return f"{command} -seed {seed}"


def write_json(data: dict[str, Any], path: Path) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_artifact_checksums(artifact_dir: Path, output_name: str = "checksums.sha256") -> None:
    output_path = artifact_dir / output_name
    with output_path.open("w", encoding="utf-8") as handle:
        for path in sorted(artifact_dir.rglob("*")):
            if path.is_file() and path != output_path:
                handle.write(f"{sha256_file(path)}  {path.relative_to(artifact_dir).as_posix()}\n")


def write_results_readme(
    path: Path,
    experiment_name: str,
    scenario: Path,
    aggregate_summary_exists: bool,
    manifest: dict[str, Any],
) -> None:
    lines = [
        f"# Result set: {path.parent.name}",
        "",
        "Curated repeated-run OTNS benchmark artifact.",
        "",
        "## Metadata",
        "",
        f"- Experiment name: `{experiment_name}`",
        f"- Scenario file: `{scenario}`",
        f"- Repeat count: `{manifest['repeat_count']}`",
        f"- Concurrent jobs: `{manifest.get('jobs', 1)}`",
        f"- Listen port base: `{manifest.get('listen_port_base')}`",
        f"- Firmware variant: `{manifest['firmware_variant']}`",
        f"- Thread device type: `{manifest['thread_device_type'] or 'unspecified'}`",
        f"- Parent search config: `{manifest['parent_search_config']}`",
        f"- Node binary path: `{manifest['node_binary_path'] or 'not recorded'}`",
        f"- Node binary profile: `{manifest['node_binary_profile'] or 'not recorded'}`",
        f"- FTD node binary path: `{manifest['ftd_node_binary_path'] or 'not recorded'}`",
        f"- FTD node binary profile: `{manifest['ftd_node_binary_profile'] or 'not recorded'}`",
        f"- Build config source: `{manifest['build_config_source'] or 'not recorded'}`",
        f"- Firmware source repository: `{manifest['firmware_source_repo'] or 'not recorded'}`",
        f"- OpenThread commit: `{manifest['openthread_commit']}`",
        f"- OTNS commit: `{manifest['otns_commit']}`",
        f"- OTNS seed base: `{manifest.get('otns_seed_base')}`",
        f"- Simulator ping RSS capture: `{manifest.get('capture_sim_ping_rss', False)}`",
        f"- Aggregate summary: `{'aggregate_summary.json' if aggregate_summary_exists else 'not generated'}`",
        f"- Manifest: `manifest.json`",
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


RUNTIME_EXCLUDES = {"tmp", "current.pcap"}


def prepare_otns_runtime_dir(runtime_dir: Path, source_workdir: Path | None) -> None:
    """Create an isolated OTNS cwd while preserving source-relative executables."""
    runtime_dir.mkdir(parents=True, exist_ok=True)
    if source_workdir is None:
        return
    source = source_workdir.resolve()
    if not source.is_dir():
        raise ValueError(f"OTNS workdir does not exist or is not a directory: {source}")
    for entry in source.iterdir():
        if entry.name in RUNTIME_EXCLUDES or entry.name.startswith("otns_") and entry.name.endswith(".replay"):
            continue
        destination = runtime_dir / entry.name
        if destination.exists() or destination.is_symlink():
            continue
        destination.symlink_to(entry.resolve(), target_is_directory=entry.is_dir())


@contextmanager
def reserve_otns_ports(ports: list[int]) -> Iterator[None]:
    """Reserve OTNS simulation IDs across concurrent repeated-run processes."""
    lock_dir = Path("/tmp/otns-maps-port-locks")
    lock_dir.mkdir(parents=True, exist_ok=True)
    handles: list[Any] = []
    try:
        for port in ports:
            handle = (lock_dir / f"{port}.lock").open("a+", encoding="utf-8")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                handle.close()
                raise RuntimeError(f"OTNS listen-port block {port} is already reserved") from exc
            handle.seek(0)
            handle.truncate()
            handle.write(f"pid={os.getpid()} port={port}\n")
            handle.flush()
            handles.append(handle)
        yield
    finally:
        for handle in reversed(handles):
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()


def validate_run_outputs(
    run_dir: Path,
    runtime_dir: Path,
    firmware_variant: str,
    simulation_id: int,
    watch_level: str,
    target_selection_seed: int | None = None,
) -> dict[str, Any]:
    """Reject incomplete or cross-contaminated outputs before aggregation."""
    errors: list[str] = []
    checks: list[str] = []
    summaries = sorted(run_dir.glob("baseline_summary_*.json"))
    if len(summaries) != 1:
        errors.append(f"expected one summary JSON, found {len(summaries)}")
        return {"status": "failed", "errors": errors, "checks": checks}

    summary_path = summaries[0]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("firmware_variant") != firmware_variant:
        errors.append(
            f"firmware variant mismatch: expected {firmware_variant!r}, got {summary.get('firmware_variant')!r}"
        )
    else:
        checks.append("firmware_variant")

    recorded_runtime = summary.get("otns_runtime_dir")
    if recorded_runtime is not None and Path(recorded_runtime).resolve() != runtime_dir.resolve():
        errors.append(f"runtime directory mismatch: {recorded_runtime}")
    else:
        checks.append("runtime_directory")

    if target_selection_seed is not None:
        if summary.get("random_seed") != target_selection_seed:
            errors.append(
                f"target-selection seed mismatch: expected {target_selection_seed}, got {summary.get('random_seed')}"
            )
        else:
            checks.append("target_selection_seed")

    runtime_logs = sorted((runtime_dir / "tmp").glob("*.log"))
    wrong_simulation_logs = [path.name for path in runtime_logs if not path.name.startswith(f"{simulation_id}_")]
    if wrong_simulation_logs:
        errors.append("runtime contains logs from another simulation ID: " + ", ".join(wrong_simulation_logs))
    else:
        checks.append("simulation_id_log_prefix")

    node_log_files = [Path(value) for value in summary.get("node_log_files", [])]
    for path in node_log_files:
        try:
            path.resolve().relative_to(run_dir.resolve())
        except ValueError:
            errors.append(f"copied node log is outside its run directory: {path}")
    if node_log_files:
        checks.append("node_log_scope")
    elif watch_level.lower() != "off":
        errors.append("watch logging was enabled but no node logs were copied")

    requested_events = [
        event for event in summary.get("preferred_parent_events", []) if event.get("event") == "requested"
    ]
    if requested_events and node_log_files:
        requested = requested_events[0]
        target = str(requested.get("target", "")).lower()
        mode = str(requested.get("mode", "")).lower()
        mobile_logs = [path for path in node_log_files if path.name.startswith("node_log_mobile_")]
        if len(mobile_logs) != 1:
            errors.append(f"expected one copied mobile log, found {len(mobile_logs)}")
        else:
            requested_lines = [
                line
                for line in mobile_logs[0].read_text(encoding="utf-8", errors="replace").splitlines()
                if "PREFPARENT event=requested" in line
            ]
            matching = [
                line
                for line in requested_lines
                if f"target={target}" in line.lower() and f"mode={mode}" in line.lower()
            ]
            if not matching:
                errors.append(f"mobile log does not contain the summary target/mode ({target}, {mode})")
            else:
                checks.append("preferred_parent_target_mode")

    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "checks": checks,
        "summary_file": str(summary_path),
        "runtime_log_count": len(runtime_logs),
    }


def execute_run(
    index: int,
    args: argparse.Namespace,
    experiment_dir: Path,
    tracked_experiment_dir: Path | None,
) -> dict[str, Any]:
    run_number = index + 1
    run_dir = experiment_dir / f"run_{run_number:03d}"
    ensure_results_dir(run_dir)
    runtime_dir = run_dir / "otns_runtime"
    run_token = timestamp_token()
    run_id = format_run_id(run_token, run_number)
    port = args.listen_port_base + index * 10
    simulation_id = (port - 9000) // 10

    cmd = [
        sys.executable,
        str(RUNNER),
        "--scenario",
        str(args.scenario.resolve()),
        "--results-dir",
        str(run_dir.resolve()),
        "--timestamp-token",
        run_token,
    ]
    if args.mock:
        cmd.append("--mock")
    else:
        prepare_otns_runtime_dir(runtime_dir, args.otns_workdir)
        run_otns_command = command_with_listen_port(args.otns_command, port)
        if args.otns_seed_base is not None:
            run_otns_command = command_with_seed(run_otns_command, args.otns_seed_base + index)
        cmd.extend(["--otns-command", run_otns_command, "--otns-runtime-dir", str(runtime_dir.resolve())])
        if args.otns_workdir is not None:
            cmd.extend(["--otns-workdir", str(args.otns_workdir.resolve())])
    if args.target_seed_base is not None:
        cmd.extend(["--directed-random-seed", str(args.target_seed_base + index)])
    if args.capture_replay:
        cmd.append("--capture-replay")
        run_replay_dir = args.replay_dir if args.replay_dir is not None else run_dir / "replay"
        cmd.extend(["--replay-dir", str(run_replay_dir.resolve())])
    if args.capture_sim_ping_rss:
        cmd.append("--capture-sim-ping-rss")
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
    optional_path_args = (
        ("--node-binary-path", args.node_binary_path),
        ("--ftd-node-binary-path", args.ftd_node_binary_path),
        ("--firmware-source-repo", args.firmware_source_repo),
    )
    for option, value in optional_path_args:
        if value is not None:
            cmd.extend([option, str(value.resolve())])
    optional_args = (
        ("--thread-device-type", args.thread_device_type),
        ("--node-binary-profile", args.node_binary_profile),
        ("--ftd-node-binary-profile", args.ftd_node_binary_profile),
        ("--build-config-source", args.build_config_source),
        ("--equivalent-to", args.equivalent_to),
    )
    for option, value in optional_args:
        if value is not None:
            cmd.extend([option, value])
    if args.copy_results_to_artifact:
        assert tracked_experiment_dir is not None
        run_tracked_dir = tracked_experiment_dir / run_id / run_id
        cmd.extend(["--copy-results-to-artifact", "--commit-artifact-dir", str(run_tracked_dir.resolve())])

    completed = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    validation: dict[str, Any] = {"status": "not_run", "errors": [], "checks": []}
    final_returncode = completed.returncode
    if completed.returncode == 0:
        validation = validate_run_outputs(
            run_dir=run_dir,
            runtime_dir=runtime_dir,
            firmware_variant=args.firmware_variant,
            simulation_id=simulation_id,
            watch_level=args.otns_watch_level,
            target_selection_seed=(args.target_seed_base + index if args.target_seed_base is not None else None),
        )
        if validation["status"] != "ok":
            final_returncode = 1

    return {
        "run_index": run_number,
        "command": cmd,
        "returncode": final_returncode,
        "process_returncode": completed.returncode,
        "stdout": completed.stdout.strip().splitlines(),
        "stderr": completed.stderr.strip(),
        "run_dir": str(run_dir),
        "otns_runtime_dir": str(runtime_dir) if not args.mock else None,
        "listen_port": port if not args.mock else None,
        "simulation_id": simulation_id if not args.mock else None,
        "otns_seed": args.otns_seed_base + index if args.otns_seed_base is not None else None,
        "target_selection_seed": args.target_seed_base + index if args.target_seed_base is not None else None,
        "validation": validation,
    }


def main() -> int:
    args = parse_args()
    if args.repeat_count < 1:
        print("--repeat-count must be >= 1", file=sys.stderr)
        return 2
    if args.jobs < 1:
        print("--jobs must be >= 1", file=sys.stderr)
        return 2
    if not args.mock and (args.listen_port_base < 9000 or args.listen_port_base % 10 != 0):
        print("--listen-port-base must be >= 9000 and divisible by 10 for real OTNS runs", file=sys.stderr)
        return 2
    last_port = args.listen_port_base + (args.repeat_count - 1) * 10
    if not args.mock and last_port > 65530:
        print(f"OTNS listen-port range ends at {last_port}, above the maximum usable port 65530", file=sys.stderr)
        return 2
    if args.otns_seed_base is not None:
        try:
            command_with_seed(args.otns_command, args.otns_seed_base)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
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

    ports = [args.listen_port_base + index * 10 for index in range(args.repeat_count)] if not args.mock else []
    runs: list[dict[str, Any]] = []
    try:
        reservation = reserve_otns_ports(ports) if ports else nullcontext()
        with reservation:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(args.jobs, args.repeat_count)) as executor:
                futures = {
                    executor.submit(execute_run, index, args, experiment_dir, tracked_experiment_dir): index
                    for index in range(args.repeat_count)
                }
                for future in concurrent.futures.as_completed(futures):
                    index = futures[future]
                    try:
                        runs.append(future.result())
                    except Exception as exc:
                        runs.append(
                            {
                                "run_index": index + 1,
                                "returncode": 1,
                                "process_returncode": None,
                                "stderr": f"runner orchestration failed: {exc}",
                                "stdout": [],
                                "run_dir": str(experiment_dir / f"run_{index + 1:03d}"),
                                "validation": {"status": "not_run", "errors": [str(exc)], "checks": []},
                            }
                        )
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    runs.sort(key=lambda run: run["run_index"])

    manifest = {
        "experiment_name": experiment_name,
        "scenario": str(args.scenario),
        "repeat_count": args.repeat_count,
        "jobs": min(args.jobs, args.repeat_count),
        "listen_port_base": args.listen_port_base if not args.mock else None,
        "isolated_runtime_directories": not args.mock,
        "port_locking": not args.mock,
        "mock": args.mock,
        "firmware_variant": args.firmware_variant,
        "thread_device_type": args.thread_device_type,
        "parent_search_config": args.parent_search_config,
        "node_binary_path": str(args.node_binary_path) if args.node_binary_path is not None else None,
        "node_binary_profile": args.node_binary_profile,
        "ftd_node_binary_path": str(args.ftd_node_binary_path) if args.ftd_node_binary_path is not None else None,
        "ftd_node_binary_profile": args.ftd_node_binary_profile,
        "build_config_source": args.build_config_source,
        "firmware_source_repo": str(args.firmware_source_repo) if args.firmware_source_repo is not None else None,
        "openthread_commit": args.openthread_commit,
        "otns_commit": args.otns_commit,
        "otns_watch_level": args.otns_watch_level,
        "otns_seed_base": args.otns_seed_base,
        "target_seed_base": args.target_seed_base,
        "capture_replay": args.capture_replay,
        "capture_sim_ping_rss": args.capture_sim_ping_rss,
        "tracked_experiment_dir": str(tracked_experiment_dir) if tracked_experiment_dir is not None else None,
        "runs": runs,
    }
    manifest_path = experiment_dir / "repeated_run_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")

    failed_runs = [run for run in runs if run.get("returncode") != 0]
    if failed_runs:
        failed_labels = ", ".join(str(run["run_index"]) for run in failed_runs)
        print(f"Repeated runs failed validation or execution: {failed_labels}", file=sys.stderr)
        print(manifest_path)
        return 1

    if tracked_experiment_dir is not None:
        tracked_experiment_dir.mkdir(parents=True, exist_ok=True)
        artifact_manifest_path = tracked_experiment_dir / "repeated_run_manifest.json"
        tracked_manifest_path = tracked_experiment_dir / "manifest.json"
        tracked_scenario_path = tracked_experiment_dir / "scenario.yaml"
        shutil.copy2(args.scenario, tracked_scenario_path)
        artifact_manifest = dict(manifest)
        artifact_manifest.update(
            {
                "artifact_schema_version": 1,
                "artifact_type": "repeated_experiment",
                "scenario_copy_file": tracked_scenario_path.name,
                "scenario_sha256": sha256_file(args.scenario),
                "checksums_file": "checksums.sha256",
            }
        )
        write_json(artifact_manifest, artifact_manifest_path)
        write_json(artifact_manifest, tracked_manifest_path)

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
            manifest=manifest,
        )
        write_artifact_checksums(tracked_experiment_dir)
        print(tracked_experiment_dir)
        print(tracked_manifest_path)
        print(artifact_manifest_path)
        print(aggregate_summary_path)

    print(experiment_dir)
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
