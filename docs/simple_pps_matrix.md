# Simple Scenario PPS Matrix

This page records the repeated PPS-off/PPS-on matrix for the active simple parent-switch scenarios. These runs use the current extended 5 m/s path with closer router spacing and overlapping intended coverage, so they should not be mixed with archived wider-geometry or earlier short-path simple results without labeling the geometry difference.

No MAPS policy or OpenThread parent-selection logic is implemented here. The only intended stock OpenThread difference is `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`.

## Scenario Geometry

All three active scenarios place Router A at `(250, 300)`, Router B at `(650, 300)`, and move the end device from `(150, 360)` to `(750, 360)`. Router B is still introduced after initial attachment to Router A.

The scenarios assume OTNS `MeterPerUnit = 0.1`, so one coordinate unit is treated as 0.1 m unless the radio parameter is overridden. The 600-coordinate-unit path is 60 m; with 12 seconds of movement, the target speed is 5 m/s. The mobile then dwells at the end for 320 seconds.

## Artifacts

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260710-190523-experiment/`
- MED PPS on: `results/med_simple_parent_switch_med-pps-on-repeated/20260710-190719-experiment/`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260710-190908-experiment/`
- FED PPS on: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260710-191055-experiment/`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260710-191237-experiment/`
- SED PPS on: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260710-191322-experiment/`

Each repeated artifact contains 10 CSV files, 10 summary JSON files, 10 replay files, 10 replay metadata JSON files, 30 node logs, `aggregate_summary.json`, `repeated_run_manifest.json`, `manifest.json`, `README.md`, and one representative MP4.

## Aggregate Metrics

| Profile | PPS | Switch rate | Mean switch time (s) | Median switch time (s) | SD switch time (s) | Mean switch x | Median switch x | SD switch x | Mean outage (s) | Median outage (s) | SD outage (s) | Mean PDR | Median PDR | SD PDR | Mean switches | SD switches | Oscillation rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MED | off | 0.2 | 615 | 615 | 149.906638 | 750 | 750 | 0 | 42.6 | 3 | 85.804947 | 0.933253 | 0.997719 | 0.14084 | 0.2 | 0.421637 | 0 |
| MED | on | 1 | 559.2 | 562 | 4.685676 | 750 | 750 | 0 | 1 | 0 | 1.414214 | 0.999097 | 1 | 0.002032 | 1 | 0 | 0 |
| FED | off | 0.1 | 525 | 525 | 0 | 750 | 750 | 0 | 4 | 1.5 | 8.563488 | 0.995907 | 0.99849 | 0.007918 | 0.1 | 0.316228 | 0 |
| FED | on | 0.4 | 596.25 | 556 | 85.234481 | 750 | 750 | 0 | 14.1 | 0 | 37.41791 | 0.984679 | 1 | 0.044367 | 0.4 | 0.516398 | 0 |
| SED | off | 0.1 | 583 | 583 | 0 | 750 | 750 | 0 | 0.3 | 0 | 0.948683 | 0.017056 | 0.02036 | 0.005504 | 0.1 | 0.316228 | 0 |
| SED | on | 0.8 | 559.75 | 556.5 | 9.866972 | 750 | 750 | 0 | 0.2 | 0 | 0.421637 | 0.00993 | 0.01087 | 0.005619 | 0.8 | 0.421637 | 0 |

## Interpretation

With the extended 5 m/s path, all observed switches happened at x=750 during the end dwell rather than during the 12-second transit. This makes the current scenario useful for exposing whether stock OpenThread eventually leaves a sticky parent after the mobile has moved beyond Router B, but it does not yet show in-transit switching.

MED PPS-on switched in all 10 runs while PPS-off switched in 2 of 10. PPS-on also had earlier mean switch timing, near-zero outage, and slightly higher packet delivery ratio.

FED PPS-on switched in 4 of 10 runs while PPS-off switched in 1 of 10. FED PPS-on did not improve outage or PDR in this 10-run sample, and the switch-time sample sizes remain small.

SED PPS-on switched in 8 of 10 runs while PPS-off switched in 1 of 10. SED packet delivery ratio remains non-primary evidence because regular SED ping probing is unreliable in OTNS; parent-command observation is the main SED signal.

No oscillation was observed in any of the six extended-path repeated arms.

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
