#!/usr/bin/env python3
"""Verify a self-describing OTNS result artifact and its payload checksums."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact_dir", type=Path)
    return parser.parse_args()


def load_checksums(path: Path) -> dict[str, str]:
    checksums: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        try:
            digest, relative_path = line.split("  ", 1)
        except ValueError as exc:
            raise ValueError(f"Malformed checksum line {line_number}") from exc
        candidate = Path(relative_path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"Unsafe checksum path: {relative_path}")
        if relative_path in checksums:
            raise ValueError(f"Duplicate checksum path: {relative_path}")
        checksums[relative_path] = digest
    return checksums


def require_relative_file(artifact_dir: Path, value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Missing {label}")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"{label} is not artifact-relative: {value}")
    path = artifact_dir / relative
    if not path.is_file():
        raise ValueError(f"Missing {label}: {value}")
    return path


def verify_artifact(artifact_dir: Path) -> dict[str, Any]:
    artifact_dir = artifact_dir.resolve()
    manifest_path = artifact_dir / "manifest.json"
    checksums_path = artifact_dir / "checksums.sha256"
    if not manifest_path.is_file() or not checksums_path.is_file():
        raise ValueError("Artifact requires manifest.json and checksums.sha256")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("artifact_schema_version") != 1:
        raise ValueError("Unsupported or missing artifact_schema_version")

    checksums = load_checksums(checksums_path)
    actual_files = {
        path.relative_to(artifact_dir).as_posix()
        for path in artifact_dir.rglob("*")
        if path.is_file() and path != checksums_path
    }
    if set(checksums) != actual_files:
        missing = sorted(actual_files - set(checksums))
        extra = sorted(set(checksums) - actual_files)
        raise ValueError(f"Checksum inventory mismatch: unlisted={missing}, missing={extra}")
    for relative_path, expected in checksums.items():
        actual = sha256_file(artifact_dir / relative_path)
        if actual != expected:
            raise ValueError(f"Checksum mismatch for {relative_path}: expected {expected}, got {actual}")

    if manifest.get("artifact_type") == "repeated_experiment":
        scenario_path = require_relative_file(
            artifact_dir, manifest.get("scenario_copy_file"), "scenario copy"
        )
        if sha256_file(scenario_path) != manifest.get("scenario_sha256"):
            raise ValueError("Packaged scenario does not match scenario_sha256")
        require_relative_file(artifact_dir, "aggregate_summary.json", "aggregate summary")
        require_relative_file(artifact_dir, "README.md", "README")
        nested_manifests = sorted(
            path
            for path in artifact_dir.rglob("manifest.json")
            if path != manifest_path
        )
        nested_results = [verify_artifact(path.parent) for path in nested_manifests]
        if len(nested_results) != manifest.get("repeat_count"):
            raise ValueError(
                f"Expected {manifest.get('repeat_count')} nested runs, found {len(nested_results)}"
            )
        return {
            "status": "ok",
            "artifact_dir": str(artifact_dir),
            "artifact_type": "repeated_experiment",
            "scenario": Path(str(manifest.get("scenario"))).stem,
            "payload_file_count": len(checksums),
            "verified_run_count": len(nested_results),
        }

    scenario_path = require_relative_file(artifact_dir, manifest.get("scenario_copy_file"), "scenario copy")
    if sha256_file(scenario_path) != manifest.get("scenario_sha256"):
        raise ValueError("Packaged scenario does not match scenario_sha256")
    require_relative_file(artifact_dir, manifest.get("csv_file"), "sample CSV")
    summary_path = require_relative_file(artifact_dir, manifest.get("summary_file"), "summary JSON")
    require_relative_file(artifact_dir, "README.md", "README")

    scenario_type = manifest.get("scenario_type")
    if scenario_type == "directed_parent_switch":
        require_relative_file(
            artifact_dir,
            manifest.get("preferred_parent_event_file"),
            "preferred-parent event CSV",
        )
        if not manifest.get("protocol_timing_complete"):
            raise ValueError("Directed artifact has incomplete protocol timing")

    for key in ("parent_rank_file", "replay_file", "replay_metadata_file"):
        value = manifest.get(key)
        if value is not None:
            require_relative_file(artifact_dir, value, key)
    for value in manifest.get("node_log_files", []):
        require_relative_file(artifact_dir, value, "node log")

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    for key in (
        "result_classification",
        "directed_result_classification",
        "random_seed",
        "protocol_timing_source",
        "protocol_timing_complete",
    ):
        if summary.get(key) != manifest.get(key):
            raise ValueError(f"Summary/manifest mismatch for {key}")
    for key in (
        "preferred_parent_event_file",
        "parent_rank_file",
        "replay_file",
        "replay_metadata_file",
    ):
        value = summary.get(key)
        if value is not None and Path(value).is_absolute():
            raise ValueError(f"Summary field {key} is not artifact-relative")
    if any(Path(value).is_absolute() for value in summary.get("node_log_files", [])):
        raise ValueError("Summary node_log_files contains an absolute path")

    binary_checks = 0
    for node in manifest.get("node_executables", {}).values():
        binary_path = node.get("path")
        expected = node.get("sha256")
        if binary_path and expected and Path(binary_path).is_file():
            binary_checks += 1
            if sha256_file(Path(binary_path)) != expected:
                raise ValueError(f"Executable fingerprint mismatch: {binary_path}")

    return {
        "status": "ok",
        "artifact_dir": str(artifact_dir),
        "run_id": manifest.get("run_id"),
        "scenario": manifest.get("scenario_name"),
        "result_classification": manifest.get("result_classification"),
        "payload_file_count": len(checksums),
        "binary_fingerprints_checked": binary_checks,
    }


def main() -> int:
    args = parse_args()
    try:
        result = verify_artifact(args.artifact_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
