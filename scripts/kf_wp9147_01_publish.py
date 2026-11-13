"""wp-9147-01: publish the KF-RESULT report to the platform (/tensor/reports).

The markdown payload is the rendered deliverable docs/kf_result_wp-9147-01.md verbatim (it already
contains exactly one fenced json result block); the PNG is attached through figures[].
Title/tags follow the work-package delivery convention: `KF-RESULT wp-9147-01` + tag
`kf-wp:wp-9147-01`.

Falls back through payload shapes if the server rejects the first one and prints every response, so
a failure is diagnosable rather than guessed. Credentials come from env, never hardcoded.

Usage: python3 scripts/kf_wp9147_01_publish.py [--dry-run]
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PKG = pathlib.Path("docs/kf/wp-9147-01")
REPORT_MD = pathlib.Path("docs/kf_result_wp-9147-01.md")
PNG = PKG / "figures" / "asset_locator_map.png"
PAYLOAD = pathlib.Path("/tmp/report_wp-9147-01.json")

TITLE = "KF-RESULT wp-9147-01"
TAGS = ["kf-wp:wp-9147-01", "KF-RESULT", "asset-registration", "EEXI", "CII", "report-9147"]


def call(path: str, body: dict, tok: str | None = None) -> tuple[int, str]:
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:800]


def login() -> str:
    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit(f"login failed: {st} {body[:300]}")
    d = json.loads(body)
    return d.get("access_token") or d.get("token")


def build_payload() -> dict:
    manifest = json.loads((PKG / "asset_manifest.json").read_text())
    acc = json.loads((PKG / "acceptance_check.json").read_text())
    c = manifest["counts"]
    summary = (
        f"wp-9147-01 asset registration for report 9147: markdown sha256 recomputed and equal to the "
        f"contract hash (754d6131…); {c['assets']} assets located by programmatic char spans "
        f"({c['resolved_in_source']} resolved_in_source / {c['referenced_unresolved']} "
        f"referenced_unresolved / {c['declared_absent']} declared_absent); claims intentionally "
        f"empty (no extraction); acceptance {acc['passed']}/{acc['total']} recomputed pass."
    )
    figures = []
    if PNG.exists():
        figures.append({
            "name": PNG.name,
            "caption": "wp-9147-01 asset locator map: char-offset span of each of the 12 registered "
                       "assets over the 1649-char markdown; colour = resolution state "
                       "(green resolved_in_source / orange referenced_unresolved / purple "
                       "declared_absent). Rendered from asset_manifest.json.",
            "png_base64": base64.b64encode(PNG.read_bytes()).decode(),
        })
    return {
        "title": TITLE,
        "summary": summary,
        "scenario_key": manifest["source"]["scenario_key"],
        "mission_id": 15634,
        "tags": TAGS,
        "markdown": REPORT_MD.read_text(encoding="utf-8"),
        "figures": figures,
    }


def main() -> int:
    payload = build_payload()
    PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False))
    print(f"payload: {PAYLOAD} ({PAYLOAD.stat().st_size} bytes, "
          f"{len(payload['figures'])} figure(s), markdown {len(payload['markdown'])} chars)")
    if "--dry-run" in sys.argv:
        print("dry-run: not posting")
        return 0
    tok = login()
    variants = [
        ("full", payload),
        ("no_figures", {k: v for k, v in payload.items() if k != "figures"}),
        ("minimal", {k: payload[k] for k in ("title", "summary", "scenario_key", "mission_id", "markdown")}),
    ]
    for name, body in variants:
        st, resp = call("/tensor/reports", body, tok)
        print(f"[{name}] {st} {resp[:300]}")
        if st in (200, 201):
            d = json.loads(resp)
            print("posted as report_id =", d.get("id"), "| title =", d.get("title"))
            return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())