# Comparable Attach Timing

Directed preferred-parent runs expose four timestamped native OpenThread
events:

| Semantic boundary | Native event |
| --- | --- |
| Parent Request sent | `parent_request_started` after successful `SendTo()` acceptance |
| Target Parent Response received | `target_response` after MLE validation and target matching |
| Child ID Request sent | `child_id_request_started` after successful `SendChildIdRequest()` |
| Child ID Response received | `child_id_response_received` after the response is accepted and child state is installed |

The event fields are:

```text
time_us=<uint32>
timing_source=otns_openthread_event
resolution_us=1
```

`time_us` comes from `otPlatAlarmMicroGetNow()` in the child node process. It is
a 32-bit node-local simulated clock, not the global OTNS scenario clock. The
runner handles wraparound when deriving short intervals. Absolute event times
must not be subtracted from the global parent-deletion time.

## Derived intervals

`protocol_timing_ms` uses the same semantic sequence as the hardware PCAP
analyzer:

- `parent_request_to_response`;
- `parent_response_to_child_id_request`;
- `child_id_request_to_response`;
- `parent_request_to_child_id_response` (full attach).

The summary identifies these values as `otns_openthread_event` with 1 µs source
resolution. The raw events are also written to
`preferred_parent_events_<timestamp>.csv`.

RFSIM may report 0 µs between Parent Response handling and Child ID Request
submission. This means no simulated time elapsed between the two callbacks; it
does not claim that physical hardware performs the work instantaneously.

## Parent-removal observation

Parent deletion uses the global OTNS CLI time and is labeled
`otns_simulator_time`. Final target confirmation is sampled by the runner and
is labeled `otns_parent_poll`. With the current one-second sampling interval,
`parent_deletion_to_target_observed_ms` has one-second resolution and must not be
presented as equivalent to the microsecond protocol intervals.

Hardware results retain `hardware_pcap` as their timing source. Comparing
hardware and OTNS is valid at the interval-definition level, not as
cycle-accurate or radio-equivalent execution.
