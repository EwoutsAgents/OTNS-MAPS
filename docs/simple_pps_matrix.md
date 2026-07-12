# Simple Scenario PPS Matrix

This page records the current repeated PPS-off/PPS-on matrix for the active
simple parent-switch scenarios. The active topology is a three-router, static
0 dBm topology with an explicit initial-attachment gate.

No MAPS policy or OpenThread parent-selection logic is implemented here.
PPS-off disables `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`; active PPS-on enables
it and sets `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`. This is tuned
stock OpenThread, not the upstream/default PPS interval.

## Scenario Geometry

All three active scenarios place Router A at `(350, 300)`, Router B at
`(875, 300)`, Router C at `(1400, 300)`, and create the mobile end device at
`(350, 360)`, close to Router A. Router A and the mobile are created first. The
runner waits until the mobile is observed parented to Router A, then introduces
Router B and Router C, settles, and starts movement from `(350, 360)` to
`(1600, 360)`.

The start/end offsets are intentionally not symmetric. The left-side offset was
removed because it made initial Router A attachment unreliable as the endpoint
was pushed farther away. This version keeps the initial attachment controlled
while still putting Router A under endpoint pressure.

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
| Router B -> mobile endpoint | -98.075 |
| Router C -> mobile endpoint | -77.313 |
| Router A -> Router B | -92.649 |
| Router B -> Router C | -92.649 |

Router A is weak at the endpoint, Router C is a strong endpoint parent
candidate, and the A-B/B-C router links remain viable in the model.

## Artifacts

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260712-231710-experiment/`
- MED PPS on: `results/med_simple_parent_switch_med-pps-on-repeated/20260712-231821-experiment/`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260712-231931-experiment/`
- FED PPS on: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260712-232041-experiment/`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260712-232151-experiment/`
- SED PPS on: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260712-232309-experiment/`

Each repeated artifact contains 10 CSV files, 10 summary JSON files, 10 replay
files, 10 replay metadata JSON files, node logs, `aggregate_summary.json`,
`repeated_run_manifest.json`, `manifest.json`, `README.md`, one representative
dot RSS-over-time SVG, and one representative MP4 beside the run-01 replay.

## Aggregate Metrics

| Profile | PPS | Attach gate | Initial A | Pre-move switch | Switch rate | Mean switches | Mean 1st switch (s) | SD 1st switch | Mean outage (s) | SD outage | Mean PDR | SD PDR | Median end-dwell RSS (dBm) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MED | off | 10/10 | 10/10 | 0/10 | 9/10 | 0.9 | 222.0 | 3.937004 | 20.9 | 7.385421 | 0.985463 | 0.004879 | -77.313 |
| MED | on-30s | 10/10 | 10/10 | 0/10 | 9/10 | 0.9 | 237.333333 | 45.332108 | 20.9 | 7.607745 | 0.982983 | 0.006147 | -77.313 |
| FED | off | 10/10 | 10/10 | 0/10 | 10/10 | 1.0 | 220.6 | 6.186006 | 18.4 | 7.183314 | 0.98637 | 0.006517 | -77.313 |
| FED | on-30s | 10/10 | 9/10 | 1/10 | 10/10 | 1.1 | 245.5 | 90.117516 | 16.4 | 4.005552 | 0.987106 | 0.004331 | -77.313 |
| SED | off | 10/10 | 10/10 | 0/10 | 10/10 | 1.0 | 221.1 | 3.034981 | 1.6 | 0.966092 | 0.982573 | 0.00451 | -77.313 |
| SED | on-30s | 10/10 | 10/10 | 0/10 | 10/10 | 1.2 | 218.7 | 11.489609 | 3.2 | 6.613118 | 0.979582 | 0.003337 | -77.313 |

## Parent Sequences

- MED PPS off: `8x router_a -> router_c`; `1x router_a`; `1x router_a -> router_b`
- MED PPS on-30s: `9x router_a -> router_c`; `1x router_a`
- FED PPS off: `8x router_a -> router_c`; `2x router_a -> router_b`
- FED PPS on-30s: `8x router_a -> router_c`; `1x router_a -> router_b -> router_c`; `1x router_b -> router_c`
- SED PPS off: `9x router_a -> router_c`; `1x router_a -> router_b`
- SED PPS on-30s: `6x router_a -> router_c`; `2x router_a -> router_b`; `2x router_a -> router_b -> router_c`

## Endpoint Parent Distribution

| Profile | PPS | Router A final | Router B final | Router C final | Unresolved final |
|---|---|---:|---:|---:|---:|
| MED | off | 1 | 1 | 8 | 0 |
| MED | on-30s | 1 | 0 | 9 | 0 |
| FED | off | 0 | 2 | 8 | 0 |
| FED | on-30s | 0 | 0 | 10 | 0 |
| SED | off | 0 | 1 | 9 | 0 |
| SED | on-30s | 0 | 2 | 8 | 0 |

Router A remained the final parent in 2 of 60 runs. The initial attachment gate
succeeded in 60 of 60 runs. No run ended unresolved.

## Detach Recovery

| Profile | PPS | Detached/no reattach | Reattached new parent | Reattached same parent | No detach |
|---|---|---:|---:|---:|---:|
| MED | off | 0 | 8 | 1 | 1 |
| MED | on-30s | 0 | 8 | 0 | 2 |
| FED | off | 0 | 7 | 0 | 3 |
| FED | on-30s | 0 | 7 | 0 | 3 |
| SED | off | 0 | 10 | 0 | 0 |
| SED | on-30s | 0 | 10 | 0 | 0 |

The detached-no-reattach failure is now absent in the full 60-run matrix. Most
switches are still failure/recovery driven: the mobile detaches near the endpoint
and reattaches to a stronger parent, usually Router C.

## Parent Probe and Simulator RSS Metrics

![End-dwell simulator RSS comparison](simple_pps_matrix_rss_end_dwell.svg)

Representative dot RSS-over-time plots are stored with each repeated artifact:

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260712-231710-experiment/rss_over_time_run01.svg`
- MED PPS on-30s: `results/med_simple_parent_switch_med-pps-on-repeated/20260712-231821-experiment/rss_over_time_run01.svg`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260712-231931-experiment/rss_over_time_run01.svg`
- FED PPS on-30s: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260712-232041-experiment/rss_over_time_run01.svg`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260712-232151-experiment/rss_over_time_run01.svg`
- SED PPS on-30s: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260712-232309-experiment/rss_over_time_run01.svg`

