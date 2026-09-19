# Comparable Attach Timing

Directed and static parent-removal OTNS runs retain separate timing views. They
must not be mixed within an interval.

## Canonical air-to-air metrics

`protocol_timing_ms` is derived from the run's OTNS IEEE 802.15.4 PCAP and is
labeled `protocol_timing_source = otns_pcap`. The runner forces `-pcap wpan`
for attach runs, copies `current.pcap` out of the isolated runtime as
`otns_packets_<token>.pcap`, and includes that file in tracked artifacts and
their checksum inventory.

The extractor decrypts Thread traffic with the configured network key and
selects one operation-specific sequence using the operation start time, child
extended address, selected target extended address, MLE command, and packet
direction:

| Boundary | MLE command | Required direction |
| --- | ---: | --- |
| Parent Request on air | 9 | child to selected target (or multicast for multicast mode) |
| Parent Response on air | 10 | selected target to child |
| Child ID Request on air | 11 | child to selected target |
| Child ID Response on air | 12 | selected target to child |

For static parent-removal operations the replacement parent is not known in
advance. The extractor therefore learns it from the Child ID Request
destination, then matches that router's preceding Parent Response and following
Child ID Response. This avoids selecting the first response from an unrelated
router.

The canonical intervals are:

- `parent_request_to_response`;
- `parent_response_to_child_id_request`;
- `child_id_request_to_response`;
- `parent_request_to_child_id_response` (full attach).

All four values come from the same packet sequence. Initial attachment traffic,
other routers, ACK frames, and unrelated MLE traffic are excluded. An absent or
ambiguous sequence leaves canonical timing incomplete with one of:
`pcap_missing`, `pcap_parse_error`, `missing_parent_request`,
`missing_parent_response`, `missing_child_id_request`,
`missing_child_id_response`, or `ambiguous_attach_sequence`. The runner never
falls back to internal event timing for a missing PCAP interval.

OTNS classic PCAP timestamps have microsecond resolution and represent the
simulator's captured IEEE 802.15.4 frame time. They provide equivalent
air-to-air boundaries for comparison with hardware sniffer PCAP, but they are
not a cycle-accurate ESP32-C6 radio model.

## Internal OpenThread metrics

The existing native events remain in `preferred_parent_events_<token>.csv` and
the summary under `openthread_event_timing`:

| Native event | Meaning |
| --- | --- |
| `parent_request_started` | `SendTo()` accepted the Parent Request |
| `target_response` | MLE validated and matched the target response |
| `child_id_request_started` | `SendChildIdRequest()` accepted the request |
| `child_id_response_received` / `succeeded` | response accepted and child state installed |

Their `time_us` values come from `otPlatAlarmMicroGetNow()` in the child
process and are labeled `otns_openthread_event`. This is a 32-bit node-local
simulated clock. RFSIM can report 0 us between Parent Response handling and
Child ID Request submission because synchronous stack execution consumes no
simulated time. That remains useful diagnostic evidence, but is no longer used
as the hardware-comparison metric.

## Other clocks

Parent deletion uses global OTNS CLI time (`otns_simulator_time`). Final target
confirmation uses one-second runner polling (`otns_parent_poll`). Neither is
substituted into the packet-derived protocol intervals.

Hardware results use `hardware_pcap`; canonical OTNS results use `otns_pcap`.
Both now measure packet-to-packet boundaries, while their physical and
simulated radio environments remain different.
