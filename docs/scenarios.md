# Scenario Definitions

The active benchmark matrix uses three simple parent-switch scenarios:

- `scenarios/med_simple_parent_switch.yaml`
- `scenarios/fed_simple_parent_switch.yaml`
- `scenarios/sed_simple_parent_switch.yaml`

## Simple Parent Switch

A simple parent-switch scenario has three routers, one mobile end device, straight-line movement, delayed Router B/Router C activation, static 0 dBm transmit power, and no intentional dead zone. The mobile starts near Router A, moves beyond Router C, and dwells at the end to give late or sticky parent switching behavior time to appear.

Router A and the mobile end device are created first. The scenario then runs a fixed Router-A-only attachment window before Router B and Router C are introduced. A post-activation settle period runs after Router B/C activation, and only then does movement toward Router C begin. All active scenarios keep `expected_initial_parent: router_a`.

The post-activation settle period is monitored, not treated as invisible time. The runner polls the mobile parent during this phase and records `pre_movement_parent_sequence`, `pre_movement_parent_final`, `pre_movement_switch_count`, and `pre_movement_parent_events` in the summary JSON. If the mobile leaves Router A before movement sampling starts, the run is classified as `pre_movement_switch_observed` instead of being folded into `initial_parent_unexpected`.

## Geometry

All active simple scenarios use the same intended overlapping-coverage geometry:

| Node | x | y |
|---|---:|---:|
| Router A | 350 | 300 |
| Router B | 875 | 300 |
| Router C | 1400 | 300 |
| Mobile attach/movement start | 350 | 360 |
| Mobile end | 1600 | 360 |

The moving end device stays horizontally offset from the router line. The old symmetric start/end offset was removed because a large left-side offset made initial Router A attachment unreliable. The active geometry instead starts near Router A for a fixed Router-A-only attachment window, then moves the ED past Router C. Router B remains between Router A and Router C so it can preserve mesh connectivity while also acting as a possible intermediate parent.

All nodes set OpenThread transmit power to `0 dBm` once during initialization using `txpower 0`; the runner verifies the configured value with `txpower` when possible.

OTNS uses the `MeterPerUnit` radio parameter for coordinate scaling. The scenarios assume the default `MeterPerUnit = 0.1`, so one coordinate unit is treated as 0.1 m unless the radio parameter is overridden. This default is recorded in the local OTNS source at `radiomodel/model_params.go` and listed by `cli/README.md`.

The mobile path from x=350 to x=1600 spans 1250 coordinate units, which is 125 m at `MeterPerUnit = 0.1`. With 25 one-second movement steps, the target movement speed is 5 m/s. Router C is placed close enough to the endpoint to give a detached mobile a strong reattachment candidate while Router A is weak at the endpoint.

Model-derived RSS with static `0 dBm` transmit power is approximately:

| Link | RSS (dBm) |
|---|---:|
| Router A -> mobile endpoint | -107.098 |
| Router B -> mobile endpoint | -98.075 |
| Router C -> mobile endpoint | -77.313 |
| Router A -> Router B | -92.649 |
| Router B -> Router C | -92.649 |

The runner sends exactly one 1 Hz ICMP ping from the mobile end device to its currently observed parent when that parent resolves to a known router. When `--capture-sim-ping-rss` is enabled, the runner also attaches simulator-model RSS/LQI to that ping event using OTNS `MutualInterference` parameters at the ping source/destination positions.

If the mobile detaches, summaries record `detach_count`, first detach/reattach timing and position, `reattach_latency_s`, `ended_detached`, and `recovery_classification`. The recovery classifications distinguish `detached_no_reattach`, `detached_reattached_same_parent`, and `detached_reattached_new_parent`.

## Timing

| Scenario | Step seconds | Movement steps | Router-A-only delay before B/C (s) | Post-activation settle (s) | Hold end steps | End dwell (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| MED simple | 1 | 25 | 300 | 180 | 320 | 320 |
| FED simple | 1 | 25 | 300 | 180 | 320 | 320 |
| SED simple | 1 | 25 | 300 | 180 | 320 | 320 |

The SED scenario now uses the same activation timing as MED/FED so the repeated PPS matrix uses a consistent geometry and movement schedule across profiles. SED observability remains different because regular SED packet probing is unreliable.

## Observability

| Scenario | Device profile | Primary parent observation | Packet probe reliable |
|---|---|---|---|
| MED simple | `minimal_end_device` | `packet_probe` | `true` |
| FED simple | `full_end_device` | `packet_probe` | `true` |
| SED simple | `sleepy_end_device` | `parent_command` | `false` |

For FED, OTNS maps `fed` and router nodes to the FTD executable family, so `--ftd-node-binary-path` affects both the mobile FED and routers.

For SED, regular ping probing is unreliable in OTNS. Parent attachment is inferred from the OT CLI `parent` command and child state; packet delivery ratio is not primary evidence.

## Historical Names

Older committed artifacts may reference previous scenario names:

- `baseline_mobile_parent_switch`
- `calibrated_mobile_parent_switch`
- `fed_mobile_parent_switch`
- `sed_mobile_parent_switch`

The current equivalent active scenarios are:

- `med_simple_parent_switch`
- `fed_simple_parent_switch`
- `sed_simple_parent_switch`

The original `baseline_mobile_parent_switch` scenario was a historical smoke/reference scenario and is no longer part of the active benchmark matrix.

## Geometry Compatibility

The active simple scenarios use the extended 5 m/s path described above. Results generated under previous wider or shorter simple geometry are historical and should not be mixed with current simple-scenario results without clearly labeling the geometry difference.
