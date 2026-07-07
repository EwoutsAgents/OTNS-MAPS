# Calibrated switch-attempt artifact

This directory contains a representative real OTNS run from the calibrated stock benchmark scenario.

## Run metadata

- Date: 2026-07-07 UTC
- Scenario: `calibrated_mobile_parent_switch`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1 -listen localhost:9980`
- OTNS workdir used: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- Selected radio model: `MutualInterference`
- Initial observed parent: `router_a`
- Final observed parent: `router_b`
- Result classification: `switch_observed`

## Files

- `baseline_run_switch_attempt.csv`
- `baseline_summary_switch_attempt.json`

## Purpose

This committed example exists to show a calibrated stock OpenThread run where a parent change was observed under mobility without modifying OpenThread parent-selection logic.

It is still a single representative run, not a statistically meaningful experiment.

## Observed behavior

- Router B was introduced after the mobile node had already attached to Router A.
- Movement then pushed the mobile node toward Router B.
- A stock parent switch from `router_a` to `router_b` was observed at simulation time `960.0 s`.

## Known limitations

- This calibrated scenario is not perfectly deterministic across repeated executions. Some runs still stay on `router_a` for the full path.
- Live scan-derived candidate-parent RSSI and LQI fields are still empty in the benchmark CSV.
- This run is a stock OpenThread benchmark only. No new parent-selection algorithm was added.

## Analysis validation

The example can be summarized with:

```bash
python3 analysis/analyze_baseline.py examples/switch-attempt/baseline_run_switch_attempt.csv
```