Representative MP4s are stored beside each run-01 replay:

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260712-231710-experiment/20260712-231710-run01/20260712-231710-run01/med_simple_parent_switch_20260712T231710Z.mp4`
- MED PPS on-30s: `results/med_simple_parent_switch_med-pps-on-repeated/20260712-231821-experiment/20260712-231821-run01/20260712-231821-run01/med_simple_parent_switch_20260712T231821Z.mp4`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260712-231931-experiment/20260712-231931-run01/20260712-231931-run01/fed_simple_parent_switch_20260712T231931Z.mp4`
- FED PPS on-30s: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260712-232041-experiment/20260712-232041-run01/20260712-232041-run01/fed_simple_parent_switch_20260712T232041Z.mp4`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260712-232151-experiment/20260712-232151-run01/20260712-232151-run01/sed_simple_parent_switch_20260712T232151Z.mp4`
- SED PPS on-30s: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260712-232309-experiment/20260712-232309-run01/20260712-232309-run01/sed_simple_parent_switch_20260712T232309Z.mp4`

## Interpretation

The current topology solves the detached-no-reattach failure observed in the
earlier MED PPS-off run while keeping the Router A initial condition controlled.
Router A still remains final in 2 of 60 runs, both without an in-window switch,
so the benchmark is not a guaranteed-switch setup.

The observed behavior is mostly endpoint failure recovery rather than a clean
mid-path A -> B -> C parent progression. Router C is the dominant final parent,
and Router B is only occasionally selected as an intermediate or final parent.

PPS-on does not uniformly improve switch rate here because the endpoint already
forces failure-driven switching in most PPS-off runs. Its value should be judged
with outage, PDR, pre-movement behavior, and parent sequence, not only switch
rate.

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
`--video-fps 8`, `--end-device-y-offset 80`, and `--show-log-panel`.

## Limitations

- Ten runs per arm is still a small sample.
- Switch timing is dominated by endpoint dwell in most arms; the first switch
  normally appears after movement reaches the endpoint.
- Router B does not consistently appear as an intermediate parent.
- Router A remains final in 2 of 60 runs.
- One FED PPS-on run switched before movement sampling and is classified as
  `pre_movement_switch_observed`.
- SED packet delivery ratio is not primary evidence.
- FED uses OTNS's FTD executable family for both routers and the mobile FED.
- Simulator RSS is model-derived from OTNS `MutualInterference` at ping event
  positions because the exported replay/log artifacts do not expose receive
  RSS/LQI events for direct matching.
