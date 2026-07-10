# Simple Scenario PPS Matrix

This page records the repeated PPS-off/PPS-on matrix for the active simple parent-switch scenarios. These runs use the current extended 5 m/s path with closer router spacing and overlapping intended coverage, so they should not be mixed with archived wider-geometry or earlier short-path simple results without labeling the geometry difference.

No MAPS policy or OpenThread parent-selection logic is implemented here. PPS-off disables `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`; active PPS-on enables it and sets `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`. This is tuned stock OpenThread, not the upstream/default PPS interval.

## Scenario Geometry

All three active scenarios place Router A at `(250, 300)`, Router B at `(650, 300)`, and move the end device from `(150, 360)` to `(750, 360)`. Router B is still introduced after initial attachment to Router A.

The scenarios assume OTNS `MeterPerUnit = 0.1`, so one coordinate unit is treated as 0.1 m unless the radio parameter is overridden. The 600-coordinate-unit path is 60 m; with 12 seconds of movement, the target speed is 5 m/s. The mobile then dwells at the end for 320 seconds. Each 1-second sample also sends a mobile-to-current-parent ping when the parent resolves to a known router. That parent probe measures reachability and RTT, not RSSI.

## Artifacts

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260710-210603-experiment/`
- MED PPS on: `results/med_simple_parent_switch_med-pps-on-repeated/20260710-210833-experiment/`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260710-211049-experiment/`
- FED PPS on: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260710-211309-experiment/`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260710-211542-experiment/`
- SED PPS on: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260710-211830-experiment/`

Each repeated artifact contains 10 CSV files, 10 summary JSON files, 10 replay files, 10 replay metadata JSON files, 30 node logs, `aggregate_summary.json`, `repeated_run_manifest.json`, `manifest.json`, `README.md`, and one representative MP4.

## Aggregate Metrics

| Profile | PPS | Switch rate | Mean switch time (s) | Median switch time (s) | SD switch time (s) | Mean switch x | Mean outage (s) | Median outage (s) | SD outage (s) | Mean PDR | SD PDR | Mean switches | SD switches | Oscillation rate | Mean parent-probe PDR | SD parent-probe PDR | Mean parent-probe RTT avg (ms) | SD parent-probe RTT avg (ms) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MED | off | 0.5 | 528.4 | 505 | 54.569222 | 750 | 7.5 | 7.5 | 7.516648 | 0.97222 | 0.070072 | 0.5 | 0.527046 | 0 | 0.994131 | 0.005921 | 20.816775 | 2.198348 |
| MED | on-30s | 0.4 | 507.5 | 508 | 4.795832 | 750 | 2.7 | 1.5 | 4.571652 | 0.997457 | 0.002714 | 0.4 | 0.516398 | 0 | 0.997863 | 0.002927 | 19.171703 | 2.898389 |
| FED | off | 0 | n/a | n/a | n/a | n/a | 1.2 | 0 | 2.097618 | 0.998188 | 0.002118 | 0 | 0 | 0 | 0.998788 | 0.002122 | 21.124595 | 3.485402 |
| FED | on-30s | 0.7 | 562.285714 | 539 | 61.293595 | 750 | 7.1 | 1.5 | 8.987028 | 0.996382 | 0.0043 | 0.7 | 0.483046 | 0 | 0.996244 | 0.004854 | 21.344671 | 3.076248 |
| SED | off | 0.5 | 537.8 | 505 | 53.345103 | 750 | 0.9 | 0.5 | 1.197219 | 0.985725 | 0.02517 | 0.5 | 0.527046 | 0 | 0.974437 | 0.059425 | 61.191555 | 101.853935 |
| SED | on-30s | 0.3 | 500.666667 | 502 | 3.21455 | 750 | 0.2 | 0 | 0.421637 | 0.996682 | 0.003897 | 0.3 | 0.483046 | 0 | 0.995722 | 0.004636 | 31.771296 | 4.821238 |

## Interpretation

With the extended 5 m/s path and the 1 Hz parent probe, all observed switches still happened at x=750 during the end dwell rather than during the 12-second transit. The scenario currently tests eventual sticky-parent release after arrival more than in-transit switching.

MED PPS-on-30s switched in 4 of 10 runs while PPS-off switched in 5 of 10. PPS-on-30s had lower mean outage and higher packet delivery, but did not improve switch-observed rate in this sample.

FED PPS-on-30s switched in 7 of 10 runs while PPS-off switched in 0 of 10. This is the strongest profile-level effect in the current matrix, although PPS-on-30s also had higher mean outage than PPS-off.

SED PPS-on-30s switched in 3 of 10 runs while PPS-off switched in 5 of 10. SED packet delivery and parent-probe metrics remain secondary evidence because regular SED ping behavior is not the primary attachment signal; parent-command observation remains primary.

The parent probe generally showed high delivery to the currently observed parent, including during end dwell. That means the old parent path often remained usable even when the mobile had arrived beyond Router B, which helps explain sticky-parent behavior. The probe is a connectivity/RTT measurement, not RSSI.

No oscillation was observed in any of the six PPS-on-30s repeated arms.

## Commands

The six repeated arms used `scripts/run_repeated_baseline.py` with `--repeat-count 10`, `--capture-replay`, `--copy-results-to-artifact`, `--otns-watch-level trace`, the explicit PPS binaries documented in [`pps_build_variants.md`](pps_build_variants.md); PPS-on binaries use `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`, and these scenario paths:

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
