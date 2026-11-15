#!/usr/bin/env python3
"""wp-12068-01 (report 12068) — pin the source bytes and re-verify the package offline.

Why this exists
---------------
``tests/test_kf_wp12068_01.py`` re-resolves every locator against the *live* platform markdown and
**skips** (never passes) when the API is unreachable.  The consequence is a real hole: on a machine
without platform access the shipped locators/hashes are never re-proved, so the package is only as
trustworthy as the day it was emitted.  This tool closes that hole by

  1. ``snapshot`` — fetch ``GET /api/v1/tensor/reports/12068`` exactly once, pin the ``markdown``
     bytes byte-for-byte inside the package (``source/report-12068.md``) together with their
     sha256/chars/bytes (``source/source_manifest.json``);
  2. ``verify``   — re-derive, from the *pinned* bytes only, every hash and every locator that the
     manifest claims (char span, verbatim quote, 1-based line map, uniqueness, class/resolution
     counts, envelope cross-links), and optionally ``--live`` to re-fetch and report **drift**.

Nothing here writes a ``verified`` or ``published`` claim: publication state stays
``awaiting_pr_merge`` (the platform pr-gate owns promotion), and the tool never reads any report
other than 12068.

Usage
-----
  python3 scripts/kf/wp12068_01_reverify.py snapshot           # needs platform access
  python3 scripts/kf/wp12068_01_reverify.py verify             # offline, always available
  python3 scripts/kf/wp12068_01_reverify.py verify --live      # offline checks + drift check
  python3 scripts/kf/wp12068_01_reverify.py verify --check     # exit 1 on any failing check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "docs" / "kf" / "wp-12068-01"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.json"
SOURCE_DIR = PKG / "source"
PINNED_SOURCE = SOURCE_DIR / "report-12068.md"
SOURCE_MANIFEST = SOURCE_DIR / "source_manifest.json"
REVERIFY = PKG / "reverify.json"

PACKAGE_ID = "wp-12068-01"
REPORT_ID = "12068"
MISSION_ID = 15738
CONTRACT_HASH = "de2f16253ed522c619246898f442983d5a66f3a2bec42c2fe271847a2020cbf0"
CONTRACT_CHARS = 1086
CONTRACT_BYTES = 1113

LINE_CONVENTION = "end_line = 1-based line of the last character (md.count('\\n', 0, end_char - 1) + 1)"


# ----------------------------------------------------------------------------- helpers
def _rel(path) -> str:
    """Path for display: repo-relative when possible, absolute otherwise (temp/tampered trees)."""
    try:
        return str(Path(path).relative_to(REPO))
    except ValueError:
        return str(path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _line_of(md: str, char_index: int) -> int:
    """1-based line number of ``char_index`` (0-based char offset into ``md``)."""
    return md.count("\n", 0, char_index) + 1


def _login(base: str, user: str, password: str) -> str:
    body = json.dumps({"username": user, "password": password}).encode()
    req = urllib.request.Request(
        base + "/auth/login", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    token = payload.get("access_token") or payload.get("token")
    if not token:
        raise SystemExit(f"login returned no token: keys={sorted(payload)}")
    return token


def fetch_report(report_id: str = REPORT_ID) -> dict:
    """Fetch one report record; scope guard: no other report is ever read."""
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    token = _login(base, os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"])
    req = urllib.request.Request(
        f"{base}/tensor/reports/{report_id}", headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        record = json.load(r)
    if str(record.get("id", report_id)) != str(report_id):
        raise SystemExit(f"scope violation: asked for {report_id}, got {record.get('id')}")
    return record


# ----------------------------------------------------------------------------- snapshot
def cmd_snapshot(force: bool = False) -> dict:
    record = fetch_report()
    md = record.get("markdown", "")
    raw = md.encode("utf-8")
    digest = _sha256_bytes(raw)
    if PINNED_SOURCE.exists() and not force:
        if _sha256_bytes(PINNED_SOURCE.read_bytes()) == digest:
            print(f"snapshot already pinned and identical (sha256={digest[:16]}…), nothing to do")
            return json.loads(SOURCE_MANIFEST.read_text())
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    PINNED_SOURCE.write_bytes(raw)
    pinned = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "mission_id": MISSION_ID,
        "endpoint": f"GET /api/v1/tensor/reports/{REPORT_ID}",
        "field": "markdown",
        "path": _rel(PINNED_SOURCE),
        "sha256": digest,
        "chars": len(md),
        "bytes_utf8": len(raw),
        "encoding": "utf-8",
        "lines": md.count("\n") + (0 if md.endswith("\n") else 1),
        "contract_hash": CONTRACT_HASH,
        "contract_hash_matches": digest == CONTRACT_HASH,
        "platform": {
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "tags": record.get("tags"),
            "status": record.get("status"),
            "figures": [
                {"name": f.get("name"), "caption": f.get("caption"),
                 "png_bytes": len(f.get("png_base64") or "")}
                for f in record.get("figures", [])
            ],
        },
        "snapshot_at": _now(),
        "note": ("byte-exact pin of the platform markdown so the 9 locators stay re-derivable "
                 "without platform access; the pin is a copy, never a re-typed transcription"),
    }
    SOURCE_MANIFEST.write_text(json.dumps(pinned, ensure_ascii=False, indent=2) + "\n")
    print(f"pinned {len(raw)} bytes sha256={digest} -> {_rel(PINNED_SOURCE)}")
    return pinned


# ----------------------------------------------------------------------------- verify
def _check(checks: list[dict], cid: str, ok: bool, detail: str) -> bool:
    checks.append({"id": cid, "pass": bool(ok), "detail": detail})
    return bool(ok)


def cmd_verify(live: bool = False, out: Path | None = None) -> dict:
    checks: list[dict] = []
    manifest = json.loads(MANIFEST.read_text())
    envelope = json.loads(ENVELOPE.read_text())
    pinned = json.loads(SOURCE_MANIFEST.read_text()) if SOURCE_MANIFEST.exists() else None

    # -- 1. the pinned source itself
    ok_pin = _check(
        checks, "pinned_source_present",
        PINNED_SOURCE.exists() and pinned is not None,
        f"{_rel(PINNED_SOURCE)} exists={PINNED_SOURCE.exists()} "
        f"source_manifest={SOURCE_MANIFEST.name} exists={pinned is not None}",
    )
    if not ok_pin:
        result = {"package_id": PACKAGE_ID, "report_id": REPORT_ID, "checks": checks,
                  "all_pass": False, "checked_at": _now(),
                  "publication_state": "awaiting_pr_merge",
                  "scope_note": "run `snapshot` with platform access first"}
        _emit(result, out)
        return result

    raw = PINNED_SOURCE.read_bytes()
    md = raw.decode("utf-8")
    digest = _sha256_bytes(raw)
    _check(checks, "pinned_source_hash_matches_pin",
           digest == pinned["sha256"],
           f"recomputed={digest} pin={pinned['sha256']} chars={len(md)} bytes={len(raw)}")
    _check(checks, "pinned_source_matches_contract",
           digest == CONTRACT_HASH and len(md) == CONTRACT_CHARS and len(raw) == CONTRACT_BYTES,
           f"contract hash={CONTRACT_HASH} chars={CONTRACT_CHARS} bytes={CONTRACT_BYTES}; "
           f"got hash={digest} chars={len(md)} bytes={len(raw)}")

    # -- 2. package manifests agree with the pin
    msrc = manifest["source"]
    prov = envelope["provenance"]
    _check(checks, "manifest_source_matches_pin",
           msrc["hash"] == digest and msrc["chars"] == len(md) and msrc["bytes_utf8"] == len(raw),
           f"manifest hash={msrc['hash']} chars={msrc['chars']} bytes={msrc['bytes_utf8']}")
    prov_hash = str(prov["source_hash"]).split(":", 1)[-1]
    _check(checks, "envelope_provenance_matches_pin",
           prov_hash == digest and prov["source_chars"] == len(md)
           and prov["source_bytes_utf8"] == len(raw),
           f"envelope source_hash={prov['source_hash']} chars={prov['source_chars']} "
           f"bytes={prov['source_bytes_utf8']}")
    _check(checks, "report_id_scoped",
           manifest["report_id"] == REPORT_ID == str(envelope["report_id"])
           and pinned["report_id"] == REPORT_ID,
           f"manifest={manifest['report_id']} envelope={envelope['report_id']} pin={pinned['report_id']}")

    # -- 3. every locator re-derived from the pinned bytes
    line_bad, span_bad, quote_bad, uniq_bad = [], [], [], []
    for asset in manifest["assets"]:
        aid = asset["asset_id"]
        loc = asset["locator"]
        s, e = loc["start_char"], loc["end_char"]
        if not (0 <= s < e <= len(md)):
            span_bad.append(f"{aid}:{s}..{e} outside 0..{len(md)}")
            continue
        if md[s:e] != loc["quote"]:
            quote_bad.append(aid)
        if _line_of(md, s) != loc["start_line"] or _line_of(md, e - 1) != loc["end_line"]:
            line_bad.append(f"{aid}: recorded {loc['start_line']}-{loc['end_line']} "
                            f"recomputed {_line_of(md, s)}-{_line_of(md, e - 1)}")
        occurrences = md.count(loc["quote"])
        if loc["quote"] and occurrences != 1:
            uniq_bad.append(f"{aid}: quote occurs {occurrences}x")
        if loc["method"] == "char_span" and s == 0 and e == len(md):
            uniq_bad.append(f"{aid}: char_span degraded to whole document")
    n = len(manifest["assets"])
    _check(checks, "locator_spans_inside_source", not span_bad, f"assets={n} violations={span_bad}")
    _check(checks, "locator_quotes_re_slice_verbatim", not quote_bad,
           f"re-sliced md[start:end] for {n} assets; mismatching={quote_bad}")
    _check(checks, "locator_line_map_recomputed", not line_bad,
           f"convention: {LINE_CONVENTION}; mismatching={line_bad}")
    _check(checks, "locator_quotes_unique_in_source", not uniq_bad,
           f"each quote must occur exactly once in the pinned markdown; problems={uniq_bad}")

    # -- 4. class / resolution bookkeeping is recomputed, not trusted
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for asset in manifest["assets"]:
        by_class[asset["asset_class"]] = by_class.get(asset["asset_class"], 0) + 1
        by_res[asset["resolution"]] = by_res.get(asset["resolution"], 0) + 1
    counts = manifest["counts"]
    _check(checks, "counts_recomputed_from_assets",
           counts["assets"] == n and counts["by_class"] == by_class
           and counts["by_resolution"] == by_res
           and counts["resolved_in_source"] == by_res.get("resolved_in_source", 0)
           and counts["referenced_unresolved"] == by_res.get("referenced_unresolved", 0),
           f"assets={counts['assets']}/{n} by_class={by_class} by_resolution={by_res}")
    ids = [a["asset_id"] for a in manifest["assets"]]
    _check(checks, "asset_ids_unique", len(set(ids)) == len(ids), f"ids={ids}")
    _check(checks, "claims_empty_and_nothing_verified",
           manifest.get("claims") == [] and envelope.get("claims") == []
           and not any(a.get("status") == "verified" for a in manifest["assets"]),
           "registration does not extract claims; no asset carries status='verified'")

    # -- 5. the honest limitation is itself checkable: figures carry no bytes, names absent
    metas = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    names = [a["label"] for a in metas]
    _check(checks, "figures_metadata_only_and_absent_from_body",
           all(a["resolution"] == "referenced_unresolved" for a in metas)
           and names == [f["name"] for f in pinned["platform"]["figures"]]
           and all(not f["png_bytes"] for f in pinned["platform"]["figures"])
           and not any(nm in md for nm in names),
           f"{len(metas)} figures, payload bytes=0, names in body="
           f"{[nm for nm in names if nm in md]}")

    # -- 6. envelope <-> delivered manifest cross-links
    man_raw = MANIFEST.read_bytes()
    env_out = envelope["outputs"]["asset_manifest.json"]
    _check(checks, "delivered_manifest_matches_envelope",
           env_out["sha256"] == _sha256_bytes(man_raw) and env_out["bytes"] == len(man_raw)
           and env_out["asset_count"] == n and env_out["claims"] == 0,
           f"sha256={_sha256_bytes(man_raw)} bytes={len(man_raw)} "
           f"asset_count={env_out['asset_count']}")

    # -- 7. optional drift check against the platform
    drift = {"checked": False, "live_sha256": None, "drift": None, "detail": "not requested"}
    if live:
        try:
            record = fetch_report()
            live_md = record.get("markdown", "")
            live_digest = _sha256_bytes(live_md.encode("utf-8"))
            same = live_digest == digest
            drift = {
                "checked": True,
                "live_sha256": live_digest,
                "live_chars": len(live_md),
                "drift": not same,
                "detail": ("live source identical to the pin" if same else
                           "LIVE SOURCE DRIFTED: the pinned package is stale and must be re-emitted"),
            }
            _check(checks, "live_source_matches_pin", same, drift["detail"])
        except Exception as exc:  # noqa: BLE001 - unreachable platform must not fake a pass
            drift = {"checked": False, "live_sha256": None, "drift": None,
                     "detail": f"live check unavailable: {type(exc).__name__}: {exc}"}
            checks.append({"id": "live_source_matches_pin", "pass": None,
                           "detail": drift["detail"]})

    result = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "mission_id": MISSION_ID,
        "checked_at": _now(),
        "mode": "offline+pinned" + ("+live" if live else ""),
        "pinned_source": {
            "path": _rel(PINNED_SOURCE),
            "sha256": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "snapshot_at": pinned.get("snapshot_at"),
        },
        "line_convention": LINE_CONVENTION,
        "checks": checks,
        "n_checks": len(checks),
        "n_pass": sum(1 for c in checks if c["pass"] is True),
        "n_fail": sum(1 for c in checks if c["pass"] is False),
        "n_skipped": sum(1 for c in checks if c["pass"] is None),
        "all_pass": all(c["pass"] is not False for c in checks),
        "live_drift": drift,
        "publication_state": "awaiting_pr_merge",
        "scope_note": ("offline re-derivation by the producing agent over the pinned source bytes; "
                       "the authoritative verification and the promotion decision remain the "
                       "platform pr-gate's, which flips this package to published only on merge"),
    }
    _emit(result, out)
    return result


def _emit(result: dict, out: Path | None = None) -> None:
    (out or REVERIFY).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in
                      ("n_checks", "n_pass", "n_fail", "n_skipped", "all_pass")}, indent=2))
    for c in result.get("checks", []):
        flag = {True: "PASS", False: "FAIL", None: "SKIP"}[c["pass"]]
        print(f"  [{flag}] {c['id']}: {c['detail']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["snapshot", "verify"])
    ap.add_argument("--force", action="store_true", help="snapshot: overwrite an existing pin")
    ap.add_argument("--live", action="store_true", help="verify: also re-fetch and report drift")
    ap.add_argument("--check", action="store_true", help="verify: exit 1 if any check fails")
    ap.add_argument("--out", type=Path, default=None,
                    help="verify: write the record elsewhere (default docs/kf/wp-12068-01/reverify.json)")
    args = ap.parse_args()
    if args.command == "snapshot":
        cmd_snapshot(force=args.force)
        return 0
    result = cmd_verify(live=args.live, out=args.out)
    if args.check and not result["all_pass"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())