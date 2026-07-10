# OTNS-MAPS

OTNS-MAPS is a baseline-benchmark workspace for studying stock OpenThread parent switching under mobility in the OpenThread Network Simulator (OTNS).

This repository does not change OpenThread parent-selection logic. The first milestone is a repeatable reference experiment that measures how an unmodified mobile end device behaves while moving from one potential parent toward another.

## Repository layout

```text
OTNS-MAPS/
├── README.md
├── analysis/
│   └── analyze_baseline.py
├── docs/
│   └── benchmark_design.md
├── examples/
│   └── real-baseline/
│       ├── README.md
│       ├── baseline_run_example.csv
│       └── baseline_summary_example.json
│   └── switch-attempt/
│       ├── README.md
│       ├── baseline_run_switch_attempt.csv
│       └── baseline_summary_switch_attempt.json
│   └── sed-baseline/
│       ├── README.md
│       ├── baseline_run_sed_example.csv
│       └── baseline_summary_sed_example.json
├── results/
│   └── .gitkeep
├── scenarios/
│   ├── baseline_mobile_parent_switch.yaml
│   ├── calibrated_mobile_parent_switch.yaml
│   └── sed_mobile_parent_switch.yaml
└── scripts/
    ├── run_baseline.py
    ├── replay_to_mp4.py
    ├── run_repeated_baseline.py
    └── validate_otns_cli.py
```

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install repository dependencies:

```bash
pip install -r requirements.txt
```

Install OTNS locally:

```bash
git clone https://github.com/openthread/ot-ns.git
cd ot-ns
./script/bootstrap
```

Ensure the `otns` executable is on `PATH`. OTNS documents that it is typically installed into `$(go env GOPATH)/bin`:

```bash
export PATH="$(go env GOPATH)/bin:$PATH"
```

If you do not want to expose `otns` on `PATH`, the benchmark runner can use an explicit path:

```bash
python3 scripts/run_baseline.py --otns-command /path/to/otns
```

If OTNS is launched from outside its own checkout, relative node executable paths may not resolve. In that case, also pass the OTNS checkout as the launch working directory:

```bash
python3 scripts/run_baseline.py \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns
```

## Benchmark

The baseline scenario contains:

- Router A
- Router B
- one mobile MED that starts near Router A and moves toward Router B

The benchmark prefers the `MutualInterference` OTNS radio model. If it is unavailable, the runner falls back in this order:

1. `MIDisc`
2. `Ideal_Rssi`
3. `Ideal`

The repository now includes three stock benchmark scenarios:

- `scenarios/baseline_mobile_parent_switch.yaml` for the original reference run
- `scenarios/calibrated_mobile_parent_switch.yaml` for a delayed-router variant that tries to induce an observable stock parent change without modifying OpenThread logic
- `scenarios/sed_mobile_parent_switch.yaml` for a Sleepy End Device variant that treats the `parent` command as the primary attachment observation path

The original baseline and calibrated switch-attempt scenario use a MED because OTNS documents that a regular SED typically does not respond to ping traffic. The SED benchmark is documented separately and marks packet probes as unreliable by design.

The repository also carries a MED-only Periodic Parent Search comparison. PPS is OpenThread's built-in periodic search for a better parent while a child remains attached. This comparison is intentionally stock OpenThread only: `stock-med-pps-off` and `stock-med-pps-on` differ only by the compile-time value of `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE` for the MTD binary used by `add med`. The current/default local MED build is a discovery result, not a third benchmark arm; in this checkout it is classified as equivalent to `stock-med-pps-on`. See [`docs/pps_build_variants.md`](docs/pps_build_variants.md), [`docs/pps_med_comparison.md`](docs/pps_med_comparison.md), and [`docs/pps_med_repeated_comparison.md`](docs/pps_med_repeated_comparison.md).

## Run

Real OTNS run:

```bash
python3 scripts/run_baseline.py
```

Calibrated run with replay capture and tracked results export:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns \
  --otns-watch-level info \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name switch-observed \
  --firmware-variant stock-openthread \
  --openthread-commit <sha> \
  --otns-commit <sha>
