# OTNS-MAPS

OTNS-MAPS is a baseline-benchmark workspace for studying stock OpenThread parent switching under mobility in the OpenThread Network Simulator (OTNS).

This repository does not change OpenThread parent-selection logic. The first milestone is a repeatable reference experiment that measures how an unmodified mobile end device behaves while moving from one potential parent toward another.

## Repository layout

```text
OTNS-MAPS/
├── README.md
├── analysis/
│   └── analyze_baseline.py
├── artifacts/
│   └── .gitkeep
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
    ├── replay_to_gif.py
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

## Run

Real OTNS run:

```bash
python3 scripts/run_baseline.py
```

Calibrated run with replay capture and tracked artifact export:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name calibrated-med-switch-observed \
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

Run repeated experiments with replay capture and tracked artifact export:

```bash
python3 scripts/run_repeated_baseline.py \
  --scenario scenarios/calibrated_mobile_parent_switch.yaml \
  --repeat-count 3 \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns \
  --capture-replay \
  --copy-results-to-artifact \
  --artifact-name calibrated-med-repeated-demo \
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

Render a replay file into a GIF:

```bash
python3 scripts/replay_to_gif.py \
  artifacts/calibrated-med-switch-observed/replay/<captured-file>.replay \
  --output-gif results/gifs/<captured-file>.gif \
  --replay-speed 4 \
  --cover-full-replay \
  --end-device-y-offset 40 \
  --gif-frame-duration-ms 500 \
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
- Run `python3 scripts/run_baseline.py --scenario scenarios/calibrated_mobile_parent_switch.yaml --otns-command '/path/to/otns -web=false -autogo=false -speed 1' --otns-workdir /path/to/ot-ns --capture-replay --copy-results-to-artifact --artifact-name calibrated-med-switch-observed`
- Confirm CSV and JSON outputs are created in `results/`
- Confirm a replay file and replay metadata JSON are created in `results/replays/`
- Confirm tracked artifacts are copied into `artifacts/<artifact-name>/`
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

Replay GIF rendering writes:

- `results/gifs/<replay-stem>.gif` by default

The CSV records parent state over time for the mobile node, movement position, packet-delivery probe results, and any parent-switch events inferred from observed parent state.

Repeated experiments create a subdirectory under `results/repeated/` with one subdirectory per run plus a `repeated_run_manifest.json` file.

Generated benchmark outputs in `results/` remain ignored by default.

Curated benchmark evidence can be copied into tracked `artifacts/` directories when `--copy-results-to-artifact` is used. That export includes the CSV, summary JSON, replay file if captured, replay metadata JSON, and an artifact manifest.

Replay files can be opened with:

```bash
otns-replay artifacts/<artifact-name>/replay/<captured-file>.replay
```

Replay GIFs can be generated with:

```bash
python3 scripts/replay_to_gif.py \
  artifacts/<artifact-name>/replay/<captured-file>.replay \
  --replay-speed 4 \
  --cover-full-replay \
  --end-device-y-offset 40 \
  --gif-frame-duration-ms 500 \
  --show-log-panel
```

`--replay-speed` rewrites the replay into a temporary constant-speed copy before rendering. `--cover-full-replay` then spaces screenshots across that normalized replay so the GIF covers the full run instead of just the first event burst. `--end-device-y-offset` is a visual-only tweak for clearer separation from routers in the replay UI. `--show-log-panel` overlays a readable OTNS-style event panel into the GIF.

Replay metadata matters because later firmware comparisons will need to distinguish stock OpenThread runs from modified OpenThread or future MAPS variants.

## Artifact output

The repository now keeps two result paths separate:

- `results/` is scratch space for local ad-hoc runs and stays ignored by Git.
- `artifacts/` is for curated benchmark evidence that should be committed and shared.

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
