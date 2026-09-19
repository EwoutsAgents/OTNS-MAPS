# ucast: simulated PCAP and hardware PCAP

Each OTNS column uses exactly 100 accepted runs. Values are mean +/- sample SD in ms.

| Routers | Interval | Internal OTNS event | OTNS PCAP | Hardware PCAP |
| ---: | --- | ---: | ---: | ---: |
| 2 | Parent Request -> Parent Response | 257.794 +/- 147.595 | 247.268 +/- 147.355 | 269.490 +/- 139.720 |
| 2 | Parent Response -> Child ID Request | 0.000 +/- 0.000 | 5.925 +/- 1.274 | 10.480 +/- 0.870 |
| 2 | Child ID Request -> Child ID Response | 10.736 +/- 1.731 | 5.675 +/- 1.316 | 13.840 +/- 0.930 |
| 2 | Full attach | 268.530 +/- 147.880 | 258.868 +/- 147.644 | 293.800 +/- 139.960 |
| 3 | Parent Request -> Parent Response | 511.710 +/- 2398.471 | 501.401 +/- 2398.614 | 251.450 +/- 145.860 |
| 3 | Parent Response -> Child ID Request | 0.000 +/- 0.000 | 5.909 +/- 1.501 | 10.510 +/- 0.890 |
| 3 | Child ID Request -> Child ID Response | 10.746 +/- 2.071 | 5.701 +/- 1.405 | 13.970 +/- 0.830 |
| 3 | Full attach | 522.456 +/- 2398.591 | 513.010 +/- 2398.733 | 275.930 +/- 145.950 |
| 4 | Parent Request -> Parent Response | 270.761 +/- 146.477 | 260.124 +/- 146.876 | 248.300 +/- 138.410 |
| 4 | Parent Response -> Child ID Request | 0.000 +/- 0.000 | 6.393 +/- 2.858 | 10.490 +/- 0.920 |
| 4 | Child ID Request -> Child ID Response | 11.312 +/- 4.196 | 5.855 +/- 1.833 | 13.910 +/- 0.960 |
| 4 | Full attach | 282.073 +/- 146.218 | 272.372 +/- 146.565 | 272.710 +/- 138.370 |

The OTNS-PCAP column is canonical for hardware comparison. The event column is retained only to inspect internal stack behavior. `accepted_runs.csv` records every interval and frame selection; `selection_manifest.json` records every selected and excluded summary. All 300 selected PCAPs are preserved under `pcaps/`.

The PCAP timestamp is the OTNS simulated IEEE 802.15.4 frame time. It aligns packet boundaries with the hardware sniffer analysis but does not model ESP32-C6 execution or physical RF cycle-accurately.
