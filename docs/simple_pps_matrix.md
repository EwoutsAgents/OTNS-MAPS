# Simple Scenario PPS Matrix

This page records the current repeated PPS-off/PPS-on matrix for the active
simple parent-switch scenarios. The active topology is a four-router, static
0 dBm topology with a fixed Router-A-only delay before Router B/C/D activation.

No MAPS policy or OpenThread parent-selection logic is implemented here.
PPS-off disables `OPENTHREAD_CONFIG_PARENT_SEARCH_ENABLE`; active PPS-on enables
it and sets `OPENTHREAD_CONFIG_PARENT_SEARCH_CHECK_INTERVAL=30`. This is tuned
stock OpenThread, not the upstream/default PPS interval.

## Scenario Geometry

All three active scenarios place Router A at `(350, 300)`, Router B at
`(875, 300)`, Router C at `(1400, 300)`, Router D at `(1925, 300)`, and create
the mobile end device at `(350, 360)`, close to Router A. Router A and the
mobile are created first. After a fixed 600 s Router-A-only delay, the runner
introduces Router B, Router C, and Router D, monitors a 600 s post-activation
settle period, and starts movement from `(350, 360)` to `(2125, 360)`.

The start/end offsets are intentionally not symmetric. The left-side offset was
removed because it made initial Router A attachment unreliable as the endpoint
was pushed farther away. This version uses a fixed static delay near Router A
while extending the router chain so Router A is much weaker at the endpoint
without increasing adjacent router spacing.

Every node is configured to static `0 dBm` transmit power during node
initialization with the OpenThread CLI `txpower 0` command. The runner verifies
this with `txpower` when the CLI returns a value.

The scenarios assume OTNS `MeterPerUnit = 0.1`, so one coordinate unit is
treated as 0.1 m unless the radio parameter is overridden. The movement path is
1775 coordinate units, which is 177.5 m. With 36 one-second movement steps, the
effective speed is about 4.93 m/s. The mobile then dwells at the end for
600 seconds.

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
| Router A -> mobile endpoint | -112.921 |
| Router B -> mobile endpoint | -107.098 |
| Router C -> mobile endpoint | -98.075 |
| Router D -> mobile endpoint | -77.313 |
| Router A -> Router B | -92.649 |
| Router B -> Router C | -92.649 |
| Router C -> Router D | -92.649 |

Router A is now very weak at the endpoint, Router D is a strong endpoint parent
candidate, and the A-B/B-C/C-D router links remain equal in the model.

