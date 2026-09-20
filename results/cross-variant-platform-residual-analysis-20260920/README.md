# Cross-variant OTNS versus ESP32-C6 timing residuals

## 1. Question

What causes the remaining on-air attachment timing difference between native OTNS and ESP32-C6 after using identical PCAP packet boundaries?

The narrow result is that the protocol state-machine modes explain the large variant-dependent timer shapes, while a platform-common residual remains in receive/ACK-to-next-MLE-frame turnaround. Immediate IEEE 802.15.4 data-frame-to-ACK timing agrees to microseconds. The existing captures cannot apportion the remaining milliseconds among ESP32 task wakeup, OpenThread CPU execution, timer dispatch, message construction, and radio-driver startup.

## 2. Data provenance

- OTNS-MAPS branch `revised-solution-fast-attach-based`, input commit `7bf760e127f58ed38d57ac9413b1408744ce27b8`.
- Hardware/reference repository input commit `c269aca295e621253878384364b13a87525a497e`.
- Pinned OpenThread revision `a12ff0d0f54fd41954b45047fcdd08f302731c5f`.
- ESP-IDF package 5.5.4 (`framework-espidf` package version `3.50504`).
- Five valid variants, three router counts, two platforms, exactly 100 accepted runs per cell: 3,000 normalized observations.
- Cross-platform differences are differences of independent distribution statistics. No hardware run is paired with an OTNS run.
- Confidence intervals use 5,000 deterministic independent-sample bootstrap resamples.

Inputs are the five committed OTNS n=100 PCAP comparison directories and the hardware `testing/results/n100-comparison-2026-09` bundle. `source_manifest.json` records them.

## 3. Validity

The valid variants are `stock`, `stock-low-power`, `ucast`, `fast-attach-corrected`, and `fast-attach-ucast-1`. Corrected plain Fast Attach requires the proven Detached → arm → F=1 → acceptable-LQ3 early continuation lifecycle.

The historical `results/fast-attach-n100-pcap-comparison-20260919` campaign is excluded because runtime Fast Attach was not armed and F=0 followed the ordinary scan-timeout path. It contributes no pooled statistics here.

Every normalized row uses one complete PR → PRsp → CIDReq → CIDRsp sequence. ACKs are accepted only when the data frame requested one, the ACK MAC sequence matches, and it occurs within the next four frames before another selected MLE frame. Multicast Parent Requests do not request ACKs and are `N/A`. The documented midnight-crossing hardware capture uses its provenance-defined post-midnight recovery sequence.

## 4. Cross-variant results

The complete unified table is in `generated_tables.md`; means below are in milliseconds and delta means hardware minus OTNS.

| Variant | Routers | Δ PR→PRsp | Δ PRsp→CIDReq | Δ CIDReq→CIDRsp | Δ full |
| --- | ---: | ---: | ---: | ---: | ---: |
| stock | 2 / 3 / 4 | 13.259 / -61.407 / -27.755 | -11.307 / 62.957 / 29.189 | 8.057 / 8.304 / 8.349 | 10.010 / 9.853 / 9.782 |
| stock-low-power | 2 / 3 / 4 | -20.621 / -8.879 / 34.776 | 22.310 / 10.280 / -33.068 | 8.269 / 8.254 / 8.118 | 9.958 / 9.654 / 9.826 |
| ucast | 2 / 3 / 4 | 22.218 / -249.955 / -11.820 | 4.551 / 4.605 / 4.095 | 8.164 / 8.266 / 8.060 | 34.933 / -237.083 / 0.335 |
| fast-attach-corrected | 2 / 3 / 4 | 7.216 / 0.562 / 10.669 | 5.209 / 5.472 / 6.434 | 8.126 / 8.222 / 8.897 | 20.551 / 14.255 / 26.000 |
| fast-attach-ucast-1 | 2 / 3 / 4 | 6.206 / 5.964 / 6.113 | 4.373 / 4.818 / 2.932 | 7.992 / 7.855 / 7.554 | 18.571 / 18.637 / 16.598 |

