# Simple Scenario PPS Matrix

This page records the repeated PPS-off/PPS-on matrix for the active simple parent-switch scenarios. These runs use the current widened 5 m/s path, so they should not be mixed with archived earlier simple-geometry results without labeling the geometry difference.

No MAPS policy or OpenThread parent-selection logic is implemented here. PPS-off disables `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`; active PPS-on enables it and sets `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`. This is tuned stock OpenThread, not the upstream/default PPS interval.

## Scenario Geometry

All three active scenarios place Router A at `(250, 300)`, Router B at `(800, 300)`, and move the end device from `(150, 360)` to `(900, 360)`. Router B is still introduced after initial attachment to Router A.

The scenarios assume OTNS `MeterPerUnit = 0.1`, so one coordinate unit is treated as 0.1 m unless the radio parameter is overridden. The 750-coordinate-unit path is 75 m; with 15 seconds of movement, the target speed is 5 m/s. The mobile then dwells at the end for 320 seconds. The active runner sends exactly one 1 Hz ICMP ping from the mobile end device to its currently observed parent when that parent resolves to a known router.

The runner records parent-probe reachability/RTT and, when `--capture-sim-ping-rss` is enabled, attaches simulator-level RSS/LQI to each parent ping. The primary RSS field is `mobile_to_parent_reply_rx_sim_rss_dbm`, the parent reply received at the mobile ED. The RSS source is `otns_model_derived_at_ping`: a fallback derived from the OTNS `MutualInterference` 3GPP indoor radio model at the exact ping source/destination positions and sample time. It is simulator-model RSS tied to ping events, not OpenThread neighbor/parent-table RSS and not scan RSS.

## Artifacts

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260711-214327-experiment/`
- MED PPS on: `results/med_simple_parent_switch_med-pps-on-repeated/20260711-214427-experiment/`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260711-214526-experiment/`
- FED PPS on: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260711-214628-experiment/`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260711-214729-experiment/`
- SED PPS on: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260711-214838-experiment/`

Each repeated artifact contains 10 CSV files, 10 summary JSON files, 10 replay files, 10 replay metadata JSON files, 30 node logs, `aggregate_summary.json`, `repeated_run_manifest.json`, `manifest.json`, `README.md`, and one representative RSS-over-time SVG.

## Aggregate Metrics

| Profile | PPS | Switch rate | Mean switch time (s) | Median switch time (s) | SD switch time (s) | Mean switch x | Mean outage (s) | Median outage (s) | SD outage (s) | Mean PDR | SD PDR | Mean switches | SD switches | Oscillation rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MED | off | 0.7 | 525.428571 | 508.0 | 44.207304 | 900.0 | 11.5 | 12.5 | 6.467869 | 0.990772 | 0.005748 | 0.7 | 0.483046 | 0.0 |
| MED | on-30s | 0.7 | 548.714286 | 508.0 | 111.782101 | 864.285714 | 36.4 | 6.0 | 94.838108 | 0.983375 | 0.035667 | 0.7 | 0.483046 | 0.0 |
| FED | off | 0.2 | 550.0 | 550.0 | 63.63961 | 900.0 | 44.5 | 4.5 | 99.842376 | 0.965682 | 0.069994 | 0.2 | 0.421637 | 0.0 |
| FED | on-30s | 1.0 | 554.4 | 508.0 | 88.680701 | 900.0 | 17.2 | 15.5 | 11.390054 | 0.987879 | 0.003455 | 1.0 | 0.0 | 0.0 |
| SED | off | 0.2 | 560.5 | 560.5 | 74.246212 | 900.0 | 0.4 | 0.0 | 0.966092 | 0.994215 | 0.005373 | 0.2 | 0.421637 | 0.0 |
| SED | on-30s | 0.7 | 507.714286 | 507.0 | 9.810102 | 857.142857 | 0.5 | 0.0 | 0.971825 | 0.983154 | 0.018134 | 0.7 | 0.483046 | 0.0 |

## Parent Probe and Simulator RSS Metrics

![End-dwell simulator RSS comparison](simple_pps_matrix_rss_end_dwell.svg)

| Profile | PPS | Mean parent-probe PDR | Mobile-to-parent end-dwell RSS mean (dBm) | Mobile-to-parent end-dwell RSS SD | Mean sim-RSS match rate |
|---|---|---:|---:|---:|---:|
| MED | off | 0.990772 | -57.351077 | 13.489837 | 1.0 |
| MED | on-30s | 0.983375 | -56.656391 | 13.564856 | 1.0 |
| FED | off | 0.965682 | -70.805094 | 11.035066 | 1.0 |
| FED | on-30s | 0.987879 | -51.783177 | 8.309581 | 1.0 |
| SED | off | 0.994215 | -71.534584 | 10.257388 | 1.0 |
| SED | on-30s | 0.983154 | -56.751624 | 13.493143 | 1.0 |

Representative per-run RSS-over-time plots are stored with each repeated artifact:

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260711-214327-experiment/rss_over_time_run01.svg`
- MED PPS on-30s: `results/med_simple_parent_switch_med-pps-on-repeated/20260711-214427-experiment/rss_over_time_run01.svg`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260711-214526-experiment/rss_over_time_run01.svg`
- FED PPS on-30s: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260711-214628-experiment/rss_over_time_run01.svg`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260711-214729-experiment/rss_over_time_run01.svg`
- SED PPS on-30s: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260711-214838-experiment/rss_over_time_run01.svg`

## Interpretation

With the widened 5 m/s path and the 1 Hz parent probe, most observed switches still happened at the end dwell. MED PPS-on-30s and SED PPS-on-30s also had some switches before the final endpoint, reflected by mean switch x values below `900`.

MED PPS-on-30s and PPS-off each switched in 7 of 10 runs. PPS-on-30s had a lower median outage but a higher mean outage due to one high-outage run.

FED PPS-on-30s switched in 10 of 10 runs while PPS-off switched in 2 of 10. This remains the strongest profile-level PPS effect in the current matrix; PPS-on-30s also reduced mean outage and improved parent-probe delivery.

SED PPS-on-30s switched in 7 of 10 runs while PPS-off switched in 2 of 10. SED packet delivery and parent-probe metrics remain secondary evidence because regular SED ping behavior is not the primary attachment signal; parent-command observation remains primary.

The parent probe generally showed high delivery to the currently observed parent, including during end dwell. In the widened geometry, PPS-off FED/SED end-dwell parent RSS is around `-71 dBm` on average, while PPS-on arms often switch to Router B and show stronger end-dwell parent RSS.

No oscillation was observed in any of the six repeated arms.

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
