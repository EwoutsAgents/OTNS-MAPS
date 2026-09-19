# fast-attach: simulated PCAP and hardware PCAP

Each OTNS column uses exactly 100 accepted runs. Values are mean +/- sample SD in ms.

| Routers | Interval | Internal OTNS event | OTNS PCAP | Hardware PCAP |
| ---: | --- | ---: | ---: | ---: |
| 2 | Parent Request -> Parent Response | n/a | 229.011 +/- 143.703 | 26.470 +/- 9.410 |
| 2 | Parent Response -> Child ID Request | n/a | 520.843 +/- 143.553 | 10.880 +/- 0.820 |
| 2 | Child ID Request -> Child ID Response | n/a | 5.621 +/- 1.039 | 13.800 +/- 0.930 |
| 2 | Full attach | n/a | 755.474 +/- 1.501 | 51.140 +/- 9.430 |
| 3 | Parent Request -> Parent Response | n/a | 228.816 +/- 135.069 | 36.340 +/- 20.510 |
| 3 | Parent Response -> Child ID Request | n/a | 521.256 +/- 135.166 | 11.840 +/- 2.450 |
| 3 | Child ID Request -> Child ID Response | n/a | 5.653 +/- 1.079 | 14.420 +/- 2.760 |
| 3 | Full attach | n/a | 755.725 +/- 1.470 | 62.600 +/- 21.220 |
| 4 | Parent Request -> Parent Response | n/a | 240.701 +/- 145.956 | 39.650 +/- 22.950 |
| 4 | Parent Response -> Child ID Request | n/a | 509.192 +/- 145.936 | 12.390 +/- 4.240 |
| 4 | Child ID Request -> Child ID Response | n/a | 5.618 +/- 1.075 | 15.050 +/- 3.200 |
| 4 | Full attach | n/a | 755.511 +/- 1.728 | 67.110 +/- 24.760 |

The OTNS-PCAP column is canonical for hardware comparison. The event column is retained only to inspect internal stack behavior. `accepted_runs.csv` records every interval and frame selection; `selection_manifest.json` records every selected and excluded summary. All 300 selected PCAPs are preserved under `pcaps/`.

The PCAP timestamp is the OTNS simulated IEEE 802.15.4 frame time. It aligns packet boundaries with the hardware sniffer analysis but does not model ESP32-C6 execution or physical RF cycle-accurately.
