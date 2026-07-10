# Scenario Definitions

The active benchmark matrix uses three simple parent-switch scenarios:

- `scenarios/med_simple_parent_switch.yaml`
- `scenarios/fed_simple_parent_switch.yaml`
- `scenarios/sed_simple_parent_switch.yaml`

## Simple Parent Switch

A simple parent-switch scenario has two routers, one mobile end device, straight-line movement, delayed Router B activation, overlapping intended coverage, and no intentional dead zone. The mobile starts before Router A, moves beyond Router B, and dwells at the end to give late or sticky parent switching behavior time to appear.

Router A and the mobile end device are created first. The mobile device is allowed to attach to Router A, Router B is introduced after a delay, a post-activation settle period runs, and only then does movement toward Router B begin. All active scenarios keep `expected_initial_parent: router_a`.

## Geometry

All active simple scenarios use the same intended overlapping-coverage geometry:

| Node | x | y |
|---|---:|---:|
| Router A | 250 | 300 |
| Router B | 650 | 300 |
| Mobile start | 150 | 360 |
| Mobile end | 750 | 360 |

The moving end device should theoretically have at least one router in range throughout the path while still traversing from before Router A to beyond Router B.

OTNS uses the `MeterPerUnit` radio parameter for coordinate scaling. The scenarios assume the default `MeterPerUnit = 0.1`, so one coordinate unit is treated as 0.1 m unless the radio parameter is overridden. This default is recorded in the local OTNS source at `radiomodel/model_params.go` and listed by `cli/README.md`.

The mobile path from x=150 to x=750 spans 600 coordinate units, which is 60 m at `MeterPerUnit = 0.1`. With 12 one-second movement steps, the target movement speed is 5 m/s. The runner sends a 1 Hz mobile-to-current-parent ping when the parent resolves to a known router; this is a connectivity/RTT probe, not an RSSI measurement.

## Timing

| Scenario | Step seconds | Movement steps | Router B delay (s) | Post-activation settle (s) | Hold end steps | End dwell (s) |
|---|---:|---:|---:|---:|---:|---:|
| MED simple | 1 | 12 | 300 | 180 | 320 | 320 |
| FED simple | 1 | 12 | 300 | 180 | 320 | 320 |
| SED simple | 1 | 12 | 300 | 180 | 320 | 320 |

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
