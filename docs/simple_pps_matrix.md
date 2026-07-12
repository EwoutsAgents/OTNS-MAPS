# Simple Scenario PPS Matrix

This page records the current repeated PPS-off/PPS-on matrix for the active
simple parent-switch scenarios. The current topology is a three-router, static
0 dBm topology with an explicit initial-attachment gate.

No MAPS policy or OpenThread parent-selection logic is implemented here.
PPS-off disables `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`; active PPS-on enables
it and sets `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`. This is tuned
stock OpenThread, not the upstream/default PPS interval.

## Scenario Geometry

All three active scenarios place Router A at `(350, 300)`, Router B at
`(750, 300)`, Router C at `(1150, 300)`, and create the mobile end device at
`(350, 360)`, close to Router A. Router A and the mobile are created first. The
runner waits until the mobile is observed parented to Router A, then introduces
Router B and Router C, settles, and starts movement from `(350, 360)` to
`(1600, 360)`.

The start/end offsets are intentionally no longer symmetric. The left-side
offset was removed because it made initial Router A attachment unreliable as the
right endpoint was pushed farther away. This version keeps the initial
attachment controlled while still putting Router A under endpoint pressure.

Every node is configured to static `0 dBm` transmit power during node
initialization with the OpenThread CLI `txpower 0` command. The runner verifies
this with `txpower` when the CLI returns a value.

The scenarios assume OTNS `MeterPerUnit = 0.1`, so one coordinate unit is
treated as 0.1 m unless the radio parameter is overridden. The movement path is
1250 coordinate units, which is 125 m. With 25 one-second movement steps, the
target speed is 5 m/s. The mobile then dwells at the end for 320 seconds.

The active runner sends exactly one 1 Hz ICMP ping from the mobile end device
to its currently observed parent when that parent resolves to a known router.
With `--capture-sim-ping-rss`, the primary RSS field is
`mobile_to_parent_reply_rx_sim_rss_dbm`: parent reply RSS at the mobile ED. The
RSS source is `otns_model_derived_at_ping`, derived from the OTNS
`MutualInterference` model at the exact ping positions and using the configured
source TX power.

## Model RSS Check

Model-derived RSS with `0 dBm` TX power:

| Link | RSS (dBm) |
|---|---:|
| Router A -> mobile endpoint | -107.098 |
| Router B -> mobile endpoint | -100.705 |
| Router C -> mobile endpoint | -90.232 |
| Router A -> Router B | -88.126 |
| Router B -> Router C | -88.126 |

Router A is weaker than the previous endpoint condition, Router C remains
materially stronger than Router A, and the A-B/B-C router links remain viable
in the model.

