# Endpoint Recovery Pilot

This archive keeps aggregate-only evidence from the geometry pilot that tested
the detached-no-reattach failure seen in the attachment-gated three-router
topology.

The active promoted geometry is:

- Router A: `(350, 300)`
- Router B: `(875, 300)`
- Router C: `(1400, 300)`
- Mobile path: `(350, 360) -> (1600, 360)`
- Movement: `25` one-second steps, 125 m at `MeterPerUnit = 0.1`, target 5 m/s
- Static TX power: `0 dBm` for every node

Model-derived RSS with `0 dBm` TX power:

| Link | RSS (dBm) |
|---|---:|
| Router A -> mobile endpoint | -107.098 |
| Router B -> mobile endpoint | -98.075 |
| Router C -> mobile endpoint | -77.313 |
| Router A -> Router B | -92.649 |
| Router B -> Router C | -92.649 |

The rejected comparison point moved only Router C to `1250`. In a MED PPS-off
10-run pilot it still produced `2/10` detached-no-reattach runs and worse mean
outage/PDR, so it was not promoted.

## Promoted Geometry Pilot

| Arm | Initial attach | Initial A | Pre-move switch | Switch rate | Final parents | Detached/no reattach | Mean outage (s) | Mean PDR |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| MED PPS off | 10/10 | 10/10 | 0/10 | 9/10 | A 1, B 1, C 8 | 0/10 | 18.3 | 0.986098 |
| MED PPS on-30s | 10/10 | 10/10 | 0/10 | 10/10 | B 2, C 8 | 0/10 | 18.0 | 0.986393 |
| FED PPS off | 10/10 | 8/10 | 2/10 | 10/10 | B 2, C 8 | 0/10 | 18.0 | 0.986039 |
| FED PPS on-30s | 10/10 | 9/10 | 1/10 | 9/10 | A 1, C 9 | 0/10 | 17.6 | 0.986187 |
| SED PPS off | 10/10 | 10/10 | 0/10 | 9/10 | A 1, C 9 | 0/10 | 5.5 | 0.891373 |
| SED PPS on-30s | 10/10 | 10/10 | 0/10 | 10/10 | B 2, C 8 | 0/10 | 1.1 | 0.982199 |

Across the promoted geometry pilot, the detached-no-reattach failure was `0/60`.
This archive intentionally keeps only aggregate summaries and repeated-run
manifests from the scratch pilots; replay-heavy scratch output was not retained.
