# Fast Attach Ucast 1: internal events, simulated PCAP, and hardware PCAP

Each OTNS column uses exactly 100 accepted selected-target runs. Values are mean +/- sample SD in ms.

| Routers | Interval | Old OTNS event | New OTNS PCAP | Hardware PCAP |
| ---: | --- | ---: | ---: | ---: |
| 2 | Parent Request -> Parent Response | 16.169 +/- 3.734 | 5.244 +/- 2.532 | 11.450 +/- 1.270 |
| 2 | Parent Response -> Child ID Request | 0.000 +/- 0.000 | 6.232 +/- 2.320 | 10.610 +/- 0.810 |
| 2 | Child ID Request -> Child ID Response | 11.256 +/- 2.720 | 5.843 +/- 1.657 | 13.840 +/- 0.810 |
| 2 | Full attach | 27.425 +/- 4.148 | 17.318 +/- 3.500 | 35.890 +/- 1.860 |
| 3 | Parent Request -> Parent Response | 15.458 +/- 3.238 | 5.275 +/- 2.234 | 11.240 +/- 0.940 |
| 3 | Parent Response -> Child ID Request | 0.000 +/- 0.000 | 5.911 +/- 1.599 | 10.730 +/- 0.830 |
| 3 | Child ID Request -> Child ID Response | 10.993 +/- 2.726 | 5.957 +/- 2.180 | 13.810 +/- 0.840 |
| 3 | Full attach | 26.451 +/- 3.916 | 17.143 +/- 3.513 | 35.780 +/- 1.570 |
| 4 | Parent Request -> Parent Response | 16.863 +/- 13.742 | 5.469 +/- 2.247 | 11.580 +/- 0.980 |
| 4 | Parent Response -> Child ID Request | 0.000 +/- 0.000 | 7.673 +/- 13.058 | 10.610 +/- 0.950 |
| 4 | Child ID Request -> Child ID Response | 11.824 +/- 4.911 | 6.172 +/- 2.159 | 13.730 +/- 0.830 |
| 4 | Full attach | 28.687 +/- 17.638 | 19.314 +/- 13.844 | 35.910 +/- 1.620 |

The OTNS-PCAP column is canonical for hardware comparison. The event column is retained only to inspect internal stack behavior. `accepted_runs.csv` records every interval and frame selection; `selection_manifest.json` records every selected and excluded summary. All 300 selected PCAPs are preserved under `pcaps/`.

The PCAP timestamp is the OTNS simulated IEEE 802.15.4 frame time. It aligns packet boundaries with the hardware sniffer analysis but does not model ESP32-C6 execution or physical RF cycle-accurately.

After boundary alignment, simulated full attach remains faster by 18.572 ms
(2 routers), 18.637 ms (3 routers), and 16.596 ms (4 routers). All three
air-to-air subintervals remain shorter in OTNS. The remaining gap is therefore
not the former zero-time boundary artifact. It reflects RFSIM versus ESP32-C6
MAC/radio scheduling, physical radio turnaround and processing, and different
RF/backoff conditions. No protocol delay was inserted or tuned.

Exact validation and comparison commands are in `REPRODUCE.md`.
