# Simple Scenario PPS Matrix

This page records the current repeated PPS-off/PPS-on matrix for the active simple parent-switch scenarios. The current active topology is the three-router, static 0 dBm topology.

No MAPS policy or OpenThread parent-selection logic is implemented here. PPS-off disables `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`; active PPS-on enables it and sets `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`. This is tuned stock OpenThread, not the upstream/default PPS interval.

## Scenario Geometry

All three active scenarios place Router A at `(250, 300)`, Router B at `(525, 300)`, Router C at `(800, 300)`, and move the mobile end device from `(150, 360)` to `(900, 360)`. Router A and the mobile are created first; Router B and Router C are introduced together after initial attachment to Router A.

Every node is configured to static `0 dBm` transmit power during node initialization with the OpenThread CLI `txpower 0` command. The runner verifies this with `txpower` when the CLI returns a value.

The scenarios assume OTNS `MeterPerUnit = 0.1`, so one coordinate unit is treated as 0.1 m unless the radio parameter is overridden. The 750-coordinate-unit path is 75 m; with 15 seconds of movement, the target speed is 5 m/s. The mobile then dwells at the end for 320 seconds.

The active runner sends exactly one 1 Hz ICMP ping from the mobile end device to its currently observed parent when that parent resolves to a known router. With `--capture-sim-ping-rss`, the primary RSS field is `mobile_to_parent_reply_rx_sim_rss_dbm`: parent reply RSS at the mobile ED. The RSS source is `otns_model_derived_at_ping`, derived from the OTNS `MutualInterference` model at the exact ping positions and using the configured source TX power. It is simulator-model RSS tied to ping events, not OpenThread neighbor/parent-table RSS and not scan RSS.

## Artifacts

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260712-151919-experiment/`
- MED PPS on: `results/med_simple_parent_switch_med-pps-on-repeated/20260712-152028-experiment/`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260712-152140-experiment/`
- FED PPS on: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260712-152249-experiment/`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260712-152402-experiment/`
- SED PPS on: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260712-152521-experiment/`

Each repeated artifact contains 10 CSV files, 10 summary JSON files, 10 replay files, 10 replay metadata JSON files, node logs, `aggregate_summary.json`, `repeated_run_manifest.json`, `manifest.json`, `README.md`, one representative dot RSS-over-time SVG, and one representative MP4 beside the run-01 replay.

## Aggregate Metrics

| Profile | PPS | Switch rate | Mean switches | Max switches | Mean 1st switch (s) | Median 1st switch (s) | Mean 2nd switch (s) | Mean switch x | Mean 2nd switch x | Mean outage (s) | Mean PDR | Mean end-dwell RSS (dBm) | Oscillation rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MED | off | 0.2 | 0.2 | 1 | 505.5 | 505.5 | NA | 900.0 | NA | 4.8 | 0.995761 | -90.5426 | 0.0 |
| MED | on-30s | 0.8 | 0.8 | 1 | 521.0 | 507.0 | NA | 900.0 | NA | 11.8 | 0.990791 | -84.180567 | 0.0 |
| FED | off | 0.5 | 0.9 | 5 | 504.0 | 505.0 | 788.0 | 900.0 | 900.0 | 7.8 | 0.993595 | -83.766599 | 0.1 |
| FED | on-30s | 1.0 | 1.1 | 2 | 531.3 | 527.5 | 553.0 | 900.0 | 900.0 | 10.8 | 0.990742 | -74.0941 | 0.0 |
| SED | off | 0.5 | 0.5 | 1 | 554.6 | 507.0 | NA | 900.0 | NA | 0.9 | 0.992058 | -90.06491 | 0.0 |
| SED | on-30s | 0.7 | 0.7 | 1 | 508.0 | 506.0 | NA | 900.0 | NA | 0.7 | 0.989569 | -80.425963 | 0.0 |

## Parent Sequences

- MED PPS off: `2x router_a -> router_c`; `8x router_a`
- MED PPS on-30s: `5x router_a -> router_b`; `3x router_a -> router_c`; `2x router_a`
- FED PPS off: `4x router_a -> router_c`; `5x router_a`; `1x router_a -> router_b -> router_c -> router_b -> router_c -> router_b`
- FED PPS on-30s: `6x router_a -> router_c`; `1x router_b -> router_c`; `1x router_a -> router_b -> router_c`; `2x router_a -> router_b`
- SED PPS off: `2x router_a -> router_c`; `5x router_a`; `3x router_a -> router_b`
- SED PPS on-30s: `2x router_a -> router_b`; `3x router_a`; `5x router_a -> router_c`

## Parent Probe and Simulator RSS Metrics

![End-dwell simulator RSS comparison](simple_pps_matrix_rss_end_dwell.svg)

| Profile | PPS | Mean parent-probe PDR | Mean RTT avg (ms) | End-dwell RSS mean (dBm) | End-dwell RSS SD | Mean sim-RSS match rate |
|---|---|---:|---:|---:|---:|---:|
| MED | off | 0.995761 | 6.803332 | -90.5426 | 12.078636 | 1.0 |
| MED | on-30s | 0.990791 | 7.80808 | -84.180567 | 10.092421 | 1.0 |
| FED | off | 0.993595 | 7.0724 | -83.766599 | 14.252833 | 1.0 |
| FED | on-30s | 0.990742 | 7.162452 | -74.0941 | 7.288241 | 1.0 |
| SED | off | 0.992058 | 9.770362 | -90.06491 | 8.94289 | 1.0 |
| SED | on-30s | 0.989569 | 9.894722 | -80.425963 | 13.331997 | 1.0 |

Representative dot RSS-over-time plots are stored with each repeated artifact:

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260712-151919-experiment/rss_over_time_run01.svg`
- MED PPS on-30s: `results/med_simple_parent_switch_med-pps-on-repeated/20260712-152028-experiment/rss_over_time_run01.svg`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260712-152140-experiment/rss_over_time_run01.svg`
- FED PPS on-30s: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260712-152249-experiment/rss_over_time_run01.svg`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260712-152402-experiment/rss_over_time_run01.svg`
- SED PPS on-30s: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260712-152521-experiment/rss_over_time_run01.svg`