```

Calibrated switch-attempt run:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns
```

Local smoke test without OTNS installed:

```bash
python3 scripts/run_baseline.py --mock
```

Analyze one or more result files:

```bash
python3 analysis/analyze_baseline.py results/baseline_run_*.csv
```

Run repeated experiments:

```bash
python3 scripts/run_repeated_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --repeat-count 5 \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns
```

Run repeated experiments with replay capture and tracked results export:

```bash
python3 scripts/run_repeated_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --repeat-count 3 \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name repeated-demo \
  --firmware-variant stock-openthread \
  --openthread-commit <sha> \
  --otns-commit <sha>
```

Analyze a repeated-run experiment directory:

```bash
python3 analysis/analyze_baseline.py results/repeated/<experiment-name>
```

Run the SED scenario:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/sed_mobile_parent_switch.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns
```

Run the calibrated MED PPS comparison after building the two MTD binaries:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --otns-command '/home/ewout/go/bin/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns \
  --otns-watch-level trace \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name med-pps-off \
  --firmware-variant stock-med-pps-off \
  --thread-device-type med \
  --parent-search-config disabled \
  --node-binary-path /home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns/ot-rfsim/build/stock-med-pps-off/bin/ot-cli-mtd
```

Repeat with `--artifact-name med-pps-on`, `--firmware-variant stock-med-pps-on`, `--parent-search-config enabled`, and the PPS-on MTD binary. The tracked artifacts are stored under `results/calibrated_mobile_parent_switch_med-pps-off/` and `results/calibrated_mobile_parent_switch_med-pps-on/`.

Run the repeated calibrated MED PPS comparison with the same explicit binaries and metadata flags, using `--repeat-count 10` and artifact names `med-pps-off-repeated` and `med-pps-on-repeated`. The resulting aggregate comparison is documented in [`docs/pps_med_repeated_comparison.md`](docs/pps_med_repeated_comparison.md), with tracked artifacts under `results/calibrated_mobile_parent_switch_med-pps-off-repeated/` and `results/calibrated_mobile_parent_switch_med-pps-on-repeated/`.

Generate plots when `matplotlib` is installed:

```bash
python3 analysis/analyze_baseline.py results/baseline_run_*.csv --plot-dir results/plots
```

Validate OTNS CLI compatibility:

```bash
python3 scripts/validate_otns_cli.py \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns
```

Render a replay file into an MP4:

```bash
python3 scripts/replay_to_mp4.py \
  results/calibrated_mobile_parent_switch_switch-observed/<run-id>/<run-id>/<captured-file>.replay \
  --replay-speed 4 \
  --cover-full-replay \
  --end-device-y-offset 40 \
  --video-fps 3 \
  --show-log-panel
```

## OTNS setup

The runner expects an `otns` executable on `PATH` by default. Official install docs:

- <https://github.com/openthread/ot-ns/blob/main/GUIDE.md>
- <https://openthread.io/codelabs/openthread-network-simulator>

If OTNS is installed elsewhere, override the command:

```bash
python3 scripts/run_baseline.py --otns-command /path/to/otns
```

For local OTNS source checkouts, `--otns-workdir /path/to/ot-ns` may also be needed so OTNS can find its bundled `ot-rfsim` node executables.

Compatibility notes for the validated local OTNS CLI behavior are in [`docs/otns_cli_compatibility.md`](docs/otns_cli_compatibility.md).

## Validation checklist

- Run `python3 scripts/run_baseline.py --mock`
- Run `python3 analysis/analyze_baseline.py results/baseline_run_*.csv`
- Confirm a real `otns` launch works from the shell
- Run `python3 scripts/run_baseline.py` against a real OTNS install
- Run `python3 scripts/run_baseline.py --scenario scenarios/calibrated_mobile_parent_switch.yaml --otns-command '/path/to/otns -web=false -autogo=false -speed 1' --otns-workdir /path/to/ot-ns --capture-replay --copy-results-to-artifact --artifact-name switch-observed`
- Confirm CSV and JSON outputs are created in `results/`
- Confirm a replay file and replay metadata JSON are created in `results/replays/`
- Confirm tracked results are copied into `results/<scenario>_<variant>/<run-id>/<run-id>/`
- Confirm parent-switch events are populated when a switch occurs
- Confirm packet-delivery metrics are populated in the CSV
- Confirm outage/connectivity fields are populated in the CSV and summary JSON

