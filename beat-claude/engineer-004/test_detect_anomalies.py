#!/usr/bin/env python3
"""Tests for detect_anomalies.py using synthetic events, so they stay valid
when the challenge fixture rotates. Run: python3 -m unittest -v"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from detect_anomalies import detect


def ev(event_id, tenant="t-1", anon="anon-a", user=None, type_="page_view",
       ts="2026-06-15T14:00:00.000Z", received="2026-06-15T14:00:00.200Z",
       properties=None, **extra):
    row = {"event_id": event_id, "tenant_id": tenant, "anonymous_id": anon,
           "user_id": user, "type": type_, "ts": ts, "received_at": received,
           "properties": properties or {}}
    row.update(extra)
    return row


def run_detect(lines):
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                     encoding="utf-8") as fh:
        for line in lines:
            fh.write(line if isinstance(line, str) else json.dumps(line))
            fh.write("\n")
        path = Path(fh.name)
    try:
        return detect(path)
    finally:
        path.unlink()


class DetectorTests(unittest.TestCase):
    def test_clean_event_produces_no_findings(self):
        f = run_detect([ev("e1")])
        for key in ("malformed_json", "duplicate_event_id", "legacy_schema",
                    "missing_tenant", "clock_skew", "machine_speed_burst",
                    "pii_in_properties", "in_band_privacy_request",
                    "client_aggregate"):
            self.assertEqual(f[key], [], key)

    def test_malformed_line_is_dead_lettered_not_fatal(self):
        f = run_detect([ev("e1"), '{"event_id":"e2","broken":'])
        self.assertEqual(len(f["malformed_json"]), 1)
        self.assertEqual(f["malformed_json"][0]["line"], 2)
        self.assertEqual(f["events_parsed"], 1)

    def test_exact_retry_vs_conflicting_duplicate(self):
        base = ev("e1")
        retry = dict(base, received_at="2026-06-15T14:00:07.000Z")
        conflict = dict(ev("e2"), properties={"path": "/a"})
        conflict2 = dict(ev("e2"), properties={"path": "/b"})
        f = run_detect([base, retry, conflict, conflict2])
        kinds = {d["event_id"]: d["kind"] for d in f["duplicate_event_id"]}
        self.assertEqual(kinds, {"e1": "exact_retry", "e2": "conflicting_payloads"})

    def test_legacy_schema_aliases(self):
        legacy = {"event_id": "e1", "tenant_id": "t-1", "anonymous_id": "a",
                  "user_id": None, "type": "pageview",
                  "timestamp": "2026-06-15T14:00:00Z",
                  "properties": {"page_path": "/x", "ref": "https://r"}}
        f = run_detect([legacy])
        self.assertEqual(len(f["legacy_schema"]), 1)
        self.assertIn("timestamp", f["legacy_schema"][0]["aliases_used"])
        self.assertEqual(f["legacy_schema"][0]["legacy_type"], "pageview")
        self.assertIn("received_at", f["legacy_schema"][0]["missing_canonical"])

    def test_missing_tenant_quarantined(self):
        f = run_detect([ev("e1", tenant=None)])
        self.assertEqual(f["missing_tenant"], [{"event_id": "e1"}])

    def test_clock_skew_classes(self):
        ahead = ev("e1", ts="2026-06-15T14:01:00.000Z",
                   received="2026-06-15T14:00:00.000Z")
        gross = ev("e2", ts="2026-06-15T15:05:00.000Z",
                   received="2026-06-15T14:00:00.000Z")
        wrong_year = ev("e3", ts="2027-06-15T14:00:00.000Z",
                        received="2026-06-15T14:00:00.000Z")
        f = run_detect([ahead, gross, wrong_year, ev("e4")])
        classes = {d["event_id"]: d["class"] for d in f["clock_skew"]}
        self.assertEqual(classes,
                         {"e1": "client_ahead", "e2": "gross", "e3": "implausible"})

    def test_machine_speed_burst_reports_whole_run(self):
        rows = [
            ev(f"e{i}", anon="anon-bot",
               received=f"2026-06-15T14:00:00.{i * 20:03d}Z",
               properties={"referrer": "https://scanner.example-bot.net"})
            for i in range(4)
        ]
        f = run_detect(rows + [ev("e9", anon="anon-human",
                                  received="2026-06-15T14:09:00.000Z")])
        self.assertEqual(len(f["machine_speed_burst"]), 1)
        burst = f["machine_speed_burst"][0]
        self.assertEqual(burst["event_ids"], ["e0", "e1", "e2", "e3"])
        self.assertTrue(burst["bot_referrer_signal"])

    def test_pii_privacy_and_client_aggregates(self):
        pii = ev("e1", properties={"contact_email": "a@b.com", "phone": "+1-555-0100"})
        privacy = ev("e2", user="u-1", type_="privacy_request",
                     properties={"request": "delete_all_data", "regulation": "GDPR"})
        counter = ev("e3", properties={"count_today": 3})
        f = run_detect([pii, privacy, counter])
        self.assertEqual(f["pii_in_properties"][0]["fields"],
                         ["contact_email:email", "phone:phone"])
        self.assertEqual(f["in_band_privacy_request"][0]["request"], "delete_all_data")
        self.assertEqual(f["client_aggregate"][0]["field"], "count_today")

    def test_identity_map_includes_pre_identify_events(self):
        f = run_detect([
            ev("e1", anon="anon-x"),
            ev("e2", anon="anon-x", user="u-9", type_="identify"),
        ])
        rows = [d for d in f["identity_map"] if d["anonymous_id"] == "anon-x"]
        self.assertEqual(rows[0]["user_id"], "u-9")
        self.assertEqual(rows[0]["anonymous_event_ids"], ["e1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