The ucast mean is unstable because valid, very long Parent Response-delay observations dominate some cells. Its median deltas are materially different (full: 62.882, -2.133, and -33.831 ms), so neither statistic supports a fixed platform offset for the first leg. The raw and robust statistics, including p05/p95 and IQR, are in `interval_summary.csv`.

## 5. ACK decomposition

Across clean exchanges pooled over applicable variants and topologies:

| Interval | Hardware mean | OTNS mean | Difference |
| --- | ---: | ---: | ---: |
| directed Parent Request → ACK | 2.563819 | 2.563819 | <0.000001 ms |
| Parent Response → ACK | 4.003779 | 4.003779 | <0.000001 ms |
| Child ID Request → ACK | 3.843819 | 3.843819 | <0.000001 ms |

Per-cell ordinary means usually differ by about 0.008 ms; cells containing retransmitted attempts can move the ordinary mean. Restricting to clean exchanges makes the pooled values identical at capture precision because corresponding frame lengths and modeled airtime are identical.

The residual is after ACK completion. For immediate-selection variants, hardware-minus-OTNS ACK(PRsp)→CIDReq mean residuals are normally 4.4–6.4 ms. Robust median residuals are 4.8–5.5 ms, including the outlier-sensitive Fast-Attach-Ucast-1 four-router cell. ACK(CIDReq)→CIDRsp accounts for essentially the entire final-leg residual.

## 6. Common residuals

CIDReq→CIDRsp hardware-minus-OTNS mean residuals span 7.554–8.897 ms across all 15 valid cells; median residuals span 8.094–8.794 ms. In clean, non-duplicate, non-retransmitted exchanges, mean residuals remain 7.698–8.806 ms. Therefore:

- The residual is not Fast-Attach-specific.
- Retransmission is not its main cause.
- Router count has no monotonic effect common to all variants. The four-router corrected Fast Attach cell is higher, but the cross-variant range overlaps and does not establish a general topology law.

## 7. Protocol-specific behavior

Stock and stock-low-power retain the approximately 750 ms scan window. Parent Response position inside that window changes PR→PRsp and the remaining PRsp→CIDReq time in opposite directions. Their large first-two-leg differences cancel, while full-attach hardware-minus-OTNS remains about 9.7–10.0 ms. A small full difference is therefore not evidence of cycle-level equivalence.

Ucast also contains intentional randomized response delay and severe valid long tails; robust statistics must accompany means. Corrected Fast Attach uses a router-count-dependent randomized ceiling and immediate acceptable-LQ3 continuation. Fast-Attach-Ucast-1 uses a fixed 1 ms response policy and gives the cleanest reconstruction: its roughly 16.6–18.6 ms mean full residual is the sum of responder, child, and router turnaround residuals.

Hardware router diagnostics show stable PR→PRsp after subtracting the selected responder's intentional delay: means are 9.74–9.89 ms for stock/stock-low-power, 10.22–10.24 ms for ucast, 9.77–9.88 ms for corrected Fast Attach, and 10.24–10.58 ms for Fast-Attach-Ucast-1. The committed OTNS comparison artifacts do not preserve per-run selected response-delay diagnostics except the fixed 1 ms policy, so a symmetric adjusted-distribution claim for every OTNS variant is unavailable rather than inferred.

## 8. Source-code explanation

At pinned OpenThread revision `a12ff0d`, `Mle::Attacher::HandleParentResponse()` parses and updates the parent candidate, `SendChildIdRequest()` constructs/submits the next MLE message, and the router `HandleChildIdRequest()`/`SendChildIdResponse()` path processes the request and builds the response. `SubMac::StartCsmaBackoff()` chooses a random backoff and `BeginTransmit()` enters radio transmission.

