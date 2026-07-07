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
├── results/
│   └── .gitkeep
├── scenarios/
│   └── baseline_mobile_parent_switch.yaml
└── scripts/
    └── run_baseline.py
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

## Run

Real OTNS run:

```bash
python3 scripts/run_baseline.py
```

Local smoke test without OTNS installed:

```bash
python3 scripts/run_baseline.py --mock
```

Analyze one or more result files:

```bash
python3 analysis/analyze_baseline.py results/baseline_run_*.csv
```

## OTNS setup

The runner expects an `otns` executable on `PATH` by default. Official install docs:

- <https://github.com/openthread/ot-ns/blob/main/GUIDE.md>
- <https://openthread.io/codelabs/openthread-network-simulator>

If OTNS is installed elsewhere, override the command:

```bash
python3 scripts/run_baseline.py --otns-command /path/to/otns
```

## Outputs

Each run writes:

- `results/baseline_run_<timestamp>.csv`
- `results/baseline_summary_<timestamp>.json`

The CSV records parent state over time for the mobile node, movement position, packet-delivery probe results, and any parent-switch events inferred from observed parent state.

## Status

This repository currently establishes the stock-behaviour benchmark harness only. It is intentionally not an implementation of a mobility-aware parent-switching algorithm.
