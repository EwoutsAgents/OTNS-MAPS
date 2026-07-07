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
├── results/
│   └── .gitkeep
├── scenarios/
│   └── baseline_mobile_parent_switch.yaml
│   └── calibrated_mobile_parent_switch.yaml
└── scripts/
    ├── run_baseline.py
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

The mobile node is a MED instead of a regular SED. OTNS documents that a regular SED typically does not respond to ping traffic, which makes packet-delivery benchmarking less direct for the first baseline.

The repository now includes two stock benchmark scenarios:

- `scenarios/baseline_mobile_parent_switch.yaml` for the original reference run
- `scenarios/calibrated_mobile_parent_switch.yaml` for a delayed-router variant that tries to induce an observable stock parent change without modifying OpenThread logic

## Run

Real OTNS run:

```bash
python3 scripts/run_baseline.py
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

Analyze a repeated-run experiment directory:

```bash
python3 analysis/analyze_baseline.py results/repeated/<experiment-name>
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
- Confirm CSV and JSON outputs are created in `results/`
- Confirm parent-switch events are populated when a switch occurs
- Confirm packet-delivery metrics are populated in the CSV
- Confirm outage/connectivity fields are populated in the CSV and summary JSON

## Outputs

Each run writes:

- `results/baseline_run_<timestamp>.csv`
- `results/baseline_summary_<timestamp>.json`

The CSV records parent state over time for the mobile node, movement position, packet-delivery probe results, and any parent-switch events inferred from observed parent state.

Repeated experiments create a subdirectory under `results/repeated/` with one subdirectory per run plus a `repeated_run_manifest.json` file.

Generated benchmark outputs in `results/` remain ignored by default.

## Example real baseline output

A small curated real OTNS artifact is committed under [`examples/real-baseline/`](examples/real-baseline/).

It exists for reproducibility, format validation, and downstream analysis testing. It is not intended to represent a statistically meaningful experiment. Normal benchmark runs should still write fresh local outputs into `results/`.

## Example switch-attempt output

A second curated real OTNS artifact is committed under [`examples/switch-attempt/`](examples/switch-attempt/).

This artifact comes from the calibrated scenario that delays Router B introduction so the mobile node first attaches to Router A before movement begins. It is still a stock OpenThread benchmark, not a mobility-aware algorithm.

## Status

This repository currently establishes the stock-behaviour benchmark harness only. It is intentionally not an implementation of a mobility-aware parent-switching algorithm.