The source constants are `kCsmaMinBe=3`, `kUnitBackoffPeriod=20` symbols, and 16 µs per 2.4 GHz symbol: 0–7 initial slots, 0–2.24 ms, mean 1.12 ms. ESP-IDF passes OpenThread's `mCsmaCaEnabled` to `esp_ieee802154_transmit()`/`transmit_at()`; this proves a hardware CCA control, not a second independently demonstrated full random backoff.

Native RFSIM executes parsing, TLV work, neighbor updates, message construction, and much state-machine code on the host without charging corresponding MCU CPU time to the simulated clock. ESP32-C6 traverses RX completion/event handling, the OpenThread task/mainloop, real CPU processing, alarm handling, message/MAC preparation, and driver transmit startup in wall-clock time.

The actual child build has `CONFIG_FREERTOS_HZ=1000`. ESP-IDF 5.5.4's OpenThread alarms derive their deadline from `esp_timer_get_time()`, place it in the select-mainloop `timeval`, and fire during platform processing. VFS converts millisecond timeout to ticks with upward rounding and an additional wait tick. This supports millisecond-scale scheduling error, not an unsupported claim that a 10 ms FreeRTOS tick alone explains an 8 ms residual.

## 9. What is proven

- **PROVEN:** Full attach is the exact sum of its three packet intervals. Maximum per-run reconstruction error is 0.000001 ms.
- **PROVEN:** Immediate ACK timing is not the dominant source of the multi-millisecond discrepancy.
- **PROVEN:** The final approximately 8 ms residual occurs after the CIDReq ACK and before CIDRsp and persists in clean exchanges across all valid protocol variants.
- **PROVEN:** Stock's first-two intervals cancel algebraically under the scan-window structure.
- **STRONGLY SUPPORTED:** Real platform execution/scheduling absent from OTNS simulated-time accounting supplies most common residual time.
- **STRONGLY SUPPORTED:** The immediate-selection PRsp→CIDReq platform residual is normally about 4–6 ms after ACK completion.
- **DISPROVEN:** Fast Attach itself causes the final-leg residual.
- **DISPROVEN:** Retransmissions, immediate ACK turnaround, CSMA randomness, or FreeRTOS tick granularity alone explain the common residual.
- **UNRESOLVED:** Exact millisecond allocation among RX event dispatch, task wakeup, MLE CPU work, timer wakeup, message/security preparation, CCA, and TX-driver startup.

## 10. Outliers and packet size

No outlier was deleted. `outliers.csv` lists 3×IQR outer-fence observations and retains each one. Every row still has a complete semantically selected sequence; rows with repeated attempts or duplicate sequence evidence are flagged. Remaining extremes are classified as valid complete-sequence long tails, principally intentional/random response timing or scheduling tails.

Within the clean selected exchanges, each MLE command has one observed frame length, so within-command packet-size correlation is mathematically undefined. The existing dataset therefore cannot distinguish fixed scheduling cost from message-size-dependent CPU work. Cross-command comparison would confound packet role, direction, and code path and is not used causally.

## 11. Conclusion and remaining uncertainty

The existing data are sufficient to localize the discrepancy but not to split it internally. Protocol-defined timers explain variant and topology distribution shapes. MAC/PHY airtime and immediate ACK turnaround agree closely. Most stable remaining time lies between ACK completion and the next MLE transmission, where ESP32-C6 performs real scheduled software/platform work that native OTNS largely executes without advancing simulated time.

No new hardware experiment is required for that conclusion. The minimum unresolved quantity is the division of ACK→next-frame time among RX-task/mainloop wakeup, MLE CPU execution, alarm dispatch, MAC/security preparation, and transmit-driver/CCA startup. Separating those terms would require synchronized internal markers around RX delivery, MLE handlers, MAC submission, and radio TX start; the existing PCAP clock alone cannot do it.

See `REPRODUCE.md` for the exact command and `generated_tables.md` for both required full tables.
