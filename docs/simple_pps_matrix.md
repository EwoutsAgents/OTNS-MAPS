# Simple Scenario PPS Matrix

This page records the current repeated PPS-off/PPS-on matrix for the active simple parent-switch scenarios. The current active topology is the extended three-router, static 0 dBm topology.

No MAPS policy or OpenThread parent-selection logic is implemented here. PPS-off disables `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`; active PPS-on enables it and sets `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`. This is tuned stock OpenThread, not the upstream/default PPS interval.

## Scenario Geometry

All three active scenarios place Router A at `(250, 300)`, Router B at `(650, 300)`, Router C at `(1050, 300)`, and move the mobile end device from `(150, 360)` to `(1350, 360)`. Router A and the mobile are created first; Router B and Router C are introduced together after initial attachment to Router A.

Every node is configured to static `0 dBm` transmit power during node initialization with the OpenThread CLI `txpower 0` command. The runner verifies this with `txpower` when the CLI returns a value.

The scenarios assume OTNS `MeterPerUnit = 0.1`, so one coordinate unit is treated as 0.1 m unless the radio parameter is overridden. The 1200-coordinate-unit path is 120 m; with 24 seconds of movement, the target speed is 5 m/s. The mobile then dwells at the end for 320 seconds.

The active runner sends exactly one 1 Hz ICMP ping from the mobile end device to its currently observed parent when that parent resolves to a known router. With `--capture-sim-ping-rss`, the primary RSS field is `mobile_to_parent_reply_rx_sim_rss_dbm`: parent reply RSS at the mobile ED. The RSS source is `otns_model_derived_at_ping`, derived from the OTNS `MutualInterference` model at the exact ping positions and using the configured source TX power.

## Model RSS Check

Model-derived RSS with `0 dBm` TX power:

| Link | RSS (dBm) |
|---|---:|
| Router A -> mobile endpoint | -104.977 |
| Router B -> mobile endpoint | -97.495 |
| Router C -> mobile endpoint | -83.667 |
| Router A -> Router B | -88.126 |
| Router B -> Router C | -88.126 |

Router A is effectively at the requested `-105 dBm` endpoint target, Router C remains materially stronger, and the A-B/B-C router links remain viable in the model.

