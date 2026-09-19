# fast-attach: simulated PCAP and hardware PCAP

This corrected campaign accepts only runs proving post-detach arming, F=1, bounded randomized router delay, first-acceptable-LQ3 continuation, one-shot clearing, and a complete PCAP attach sequence. The unarmed historical campaign remains in `../fast-attach-n100-pcap-comparison-20260919/`.

Each OTNS column uses exactly 100 accepted runs. Values are mean +/- sample SD in ms.

| Routers | Interval | Internal OTNS event | OTNS PCAP | Hardware PCAP | OTNS - hardware |
| ---: | --- | ---: | ---: | ---: | ---: |
| 2 | Parent Request -> Parent Response | n/a | 19.254 +/- 8.682 | 26.470 +/- 9.410 | -7.216 ms (-27.3%) |
| 2 | Parent Response -> Child ID Request | n/a | 5.666 +/- 0.922 | 10.880 +/- 0.820 | -5.214 ms (-47.9%) |
| 2 | Child ID Request -> Child ID Response | n/a | 5.672 +/- 1.146 | 13.800 +/- 0.930 | -8.128 ms (-58.9%) |
| 2 | Full attach | n/a | 30.591 +/- 8.792 | 51.140 +/- 9.430 | -20.549 ms (-40.2%) |
| 3 | Parent Request -> Parent Response | n/a | 35.782 +/- 20.395 | 36.340 +/- 20.510 | -0.558 ms (-1.5%) |
| 3 | Parent Response -> Child ID Request | n/a | 6.372 +/- 2.842 | 11.840 +/- 2.450 | -5.468 ms (-46.2%) |
| 3 | Child ID Request -> Child ID Response | n/a | 6.194 +/- 2.430 | 14.420 +/- 2.760 | -8.226 ms (-57.0%) |
| 3 | Full attach | n/a | 48.347 +/- 20.769 | 62.600 +/- 21.220 | -14.253 ms (-22.8%) |
| 4 | Parent Request -> Parent Response | n/a | 28.989 +/- 22.795 | 39.650 +/- 22.950 | -10.661 ms (-26.9%) |
| 4 | Parent Response -> Child ID Request | n/a | 5.959 +/- 1.557 | 12.390 +/- 4.240 | -6.431 ms (-51.9%) |
| 4 | Child ID Request -> Child ID Response | n/a | 6.158 +/- 2.581 | 15.050 +/- 3.200 | -8.892 ms (-59.1%) |
| 4 | Full attach | n/a | 41.106 +/- 23.265 | 67.110 +/- 24.760 | -26.004 ms (-38.7%) |

The OTNS-PCAP column is canonical for hardware comparison. The event column is retained only to inspect internal stack behavior. `accepted_runs.csv` records every interval and frame selection; `selection_manifest.json` records every selected and excluded summary. All 300 selected PCAPs are preserved under `pcaps/`.

The PCAP timestamp is the OTNS simulated IEEE 802.15.4 frame time. It aligns packet boundaries with the hardware sniffer analysis but does not model ESP32-C6 execution or physical RF cycle-accurately.
