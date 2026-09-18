# Fast Attach Ucast 1: OTNS versus hardware

This report compares corrected OTNS `fast-attach-ucast-1` simulations with the
September 2026 ESP32-C6 hardware campaign. All timing values are milliseconds
and are reported as mean +/- sample standard deviation. Delta is OTNS minus
hardware, so a negative full-attach delta means that OTNS completed sooner.

| Routers | Timing interval | OTNS n=100 | Hardware n=100 | Delta |
| ---: | --- | ---: | ---: | ---: |
| 2 | Parent Request -> Parent Response | 15.497 +/- 3.023 | 11.45 +/- 1.27 | +4.047 |
| 2 | Parent Response -> Child ID Request | 0.000 +/- 0.000 | 10.61 +/- 0.81 | -10.610 |
| 2 | Child ID Request -> Child ID Response | 11.258 +/- 2.878 | 13.84 +/- 0.81 | -2.582 |
| 2 | **Full attach** | **26.755 +/- 3.351** | **35.89 +/- 1.86** | **-9.135 (-25.5%)** |
| 3 | Parent Request -> Parent Response | 16.101 +/- 3.281 | 11.24 +/- 0.94 | +4.861 |
| 3 | Parent Response -> Child ID Request | 0.000 +/- 0.000 | 10.73 +/- 0.83 | -10.730 |
| 3 | Child ID Request -> Child ID Response | 11.196 +/- 2.862 | 13.81 +/- 0.84 | -2.614 |
| 3 | **Full attach** | **27.297 +/- 3.791** | **35.78 +/- 1.57** | **-8.483 (-23.7%)** |
| 4 | Parent Request -> Parent Response | 16.316 +/- 3.895 | 11.58 +/- 0.98 | +4.736 |
| 4 | Parent Response -> Child ID Request | 0.000 +/- 0.000 | 10.61 +/- 0.95 | -10.610 |
| 4 | Child ID Request -> Child ID Response | 13.000 +/- 12.518 | 13.73 +/- 0.83 | -0.730 |
| 4 | **Full attach** | **29.315 +/- 13.906** | **35.91 +/- 1.62** | **-6.595 (-18.4%)** |

## Inputs and selection

The OTNS inputs are the `corrected` and `replacement` result directories next
to this report for two, three, and four routers. Each primary campaign produced
99 successful selected-target attachments from 100 attempts. One replacement
run per router count was added, yielding exactly 100 successful timing samples
per count. Attempts classified as `attached_to_non_target_parent` have no
complete protocol timing and are not treated as measurements.

The hardware values come from
`testing/results/n100-comparison-2026-09/analysis/results.csv` in
`ESPHome-Thread-ED-Switch-Parent` at commit
`e0537f6fe78d1ebf691455c8c2149c3e3533a8c2`. The table uses the raw Parent
Request-to-Parent Response interval, not the separately reported value with the
fixed 1 ms responder delay subtracted.

## Interpretation notes

- RFSIM records zero elapsed simulated time between handling the Parent
  Response and submitting the Child ID Request. Hardware PCAP includes physical
  processing, task scheduling, radio turnaround, and MAC access between the
  corresponding on-air frames.
- The OTNS Parent Request event occurs after `SendTo()` accepts the message,
  before actual simulated transmission. Hardware PCAP begins at on-air
  transmission, so the intermediate boundaries are not perfectly equivalent.
- The four-router standard deviation is dominated by one valid 158.232 ms
  full-attach observation at a simulated target RSS of -98 dBm. The four-router
  median is 27.056 ms.
- These results compare protocol behaviour under the configured OTNS radio
  model; they are not a calibrated RF reproduction of the hardware bench.

The machine-readable values are in `comparison.csv`.
