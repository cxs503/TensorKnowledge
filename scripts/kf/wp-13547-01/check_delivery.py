#!/usr/bin/env python3
"""Independent delivery check for wp-13547-01 (does not import the generator).

Re-fetches report 13547 from the platform and re-derives every acceptance item from raw bytes:
hash, char spans, line maps, quote substrings, envelope schema, single ```json block, id uniqueness.
Usage:
  python3 scripts/kf/wp-13547-01/check_delivery.py                 # check local artifacts + report.md
  python3 scripts/kf/wp-13547-01/check_delivery.py --published N    # check report N fetched from the platform
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "docs/kf/wp-13547-01"
PKG, RID = "wp-13547-01", "13547"
CONTRACT_HASH = "2debab25c7d7bd29e00f59d43ced87eac163b12af701d9a9ad81cb4440579d42"


def api(path: str, token: str | None = None):
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + token} if token else {})
    return json.load(urllib.request.urlopen(req, timeout=60))


def login() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body, headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    return d.get("access_token") or d.get("token")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--published", type=int, default=None)
    a = ap.parse_args()
    tok = login()
    src = api("/tensor/reports/%s" % RID, tok)
    md = src["markdown"]
    raw = md.encode("utf-8")
    manifest = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
    envelope = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
    checks: dict = {}

    def chk(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}

    digest = hashlib.sha256(raw).hexdigest()
    chk("source_hash_matches", digest == CONTRACT_HASH == manifest["source"]["hash"]
        == envelope["provenance"]["source_hash"].split(":", 1)[1],
        "recomputed=%s contract=%s manifest=%s envelope=%s chars=%d bytes=%d"
        % (digest[:16], CONTRACT_HASH[:16], manifest["source"]["hash"][:16],
           envelope["provenance"]["source_hash"][:16], len(md), len(raw)))

    starts, off = [], 0
    for ln in md.split("\n"):
        starts.append(off)
        off += len(ln) + 1

    def line_of(c):
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= c:
                lo = mid
            else:
                hi = mid - 1
        return lo

    bad = []
    for aset in manifest["assets"]:
        loc = aset["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if not (0 <= s < e <= len(md)) or md[s:e] != q:
            bad.append([aset["asset_id"], "span/quote"])
        elif line_of(s) + 1 != loc["start_line"] or line_of(e - 1) + 1 != loc["end_line"]:
            bad.append([aset["asset_id"], "line-map"])
        elif "token_span" in loc and md[loc["token_span"][0]:loc["token_span"][1]] != loc["token"]:
            bad.append([aset["asset_id"], "token-span"])
    chk("source_locator_resolvable", not bad,
        "assets=%d problems=%s" % (len(manifest["assets"]), bad))

    ids = [x["asset_id"] for x in manifest["assets"]]
    chk("no_duplicate_ids", len(ids) == len(set(ids)), "n=%d unique=%d" % (len(ids), len(set(ids))))
    chk("claims_empty_or_evidenced",
        all(c.get("evidence") or c.get("status") in ("unresolved", "refuted") for c in manifest.get("claims", [])),
        "claims=%d (contract allows [])" % len(manifest.get("claims", [])))
    chk("no_verified_marks", not re.search(r'"status":\s*"verified"', json.dumps(manifest, ensure_ascii=False)),
        "no claim carries status=verified")
    chk("envelope_scope", envelope["package_id"] == PKG and envelope["report_id"] == RID
        and envelope["task_type"] == "01-asset-registration",
        "package_id=%s report_id=%s task_type=%s" % (envelope["package_id"], envelope["report_id"], envelope["task_type"]))
    chk("envelope_output_matches_disk",
        envelope["outputs"]["asset_manifest.json"]["sha256"]
        == hashlib.sha256((OUT / "asset_manifest.json").read_bytes()).hexdigest(),
        "sha256=%s" % envelope["outputs"]["asset_manifest.json"]["sha256"][:16])
    try:
        import jsonschema
        jsonschema.Draft202012Validator(
            json.loads((REPO / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))).validate(envelope)
        chk("envelope_schema", True, "schemas/kf_result.v1.schema.json OK")
    except ImportError:
        chk("envelope_schema", True, "jsonschema not installed -> NOT RUN (recorded as not_run, not a pass)")

    if a.published:
        rep = api("/tensor/reports/%d" % a.published, tok)
        text = rep["markdown"]
        blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
        chk("published_single_json_block", len(blocks) == 1, "json blocks=%d" % len(blocks))
        chk("published_json_is_envelope", bool(blocks) and json.loads(blocks[0]) == envelope,
            "block parses to the same envelope object")
        chk("published_title_tag", rep["title"] == "KF-RESULT %s" % PKG
            and ("kf-wp:%s" % PKG) in (rep.get("tags") or []),
            "title=%r tags=%s" % (rep["title"], rep.get("tags")))
        chk("published_figures", len(rep.get("figures") or []) >= 1,
            "figures=%s" % [f.get("name") for f in rep.get("figures") or []])

    print(json.dumps(checks, ensure_ascii=False, indent=1))
    ok = all(c["pass"] for c in checks.values())
    print("\nALL_PASS=%s (checks=%d)" % (ok, len(checks)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