## Interpretation

Under the three-router, 0 dBm topology, most switches still occur only after the mobile reaches the endpoint and dwells at `x=900`. This means the current geometry increases switch pressure, but it still does not reliably produce a clean spatial A -> B -> C progression during movement.

PPS-on-30s increased switch-observed rate for all three profiles:

- MED: PPS off `0.2`, PPS on-30s `0.8`
- FED: PPS off `0.5`, PPS on-30s `1.0`
- SED: PPS off `0.5`, PPS on-30s `0.7`

Router B is selected in some runs, but many runs jump directly from Router A to Router C, and one FED PPS-off run oscillated between Router B and Router C during end dwell. A clean A -> B -> C trajectory is therefore not yet stable enough to treat as a controlled three-parent progression.

SED packet delivery and parent-probe metrics remain secondary evidence because regular SED ping behavior is not the primary attachment signal; parent-command observation remains primary.

## Commands

The six repeated arms used `scripts/run_repeated_baseline.py` with `--repeat-count 10`, `--capture-replay`, `--capture-sim-ping-rss`, `--copy-results-to-artifact`, `--otns-watch-level trace`, the explicit PPS binaries documented in [`pps_build_variants.md`](pps_build_variants.md), and these scenario paths:

- `scenarios/med_simple_parent_switch.yaml`
- `scenarios/fed_simple_parent_switch.yaml`
- `scenarios/sed_simple_parent_switch.yaml`

FED runs used `--ftd-node-binary-path`; MED and SED runs used `--node-binary-path`.

## Limitations

- Ten runs per arm is still a small sample.
- Switch timing is dominated by endpoint dwell in this topology.
- Router B does not consistently appear as an intermediate parent.
- SED packet delivery ratio is not primary evidence.
- FED uses OTNS's FTD executable family for both routers and the mobile FED.
- Simulator RSS is model-derived from OTNS `MutualInterference` at ping event positions because the exported replay/log artifacts do not expose receive RSS/LQI events for direct matching.
- The active RSS signal for comparison is reply-side RSS at the ED; it is recorded only when the parent ping reply is observed.
