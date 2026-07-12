# Simple Scenario PPS Matrix

This page records the current repeated PPS-off/PPS-on matrix for the active simple parent-switch scenarios. The current active topology is the positive-coordinate, symmetric-offset, three-router, static 0 dBm topology.

No MAPS policy or OpenThread parent-selection logic is implemented here. PPS-off disables `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`; active PPS-on enables it and sets `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`. This is tuned stock OpenThread, not the upstream/default PPS interval.

## Scenario Geometry

All three active scenarios place Router A at `(350, 300)`, Router B at `(750, 300)`, Router C at `(1150, 300)`, and move the mobile end device from `(0, 360)` to `(1500, 360)`. Router A and the mobile are created first; Router B and Router C are introduced together after initial attachment to Router A.

The start/end offsets are symmetric: the mobile starts 350 coordinate units before Router A and ends 350 coordinate units beyond Router C. Every coordinate remains non-negative.

Every node is configured to static `0 dBm` transmit power during node initialization with the OpenThread CLI `txpower 0` command. The runner verifies this with `txpower` when the CLI returns a value.

The scenarios assume OTNS `MeterPerUnit = 0.1`, so one coordinate unit is treated as 0.1 m unless the radio parameter is overridden. The 1500-coordinate-unit path is 150 m; with 30 seconds of movement, the target speed is 5 m/s. The mobile then dwells at the end for 320 seconds.

The active runner sends exactly one 1 Hz ICMP ping from the mobile end device to its currently observed parent when that parent resolves to a known router. With `--capture-sim-ping-rss`, the primary RSS field is `mobile_to_parent_reply_rx_sim_rss_dbm`: parent reply RSS at the mobile ED. The RSS source is `otns_model_derived_at_ping`, derived from the OTNS `MutualInterference` model at the exact ping positions and using the configured source TX power.

## Model RSS Check

Model-derived RSS with `0 dBm` TX power:

| Link | RSS (dBm) |
|---|---:|
| Router A -> mobile endpoint | -105.715 |
| Router B -> mobile endpoint | -98.635 |
| Router C -> mobile endpoint | -86.146 |
| Router A -> Router B | -88.126 |
| Router B -> Router C | -88.126 |

Router A is below the `-105 dBm` endpoint target, Router C remains materially stronger, and the A-B/B-C router links remain viable in the model.

## Artifacts

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260712-191738-experiment/`
- MED PPS on: `results/med_simple_parent_switch_med-pps-on-repeated/20260712-191848-experiment/`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260712-191958-experiment/`
- FED PPS on: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260712-192107-experiment/`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260712-192217-experiment/`
- SED PPS on: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260712-192335-experiment/`

Each repeated artifact contains 10 CSV files, 10 summary JSON files, 10 replay files, 10 replay metadata JSON files, node logs, `aggregate_summary.json`, `repeated_run_manifest.json`, `manifest.json`, `README.md`, one representative dot RSS-over-time SVG, and one representative MP4 beside the run-01 replay.

## Aggregate Metrics

| Profile | PPS | Switch rate | Mean switches | Mean 1st switch (s) | SD 1st switch | Mean switch x | Mean outage (s) | SD outage | Mean PDR | SD PDR | Mean end-dwell RSS (dBm) | Oscillation rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MED | off | 1.0 | 1 | 528.0 | 29.970356 | 1500.0 | 25.7 | 17.340063 | 0.983483 | 0.005233 | -90.464521 | 0.0 |
| MED | on-30s | 0.8 | 0.8 | 520.5 | 2.329929 | 1500.0 | 18.1 | 4.771443 | 0.986348 | 0.003821 | -91.3087 | 0.0 |
| FED | off | 0.7 | 0.7 | 524.714286 | 13.901011 | 1500.0 | 27.5 | 17.989194 | 0.988382 | 0.008028 | -90.798302 | 0.0 |
| FED | on-30s | 1.0 | 1.2 | 526.1 | 16.141389 | 1500.0 | 27.7 | 21.44787 | 0.98481 | 0.005928 | -88.567751 | 0.0 |
| SED | off | 1.0 | 1.1 | 525.3 | 13.191327 | 1500.0 | 4.2 | 4.049691 | 0.981941 | 0.007517 | -90.580529 | 0.0 |
| SED | on-30s | 0.9 | 1 | 551.444444 | 98.510293 | 1500.0 | 2.2 | 1.135292 | 0.937981 | 0.139572 | -94.511253 | 0.0 |

## Previous Matrix Comparison

The immediately preceding three-router 0 dBm matrix used Router A `(250, 300)`, Router B `(650, 300)`, Router C `(1050, 300)`, and endpoint `(1350, 360)`. The current positive symmetric topology shifts the routers right and uses endpoint `(1500, 360)`.

| Profile | PPS | Previous switch rate | Current switch rate | Previous outage (s) | Current outage (s) | Previous PDR | Current PDR |
|---|---|---:|---:|---:|---:|---:|---:|
| MED | off | 0.7 | 1.0 | 21.0 | 25.7 | 0.984269 | 0.983483 |
| MED | on-30s | 0.9 | 0.8 | 18.1 | 18.1 | 0.986111 | 0.986348 |
| FED | off | 0.9 | 0.7 | 16.7 | 27.5 | 0.988226 | 0.988382 |
| FED | on-30s | 1.0 | 1.0 | 14.2 | 27.7 | 0.990074 | 0.98481 |
| SED | off | 0.7 | 1.0 | 1.7 | 4.2 | 0.981992 | 0.981941 |
| SED | on-30s | 0.9 | 0.9 | 33.8 | 2.2 | 0.954993 | 0.937981 |

Using PPS-off switch rate as the failure-driven baseline and `PPS-on - PPS-off` as the PPS-attributable delta:

| Profile | Failure-driven switch rate | PPS-attributable switch-rate delta |
|---|---:|---:|
| MED | 1.0 | -0.2 |
| FED | 0.7 | 0.3 |
| SED | 1.0 | -0.1 |

## Parent Sequences

- MED PPS off: `7x router_a -> router_c`; `3x router_a -> router_b`
- MED PPS on-30s: `7x router_a -> router_c`; `2x router_a`; `1x router_a -> router_b`
- FED PPS off: `6x router_a -> router_c`; `1x router_c`; `1x router_b`; `1x router_a -> router_b`; `1x router_a`
- FED PPS on-30s: `8x router_a -> router_c`; `2x router_a -> router_b -> router_c`
- SED PPS off: `6x router_a -> router_c`; `3x router_a -> router_b`; `1x router_a -> router_b -> router_c`
- SED PPS on-30s: `5x router_a -> router_c`; `3x router_a -> router_b`; `1x router_a`; `1x router_a -> router_c -> router_b`

## Endpoint Parent Distribution

| Profile | PPS | Router A final | Router B final | Router C final | Unresolved final |
|---|---|---:|---:|---:|---:|
| MED | off | 0 | 3 | 7 | 0 |
| MED | on-30s | 2 | 1 | 7 | 0 |
| FED | off | 1 | 2 | 7 | 0 |
| FED | on-30s | 0 | 0 | 10 | 0 |
| SED | off | 0 | 3 | 7 | 0 |
| SED | on-30s | 1 | 4 | 5 | 0 |

Endpoint RSS by final parent follows the model values: Router A final runs have about `-105.715 dBm`, Router B final runs about `-98.635 dBm`, and Router C final runs about `-86.146 dBm` except where transient parent sequences affect the end-dwell mean.

## Parent Probe and Simulator RSS Metrics

![End-dwell simulator RSS comparison](simple_pps_matrix_rss_end_dwell.svg)

Representative dot RSS-over-time plots are stored with each repeated artifact:

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260712-191738-experiment/rss_over_time_run01.svg`
- MED PPS on-30s: `results/med_simple_parent_switch_med-pps-on-repeated/20260712-191848-experiment/rss_over_time_run01.svg`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260712-191958-experiment/rss_over_time_run01.svg`
- FED PPS on-30s: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260712-192107-experiment/rss_over_time_run01.svg`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260712-192217-experiment/rss_over_time_run01.svg`
- SED PPS on-30s: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260712-192335-experiment/rss_over_time_run01.svg`

