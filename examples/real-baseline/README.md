# Real baseline example artifact

This directory contains one representative real OTNS baseline artifact copied from a live run of the stock benchmark harness.

## Run metadata

- Date: 2026-07-07 UTC
- Scenario: `baseline_mobile_parent_switch`
- OTNS command: `/home/ewout/go/bin/otns -web=false -autogo=false -speed 1`
- OTNS workdir used: `/home/ewout/.openclaw/workspace-softwaredeveloper/ot-ns`
- Selected radio model: `MutualInterference`

## Files

- `baseline_run_example.csv`
- `baseline_summary_example.json`

## Purpose

This committed example exists for format validation, reproducibility checks, and downstream analysis testing.

It is not a statistically meaningful experiment and should not be treated as a final research result.

## Known limitations

- This representative run recorded no parent switch events.
- The mobile node remained attached to a single observed parent for the full path.
- Live scan-derived candidate-parent RSSI and LQI fields are empty because `scan` did not behave synchronously through the OTNS CLI session used by the runner in this setup.
- This run is a stock OpenThread baseline only. No mobility-aware parent-selection changes were applied.

## Analysis validation

The example can be summarized with:

```bash
python3 analysis/analyze_baseline.py examples/real-baseline/baseline_run_example.csv
```
