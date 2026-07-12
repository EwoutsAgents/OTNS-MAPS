# Topology Offset Sweep, 2026-07-12

This archive keeps aggregate evidence from three experimental symmetric-offset
topology candidates. The raw per-run CSV/replay/MP4 artifacts were not retained
here because these candidates were rejected and the replay-heavy output was
roughly 2 GB.

The active committed topology before this sweep used:

- Router A/B/C: `(350,300)`, `(750,300)`, `(1150,300)`
- Mobile path: `(0,360)` to `(1500,360)`
- `movement_steps: 30`
- delayed Router B/C activation after `300 s`

The goal of the sweep was to reduce runs where Router A remained the final
parent while keeping controlled initial attachment to Router A.

## Candidates

| Candidate | Geometry | Delayed B/C activation | Router A endpoint RSS | Result |
|---|---|---:|---:|---|
| `offset-375-delay300` | A/B/C `375/775/1175`, path `0 -> 1550` | `300 s` | `-106.071 dBm` | Rejected: Router A final remained and MED PPS-on had uncontrolled starts. |
| `offset-500-delay300` | A/B/C `500/900/1300`, path `0 -> 1800` | `300 s` | `-107.749 dBm` | Rejected: fewer Router-A finals, but more uncontrolled starts and `None` finals. |
| `offset-450-delay600` | A/B/C `450/850/1250`, path `0 -> 1700` | `600 s` | `-107.098 dBm` | Rejected: diagnostics passed, but the full matrix still had Router-A finals and uncontrolled starts. |

## Aggregate Results

Router-A-final totals across the six-arm, 60-run matrix:

- Current committed offset 350: `4/60` Router-A finals.
- Offset 375, delay 300: `5/60` Router-A finals.
- Offset 500, delay 300: `3/60` Router-A finals, but with many uncontrolled initial/final parent observations.
- Offset 450, delay 600: `3/60` Router-A finals, with `8/60` uncontrolled initial observations and `2/60` `None` finals.

The best switch-rate numbers in the rejected candidates came with worse
experimental control. The larger offsets weaken the start-to-Router-A link,
causing initial attachment instability before they reliably force Router A to
stop being viable at the endpoint.

## Conclusion

Do not replace the active topology with these candidates as-is. The sweep shows
that symmetric offset tuning alone has a narrow operating window:

- smaller offsets keep initial attachment controlled, but Router A can remain
  viable at the endpoint;
- larger offsets increase endpoint pressure, but weaken the initial Router A
  attachment too much.

The next useful approach is to separate the initial attachment condition from
the movement-start condition, or to add a small scenario mechanism that lets the
mobile attach near Router A before starting the symmetric path. That would keep
the research geometry symmetric without relying on a marginal initial radio
link.
