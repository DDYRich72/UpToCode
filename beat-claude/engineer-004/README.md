# Beat Claude — Engineer 004 submission

Candidate submission for Single Grain's [Beat Claude](https://github.com/ericosiu/beat-claude)
hiring challenge, Engineer 004 (Senior Engineer), brief version 2026-07.

| File | What it is |
|---|---|
| `SUBMISSION.md` | The written answer and full 7-part submission packet |
| `detect_anomalies.py` | Operating artifact: stdlib-only event-stream anomaly detector (10 anomaly classes, generic rules) |
| `test_detect_anomalies.py` | 9 unit tests on synthetic events (`python3 -m unittest -v`) |
| `findings.txt` / `findings.json` | Committed detector output on the round's fixture (checksum inside) |

Reproduce:

```bash
git clone https://github.com/ericosiu/beat-claude
python3 detect_anomalies.py beat-claude/challenges/engineer-004/fixtures/event_sample.jsonl
python3 -m unittest -v
```

No dependencies, no network, no credentials. Python 3.10+.
