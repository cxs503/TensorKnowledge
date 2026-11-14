#!/usr/bin/env python3
"""Pin source report 13272 for KF work package wp-13272-01 (task_type=01-asset-registration).

Work-package boundary: only report_id=13272 is read; no other report is fetched, written
or classified. This step does *not* extract claims and does *not* re-verify anything the
report asserts — it only pins bytes so a downstream工序 can point at them offline.

Outputs (inside the worktree):
  docs/kf/wp-13272-01/source/report_13272.md
      byte-identical UTF-8 encoding of the report record field ``markdown``
  docs/kf/wp-13272-01/source/report_13272.record.json
      every record field except ``markdown`` + recomputed sha256/chars/bytes of markdown
      + ``figure_fetch``: per-declared-figure byte availability (status / bytes / sha256 /
      PNG IHDR size). A declared figure whose bytes are not served is recorded as
      declared_only — never as "author attached nothing".
  docs/kf/wp-13272-01/source/figures/<name>.png
      pinned figure bytes, only when the platform serves them (magic-checked)

Usage:
  python3 scripts/kf_fetch_13272.py            # fetch + pin (idempotent)
  python3 scripts/kf_fetch_13272.py --check    # re-fetch and compare with pinned bytes
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPORT_ID = "13272"
EXPECTED_MISSION_ID = 13764
EXPECTED_SCENARIO_KEY = "green_navigation"

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "docs" / "kf" / "wp-13272-01"
SRCDIR = OUTDIR / "source"
FIGDIR = SRCDIR / "figures"
MD_PATH = SRCDIR / "report_13272.md"
RECORD_PATH = SRCDIR / "report_13272.record.json"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def api_base() -> str:
    return os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _call(path: str, data: dict | None = None, token: str | None = None, raw: bool = False):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        api_base() + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers=headers,
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read()
            return resp.status, (body if raw else json.loads(body.decode("utf-8")))
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()[:400]


def login() -> str:
    user = os.environ.get("TENSOR_AGENT_USER", "")
    password = os.environ.get("TENSOR_AGENT_PASS", "")
    if not user or not password:
        raise SystemExit("TENSOR_AGENT_USER / TENSOR_AGENT_PASS not set")
    status, payload = _call("/auth/login", {"username": user, "password": password})
    token = (payload or {}).get("access_token") if status == 200 else None
    if not token:
        raise SystemExit("login failed: %s %s" % (status, payload))
    return token


def png_size(blob: bytes) -> tuple[int, int] | None:
    """Read the IHDR width/height of a PNG blob (None when not a PNG)."""
    if not blob.startswith(PNG_MAGIC) or len(blob) < 24 or blob[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", blob[16:24])
    return width, height


def fetch_record(token: str) -> dict:
    status, record = _call("/tensor/reports/%s" % REPORT_ID, token=token)
    if status != 200 or not isinstance(record, dict):
        raise SystemExit("GET /tensor/reports/%s -> %s" % (REPORT_ID, status))
    md = record.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("record carries no markdown field")
    if str(record.get("id")) != REPORT_ID:
        raise SystemExit("record id %r != %s (work-package boundary)" % (record.get("id"), REPORT_ID))
    return record


def probe_figures(token: str, record: dict) -> list[dict]:
    """Ask the platform for each declared figure's bytes; record what actually came back."""
    out = []
    for fig in record.get("figures") or []:
        name = fig.get("name") or ""
        entry = {
            "name": name,
            "caption": fig.get("caption"),
            "declared_png_base64_chars": len(fig.get("png_base64") or ""),
            "endpoint": "/tensor/reports/%s/figures/%s" % (REPORT_ID, name),
            "pinned_path": None,
        }
        status, blob = _call(entry["endpoint"], token=token, raw=True)
        entry["http_status"] = status
        if status == 200 and isinstance(blob, bytes):
            size = png_size(blob)
            entry["bytes"] = len(blob)
            entry["sha256"] = hashlib.sha256(blob).hexdigest()
            entry["png_width_height"] = list(size) if size else None
            if size:
                FIGDIR.mkdir(parents=True, exist_ok=True)
                dest = FIGDIR / name
                dest.write_bytes(blob)
                entry["pinned_path"] = str(dest.relative_to(ROOT))
                entry["status"] = "resolved_bytes"
            else:
                entry["status"] = "not_png"
        else:
            entry["body_head"] = blob[:120].decode("utf-8", "replace") if isinstance(blob, bytes) else str(blob)
            entry["status"] = "declared_only"
        out.append(entry)
    return out


def build(record: dict, figure_fetch: list[dict]) -> tuple[str, dict]:
    md = record["markdown"]
    meta = {k: v for k, v in record.items() if k != "markdown"}
    meta["markdown_sha256"] = hashlib.sha256(md.encode("utf-8")).hexdigest()
    meta["markdown_chars"] = len(md)
    meta["markdown_bytes_utf8"] = len(md.encode("utf-8"))
    meta["markdown_lines"] = md.count("\n") + (0 if md.endswith("\n") else 1)
    meta["retrieved_via"] = "GET %s/tensor/reports/%s (Bearer)" % (api_base(), REPORT_ID)
    meta["work_package_boundary"] = "report_id=%s only; no other report read or written" % REPORT_ID
    meta["figure_fetch"] = figure_fetch
    return md, meta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="re-fetch and compare with pinned bytes")
    args = ap.parse_args(argv)

    token = login()
    record = fetch_record(token)
    if record.get("mission_id") is not None and int(record["mission_id"]) != EXPECTED_MISSION_ID:
        print("warning: mission_id %s != expected %s" % (record["mission_id"], EXPECTED_MISSION_ID), file=sys.stderr)
    if record.get("scenario_key") != EXPECTED_SCENARIO_KEY:
        print("warning: scenario_key %r != %r" % (record.get("scenario_key"), EXPECTED_SCENARIO_KEY), file=sys.stderr)

    figure_fetch = probe_figures(token, record)
    md, meta = build(record, figure_fetch)
    blob = md.encode("utf-8")

    if args.check:
        pinned = MD_PATH.read_bytes() if MD_PATH.exists() else b""
        same = pinned == blob
        print(json.dumps({
            "check": "pinned source equals freshly served markdown",
            "equal": same,
            "pinned_bytes": len(pinned),
            "served_bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
        }, ensure_ascii=False))
        return 0 if same else 1

    SRCDIR.mkdir(parents=True, exist_ok=True)
    MD_PATH.write_bytes(blob)
    RECORD_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "pinned": str(MD_PATH.relative_to(ROOT)),
        "sha256": meta["markdown_sha256"],
        "chars": meta["markdown_chars"],
        "bytes": meta["markdown_bytes_utf8"],
        "lines": meta["markdown_lines"],
        "figures": [{k: v for k, v in f.items() if k in ("name", "status", "bytes", "sha256", "png_width_height")}
                    for f in figure_fetch],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())