# Simple Scenario PPS Matrix

This page records the repeated PPS-off/PPS-on matrix for the active simple parent-switch scenarios. These runs use the current extended 5 m/s path with closer router spacing and overlapping intended coverage, so they should not be mixed with archived wider-geometry or earlier short-path simple results without labeling the geometry difference.

No MAPS policy or OpenThread parent-selection logic is implemented here. PPS-off disables `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`; active PPS-on enables it and sets `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`. This is tuned stock OpenThread, not the upstream/default PPS interval.

## Scenario Geometry

All three active scenarios place Router A at `(250, 300)`, Router B at `(650, 300)`, and move the end device from `(150, 360)` to `(750, 360)`. Router B is still introduced after initial attachment to Router A.

The scenarios assume OTNS `MeterPerUnit = 0.1`, so one coordinate unit is treated as 0.1 m unless the radio parameter is overridden. The 600-coordinate-unit path is 60 m; with 12 seconds of movement, the target speed is 5 m/s. The mobile then dwells at the end for 320 seconds. The active runner sends exactly one 1 Hz ICMP ping from the mobile end device to its currently observed parent when that parent resolves to a known router.

The runner records parent-probe reachability/RTT and, when `--capture-sim-ping-rss` is enabled, attaches simulator-level RSS/LQI to each parent ping. The primary RSS field is `mobile_to_parent_reply_rx_sim_rss_dbm`, the parent reply received at the mobile ED. The RSS source is `otns_model_derived_at_ping`: a fallback derived from the OTNS `MutualInterference` 3GPP indoor radio model at the exact ping source/destination positions and sample time. It is simulator-model RSS tied to ping events, not OpenThread neighbor/parent-table RSS and not scan RSS.

## Artifacts

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260711-131259-experiment/`
- MED PPS on: `results/med_simple_parent_switch_med-pps-on-repeated/20260711-131359-experiment/`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260711-131501-experiment/`
- FED PPS on: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260711-131605-experiment/`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260711-131707-experiment/`
- SED PPS on: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260711-131818-experiment/`

Each repeated artifact contains 10 CSV files, 10 summary JSON files, 10 replay files, 10 replay metadata JSON files, 30 node logs, `aggregate_summary.json`, `repeated_run_manifest.json`, `manifest.json`, `README.md`, and one representative RSS-over-time SVG.

## Aggregate Metrics

| Profile | PPS | Switch rate | Mean switch time (s) | Median switch time (s) | SD switch time (s) | Mean switch x | Mean outage (s) | Median outage (s) | SD outage (s) | Mean PDR | SD PDR | Mean switches | SD switches | Oscillation rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MED | off | 0.4 | 538.5 | 503.0 | 71.0 | 750 | 4.8 | 0.0 | 6.196773 | 0.995687 | 0.005661 | 0.4 | 0.516398 | 0 |
| MED | on-30s | 0.2 | 511.5 | 511.5 | 10.606602 | 750 | 2.7 | 3.0 | 3.591657 | 0.997866 | 0.002919 | 0.2 | 0.421637 | 0 |
| FED | off | 0.2 | 515.0 | 515.0 | 14.142136 | 750 | 5.7 | 0.0 | 9.031427 | 0.995608 | 0.006863 | 0.2 | 0.421637 | 0 |
| FED | on-30s | 0.9 | 533.111111 | 528.0 | 28.802971 | 750 | 2.6 | 0.0 | 4.788876 | 0.998158 | 0.003891 | 0.9 | 0.316228 | 0 |
| SED | off | 0.2 | 554.0 | 554.0 | 72.124892 | 750 | 0.2 | 0.0 | 0.421637 | 0.994009 | 0.011348 | 0.2 | 0.421637 | 0 |
| SED | on-30s | 0.1 | 503.0 | 503.0 | 0.0 | 750 | 0.1 | 0.0 | 0.316228 | 0.985968 | 0.033851 | 0.1 | 0.316228 | 0 |

## Parent Probe and Simulator RSS Metrics

![End-dwell simulator RSS comparison](simple_pps_matrix_rss_end_dwell.svg)

| Profile | PPS | Mean parent-probe PDR | Mobile-to-parent end-dwell RSS mean (dBm) | Mobile-to-parent end-dwell RSS SD | Mean sim-RSS match rate |
|---|---|---:|---:|---:|---:|
| MED | off | 0.995687 | -63.34237 | 11.580398 | 1.0 |
| MED | on-30s | 0.997866 | -67.28129 | 9.867504 | 1.0 |
| FED | off | 0.995608 | -67.156362 | 10.12182 | 1.0 |
| FED | on-30s | 0.998158 | -52.696062 | 7.141677 | 1.0 |
| SED | off | 0.994009 | -67.774937 | 8.962897 | 1.0 |
| SED | on-30s | 0.985968 | -69.5238 | 7.694454 | 1.0 |

Representative per-run RSS-over-time plots are stored with each repeated artifact:

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260711-131259-experiment/rss_over_time_run01.svg`
- MED PPS on-30s: `results/med_simple_parent_switch_med-pps-on-repeated/20260711-131359-experiment/rss_over_time_run01.svg`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260711-131501-experiment/rss_over_time_run01.svg`
- FED PPS on-30s: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260711-131605-experiment/rss_over_time_run01.svg`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260711-131707-experiment/rss_over_time_run01.svg`
- SED PPS on-30s: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260711-131818-experiment/rss_over_time_run01.svg`

## Interpretation

With the extended 5 m/s path and the 1 Hz parent probe, all observed switches still happened at x=750 during the end dwell rather than during the 12-second transit. The scenario currently tests eventual sticky-parent release after arrival more than in-transit switching.

MED PPS-on-30s switched in 2 of 10 runs while PPS-off switched in 4 of 10. PPS-on-30s had lower mean outage and slightly higher packet delivery, but the observed switches still occurred at the end dwell.

FED PPS-on-30s switched in 9 of 10 runs while PPS-off switched in 2 of 10. This is the strongest profile-level PPS effect in the current matrix; PPS-on-30s also reduced mean outage and improved parent-probe delivery.

SED PPS-on-30s switched in 1 of 10 runs while PPS-off switched in 2 of 10. SED packet delivery and parent-probe metrics remain secondary evidence because regular SED ping behavior is not the primary attachment signal; parent-command observation remains primary.

The parent probe generally showed high delivery to the currently observed parent, including during end dwell. Where the ED remains parented to Router A at the dwell position, the model-derived reply RSS at the ED is around `-71.957 dBm`, indicating Router A remains physically viable in the simulator model at the dwell position. This helps explain sticky-parent behavior.

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
- The active RSS signal for comparison is reply-side RSS at the ED; it is recorded only when the parent ping reply is observed.
