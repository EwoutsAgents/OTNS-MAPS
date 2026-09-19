# Fast Attach Ucast 1: OTNS versus hardware

This report now compares OTNS simulated-PCAP timing with the September 2026
ESP32-C6 hardware-PCAP campaign. All timing values are milliseconds and are
reported as mean +/- sample standard deviation. Delta is OTNS minus hardware,
so a negative full-attach delta means that OTNS completed sooner.

| Routers | Timing interval | OTNS PCAP n=100 | Hardware PCAP n=100 | Delta |
| ---: | --- | ---: | ---: | ---: |
| 2 | Parent Request -> Parent Response | 5.244 +/- 2.532 | 11.45 +/- 1.27 | -6.206 |
| 2 | Parent Response -> Child ID Request | 6.232 +/- 2.320 | 10.61 +/- 0.81 | -4.378 |
| 2 | Child ID Request -> Child ID Response | 5.843 +/- 1.657 | 13.84 +/- 0.81 | -7.997 |
| 2 | **Full attach** | **17.318 +/- 3.500** | **35.89 +/- 1.86** | **-18.572 (-51.7%)** |
| 3 | Parent Request -> Parent Response | 5.275 +/- 2.234 | 11.24 +/- 0.94 | -5.965 |
| 3 | Parent Response -> Child ID Request | 5.911 +/- 1.599 | 10.73 +/- 0.83 | -4.819 |
| 3 | Child ID Request -> Child ID Response | 5.957 +/- 2.180 | 13.81 +/- 0.84 | -7.853 |
| 3 | **Full attach** | **17.143 +/- 3.513** | **35.78 +/- 1.57** | **-18.637 (-52.1%)** |
| 4 | Parent Request -> Parent Response | 5.469 +/- 2.247 | 11.58 +/- 0.98 | -6.111 |
| 4 | Parent Response -> Child ID Request | 7.673 +/- 13.058 | 10.61 +/- 0.95 | -2.937 |
| 4 | Child ID Request -> Child ID Response | 6.172 +/- 2.159 | 13.73 +/- 0.83 | -7.558 |
| 4 | **Full attach** | **19.314 +/- 13.844** | **35.91 +/- 1.62** | **-16.596 (-46.2%)** |

## Inputs and selection

The OTNS values come from the new `fast-attach-ucast-1` PCAP validation
campaign in `results/fast-attach-ucast-1-n100-pcap-comparison-20260919/`.
Each router count uses exactly 100 accepted selected-target runs. The four
protocol boundaries are timestamps of the Parent Request, Parent Response,
Child ID Request, and Child ID Response frames in the preserved OTNS simulated
IEEE 802.15.4 PCAP. Internal OpenThread event timing is no longer used as the
hardware-comparison metric.

The hardware values come from
`testing/results/n100-comparison-2026-09/analysis/results.csv` in
`ESPHome-Thread-ED-Switch-Parent` at commit
`e0537f6fe78d1ebf691455c8c2149c3e3533a8c2`. Both sides now use equivalent
air-to-air packet boundaries. The raw Parent Request-to-Parent Response
interval is used; the fixed 1 ms responder delay is not subtracted.

## Interpretation notes

- The former zero-duration Parent Response-to-Child ID Request result belonged
  to internal synchronous OpenThread processing. Its OTNS PCAP value is now
  5.911-7.673 ms, depending on router count.
- OTNS remains 16.596-18.637 ms faster over the full attach after aligning the
  measurement boundaries. All three simulated air-to-air subintervals are
  shorter than their hardware equivalents.
- This remaining difference reflects RFSIM versus ESP32-C6 processing,
  MAC/radio scheduling, physical radio turnaround, and RF/backoff conditions.
  OTNS PCAP is not a cycle-accurate ESP32-C6 radio simulation.
- The four-router variability includes a long but valid simulated observation;
  no protocol delay was inserted or tuned.

The machine-readable values are in `comparison.csv`. The newer result directory
also preserves the before/after event comparison, accepted-run inventory,
selection manifest, checksums, and all 300 selected PCAPs.