## Outputs

Each run writes:

- `results/baseline_run_<timestamp>.csv`
- `results/baseline_summary_<timestamp>.json`

When replay capture is enabled, the runner also writes:

- `results/replays/<scenario_name>_<timestamp>.replay`
- `results/replays/<scenario_name>_<timestamp>.replay.json`

Replay video rendering writes:

- `<replay-file-dir>/<replay-stem>.mp4` by default

The CSV records parent state over time for the mobile node, movement position, packet-delivery probe results, and any parent-switch events inferred from observed parent state.

Repeated experiments create a subdirectory under `results/repeated/` with one subdirectory per run plus a `repeated_run_manifest.json` file.

Generated benchmark outputs in `results/` remain ignored by default.

Curated benchmark evidence can be copied into tracked `results/` directories when `--copy-results-to-artifact` is used. That export includes the CSV, summary JSON, replay file if captured, replay metadata JSON, and a manifest.
If `--otns-watch-level` is enabled for a real OTNS run, the exported run directory also includes one raw `node_log_<name>_<node-id>.log` file per simulated device.

Replay files can be opened with:

```bash
otns-replay results/<scenario>_<variant>/<run-id>/<run-id>/<captured-file>.replay
```

Replay MP4s can be generated with:

```bash
python3 scripts/replay_to_mp4.py \
  results/<scenario>_<variant>/<run-id>/<run-id>/<captured-file>.replay \
  --replay-speed 4 \
  --cover-full-replay \
  --end-device-y-offset 40 \
  --video-fps 3 \
  --show-log-panel
```

`--replay-speed` rewrites the replay into a temporary constant-speed copy before rendering. `--cover-full-replay` then spaces screenshots across that normalized replay so the MP4 covers the full run instead of just the first event burst. `--end-device-y-offset` carries a consistent visual offset for the mobile end device across rendered results. `--show-log-panel` overlays replay-visible OTNS log categories such as node add/delete, movement, role/mode changes, RLOC16 changes, parent updates, partition changes, radio toggles, and router/child table updates.

Replay metadata matters because later firmware comparisons will need to distinguish stock OpenThread runs from modified OpenThread or future MAPS variants.

## Tracked results

The repository now keeps two result paths separate:

- `results/` is scratch space for local ad-hoc runs and stays ignored by Git.
- Nested `results/<scenario>_<variant>/<run-id>/<run-id>/` directories are for curated benchmark evidence that should be committed and shared.

Tracked artifact exports are opt-in. Normal runs behave as before when `--capture-replay` and `--copy-results-to-artifact` are not used.

## Example real baseline output

A small curated real OTNS artifact is committed under [`examples/real-baseline/`](examples/real-baseline/).

It exists for reproducibility, format validation, and downstream analysis testing. It is not intended to represent a statistically meaningful experiment. Normal benchmark runs should still write fresh local outputs into `results/`.

## Example switch-attempt output

A second curated real OTNS artifact is committed under [`examples/switch-attempt/`](examples/switch-attempt/).

This artifact comes from the calibrated scenario that delays Router B introduction so the mobile node first attaches to Router A before movement begins. It is still a stock OpenThread benchmark, not a mobility-aware algorithm.

## Example SED output

A third curated real OTNS artifact is committed under [`examples/sed-baseline/`](examples/sed-baseline/).

It documents a real `sed` run where OTNS parent observation worked through the `parent` command and MLE counters, while ping-based packet probes remained unreliable. It is still stock OpenThread behavior only.

## Status

This repository currently establishes the stock-behaviour benchmark harness only. It is intentionally not an implementation of a mobility-aware parent-switching algorithm.
