# stock-low-power: simulated PCAP and hardware PCAP

Each OTNS column uses exactly 100 accepted runs. Values are mean +/- sample SD in ms.

| Routers | Interval | Internal OTNS event | OTNS PCAP | Hardware PCAP |
| ---: | --- | ---: | ---: | ---: |
| 2 | Parent Request -> Parent Response | n/a | 257.852 +/- 150.907 | 237.230 +/- 140.320 |
| 2 | Parent Response -> Child ID Request | n/a | 492.248 +/- 150.814 | 514.560 +/- 140.310 |
| 2 | Child ID Request -> Child ID Response | n/a | 5.582 +/- 0.955 | 13.850 +/- 0.990 |
| 2 | Full attach | n/a | 755.683 +/- 1.585 | 765.640 +/- 1.690 |
| 3 | Parent Request -> Parent Response | n/a | 266.016 +/- 149.997 | 257.140 +/- 146.580 |
| 3 | Parent Response -> Child ID Request | n/a | 483.995 +/- 150.005 | 494.270 +/- 146.620 |
| 3 | Child ID Request -> Child ID Response | n/a | 5.662 +/- 0.934 | 13.920 +/- 0.930 |
| 3 | Full attach | n/a | 755.674 +/- 1.516 | 765.330 +/- 1.590 |
| 4 | Parent Request -> Parent Response | n/a | 245.434 +/- 153.055 | 280.210 +/- 133.250 |
| 4 | Parent Response -> Child ID Request | n/a | 504.415 +/- 153.046 | 471.350 +/- 133.720 |
| 4 | Child ID Request -> Child ID Response | n/a | 5.867 +/- 1.347 | 13.990 +/- 1.000 |
| 4 | Full attach | n/a | 755.717 +/- 1.735 | 765.540 +/- 1.840 |

The OTNS-PCAP column is canonical for hardware comparison. The event column is retained only to inspect internal stack behavior. `accepted_runs.csv` records every interval and frame selection; `selection_manifest.json` records every selected and excluded summary. All 300 selected PCAPs are preserved under `pcaps/`.

The PCAP timestamp is the OTNS simulated IEEE 802.15.4 frame time. It aligns packet boundaries with the hardware sniffer analysis but does not model ESP32-C6 execution or physical RF cycle-accurately.