## Interpretation

The positive symmetric endpoint substantially increases failure-driven switch pressure. Router A remained the final parent in only 4 of 60 total runs:

- MED PPS off: 0 of 10
- MED PPS on-30s: 2 of 10
- FED PPS off: 1 of 10
- FED PPS on-30s: 0 of 10
- SED PPS off: 0 of 10
- SED PPS on-30s: 1 of 10

The current geometry fixes the earlier problem where Router A often remained viable at the endpoint, while preserving a controlled Router A start in the MED diagnostics. It does not make PPS-on uniformly better by switch rate: MED and SED PPS-off now switch in all runs, while PPS-on still has a small number of sticky Router-A-final runs. FED PPS-on is the cleanest arm, with all runs ending at Router C and two runs showing the full `router_a -> router_b -> router_c` progression.

SED packet delivery and parent-probe metrics remain secondary evidence because regular SED ping behavior is not the primary attachment signal; parent-command observation remains primary.

## Commands

The six repeated arms used `scripts/run_repeated_baseline.py` with `--repeat-count 10`, `--capture-replay`, `--capture-sim-ping-rss`, `--copy-results-to-artifact`, `--otns-watch-level trace`, the explicit PPS binaries documented in [`pps_build_variants.md`](pps_build_variants.md), and these scenario paths:

- `scenarios/med_simple_parent_switch.yaml`
- `scenarios/fed_simple_parent_switch.yaml`
- `scenarios/sed_simple_parent_switch.yaml`

FED runs used `--ftd-node-binary-path`; MED and SED runs used `--node-binary-path`.

Representative MP4s were rendered from run 01 of each arm with `--window-size 1600,900`, `--replay-speed 16`, `--cover-full-replay`, `--video-fps 8`, and `--show-log-panel`.

## Limitations

- Ten runs per arm is still a small sample.
- Switch timing is still dominated by endpoint dwell in most arms.
- Router B does not consistently appear as an intermediate parent.
- The FED PPS-off sequence includes runs whose first observed parent was already Router B or Router C; those should be inspected before treating FED off as a clean Router-A-start comparison.
- SED packet delivery ratio is not primary evidence.
- FED uses OTNS's FTD executable family for both routers and the mobile FED.
- Simulator RSS is model-derived from OTNS `MutualInterference` at ping event positions because the exported replay/log artifacts do not expose receive RSS/LQI events for direct matching.
