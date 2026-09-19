# stock: simulated PCAP and hardware PCAP

Each OTNS column uses exactly 100 accepted runs. Values are mean +/- sample SD in ms.

| Routers | Interval | Internal OTNS event | OTNS PCAP | Hardware PCAP |
| ---: | --- | ---: | ---: | ---: |
| 2 | Parent Request -> Parent Response | n/a | 245.273 +/- 137.875 | 258.530 +/- 148.820 |
| 2 | Parent Response -> Child ID Request | n/a | 504.724 +/- 138.064 | 493.420 +/- 148.870 |
| 2 | Child ID Request -> Child ID Response | n/a | 5.787 +/- 1.546 | 13.840 +/- 0.970 |
| 2 | Full attach | n/a | 755.785 +/- 1.908 | 765.790 +/- 1.480 |
| 3 | Parent Request -> Parent Response | n/a | 231.737 +/- 141.101 | 170.330 +/- 106.930 |
| 3 | Parent Response -> Child ID Request | n/a | 518.199 +/- 140.991 | 581.160 +/- 106.940 |
| 3 | Child ID Request -> Child ID Response | n/a | 5.672 +/- 1.432 | 13.980 +/- 0.970 |
| 3 | Full attach | n/a | 755.608 +/- 1.819 | 765.460 +/- 2.020 |
| 4 | Parent Request -> Parent Response | n/a | 223.565 +/- 145.762 | 195.810 +/- 133.510 |
| 4 | Parent Response -> Child ID Request | n/a | 526.571 +/- 145.667 | 555.760 +/- 133.510 |
| 4 | Child ID Request -> Child ID Response | n/a | 5.579 +/- 1.241 | 13.930 +/- 1.080 |
| 4 | Full attach | n/a | 755.715 +/- 1.614 | 765.500 +/- 1.760 |

The OTNS-PCAP column is canonical for hardware comparison. The event column is retained only to inspect internal stack behavior. `accepted_runs.csv` records every interval and frame selection; `selection_manifest.json` records every selected and excluded summary. All 300 selected PCAPs are preserved under `pcaps/`.

The PCAP timestamp is the OTNS simulated IEEE 802.15.4 frame time. It aligns packet boundaries with the hardware sniffer analysis but does not model ESP32-C6 execution or physical RF cycle-accurately.
