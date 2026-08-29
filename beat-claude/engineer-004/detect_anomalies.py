#!/usr/bin/env python3
"""Event-stream anomaly detector for the Beat Claude Engineer 004 fixture.

Detects anomaly CLASSES generically (no hardcoded event ids), so it keeps
working when fixtures rotate between hiring rounds:

  1. malformed_json          - lines that fail to parse (dead-letter candidates)
  2. duplicate_event_id      - same (tenant_id, event_id) delivered more than once;
                               distinguishes exact retries from conflicting payloads
  3. legacy_schema           - events using old SDK field names (timestamp/ref/
                               page_path, "pageview") or missing canonical fields
  4. missing_tenant          - events with no tenant attribution (quarantine, do
                               not guess a tenant in a multi-tenant system)
  5. clock_skew              - client ts ahead of server received_at, gross skew,
                               and implausible timestamps (wrong year)
  6. machine_speed_burst     - runs of events from one anonymous_id at inhuman
                               inter-arrival gaps; bot-like referrers noted as a
                               secondary signal, never proof on their own
  7. pii_in_properties       - emails/phone numbers inside event properties
  8. in_band_privacy_request - privacy/deletion requests arriving through the
                               unauthenticated analytics stream
  9. client_aggregate        - client-computed counters (count/total/*_today)
                               that must be re-derived server-side
 10. identity_map            - anon -> user stitching observed via identify
                               events, with the pre-identify event counts that a
                               deletion request would have to cover

Usage:
    python3 detect_anomalies.py path/to/event_sample.jsonl [--json out.json]

Pure stdlib. Deterministic output. Exit code 0 (it is a report, not a gate).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

CANONICAL_FIELDS = ("event_id", "tenant_id", "anonymous_id", "type", "ts", "received_at")
LEGACY_ALIASES = {
    "timestamp": "ts",
    "ref": "referrer",
    "page_path": "path",
}
LEGACY_TYPES = {"pageview": "page_view"}

# Clock-skew thresholds. An SDK batching events client-side can legitimately
# show ts a few seconds before received_at; ts AFTER received_at is causally
# impossible and means the client clock is ahead.
AHEAD_TOLERANCE_S = 2.0        # client ts after received_at beyond this = skew
GROSS_SKEW_S = 30 * 60         # |skew| above 30 minutes = gross misconfiguration
IMPLAUSIBLE_S = 24 * 3600      # ts more than a day from received_at = corrupt

# Machine-speed burst: N+ events from one anonymous_id where every gap between
# consecutive received_at values is under the threshold. 100ms is far below
# human navigation speed across distinct pages.
BURST_MIN_EVENTS = 3
BURST_GAP_S = 0.5

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
AGGREGATE_KEY_RE = re.compile(r"(?:^|_)(?:count|total|sum|num)(?:_|$)|_today$|_this_", re.I)
BOT_REFERRER_RE = re.compile(r"bot|crawler|spider|scanner|scraper", re.I)
PRIVACY_TYPE_RE = re.compile(r"privacy|gdpr|ccpa|erasure|deletion", re.I)


def parse_ts(value):
    """Parse an ISO-8601 timestamp; return None when absent or unparseable."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def load_events(path: Path):
    """Return (events, malformed) where events are (line_no, dict) pairs and
    malformed are findings for lines that failed to parse."""
    events, malformed = [], []
    with path.open(encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, 1):
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                preview = raw.strip()[:80]
                malformed.append({
                    "line": line_no,
                    "error": str(exc),
                    "preview": preview,
                })
                continue
            events.append((line_no, obj))
    return events, malformed


