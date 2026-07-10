# Scenario Definitions

The active benchmark matrix uses three simple parent-switch scenarios:

- `scenarios/med_simple_parent_switch.yaml`
- `scenarios/fed_simple_parent_switch.yaml`
- `scenarios/sed_simple_parent_switch.yaml`

## Simple Parent Switch

A simple parent-switch scenario has two routers, one mobile end device, straight-line movement, delayed Router B activation, overlapping intended coverage, and no intentional dead zone.

Router A and the mobile end device are created first. The mobile device is allowed to attach to Router A, Router B is introduced after a delay, a post-activation settle period runs, and only then does movement toward Router B begin. All active scenarios keep `expected_initial_parent: router_a`.

## Geometry

All active simple scenarios use the same intended overlapping-coverage geometry:

| Node | x | y |
|---|---:|---:|
| Router A | 250 | 300 |
| Router B | 650 | 300 |
| Mobile start | 250 | 360 |
| Mobile end | 650 | 360 |

This closer spacing replaces the older wider geometry. The moving end device should theoretically have at least one router in range throughout the path.

## Timing

| Scenario | Step seconds | Movement steps | Router B delay (s) | Post-activation settle (s) | Hold end steps |
|---|---:|---:|---:|---:|---:|
| MED simple | 20 | 40 | 300 | 180 | 8 |
| FED simple | 20 | 40 | 300 | 180 | 8 |
| SED simple | 30 | 36 | 360 | 240 | 8 |

The SED scenario keeps a slower sampling cadence and longer delayed-router timing because regular SED parent observation is less direct than MED/FED packet probing.

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

The simple scenarios use closer router spacing and overlapping intended coverage. Results generated under the old wider scenario geometry are historical and should not be mixed with new simple-scenario results without clearly labeling the geometry difference.
