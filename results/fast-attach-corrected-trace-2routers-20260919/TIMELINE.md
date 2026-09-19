# Corrected plain Fast Attach trace

| Event | OTNS time (s) | Proof |
| --- | ---: | --- |
| Initial attach complete | 180.845556 | attached, Fast Attach disabled |
| Parent deletion | 185.000000 | runner operation timestamp |
| Detached observed | 419.950096 | native role callback |
| Arm completed | 419.950096 | public API returned 0; enabled=1 |
| F=1 Parent Request | 420.344568 | child scan mask 0xa0 |
| Router response scheduled | 420.346944 | scan mask 0xa0; delay 17 ms <= 64 ms |
| Acceptable LQ3 response | 420.368280 | child diagnostic |
| Timer set to zero | 420.368280 | child diagnostic |
| Child ID Request | 420.368280 | enabled=1 |
| Attach complete | 420.377768 | state cleared to enabled=0 |

Canonical PCAP intervals are 19.736, 5.896, 4.456, and 30.088 ms for PR-to-PRsp, PRsp-to-CIDReq, CIDReq-to-CIDRsp, and full attach.