def detect(path: Path) -> dict:
    events, malformed = load_events(path)
    findings = {
        "input": str(path),
        "sha256": sha256_of(path),
        "lines_total": sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip()),
        "events_parsed": len(events),
        "malformed_json": malformed,
        "duplicate_event_id": [],
        "legacy_schema": [],
        "missing_tenant": [],
        "clock_skew": [],
        "machine_speed_burst": [],
        "pii_in_properties": [],
        "in_band_privacy_request": [],
        "client_aggregate": [],
        "identity_map": [],
    }

    # -- duplicates ---------------------------------------------------------
    by_key = defaultdict(list)
    for line_no, ev in events:
        key = (ev.get("tenant_id"), ev.get("event_id"))
        by_key[key].append((line_no, ev))
    for (tenant, event_id), rows in sorted(by_key.items(), key=lambda kv: str(kv[0])):
        if len(rows) < 2 or event_id is None:
            continue
        # Exact retry if everything except received_at matches.
        stripped = [
            json.dumps({k: v for k, v in ev.items() if k != "received_at"}, sort_keys=True)
            for _, ev in rows
        ]
        findings["duplicate_event_id"].append({
            "event_id": event_id,
            "tenant_id": tenant,
            "lines": [line_no for line_no, _ in rows],
            "kind": "exact_retry" if len(set(stripped)) == 1 else "conflicting_payloads",
        })

    # -- schema, tenant, skew, pii, privacy, aggregates ---------------------
    for line_no, ev in events:
        event_id = ev.get("event_id", f"line-{line_no}")

        aliases = sorted(set(ev) & set(LEGACY_ALIASES) | set(ev.get("properties", {}) or {}) & set(LEGACY_ALIASES))
        missing = [f for f in CANONICAL_FIELDS if f not in ev]
        legacy_type = ev.get("type") in LEGACY_TYPES
        if aliases or legacy_type or any(f in ("ts", "received_at") for f in missing):
            findings["legacy_schema"].append({
                "event_id": event_id,
                "aliases_used": aliases,
                "legacy_type": ev.get("type") if legacy_type else None,
                "missing_canonical": missing,
            })

        if ev.get("tenant_id") in (None, ""):
            findings["missing_tenant"].append({"event_id": event_id})

        ts, received = parse_ts(ev.get("ts")), parse_ts(ev.get("received_at"))
        if ts and received:
            skew = (ts - received).total_seconds()
            if abs(skew) > IMPLAUSIBLE_S:
                cls = "implausible"
            elif abs(skew) > GROSS_SKEW_S:
                cls = "gross"
            elif skew > AHEAD_TOLERANCE_S:
                cls = "client_ahead"
            else:
                cls = None
            if cls:
                findings["clock_skew"].append({
                    "event_id": event_id,
                    "skew_seconds": round(skew, 3),
                    "class": cls,
                    "ts": ev.get("ts"),
                    "received_at": ev.get("received_at"),
                })

        props = ev.get("properties") or {}
        hits = []
        for key, value in sorted(props.items()):
            text = str(value)
            if EMAIL_RE.search(text) or "email" in key.lower():
                hits.append(f"{key}:email")
            elif PHONE_RE.fullmatch(text.strip()) or "phone" in key.lower():
                hits.append(f"{key}:phone")
        if hits:
            findings["pii_in_properties"].append({"event_id": event_id, "fields": hits})

        type_str = str(ev.get("type", ""))
        req = str(props.get("request", ""))
        if PRIVACY_TYPE_RE.search(type_str) or PRIVACY_TYPE_RE.search(req) or "delete" in req:
            findings["in_band_privacy_request"].append({
                "event_id": event_id,
                "user_id": ev.get("user_id"),
                "anonymous_id": ev.get("anonymous_id"),
                "request": props.get("request"),
                "regulation": props.get("regulation"),
            })

        for key, value in sorted(props.items()):
            if isinstance(value, (int, float)) and AGGREGATE_KEY_RE.search(key):
                findings["client_aggregate"].append({
                    "event_id": event_id, "field": key, "value": value,
                })

    # -- machine-speed bursts (received_at is server-observed, so it is the
    #    trustworthy clock for gap analysis) --------------------------------
    by_anon = defaultdict(list)
    for line_no, ev in events:
        received = parse_ts(ev.get("received_at"))
        if ev.get("anonymous_id") and received:
            by_anon[ev["anonymous_id"]].append((received, ev))
    for anon, rows in sorted(by_anon.items()):
        rows.sort(key=lambda r: r[0])
        runs, run = [], [rows[0]]
        for prev, cur in zip(rows, rows[1:]):
            if (cur[0] - prev[0]).total_seconds() < BURST_GAP_S:
                run.append(cur)
            else:
                runs.append(run)
                run = [cur]
        runs.append(run)
        for run in runs:
            if len(run) < BURST_MIN_EVENTS:
                continue
            referrers = {
                str((ev.get("properties") or {}).get("referrer", ""))
                for _, ev in run
            }
            findings["machine_speed_burst"].append({
                "anonymous_id": anon,
                "event_ids": [ev.get("event_id") for _, ev in run],
                "max_gap_seconds": round(max(
                    (b[0] - a[0]).total_seconds() for a, b in zip(run, run[1:])
                ), 3),
                "bot_referrer_signal": sorted(
                    r for r in referrers if BOT_REFERRER_RE.search(r)
                ),
            })

    # -- identity stitching -------------------------------------------------
    anon_to_user = {}
    for line_no, ev in events:
        if ev.get("anonymous_id") and ev.get("user_id"):
            anon_to_user.setdefault(ev["anonymous_id"], ev["user_id"])
    for anon, user in sorted(anon_to_user.items()):
        pre_identify = [
            ev.get("event_id") for _, ev in events
            if ev.get("anonymous_id") == anon and not ev.get("user_id")
        ]
        findings["identity_map"].append({
            "anonymous_id": anon,
            "user_id": user,
            "anonymous_event_ids": pre_identify,
        })

    return findings


def render(findings: dict, out=sys.stdout) -> None:
    w = out.write
    w(f"Input:  {findings['input']}\n")
    w(f"SHA256: {findings['sha256']}\n")
    w(f"Lines:  {findings['lines_total']} non-empty, "
      f"{findings['events_parsed']} parsed, "
      f"{len(findings['malformed_json'])} malformed\n\n")

    sections = [
        ("malformed_json", "Malformed JSON (dead-letter, never silent-drop)"),
        ("duplicate_event_id", "Duplicate event ids (dedup at ingest)"),
        ("legacy_schema", "Legacy SDK schema (normalize, SDK cannot change)"),
        ("missing_tenant", "Missing tenant_id (quarantine, do not guess)"),
        ("clock_skew", "Client clock skew (order by received_at)"),
        ("machine_speed_burst", "Machine-speed bursts (tag as bot, keep raw)"),
        ("pii_in_properties", "PII inside properties (mask + deletion scope)"),
        ("in_band_privacy_request", "Privacy requests in-band (verify out-of-band)"),
        ("client_aggregate", "Client-computed aggregates (re-derive server-side)"),
        ("identity_map", "Identity stitching observed (deletion must cover anon events)"),
    ]
    for key, title in sections:
        rows = findings[key]
        w(f"== {title}: {len(rows)}\n")
        for row in rows:
            w(f"   {json.dumps(row, sort_keys=True)}\n")
        w("\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("path", type=Path, help="events .jsonl file")
    parser.add_argument("--json", type=Path, default=None,
                        help="also write findings as JSON to this path")
    args = parser.parse_args(argv)
    if not args.path.exists():
        parser.error(f"no such file: {args.path}")
    findings = detect(args.path)
    render(findings)
    if args.json:
        args.json.write_text(json.dumps(findings, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
        print(f"JSON written to {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
