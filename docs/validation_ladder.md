# Directed Parent-Switch Validation Ladder

Phase 11 validates the native preferred-parent integration in increasing scope.
All timings below are validation measurements, not cycle-accurate predictions of
ESP32 execution or physical IEEE 802.15.4 radio behavior.

## Build and feature isolation

The Phase 10 clean build produced four executable profiles. Phase 11 verified
their SHA-256 fingerprints again:

| Profile | SHA-256 |
| --- | --- |
| stock MTD, PPS off | `bfb2ef7b9400ff0899769a5e5658f20f0812b57ca7ece335ecb9b1266c3040a5` |
| preferred-parent MTD, PPS off | `dd6d97f5418bd7f35b1674f32687faa6116afc65d198436070e2cca8bdba3627` |
| stock FTD | `6c21e593fb01bd3cc984a138cbde863285c5842fe55dfd0b52a839fefe98064a` |
| fast-response FTD | `7bc3917e1d80d8f57258b9eb20ce5049351b772dd4da84058cd8391bd0e6c260` |

The stock MTD and FTD contain no `PREFPARENT` marker. The preferred-parent MTD
and the fast-response build do. The fast-response artifact is identified by its
isolated build configuration and fingerprint; the compile-time option does not
leave a reliable human-readable marker in the executable.

## CLI validation

A real two-router run exercised the native controller before parent removal:

- idle status reported generation 0 and `active=0`;
- malformed extended addresses and unknown modes returned `InvalidArgs`;
- a valid unicast request entered `waiting_target_response`;
- a second request returned `Busy`;
- `clear` emitted `event=cleared`;
- status after clear returned to `idle` and `active=0`.

## Protocol and fast-response validation

The directed matrix below provides an end-to-end check of target selection,
candidate capture, Child ID Request continuation, event cleanup, and final
parent identity. Earlier matched-seed Phase 7 packet validation remains the
strong regression control for the router fast path: fast unicast changed Parent
Response latency, matched multicast captures were byte-identical, and no
delayed duplicate Parent Response followed the immediate response.

## Controlled runner classifications

`tests/test_directed_parent_switch.py` exercises all setup labels and terminal
classifications through pure deterministic helpers:

- `SKIP_NO_CHILD_PARENT`;
- `SKIP_PARENT_NOT_MAPPED_TO_DEVICE`;
- `SKIP_NO_ELIGIBLE_TARGET_PARENT`;
- `SKIP_PARENT_IS_LEADER`;
- `selected_target_reached`;
- `attached_to_non_target_parent`;
- `no_reattachment`;
- `command_rejected`;
- `skipped`.

`SKIP_PARENT_IS_LEADER` is advisory: the run continues and separately records
the terminal result.

## Deterministic matrix

The real smoke matrix used one fixed OTNS seed per topology and ran stock,
multicast, unicast, and fast-response unicast with two, three, and four routers.
All three stock runs observed recovery after parent removal. All nine directed
runs acknowledged the command, reached the selected target, and exported a
complete native event sequence.

| Routers | Multicast full attach (ms) | Unicast full attach (ms) | Fast unicast full attach (ms) |
| ---: | ---: | ---: | ---: |
| 2 | 321.440 | 321.184 | 18.880 |
| 3 | 184.000 | 366.784 | 21.120 |
| 4 | 246.560 | 246.304 | 18.240 |

The scenario YAML files use different deterministic target-selection seeds, so
the selected router can differ between variants. These runs validate the whole
matrix; they are not paired performance trials.

## Repeated campaign

Ten real two-router runs per directed variant produced 30 successful target
switches and 30 complete timing sets:

| Variant | Success | Mean full attach (ms) | Sample SD (ms) | Range (ms) |
| --- | ---: | ---: | ---: | ---: |
| multicast | 10/10 | 220.316 | 176.997 | 27.960–505.440 |
| unicast | 10/10 | 324.680 | 130.869 | 90.024–501.824 |
| fast unicast | 10/10 | 20.416 | 2.833 | 16.320–26.240 |

The repeated runner now forwards the required MTD and FTD profile declarations,
so directed campaigns no longer require an external shell loop. A three-run
real fast-response test validated that path; all three runs reached the target
with complete timing.

## Four-router hardware comparison

The hardware and OTNS four-router runs use the same semantic event boundaries,
but different clocks and radio models. Hardware timing comes from PCAP; OTNS
timing comes from native node-local RFSIM events.

| Variant | Hardware full attach (ms) | OTNS smoke full attach (ms) |
| --- | ---: | ---: |
| multicast | 306 | 246.560 |
| unicast | 106 | 246.304 |
| fast unicast | 48 | 18.240 |

All three hardware child logs confirm attachment to the requested extended
address. The three OTNS runs also reached the requested target. This is a
matched topology and protocol comparison, not a statistically matched radio
experiment: it contains one run per arm, independently selected targets, and
different physical/simulated timing sources.

## Gate result

All eight validation stages pass at their intended scope. Larger statistical
claims still require repeated four-router hardware and OTNS campaigns with an
explicit target-selection and seed policy. Phase 12 packages the reproducible
commands, provenance, and result artifacts.