## Artifacts

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260712-210435-experiment/`
- MED PPS on: `results/med_simple_parent_switch_med-pps-on-repeated/20260712-210540-experiment/`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260712-210653-experiment/`
- FED PPS on: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260712-210803-experiment/`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260712-210917-experiment/`
- SED PPS on: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260712-211036-experiment/`

Each repeated artifact contains 10 CSV files, 10 summary JSON files, 10 replay
files, 10 replay metadata JSON files, node logs, `aggregate_summary.json`,
`repeated_run_manifest.json`, `manifest.json`, `README.md`, one representative
dot RSS-over-time SVG, and one representative MP4 beside the run-01 replay.

## Aggregate Metrics

| Profile | PPS | Attach gate | Initial A | Switch rate | Mean switches | Mean 1st switch (s) | SD 1st switch | Mean outage (s) | SD outage | Mean PDR | SD PDR | Median end-dwell RSS (dBm) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MED | off | 10/10 | 10/10 | 0.9 | 1.0 | 223.111111 | 3.723051 | 53.3 | 98.322655 | 0.95297 | 0.100701 | -98.00229 |
| MED | on-30s | 10/10 | 10/10 | 1.0 | 1.1 | 218.3 | 9.900056 | 18.3 | 5.755191 | 0.987299 | 0.005185 | -95.4685 |
| FED | off | 10/10 | 9/10 | 1.0 | 1.2 | 219.2 | 9.402127 | 19.1 | 5.237684 | 0.986092 | 0.004404 | -90.232 |
| FED | on-30s | 10/10 | 9/10 | 0.9 | 0.9 | 222.777778 | 4.116363 | 29.1 | 30.708124 | 0.975941 | 0.034688 | -95.4685 |
| SED | off | 10/10 | 10/10 | 1.0 | 1.0 | 223.9 | 2.643651 | 2.8 | 0.632456 | 0.974688 | 0.027146 | -90.232 |
| SED | on-30s | 10/10 | 10/10 | 1.0 | 1.1 | 220.2 | 5.138093 | 15.2 | 36.547686 | 0.980773 | 0.010302 | -90.232 |

## Parent Sequences

- MED PPS off: `4x router_a -> router_b`; `4x router_a -> router_c`; `1x router_a -> router_b -> router_c`; `1x router_a`
- MED PPS on-30s: `5x router_a -> router_c`; `4x router_a -> router_b`; `1x router_a -> router_b -> router_a`
- FED PPS off: `8x router_a -> router_c`; `1x router_a -> router_b`; `1x router_b -> router_a -> router_c -> router_a`
- FED PPS on-30s: `5x router_a -> router_c`; `4x router_a -> router_b`; `1x router_b`
- SED PPS off: `9x router_a -> router_c`; `1x router_a -> router_b`
- SED PPS on-30s: `7x router_a -> router_c`; `2x router_a -> router_b`; `1x router_a -> router_c -> router_b`

## Endpoint Parent Distribution

| Profile | PPS | Router A final | Router B final | Router C final | Unresolved final |
|---|---|---:|---:|---:|---:|
| MED | off | 0 | 4 | 5 | 1 |
| MED | on-30s | 1 | 4 | 5 | 0 |
| FED | off | 1 | 1 | 8 | 0 |
| FED | on-30s | 0 | 4 | 5 | 1 |
| SED | off | 0 | 1 | 9 | 0 |
| SED | on-30s | 0 | 2 | 7 | 1 |

Router A remained the final parent in 2 of 60 runs. The initial attachment gate
succeeded in 60 of 60 runs, and the first movement sample observed Router A in
58 of 60 runs.

## Parent Probe and Simulator RSS Metrics

![End-dwell simulator RSS comparison](simple_pps_matrix_rss_end_dwell.svg)

Representative dot RSS-over-time plots are stored with each repeated artifact:

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260712-210435-experiment/rss_over_time_run01.svg`
- MED PPS on-30s: `results/med_simple_parent_switch_med-pps-on-repeated/20260712-210540-experiment/rss_over_time_run01.svg`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260712-210653-experiment/rss_over_time_run01.svg`
- FED PPS on-30s: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260712-210803-experiment/rss_over_time_run01.svg`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260712-210917-experiment/rss_over_time_run01.svg`
- SED PPS on-30s: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260712-211036-experiment/rss_over_time_run01.svg`

## Interpretation

The attachment-gated asymmetric topology is the best tested tradeoff so far. It
keeps the Router A initial condition controlled while reducing Router-A-final
runs from 4 of 60 in the previous committed topology to 2 of 60.

The remaining Router-A-final cases are:

- MED PPS on-30s: 1 of 10
- FED PPS off: 1 of 10

The switch rate is not a pure PPS benefit metric here. Failure-driven switching
is already strong in the PPS-off arms because the endpoint makes Router A weak.
PPS-on mainly improves MED outage/PDR in this sample; it does not uniformly
increase switch rate across all profiles.

SED packet delivery and parent-probe metrics remain secondary evidence because
regular SED ping behavior is not the primary attachment signal; parent-command
observation remains primary.

## Commands

The six repeated arms used `scripts/run_repeated_baseline.py` with
`--repeat-count 10`, `--capture-replay`, `--capture-sim-ping-rss`,
`--copy-results-to-artifact`, `--otns-watch-level trace`, the explicit PPS
binaries documented in [`pps_build_variants.md`](pps_build_variants.md), and
these scenario paths:

- `scenarios/med_simple_parent_switch.yaml`
- `scenarios/fed_simple_parent_switch.yaml`
- `scenarios/sed_simple_parent_switch.yaml`

FED runs used `--ftd-node-binary-path`; MED and SED runs used
`--node-binary-path`.

Representative MP4s were rendered from run 01 of each arm with
`--window-size 1600,900`, `--replay-speed 16`, `--cover-full-replay`,
`--video-fps 8`, and `--show-log-panel`.

## Limitations

- Ten runs per arm is still a small sample.
- Switch timing is still dominated by endpoint dwell in most arms; the first
  switch normally appears after movement reaches the endpoint.
- Router B does not consistently appear as an intermediate parent.
- This matrix was generated before post-activation settle parent changes were
  promoted into explicit `pre_movement_*` summary fields. Current runs now
  distinguish switches before movement sampling from unexpected first samples.
- MED PPS off and FED/SED PPS on each include one unresolved final parent.
- SED packet delivery ratio is not primary evidence.
- FED uses OTNS's FTD executable family for both routers and the mobile FED.
- Simulator RSS is model-derived from OTNS `MutualInterference` at ping event
  positions because the exported replay/log artifacts do not expose receive
  RSS/LQI events for direct matching.
