from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import run_baseline
from scripts import run_repeated_baseline
from scripts import verify_artifact


class ArtifactIntegrityTests(unittest.TestCase):
    def create_directed_artifact(self, root: Path) -> Path:
        artifact = root / "artifact"
        artifact.mkdir()
        (artifact / "README.md").write_text("# Test\n", encoding="utf-8")
        (artifact / "scenario.yaml").write_text("name: test\n", encoding="utf-8")
        (artifact / "samples.csv").write_text("sample_index\n0\n", encoding="utf-8")
        (artifact / "events.csv").write_text("event\nrequested\n", encoding="utf-8")
        summary = {
            "result_classification": "selected_target_reached",
            "directed_result_classification": "selected_target_reached",
            "random_seed": 42,
            "protocol_timing_source": "otns_openthread_event",
            "protocol_timing_complete": True,
            "preferred_parent_event_file": "events.csv",
            "parent_rank_file": None,
            "replay_file": None,
            "replay_metadata_file": None,
            "node_log_files": [],
        }
        run_baseline.write_json(summary, artifact / "summary.json")
        manifest = {
            "artifact_schema_version": 1,
            "run_id": "test-run",
            "scenario_name": "test",
            "scenario_type": "directed_parent_switch",
            "scenario_copy_file": "scenario.yaml",
            "scenario_sha256": run_baseline.sha256_file(artifact / "scenario.yaml"),
            "csv_file": "samples.csv",
            "summary_file": "summary.json",
            "preferred_parent_event_file": "events.csv",
            "parent_rank_file": None,
            "replay_file": None,
            "replay_metadata_file": None,
            "node_log_files": [],
            "result_classification": "selected_target_reached",
            "directed_result_classification": "selected_target_reached",
            "random_seed": 42,
            "protocol_timing_source": "otns_openthread_event",
            "protocol_timing_complete": True,
            "node_executables": {},
        }
        run_baseline.write_json(manifest, artifact / "manifest.json")
        run_baseline.write_artifact_checksums(artifact)
        return artifact

    def test_valid_directed_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            artifact = self.create_directed_artifact(Path(temporary_directory))
            result = verify_artifact.verify_artifact(artifact)
            self.assertEqual("ok", result["status"])
            self.assertEqual(6, result["payload_file_count"])

    def test_tampered_payload_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            artifact = self.create_directed_artifact(Path(temporary_directory))
            (artifact / "events.csv").write_text("event\ntampered\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Checksum mismatch"):
                verify_artifact.verify_artifact(artifact)

    def test_absolute_summary_reference_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            artifact = self.create_directed_artifact(Path(temporary_directory))
            summary_path = artifact / "summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["preferred_parent_event_file"] = "/tmp/events.csv"
            run_baseline.write_json(summary, summary_path)
            run_baseline.write_artifact_checksums(artifact)
            with self.assertRaisesRegex(ValueError, "not artifact-relative"):
                verify_artifact.verify_artifact(artifact)

    def test_repeated_command_adds_explicit_seed(self) -> None:
        command = run_repeated_baseline.command_with_seed("otns -web=false", 3201)
        self.assertEqual("otns -web=false -seed 3201", command)
        with self.assertRaisesRegex(ValueError, "cannot be combined"):
            run_repeated_baseline.command_with_seed("otns -seed 1", 3201)


if __name__ == "__main__":
    unittest.main()
