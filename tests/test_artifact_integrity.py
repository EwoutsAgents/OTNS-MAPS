from __future__ import annotations

import json
import os
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

    def test_repeated_command_assigns_requested_listen_port(self) -> None:
        self.assertEqual(
            "otns -web=false -listen localhost:12000",
            run_repeated_baseline.command_with_listen_port("otns -web=false", 12000),
        )
        self.assertEqual(
            "otns -listen localhost:12010 -web=false",
            run_repeated_baseline.command_with_listen_port(
                "otns -listen localhost:9990 -web=false",
                12010,
            ),
        )

    def test_runtime_directory_mirrors_only_static_workdir_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source"
            runtime = root / "runtime"
            source.mkdir()
            (source / "ot-rfsim").mkdir()
            (source / "tmp").mkdir()
            (source / "current.pcap").write_bytes(b"pcap")
            (source / "otns_0.replay").write_text("replay", encoding="utf-8")

            run_repeated_baseline.prepare_otns_runtime_dir(runtime, source)

            self.assertTrue((runtime / "ot-rfsim").is_symlink())
            self.assertFalse((runtime / "tmp").exists())
            self.assertFalse((runtime / "current.pcap").exists())
            self.assertFalse((runtime / "otns_0.replay").exists())

    def test_port_reservation_rejects_overlapping_runner(self) -> None:
        port = 100000 + os.getpid()
        with run_repeated_baseline.reserve_otns_ports([port]):
            with self.assertRaisesRegex(RuntimeError, "already reserved"):
                with run_repeated_baseline.reserve_otns_ports([port]):
                    pass

    def test_run_validation_rejects_another_simulation_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            run_dir = root / "run"
            runtime = run_dir / "otns_runtime"
            (runtime / "tmp").mkdir(parents=True)
            (runtime / "tmp" / "999_1.log").write_text("wrong simulation\n", encoding="utf-8")
            run_baseline.write_json(
                {
                    "firmware_variant": "test",
                    "otns_runtime_dir": str(runtime),
                    "node_log_files": [],
                },
                run_dir / "baseline_summary_test.json",
            )

            validation = run_repeated_baseline.validate_run_outputs(
                run_dir,
                runtime,
                firmware_variant="test",
                simulation_id=100,
                watch_level="off",
            )
            self.assertEqual("failed", validation["status"])
            self.assertIn("another simulation ID", validation["errors"][0])


if __name__ == "__main__":
    unittest.main()
