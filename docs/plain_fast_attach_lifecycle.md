# Plain Fast Attach lifecycle in OTNS

## Root cause

### Observations before the fix

- The MTD binary contained `otThreadSetFastAttachEnabled()` and was compiled with `OPENTHREAD_CONFIG_MLE_FAST_ATTACH_ENABLE=1`.
- The FTD binary contained router-side F-bit handling, including the `active_router_count * 32 ms` response ceiling and `ParentResponseDelay` diagnostic.
- No native OTNS application or runner code called `otThreadSetFastAttachEnabled()` during parent removal.
- A recorded recovery Parent Request produced `scan_mask=0x80`. Bit `0x20` was clear, so F=0.
- Historical n=100 PR-to-PRsp plus PRsp-to-CIDReq means were 749.854, 750.072, and 749.893 ms for 2, 3, and 4 routers.

### Interpretation

Fast Attach support was compiled into both node types, but the application-level one-shot state was never armed. The recovery request was therefore ordinary, and `HandleParentResponse()` could not take the Fast Attach early-selection branch. The child continued when the normal Parent Request scan timer expired near 750 ms.

The missing behavior was the OTNS equivalent of the hardware `thread_fast_attach` component: observe a post-attachment Detached role and call the public Fast Attach API before recovery begins.

| Behavioral check | Before | After |
| --- | --- | --- |
| Fast Attach compiled into MTD and FTD | yes | yes |
| Armed after post-attachment detach | no | yes, public API returns success |
| Recovery Parent Request F bit | 0 (`scan_mask=0x80`) | 1 (`scan_mask=0xa0`) |
| First acceptable LQ3 response ends the scan | no | yes |
| Ordinary approximately 750 ms timeout path | yes | no |
| One-shot state clears after attachment | not exercised | yes |

## Implementation

The plain Fast Attach MTD build applies `patches/otns/plain-fast-attach-native-adapter.patch` from the hardware/reference repository. A CLI application state-change callback records initial attachment, waits for a later Detached transition, calls `otThreadSetFastAttachEnabled(instance, true)` exactly once, confirms `otThreadIsFastAttachEnabled(instance)`, and then leaves the existing MLE implementation to conduct recovery.

The adapter is guarded by `OPENTHREAD_CONFIG_MLE_FAST_ATTACH_AUTO_ARM_AFTER_DETACH_ENABLE` and `!OPENTHREAD_FTD`. The flag is enabled only for plain `fast-attach`. Stock and `fast-attach-ucast-1` build definitions are unchanged. The adapter does not write `mFastAttachEnabled`, modify `SetStateDetached()`, bypass the runtime flag, or add delays.

Diagnostics prove the child lifecycle, outgoing scan mask, acceptable LQ3 response, zero-timer continuation, Child ID Request, and one-shot clearing. Router logs prove receipt of F=1 and the randomized response delay.

## Runner validity

Plain Fast Attach summaries contain a `fast_attach` object. Acceptance requires initial attachment and parent removal; Detached observation and successful arming; enabled state before the F=1 request; router receipt of F=1 and a delay no greater than `router_count * 32 ms`; acceptable LQ3 response and `early_timer_zero`; Child ID Request; complete PCAP sequence; reattachment; and one-shot clearing.

Invalid runs receive an explicit `fast_attach_*` classification. Repeated-run validation rejects them, and aggregation requires `fast_attach.valid=true` whenever the lifecycle is expected.

## Instrumented two-router trace

The committed trace is in `results/fast-attach-corrected-trace-2routers-20260919/`.

| Event | OTNS time (s) | Evidence |
| --- | ---: | --- |
| Initial child attached | 180.845556 | `attached_seen role=2 enabled=0` |
| Current parent deleted | 185.000000 | runner summary |
| Detached observed | 419.950096 | `detached_seen role=1` |
| Fast Attach armed | 419.950096 | `api_error=0 enabled=1` |
| Recovery Parent Request | 420.344568 | `scan_mask=0xa0 enabled=1` |
| Router schedules response | 420.346944 | F=1, delay 17 ms, ceiling 64 ms |
| Acceptable LQ3 response | 420.368280 | `acceptable_lq3_response` |
| Early continuation | 420.368280 | `early_timer_zero` |
| Child ID Request | 420.368280 | `child_id_request enabled=1` |
| Attachment completed/cleared | 420.377768 | `attached_clear enabled=0` |

The ordering is `Detached == arm < Parent Request`. Response, zero-timer, and Child ID Request logs share one timestamp, proving immediate continuation instead of the ordinary timeout. PCAP intervals are 19.736, 5.896, 4.456, and 30.088 ms.

## Validation results

The gated 10-run campaigns passed 10/10 for every topology. Every run proved the complete lifecycle and PCAP sequence.

| Routers | Router response delays | PR-to-PRsp + PRsp-to-CIDReq mean | Full attach mean +/- SD |
| ---: | ---: | ---: | ---: |
| 2 | 12-32 ms | 33.696 ms | 39.656 +/- 6.662 ms |
| 3 | 5-96 ms | 36.940 ms | 44.193 +/- 17.333 ms |
| 4 | 1-115 ms | 25.333 ms | 33.770 +/- 18.685 ms |

The delay distributions are randomized and bounded by 64, 96, and 128 ms. They are not the fixed 1 ms policy of `fast-attach-ucast-1`.

## Corrected n=100 result

The corrected comparison is in `results/fast-attach-corrected-n100-pcap-comparison-20260919/`. The old `results/fast-attach-n100-pcap-comparison-20260919/` result is retained and marked as historical invalid Fast Attach evidence.

| Routers | Corrected OTNS full attach | Hardware full attach |
| ---: | ---: | ---: |
| 2 | 30.591 +/- 8.792 ms | 51.140 +/- 9.430 ms |
| 3 | 48.347 +/- 20.769 ms | 62.600 +/- 21.220 ms |
| 4 | 41.106 +/- 23.265 ms | 67.110 +/- 24.760 ms |

These differences are reported without calibration or claims about simulator accuracy. The acceptance result is behavioral: OTNS now executes the application-level post-detach arming and MLE Fast Attach state-machine semantics used by hardware.

## Regression boundaries

- Stock builds do not define the adapter flag.
- `fast-attach-ucast-1` retains separate directed-operation arming and its fixed 1 ms responder behavior.
- Canonical `otns_pcap` boundaries are unchanged.
- Successful attachment clears the one-shot state; later recovery requires another Detached transition.