## Artifacts

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260712-165427-experiment/`
- MED PPS on: `results/med_simple_parent_switch_med-pps-on-repeated/20260712-165537-experiment/`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260712-165645-experiment/`
- FED PPS on: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260712-165754-experiment/`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260712-165903-experiment/`
- SED PPS on: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260712-170023-experiment/`

Each repeated artifact contains 10 CSV files, 10 summary JSON files, 10 replay files, 10 replay metadata JSON files, node logs, `aggregate_summary.json`, `repeated_run_manifest.json`, `manifest.json`, `README.md`, one representative dot RSS-over-time SVG, and one representative MP4 beside the run-01 replay.

## Aggregate Metrics

| Profile | PPS | Switch rate | Mean switches | Max switches | Mean 1st switch (s) | Median 1st switch (s) | Mean switch x | Mean outage (s) | Mean PDR | Mean end-dwell RSS (dBm) | Oscillation rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MED | off | 0.7 | 0.7 | 1 | 514.0 | 516.0 | 1350.0 | 21.0 | 0.984269 | -94.2084 | 0.0 |
| MED | on-30s | 0.9 | 0.9 | 1 | 513.0 | 512.0 | 1350.0 | 18.1 | 0.986111 | -89.9464 | 0.0 |
| FED | off | 0.9 | 0.9 | 1 | 512.333333 | 514.0 | 1305.555556 | 16.7 | 0.988226 | -89.9464 | 0.0 |
| FED | on-30s | 1.0 | 1.1 | 2 | 509.5 | 511.5 | 1205.0 | 14.2 | 0.990074 | -85.236138 | 0.0 |
| SED | off | 0.7 | 0.7 | 1 | 569.285714 | 515.0 | 1350.0 | 1.7 | 0.981992 | -95.443318 | 0.0 |
| SED | on-30s | 0.9 | 0.9 | 1 | 513.777778 | 515.0 | 1350.0 | 33.8 | 0.954993 | -86.739889 | 0.0 |

## Previous Matrix Comparison

The immediately preceding three-router 0 dBm matrix used Router B `(525, 300)`, Router C `(800, 300)`, and endpoint `(900, 360)`. The extended topology moved Router B to `(650, 300)`, Router C to `(1050, 300)`, and endpoint to `(1350, 360)`.

| Profile | PPS | Previous switch rate | Extended switch rate | Previous outage (s) | Extended outage (s) | Previous PDR | Extended PDR |
|---|---|---:|---:|---:|---:|---:|---:|
| MED | off | 0.2 | 0.7 | 4.8 | 21.0 | 0.995761 | 0.984269 |
| MED | on-30s | 0.8 | 0.9 | 11.8 | 18.1 | 0.990791 | 0.986111 |
| FED | off | 0.5 | 0.9 | 7.8 | 16.7 | 0.993595 | 0.988226 |
| FED | on-30s | 1.0 | 1.0 | 10.8 | 14.2 | 0.990742 | 0.990074 |
| SED | off | 0.5 | 0.7 | 0.9 | 1.7 | 0.992058 | 0.981992 |
| SED | on-30s | 0.7 | 0.9 | 0.7 | 33.8 | 0.989569 | 0.954993 |

Using PPS-off switch rate as the failure-driven baseline and `PPS-on - PPS-off` as the PPS-attributable delta:

| Profile | Failure-driven switch rate | PPS-attributable switch-rate delta |
|---|---:|---:|
| MED | 0.7 | 0.2 |
| FED | 0.9 | 0.1 |
| SED | 0.7 | 0.2 |

## Parent Sequences

- MED PPS off: `3x router_a`; `3x router_a -> router_b`; `4x router_a -> router_c`
- MED PPS on-30s: `6x router_a -> router_c`; `3x router_a -> router_b`; `1x router_a`
- FED PPS off: `2x router_b -> router_c`; `1x router_a`; `3x router_a -> router_b`; `4x router_a -> router_c`
- FED PPS on-30s: `8x router_a -> router_c`; `1x router_a -> router_b -> router_c`; `1x router_a -> router_b`
- SED PPS off: `5x router_a -> router_c`; `3x router_a`; `2x router_a -> router_b`
- SED PPS on-30s: `7x router_a -> router_c`; `2x router_a -> router_b`; `1x router_a/unresolved`

## Endpoint Parent Distribution

| Profile | PPS | Router A final | Router B final | Router C final | Unresolved final |
|---|---|---:|---:|---:|---:|
| MED | off | 3 | 3 | 4 | 0 |
| MED | on-30s | 1 | 3 | 6 | 0 |
| FED | off | 1 | 3 | 6 | 0 |
| FED | on-30s | 0 | 1 | 9 | 0 |
| SED | off | 3 | 2 | 5 | 0 |
| SED | on-30s | 0 | 2 | 7 | 1 |

Endpoint RSS by final parent follows the model values: Router A final runs have about `-104.977 dBm`, Router B final runs about `-97.495 dBm`, and Router C final runs about `-83.667 dBm` except where transient final-position samples moved the mean slightly.

## Parent Probe and Simulator RSS Metrics

![End-dwell simulator RSS comparison](simple_pps_matrix_rss_end_dwell.svg)

Representative dot RSS-over-time plots are stored with each repeated artifact:

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260712-165427-experiment/rss_over_time_run01.svg`
- MED PPS on-30s: `results/med_simple_parent_switch_med-pps-on-repeated/20260712-165537-experiment/rss_over_time_run01.svg`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260712-165645-experiment/rss_over_time_run01.svg`
- FED PPS on-30s: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260712-165754-experiment/rss_over_time_run01.svg`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260712-165903-experiment/rss_over_time_run01.svg`
- SED PPS on-30s: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260712-170023-experiment/rss_over_time_run01.svg`

## Interpretation

The extended endpoint substantially increased switch pressure. Router A remained the final parent in only 8 of 60 total runs:

- MED PPS off: 3 of 10
- MED PPS on-30s: 1 of 10
- FED PPS off: 1 of 10
- FED PPS on-30s: 0 of 10
- SED PPS off: 3 of 10
- SED PPS on-30s: 0 of 10, with one unresolved final sample

PPS-on-30s still improves switch rate over PPS-off, but the extended geometry also creates a strong failure-driven switching effect in PPS-off. Most switches still occur at or near endpoint dwell, so the topology increases pressure but does not yet provide a smooth, deterministic A -> B -> C progression during movement.

SED packet delivery and parent-probe metrics remain secondary evidence because regular SED ping behavior is not the primary attachment signal; parent-command observation remains primary.

## Commands

The six repeated arms used `scripts/run_repeated_baseline.py` with `--repeat-count 10`, `--capture-replay`, `--capture-sim-ping-rss`, `--copy-results-to-artifact`, `--otns-watch-level trace`, the explicit PPS binaries documented in [`pps_build_variants.md`](pps_build_variants.md), and these scenario paths:

- `scenarios/med_simple_parent_switch.yaml`
- `scenarios/fed_simple_parent_switch.yaml`
- `scenarios/sed_simple_parent_switch.yaml`

FED runs used `--ftd-node-binary-path`; MED and SED runs used `--node-binary-path`.

## Limitations

- Ten runs per arm is still a small sample.
- Switch timing is still dominated by endpoint dwell in most arms.
- Router B does not consistently appear as an intermediate parent.
- One SED PPS-on run ended with unresolved final parent observation.
- SED packet delivery ratio is not primary evidence.
- FED uses OTNS's FTD executable family for both routers and the mobile FED.
- Simulator RSS is model-derived from OTNS `MutualInterference` at ping event positions because the exported replay/log artifacts do not expose receive RSS/LQI events for direct matching.
