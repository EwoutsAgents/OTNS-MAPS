# Simple Scenario PPS Matrix

This page records the repeated PPS-off/PPS-on matrix for the active simple parent-switch scenarios. These runs use closer router spacing and overlapping intended coverage, so they should not be mixed with archived wider-geometry results without labeling the geometry difference.

No MAPS policy or OpenThread parent-selection logic is implemented here. The only intended stock OpenThread difference is `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`.

## Scenario Geometry

All three active scenarios place Router A at `(250, 300)`, Router B at `(650, 300)`, and move the end device from `(250, 360)` to `(650, 360)`. Router B is still introduced after initial attachment to Router A.

## Artifacts

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260710-174353-experiment/`
- MED PPS on: `results/med_simple_parent_switch_med-pps-on-repeated/20260710-174436-experiment/`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260710-174519-experiment/`
- FED PPS on: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260710-174558-experiment/`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260710-174639-experiment/`
- SED PPS on: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260710-174719-experiment/`

Each repeated artifact contains 10 CSV files, 10 summary JSON files, 10 replay files, 10 replay metadata JSON files, 30 node logs, `aggregate_summary.json`, `repeated_run_manifest.json`, `manifest.json`, `README.md`, and one representative MP4.

## Aggregate Metrics

| Profile | PPS | Switch rate | Mean switch time (s) | Median switch time (s) | SD switch time (s) | Mean switch x | Median switch x | SD switch x | Mean outage (s) | Median outage (s) | SD outage (s) | Mean PDR | Median PDR | SD PDR | Mean switches | SD switches | Oscillation rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MED | off | 0.2 | 1320.0 | 1320.0 | 169.705627 | 629.487 | 629.487 | 29.009763 | 56.0 | 0.0 | 79.888812 | 0.9375 | 1.0 | 0.090545 | 0.2 | 0.421637 | 0.0 |
| MED | on | 0.9 | 1113.333333 | 1120.0 | 10.0 | 564.53 | 567.949 | 5.1285 | 0.0 | 0.0 | 0.0 | 0.996875 | 1.0 | 0.009882 | 0.9 | 0.316228 | 0.0 |
| FED | off | 0.1 | 960.0 | 960.0 | 0.0 | 485.897 | 485.897 | 0.0 | 4.0 | 0.0 | 12.649111 | 0.929167 | 1.0 | 0.159632 | 0.1 | 0.316228 | 0.0 |
| FED | on | 0.5 | 1112.0 | 1120.0 | 10.954451 | 563.8462 | 567.949 | 5.61799 | 16.0 | 0.0 | 29.514591 | 0.922917 | 0.994792 | 0.157227 | 0.5 | 0.527046 | 0.0 |
| SED | off | 0.1 | 1560.0 | 1560.0 | 0.0 | 604.286 | 604.286 | 0.0 | 0.0 | 0.0 | 0.0 | 0.006818 | 0.0 | 0.010978 | 0.1 | 0.316228 | 0.0 |
| SED | on | 0.9 | 1343.333333 | 1320.0 | 238.012605 | 521.746111 | 512.857 | 90.67143 | 3.0 | 0.0 | 9.486833 | 0.010227 | 0.005682 | 0.0113 | 0.9 | 0.316228 | 0.0 |

## Interpretation

With the closer simple geometry, MED PPS-on switched in 9 of 10 runs while PPS-off switched in 2 of 10. PPS-on also switched earlier by mean timing and position, eliminated inferred outage in this sample, and had a slightly higher packet delivery ratio.

FED PPS-on switched in 5 of 10 runs while PPS-off switched in 1 of 10. In switch-observed runs, PPS-off switched earlier, but the sample size is only one switch-observed PPS-off run. FED packet delivery remained high for both variants.

SED PPS-on switched in 9 of 10 runs while PPS-off switched in 1 of 10. SED packet delivery ratio remains non-primary evidence because regular SED ping probing is unreliable in OTNS; parent-command observation is the main SED signal.

No oscillation was observed in any of the six simple-scenario repeated arms.

## Commands

The six repeated arms used `scripts/run_repeated_baseline.py` with `--repeat-count 10`, `--capture-replay`, `--copy-results-to-artifact`, `--otns-watch-level trace`, the explicit PPS binaries documented in [`pps_build_variants.md`](pps_build_variants.md), and these scenario paths:

- `scenarios/med_simple_parent_switch.yaml`
- `scenarios/fed_simple_parent_switch.yaml`
- `scenarios/sed_simple_parent_switch.yaml`

FED runs used `--ftd-node-binary-path`; MED and SED runs used `--node-binary-path`.

## Limitations

- Ten runs per arm is still a small sample.
- The simple geometry is intentionally different from archived wide-geometry artifacts.
- SED packet delivery ratio is not primary evidence.
- FED uses OTNS's FTD executable family for both routers and the mobile FED.
- Replay MP4s are visual evidence; CSV and JSON summaries are the metric sources.
