# Scenario Definitions

The active benchmark matrix uses three simple parent-switch scenarios:

- `scenarios/med_simple_parent_switch.yaml`
- `scenarios/fed_simple_parent_switch.yaml`
- `scenarios/sed_simple_parent_switch.yaml`

## Simple Parent Switch

A simple parent-switch scenario has three routers, one mobile end device, straight-line movement, delayed Router B/Router C activation, static 0 dBm transmit power, and no intentional dead zone. The mobile starts before Router A, moves beyond Router C, and dwells at the end to give late or sticky parent switching behavior time to appear.

Router A and the mobile end device are created first. The mobile device is allowed to attach to Router A, Router B and Router C are introduced after a delay, a post-activation settle period runs, and only then does movement toward Router C begin. All active scenarios keep `expected_initial_parent: router_a`.

## Geometry

All active simple scenarios use the same intended overlapping-coverage geometry:

| Node | x | y |
|---|---:|---:|
| Router A | 350 | 300 |
| Router B | 750 | 300 |
| Router C | 1150 | 300 |
| Mobile start | 0 | 360 |
| Mobile end | 1500 | 360 |

The moving end device stays horizontally offset from the router line and traverses from before Router A to beyond Router C. The start/end offsets are symmetric: 350 coordinate units before Router A and 350 coordinate units beyond Router C. The active geometry keeps Router B between Router A and Router C so Router B can preserve mesh connectivity while also acting as a possible intermediate parent.

All nodes set OpenThread transmit power to `0 dBm` once during initialization using `txpower 0`; the runner verifies the configured value with `txpower` when possible.

OTNS uses the `MeterPerUnit` radio parameter for coordinate scaling. The scenarios assume the default `MeterPerUnit = 0.1`, so one coordinate unit is treated as 0.1 m unless the radio parameter is overridden. This default is recorded in the local OTNS source at `radiomodel/model_params.go` and listed by `cli/README.md`.

The mobile path from x=0 to x=1500 spans 1500 coordinate units, which is 150 m at `MeterPerUnit = 0.1`. With 30 one-second movement steps, the target movement speed is 5 m/s. The runner sends exactly one 1 Hz ICMP ping from the mobile end device to its currently observed parent when that parent resolves to a known router. When `--capture-sim-ping-rss` is enabled, the runner also attaches simulator-model RSS/LQI to that ping event using OTNS `MutualInterference` parameters at the ping source/destination positions.

## Timing

| Scenario | Step seconds | Movement steps | Router B/C delay (s) | Post-activation settle (s) | Hold end steps | End dwell (s) |
|---|---:|---:|---:|---:|---:|---:|
| MED simple | 1 | 30 | 300 | 180 | 320 | 320 |
| FED simple | 1 | 30 | 300 | 180 | 320 | 320 |
| SED simple | 1 | 30 | 300 | 180 | 320 | 320 |

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
