# Directed Parent-Switch Scenarios

The directed scenarios run the preferred-parent OpenThread implementation as a
native OTNS MTD and use either stock or fast-response FTD router binaries. They
mirror the ESPHome hardware procedure without running ESP32 firmware binaries.

## Matrix

`scenarios/directed/` contains multicast, unicast, and `ucast_fastpr` variants
for two, three, and four routers. The corresponding stock baselines remain in
`scenarios/static/`.

Every directed scenario uses:

- 300 seconds of router settling;
- 5 seconds for initial MED attachment;
- deterministic selection of a non-current router by extended address;
- preservation of the observed initial parent while OpenThread discovers and
  validates the selected replacement;
- 360 seconds of post-request observation at one-second intervals;
- disabled Periodic Parent Search in the Phase 8 MTD builds.

## Binary profiles

Real directed runs require both executable paths and declared profiles. The
runner rejects multicast with fast-response routers, fast-response routers with
multicast mode, stock MTDs, missing binaries, non-executable files, and router
profiles that contradict the scenario.

Use `preferred-parent` for the MTD profile. Use `stock` for multicast/unicast
routers and `fastpr` for `ucast_fastpr` routers:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/directed/med_directed_ucast_2routers.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns \
  --node-binary-path /path/to/preferred-parent-mtd-pps-off/ot-cli-mtd \
  --node-binary-profile preferred-parent \
  --ftd-node-binary-path /path/to/stock-ftd/ot-cli-ftd \
  --ftd-node-binary-profile stock \
  --firmware-variant otns-preferred-parent-ucast
```

For `med_directed_ucast_fastpr_*.yaml`, select the fast-response FTD and pass
`--ftd-node-binary-profile fastpr`.

`scripts/run_repeated_baseline.py` accepts the same binary paths and profile
arguments, including `--node-binary-profile` and
`--ftd-node-binary-profile`, for repeated directed campaigns.

The global MTD/FTD paths provide homogeneous defaults. A node may override its
default with `nodes.<name>.executable`; OTNS then receives
`add <type> exe "<path>"`. Relative paths are resolved against the scenario
file, and environment variables and `~` are expanded. Each node's resolved
path, SHA-256, declared firmware profile, and OTNS node ID are recorded under
`node_executables` in the summary and artifact manifest.

## Result fields

Directed summaries record:

- initial parent name, node ID, extended address, and RLOC16;
- selected target name, node ID, extended address, and RLOC16;
- deterministic random seed and selection policy;
- command acknowledgement, raw command output, and command error;
- preferred-parent structured events for the active generation;
- parent deletion time and final parent;
- router topology snapshots and role/RLOC changes;
- final classification and labels.

Labels align with the hardware runner where meaningful:

- `SKIP_NO_CHILD_PARENT`;
- `SKIP_PARENT_NOT_MAPPED_TO_DEVICE`;
- `SKIP_NO_ELIGIBLE_TARGET_PARENT`;
- `SKIP_PARENT_IS_LEADER`;
- `COMMAND_REJECTED`;
- `SELECTED_TARGET_REACHED`;
- `ATTACHED_TO_NON_TARGET_PARENT`;
- `NO_REATTACHMENT`;
- `ROUTER_TOPOLOGY_CHANGED`.

Leader-parent and topology-change labels do not invalidate a run by themselves.

## Validation

Mock validation covers all nine scenarios and invalid profile combinations.
The Phase 9 real exit matrix ran all two-router variants with the Phase 8
artifacts. Multicast, unicast, and fast-response unicast each acknowledged the
command, emitted the selected-parent event sequence, and finished attached to
the requested target.

Timestamped native binaries add `time_us`, `timing_source`, and `resolution_us`
to the four protocol events. The runner exports these events to
`preferred_parent_events_<timestamp>.csv` and derives comparable attach
intervals in the summary JSON. See
[`comparable_timing.md`](comparable_timing.md).
