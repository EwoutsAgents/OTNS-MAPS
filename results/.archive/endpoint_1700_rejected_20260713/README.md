# Endpoint 1700 Rejected Test

This archive preserves aggregate-only evidence for a rejected endpoint extension tested on 2026-07-13.

The active three-router topology was temporarily changed from endpoint `x=1600` to endpoint `x=1700`, with `movement_steps` changed from `25` to `27` to preserve the 5 m/s movement speed. Routers were not moved.

The result was worse than the previous active endpoint:

- Router-A-final cases increased from `2/60` to `5/60`.
- One SED PPS-off run ended detached without reattachment.
- FED PPS-on introduced pre-movement switches in the aggregate.

Because this did not improve the benchmark, the replay-heavy experiment output was not committed and the active scenarios were restored to endpoint `x=1600`.

Archived aggregate summaries:

- `med_pps_off_aggregate_summary.json`
- `med_pps_on_aggregate_summary.json`
- `fed_pps_off_aggregate_summary.json`
- `fed_pps_on_aggregate_summary.json`
- `sed_pps_off_aggregate_summary.json`
- `sed_pps_on_aggregate_summary.json`

Endpoint-1700 aggregate highlights:

- MED PPS off: `8/10` switched; final parents `router_a=2`, `router_b=2`, `router_c=6`.
- MED PPS on-30s: `10/10` switched; final parents `router_b=5`, `router_c=5`.
- FED PPS off: `9/10` switched; final parents `router_a=1`, `router_b=3`, `router_c=6`.
- FED PPS on-30s: `8/10` switched, with `5/10` pre-movement switch runs; final parents `router_b=1`, `router_c=9`.
- SED PPS off: `9/10` switched; final parents `None=1`, `router_a=1`, `router_b=1`, `router_c=7`; detached-no-reattach `1/10`.
- SED PPS on-30s: `9/10` switched; final parents `router_a=1`, `router_c=9`.