## Artifacts

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260713-022826-experiment/`
- MED PPS on: `results/med_simple_parent_switch_med-pps-on-repeated/20260713-023051-experiment/`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260713-023312-experiment/`
- FED PPS on: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260713-023537-experiment/`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260713-023810-experiment/`
- SED PPS on: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260713-024054-experiment/`

Each repeated artifact contains 10 CSV files, 10 summary JSON files, 10 replay
files, 10 replay metadata JSON files, node logs, `aggregate_summary.json`,
`repeated_run_manifest.json`, `manifest.json`, `README.md`, and one
representative dot RSS-over-time SVG. MP4 rendering was skipped for this
600/600/600 timing refresh because the longer static-delay replay rendering was
slow and the CSV/JSON/replay/RSS artifacts were sufficient for comparison.

## Aggregate Metrics

| Profile | PPS | Static delay (s) | Initial A | Pre-move switch | In-sampling switch rate | Mean switches | Mean 1st switch (s) | SD 1st switch | Mean outage (s) | SD outage | Mean PDR | SD PDR | Median end-dwell RSS (dBm) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MED | off | 600 | 10/10 | 0/10 | 10/10 | 1.3 | 1234.9 | 6.063552 | 25.8 | 8.080154 | 0.989934 | 0.003876 | -77.313 |
| MED | on-30s | 600 | 10/10 | 0/10 | 10/10 | 1.2 | 1228.4 | 12.094076 | 82.7 | 187.123875 | 0.901573 | 0.281157 | -77.313 |
| FED | off | 600 | 9/10 | 2/10 | 9/10 | 1.4 | 1226.111111 | 10.68228 | 21.0 | 7.745967 | 0.991601 | 0.003772 | -77.313 |
| FED | on-30s | 600 | 7/10 | 4/10 | 10/10 | 7.9 | 1231.1 | 13.519122 | 22.6 | 5.910443 | 0.991755 | 0.0032 | -77.832917 |
| SED | off | 600 | 10/10 | 0/10 | 10/10 | 1.2 | 1233.7 | 7.631077 | 1.7 | 1.494434 | 0.984521 | 0.006972 | -77.313 |
| SED | on-30s | 600 | 10/10 | 0/10 | 10/10 | 1.5 | 1242.9 | 33.28146 | 13.8 | 30.27577 | 0.985776 | 0.002752 | -77.713609 |

## Parent Sequences

- MED PPS off: `7x router_a -> router_d`; `2x router_a -> router_b -> router_d`; `1x router_a -> router_c -> router_d`
- MED PPS on-30s: `6x router_a -> router_d`; `2x router_a -> router_b`; `1x router_a -> router_c -> router_b`; `1x router_a -> router_c -> router_d`
- FED PPS off: `5x router_a -> router_d`; `2x router_a -> router_c -> router_d`; `1x router_a -> router_b -> router_d`; `1x router_a -> router_c -> router_b -> router_d`; `1x router_c`
- FED PPS on-30s: `2x router_a -> router_c -> router_d`; `2x router_b -> router_d`; `1x router_a -> router_b -> router_c -> router_b -> router_c -> router_d`; `1x router_a -> router_b -> router_d`; `1x router_a -> router_d`; `1x router_b -> router_c`; `2x long router_c/router_d oscillation after leaving router_a`
- SED PPS off: `7x router_a -> router_d`; `1x router_a -> router_b -> router_d`; `1x router_a -> router_c`; `1x router_a -> router_c -> router_d`
- SED PPS on-30s: `4x router_a -> router_c -> router_d`; `4x router_a -> router_d`; `1x router_a -> router_b -> router_d`; `1x router_a -> router_c`

## Endpoint Parent Distribution

| Profile | PPS | Router A final | Router B final | Router C final | Router D final | Unresolved final |
|---|---|---:|---:|---:|---:|---:|
| MED | off | 0 | 0 | 0 | 10 | 0 |
| MED | on-30s | 0 | 3 | 0 | 7 | 0 |
| FED | off | 0 | 0 | 1 | 9 | 0 |
| FED | on-30s | 0 | 0 | 1 | 9 | 0 |
| SED | off | 0 | 0 | 1 | 9 | 0 |
| SED | on-30s | 0 | 0 | 1 | 9 | 0 |

Router A remained the final parent in 0 of 60 runs. The matrix contains
59 of 60 in-sampling switches plus one FED PPS-off run that switched during the
monitored pre-movement settle window and then stayed on Router C. Counting
pre-movement switch evidence, all 60 runs left Router A.

## Detach Recovery

| Profile | PPS | Detached/no reattach | Reattached new parent | Reattached same parent | No detach |
|---|---|---:|---:|---:|---:|
| MED | off | 0 | 9 | 0 | 1 |
| MED | on-30s | 0 | 7 | 1 | 2 |
| FED | off | 0 | 4 | 0 | 6 |
| FED | on-30s | 0 | 6 | 0 | 4 |
| SED | off | 0 | 10 | 0 | 0 |
| SED | on-30s | 0 | 10 | 0 | 0 |

The detached-no-reattach failure is absent in the full 60-run matrix. Most
switches are still failure/recovery driven: the mobile detaches near the endpoint
and reattaches to a stronger parent, usually Router D.

## Parent Probe and Simulator RSS Metrics

![End-dwell simulator RSS comparison](simple_pps_matrix_rss_end_dwell.svg)

Representative dot RSS-over-time plots are stored with each repeated artifact:

- MED PPS off: `results/med_simple_parent_switch_med-pps-off-repeated/20260713-022826-experiment/rss_over_time_run01.svg`
- MED PPS on-30s: `results/med_simple_parent_switch_med-pps-on-repeated/20260713-023051-experiment/rss_over_time_run01.svg`
- FED PPS off: `results/fed_simple_parent_switch_fed-pps-off-repeated/20260713-023312-experiment/rss_over_time_run01.svg`
- FED PPS on-30s: `results/fed_simple_parent_switch_fed-pps-on-repeated/20260713-023537-experiment/rss_over_time_run01.svg`
- SED PPS off: `results/sed_simple_parent_switch_sed-pps-off-repeated/20260713-023810-experiment/rss_over_time_run01.svg`
- SED PPS on-30s: `results/sed_simple_parent_switch_sed-pps-on-repeated/20260713-024054-experiment/rss_over_time_run01.svg`

MP4 rendering was skipped for this matrix because the added static delays make
the replay-to-video pass slow. Replay files remain available for every run.

## Interpretation

Adding Router D solved the Router-A-final problem without changing adjacent
router spacing. The endpoint is farther from Router A, but Router D gives a
strong endpoint candidate while C-D preserves the same modeled router-router
link strength as A-B and B-C.

The result is not a clean mid-path A -> B -> C -> D progression. Most runs still
jump from Router A directly to Router D, or briefly use Router B/C before Router
D. The benchmark is therefore good for forcing stock OpenThread off Router A,
but not yet good for studying smooth sequential parent progression.

FED PPS-on-30s shows two long Router C/Router D oscillation runs. That means the
four-router topology improved switch completion but introduced a stability
signal that should be tracked in future geometry work.

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

MP4 rendering was skipped for this timing refresh. Replay files can be rendered
later with `scripts/replay_to_mp4.py` if visual video evidence is needed.

## Limitations

- Ten runs per arm is still a small sample.
- Switch timing is dominated by endpoint dwell in most arms; the first switch
  normally appears after movement reaches the endpoint.
- Router B and Router C do not consistently appear as intermediate parents.
- FED PPS-on-30s had two long Router C/Router D oscillation runs.
- Static-delay MP4 rendering was skipped because replay capture is sufficient
  and the longer fixed-delay replays make video rendering slow.
- SED packet delivery ratio is not primary evidence.
- FED uses OTNS's FTD executable family for both routers and the mobile FED.
- Simulator RSS is model-derived from OTNS `MutualInterference` at ping event
  positions because the exported replay/log artifacts do not expose receive
  RSS/LQI events for direct matching.
