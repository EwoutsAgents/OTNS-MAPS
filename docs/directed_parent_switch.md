# Directed Parent-Switch Scenarios

The directed scenarios run the preferred-parent OpenThread implementation as a
native OTNS MTD and use either stock or fast-response FTD router binaries. They
mirror the ESPHome hardware procedure without running ESP32 firmware binaries.

## Matrix

`scenarios/directed/` contains multicast, unicast, legacy `ucast_fastpr`,
and `fast_attach_1` variants for two, three, and four routers. The latter mirrors
the current selected ESPHome hardware arm. The corresponding
stock baselines remain in `scenarios/static/`.

Every directed scenario uses:

- 180 seconds of router settling;
- 5 seconds for initial MED attachment;
- deterministic selection of a non-current router by extended address;
- preservation of the observed initial parent while OpenThread discovers and
  validates the selected replacement;
- 255 seconds of post-request observation at one-second intervals;
- disabled Periodic Parent Search in the Phase 8 MTD builds.

## Binary profiles

Real directed runs require both executable paths and declared profiles. The
runner rejects multicast with fast-response routers, fast-response routers with
multicast mode, stock MTDs, missing binaries, non-executable files, and router
profiles that contradict the scenario.

Use `preferred-parent` for the legacy MTD profile. Multicast and ordinary-unicast
scenarios require the logging-only `stock-ftd-delay-diagnostic` router profile
so the selected random Parent Response delay can be subtracted from packet
timing. Use `fastpr` for `ucast_fastpr` routers:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/directed/med_directed_ucast_2routers.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns \
  --node-binary-path /path/to/preferred-parent-mtd-pps-off/ot-cli-mtd \
  --node-binary-profile preferred-parent \
  --ftd-node-binary-path /path/to/stock-ftd-delay-diagnostic/ot-cli-ftd \
  --ftd-node-binary-profile stock-ftd-delay-diagnostic \
  --firmware-variant otns-preferred-parent-ucast
```

For `med_directed_ucast_fastpr_*.yaml`, select the fast-response FTD and pass
`--ftd-node-binary-profile fastpr`.

For `med_directed_ucast_fast_attach_1_*.yaml`, use `fast-attach-ucast-1` for
both profiles. It uses the same OpenThread controller and fixed response-delay
policy as the selected ESPHome hardware variant:

```bash
python3 scripts/run_baseline.py \
  --scenario scenarios/directed/med_directed_ucast_fast_attach_1_2routers.yaml \
  --otns-command '/path/to/otns -web=false -autogo=false -speed 1' \
  --otns-workdir /path/to/ot-ns \
  --node-binary-path /path/to/fast-attach-ucast-1-mtd-pps-off/ot-cli-mtd \
  --node-binary-profile fast-attach-ucast-1 \
  --ftd-node-binary-path /path/to/fast-attach-ucast-1-ftd/ot-cli-ftd \
  --ftd-node-binary-profile fast-attach-ucast-1 \
  --firmware-variant otns-fast-attach-ucast-1
```

After a repeated multicast or ordinary-unicast campaign, derive the adjusted
packet timing with:

```bash
python3 /path/to/ESPHome-Thread-ED-Switch-Parent/testing/scripts/analyze_test_logs.py \
  --otns-results-dir /path/to/repeated-results \
  --subtract-parent-response-random-delay \
  --summary-only
```

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

Mock validation covers all fifteen scenarios and invalid profile combinations.
The Phase 9 real exit matrix ran all two-router variants with the Phase 8
artifacts. Multicast, unicast, and fast-response unicast each acknowledged the
command, emitted the selected-parent event sequence, and finished attached to
the requested target.

Timestamped native binaries add `time_us`, `timing_source`, and `resolution_us`
to the four protocol events. The runner exports these events to
`preferred_parent_events_<timestamp>.csv` and derives comparable attach
intervals in the summary JSON. See
[`comparable_timing.md`](comparable_timing.md).
