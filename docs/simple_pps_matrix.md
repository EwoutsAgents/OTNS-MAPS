# Simple Scenario PPS Matrix

This page records the repeated PPS-off/PPS-on matrix for the active simple parent-switch scenarios. These runs use the current extended 5 m/s path with closer router spacing and overlapping intended coverage, so they should not be mixed with archived wider-geometry or earlier short-path simple results without labeling the geometry difference.

No MAPS policy or OpenThread parent-selection logic is implemented here. PPS-off disables `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`; active PPS-on enables it and sets `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`. This is tuned stock OpenThread, not the upstream/default PPS interval.

## Scenario Geometry

All three active scenarios place Router A at `(250, 300)`, Router B at `(650, 300)`, and move the end device from `(150, 360)` to `(750, 360)`. Router B is still introduced after initial attachment to Router A.

The scenarios assume OTNS `MeterPerUnit = 0.1`, so one coordinate unit is treated as 0.1 m unless the radio parameter is overridden. The 600-coordinate-unit path is 60 m; with 12 seconds of movement, the target speed is 5 m/s. The mobile then dwells at the end for 320 seconds. Each 1-second sample also sends a mobile-to-current-parent ping when the parent resolves to a known router.

The runner records parent-probe reachability/RTT and, when `--capture-sim-ping-rss` is enabled, attaches simulator-level RSS/LQI to each ping probe. In this pass the RSS source is `otns_model_derived_at_ping`: a fallback derived from the OTNS `MutualInterference` 3GPP indoor radio model at the exact ping source/destination positions and sample time. It is simulator-model RSS tied to ping events, not OpenThread neighbor/parent-table RSS and not scan RSS.

## Artifacts

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260710-225151-experiment/`
- MED PPS on: `results/med_simple_parent_switch_med-pps-on-repeated/20260710-225424-experiment/`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260710-225642-experiment/`
- FED PPS on: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260710-225921-experiment/`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260710-230147-experiment/`
- SED PPS on: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260710-230439-experiment/`

Each repeated artifact contains 10 CSV files, 10 summary JSON files, 10 replay files, 10 replay metadata JSON files, 30 node logs, `aggregate_summary.json`, `repeated_run_manifest.json`, `manifest.json`, `README.md`, and one representative MP4.

## Aggregate Metrics

| Profile | PPS | Switch rate | Mean switch time (s) | Median switch time (s) | SD switch time (s) | Mean switch x | Mean outage (s) | Median outage (s) | SD outage (s) | Mean PDR | SD PDR | Mean switches | SD switches | Oscillation rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MED | off | 0.2 | 503.0 | 503.0 | 0.0 | 750 | 3.9 | 3.0 | 5.300943 | 0.996025 | 0.004601 | 0.2 | 0.421637 | 0 |
| MED | on-30s | 0.4 | 505.0 | 507.5 | 8.524475 | 750 | 2.7 | 1.5 | 4.571652 | 0.997135 | 0.003741 | 0.4 | 0.516398 | 0 |
| FED | off | 0.3 | 604.0 | 589.0 | 107.289328 | 750 | 4.3 | 1.5 | 6.074537 | 0.997833 | 0.003298 | 0.3 | 0.483046 | 0 |
| FED | on-30s | 0.8 | 533.875 | 529.5 | 26.925492 | 750 | 3.6 | 1.5 | 5.440588 | 0.996619 | 0.004932 | 0.8 | 0.421637 | 0 |
| SED | off | 0.5 | 503.4 | 503.0 | 0.894427 | 750 | 0.7 | 0.5 | 0.948683 | 0.994309 | 0.005973 | 0.5 | 0.527046 | 0 |
| SED | on-30s | 0.2 | 503.5 | 503.5 | 0.707107 | 750 | 0.3 | 0.0 | 0.674949 | 0.998165 | 0.002045 | 0.2 | 0.421637 | 0 |

## Parent Probe and Simulator RSS Metrics

| Profile | PPS | Mean parent-probe PDR | Router A end-dwell RSS mean (dBm) | Router A end-dwell RSS SD | Mobile-to-parent end-dwell RSS mean (dBm) | Mobile-to-parent end-dwell RSS SD | Mean sim-RSS match rate |
|---|---|---:|---:|---:|---:|---:|---:|
| MED | off | 0.996318 | -71.957 | 0.0 | -67.242675 | 9.93867 | 0.9998 |
| MED | on-30s | 0.997557 | -71.957 | 0.0 | -62.596338 | 12.090487 | 0.9997 |
| FED | off | 0.997823 | -71.957 | 0.0 | -67.164007 | 8.638489 | 0.999299 |
| FED | on-30s | 0.996315 | -71.957 | 0.0 | -52.582906 | 7.115965 | 0.9998 |
| SED | off | 0.992909 | -71.957 | 0.0 | -60.171666 | 12.422833 | 0.999299 |
| SED | on-30s | 0.997246 | -71.957 | 0.0 | -67.242913 | 9.938167 | 0.9997 |

## Interpretation

With the extended 5 m/s path and the 1 Hz parent probe, all observed switches still happened at x=750 during the end dwell rather than during the 12-second transit. The scenario currently tests eventual sticky-parent release after arrival more than in-transit switching.

MED PPS-on-30s switched in 4 of 10 runs while PPS-off switched in 2 of 10. PPS-on-30s had lower mean outage and slightly higher packet delivery, but the observed switches still occurred at the end dwell.

FED PPS-on-30s switched in 8 of 10 runs while PPS-off switched in 3 of 10. This is the strongest profile-level PPS effect in the current matrix; PPS-on-30s also reduced mean switch time and mean outage.

SED PPS-on-30s switched in 2 of 10 runs while PPS-off switched in 5 of 10. SED packet delivery and parent-probe metrics remain secondary evidence because regular SED ping behavior is not the primary attachment signal; parent-command observation remains primary.

The parent probe generally showed high delivery to the currently observed parent, including during end dwell. The model-derived Router A end-dwell RSS is about `-71.957 dBm` for all profiles because it is determined by the fixed end position `(750, 360)` relative to Router A. This indicates Router A remains physically viable in the simulator model at the dwell position, which helps explain sticky-parent behavior.

No oscillation was observed in any of the six PPS-on-30s repeated arms.

## Commands

The six repeated arms used `scripts/run_repeated_baseline.py` with `--repeat-count 10`, `--capture-replay`, `--capture-sim-ping-rss`, `--copy-results-to-artifact`, `--otns-watch-level trace`, the explicit PPS binaries documented in [`pps_build_variants.md`](pps_build_variants.md); PPS-on binaries use `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`, and these scenario paths:

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
- Simulator RSS is model-derived from OTNS `MutualInterference` at ping event positions because the exported replay/log artifacts do not expose receive RSS/LQI events for direct matching.
- Failed pings still have request-side model-derived RSS; reply-side RSS is recorded only when the ping reply is observed.
